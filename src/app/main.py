import time
from collections import Counter, deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import yaml

from src.control.pid import PID
from src.detection.face_detector import detect_faces
from src.detection.face_recognizer import build_face_recognizer
from src.detection.object_detector import detect_objects
from src.hardware.servo_controller import ServoController
from src.input.camera import open_camera, resolve_camera_runtime
from src.tracking.tracker import TargetTracker
from src.utils.metrics import FpsCounter
from src.utils.logger import get_logger


def load_config() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "default.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def vote_identity(history: Deque[Dict[str, object]], vote_min_count: int) -> Dict[str, object]:
    if not history:
        return {"label": "unknown", "score": 0.0, "known": False}

    known_items = [item for item in history if bool(item.get("known", False))]
    if not known_items:
        return {"label": "unknown", "score": 0.0, "known": False}

    label_counter = Counter(str(item.get("label", "unknown")) for item in known_items)
    top_label, top_count = label_counter.most_common(1)[0]
    if int(top_count) < int(vote_min_count):
        return {"label": "unknown", "score": 0.0, "known": False}

    label_scores = [float(item.get("score", 0.0)) for item in known_items if str(item.get("label", "unknown")) == top_label]
    if not label_scores:
        return {"label": "unknown", "score": 0.0, "known": False}

    return {
        "label": top_label,
        "score": float(sum(label_scores) / len(label_scores)),
        "known": True,
    }


def pick_control_target(
    candidates: List[Dict[str, object]],
    selected_target_id: Optional[int],
    selected_priority: bool,
) -> Optional[Dict[str, object]]:
    if not candidates:
        return None

    if selected_priority and selected_target_id is not None:
        for candidate in candidates:
            if int(candidate["track_id"]) == int(selected_target_id):
                return candidate

    return max(candidates, key=lambda item: float(item.get("priority_score", 0.0)))


def main() -> None:
    cfg = load_config()
    logger = get_logger()
    face_recognizer = build_face_recognizer(cfg)
    tracking_cfg = cfg.get("tracking", {})
    face_tracker = TargetTracker(
        max_missing_frames=int(tracking_cfg.get("max_missing_frames", 15)),
        iou_match_threshold=float(tracking_cfg.get("face_iou_match_threshold", 0.35)),
        smooth_alpha=float(tracking_cfg.get("face_box_smooth_alpha", 0.55)),
    )
    vote_window = max(1, int(tracking_cfg.get("identity_vote_window_frames", 3)))
    vote_min_count = max(1, int(tracking_cfg.get("identity_vote_min_count", 2)))
    vote_min_count = min(vote_window, vote_min_count)
    identity_histories: Dict[int, Deque[Dict[str, object]]] = {}
    face_rec_cfg = cfg.get("detection", {}).get("face_recognize", {})
    console_similarity_log = bool(face_rec_cfg.get("console_similarity_log_enabled", True))
    console_similarity_interval_sec = float(face_rec_cfg.get("console_similarity_log_interval_sec", 0.5))
    last_console_log_ts: Dict[int, float] = {}
    control_cfg = cfg.get("control", {})
    deadband_px = float(control_cfg.get("deadband_px", 15))
    max_step_deg = float(control_cfg.get("max_step_deg", 3))
    control_timeout_sec = float(control_cfg.get("timeout_sec", 1.5))
    control_log_interval_sec = float(control_cfg.get("console_direction_log_interval_sec", 0.5))
    selected_priority = bool(tracking_cfg.get("selected_priority", True))

    pan_cfg = control_cfg.get("pan_pid", {})
    tilt_cfg = control_cfg.get("tilt_pid", {})
    pan_pid = PID(float(pan_cfg.get("kp", 0.012)), float(pan_cfg.get("ki", 0.0)), float(pan_cfg.get("kd", 0.004)))
    tilt_pid = PID(float(tilt_cfg.get("kp", 0.010)), float(tilt_cfg.get("ki", 0.0)), float(tilt_cfg.get("kd", 0.003)))
    servo_controller = ServoController(log_interval_sec=control_log_interval_sec)

    selected_target_id: Optional[int] = None
    virtual_pan_deg = 0.0
    virtual_tilt_deg = 0.0
    last_control_ts = time.perf_counter()
    last_target_seen_ts = last_control_ts
    last_no_target_log_ts = 0.0

    camera_runtime = resolve_camera_runtime(cfg.get("runtime", {}))
    cap = open_camera(
        index=int(camera_runtime["camera_index"]),
        width=int(camera_runtime["width"]),
        height=int(camera_runtime["height"]),
        fps=int(camera_runtime["input_fps"]),
        backend=str(camera_runtime["camera_backend"]),
        use_csi=bool(camera_runtime["camera_use_csi"]),
        gstreamer_pipeline=str(camera_runtime["camera_gstreamer_pipeline"]),
        flip_method=int(camera_runtime["camera_flip_method"]),
    )

    fps_counter = FpsCounter(window_sec=1.0)
    start = time.perf_counter()

    while True:
        ok, frame = cap.read()
        if not ok:
            logger.warning("Khong doc duoc frame tu camera")
            break

        frame_now = time.perf_counter()
        dt = max(1e-3, frame_now - last_control_ts)
        last_control_ts = frame_now

        faces = detect_faces(
            frame,
            cfg["detection"]["face_conf_threshold"],
            cfg["detection"].get("face_nms_iou_threshold", 0.35),
        )
        frame_h, frame_w = frame.shape[:2]
        tracked_faces = face_tracker.update(faces, frame_size=(frame_w, frame_h))

        active_track_ids = set()
        control_candidates: List[Dict[str, object]] = []
        for tracked_face in tracked_faces:
            track_id = int(tracked_face["track_id"])
            active_track_ids.add(track_id)

            if track_id not in identity_histories:
                identity_histories[track_id] = deque(maxlen=vote_window)

            raw_identity = {"label": "unknown", "score": 0.0, "known": False}
            if tracked_face.get("detected", False) and face_recognizer is not None:
                raw_identity = face_recognizer.recognize(frame, tracked_face["box"])
                identity_histories[track_id].append(raw_identity)

            if console_similarity_log and tracked_face.get("detected", False):
                last_ts = float(last_console_log_ts.get(track_id, 0.0))
                if frame_now - last_ts >= max(0.1, console_similarity_interval_sec):
                    pixel_similarity = float(raw_identity.get("pixel_similarity", 0.0))
                    rival_score = float(raw_identity.get("rival_score", -1.0))
                    raw_label = str(raw_identity.get("label", "unknown"))
                    raw_score = float(raw_identity.get("score", 0.0))
                    raw_known = bool(raw_identity.get("known", False))
                    print(
                        "[SIM] "
                        f"track=T{track_id} raw_label={raw_label} "
                        f"known={raw_known} sim={raw_score:.4f} "
                        f"pixel_sim={pixel_similarity:.4f} rival={rival_score:.4f}"
                    )
                    last_console_log_ts[track_id] = frame_now

            identity = vote_identity(identity_histories[track_id], vote_min_count)

            (startX, startY, endX, endY) = tracked_face["box"]
            confidence = float(tracked_face.get("confidence", 0.0))
            missing_frames = int(tracked_face.get("missing_frames", 0))
            detected = bool(tracked_face.get("detected", False))

            color = (0, 255, 0) if identity["known"] else (0, 220, 255)
            thickness = 2 if detected else 1
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, thickness)

            label = str(identity["label"])
            rec_score = float(identity["score"])
            hold_text = "" if detected else f" hold:{missing_frames}"
            text = f"T{track_id} {label} | det:{confidence:.2f} rec:{rec_score:.2f}{hold_text}"
            y = startY - 10 if startY - 10 > 10 else startY + 10
            cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

            if detected:
                area = max(1, (endX - startX) * (endY - startY))
                priority_score = float(area) * (1.2 if bool(identity.get("known", False)) else 1.0)
                control_candidates.append(
                    {
                        "track_id": track_id,
                        "box": tracked_face["box"],
                        "priority_score": priority_score,
                    }
                )

        stale_track_ids = [track_id for track_id in identity_histories.keys() if track_id not in active_track_ids]
        for stale_track_id in stale_track_ids:
            del identity_histories[stale_track_id]
            if stale_track_id in last_console_log_ts:
                del last_console_log_ts[stale_track_id]

        selected_target = pick_control_target(control_candidates, selected_target_id, selected_priority)
        frame_center_x = frame_w / 2.0
        frame_center_y = frame_h / 2.0
        if selected_target is not None:
            selected_target_id = int(selected_target["track_id"])
            last_target_seen_ts = frame_now

            x1, y1, x2, y2 = selected_target["box"]
            target_center_x = (x1 + x2) / 2.0
            target_center_y = (y1 + y2) / 2.0

            err_x = target_center_x - frame_center_x
            err_y = target_center_y - frame_center_y
            pan_error = 0.0 if abs(err_x) <= deadband_px else err_x
            tilt_error = 0.0 if abs(err_y) <= deadband_px else err_y

            pan_step = pan_pid.step(pan_error, dt)
            tilt_step = tilt_pid.step(tilt_error, dt)
            pan_step = max(-max_step_deg, min(max_step_deg, pan_step))
            tilt_step = max(-max_step_deg, min(max_step_deg, tilt_step))

            virtual_pan_deg += pan_step
            virtual_tilt_deg += tilt_step
            servo_controller.set_angle(virtual_pan_deg, virtual_tilt_deg)

            cv2.circle(frame, (int(target_center_x), int(target_center_y)), 4, (255, 255, 0), -1)
            cv2.putText(
                frame,
                f"CTRL T{selected_target_id} ex:{pan_error:.0f} ey:{tilt_error:.0f}",
                (10, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2,
            )
        else:
            if frame_now - last_target_seen_ts >= max(0.2, control_timeout_sec):
                if frame_now - last_no_target_log_ts >= max(0.2, control_log_interval_sec):
                    print("[SERVO-DEMO] cmd=NO_TARGET")
                    last_no_target_log_ts = frame_now
                selected_target_id = None
                pan_pid.reset()
                tilt_pid.reset()
        
        objects = detect_objects(frame, cfg["detection"]["object_conf_threshold"], cfg["detection"]["nms_iou_threshold"])
        for obj in objects:
            (startX, startY, endX, endY) = obj["box"]
            label = obj["label"]
            confidence = obj["confidence"]
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 0, 255), 2)
            text = f"{label}: {confidence:.2f}"
            y = startY - 10 if startY - 10 > 10 else startY + 10
            cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
    
        fps = fps_counter.tick()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Uptime ms: {elapsed_ms:.0f}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Day1 Baseline", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
