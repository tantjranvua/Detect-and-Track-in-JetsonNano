import argparse
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import yaml

from src.detection.face_detector import detect_faces
from src.input.camera import open_camera, resolve_camera_runtime


def load_config() -> Dict[str, object]:
    config_path = Path(__file__).resolve().parents[2] / "config" / "default.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args(default_gallery_dir: str, default_count: int, default_cooldown_ms: int) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture face gallery images from camera")
    parser.add_argument("--person", required=True, help="Nguoi can thu thap anh gallery")
    parser.add_argument("--count", type=int, default=default_count, help="So anh can luu")
    parser.add_argument("--gallery-dir", default=default_gallery_dir, help="Thu muc gallery")
    parser.add_argument("--cooldown-ms", type=int, default=default_cooldown_ms, help="Khoang nghi toi thieu giua 2 lan luu")
    return parser.parse_args()


def resolve_gallery_dir(gallery_dir: str) -> Path:
    path = Path(gallery_dir)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[2] / path


def clamp_box(box: Tuple[int, int, int, int], frame_shape: Tuple[int, int, int]) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    h, w = frame_shape[:2]
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))
    return x1, y1, x2, y2


def pick_primary_face(faces: list) -> Optional[Dict[str, object]]:
    if not faces:
        return None

    def score(face: Dict[str, object]) -> float:
        x1, y1, x2, y2 = face["box"]
        area = max(1, (x2 - x1) * (y2 - y1))
        confidence = float(face.get("confidence", 0.0))
        return area * max(0.1, confidence)

    return max(faces, key=score)


def main() -> None:
    cfg = load_config()
    face_rec_cfg = cfg.get("detection", {}).get("face_recognize", {})
    default_gallery_dir = str(face_rec_cfg.get("gallery_dir", "data/face_gallery"))
    default_count = int(face_rec_cfg.get("capture_default_count", 20))
    default_cooldown_ms = int(face_rec_cfg.get("capture_cooldown_ms", 300))
    args = parse_args(default_gallery_dir, default_count, default_cooldown_ms)

    person_name = args.person.strip().replace(" ", "_")
    if not person_name:
        raise ValueError("--person khong duoc rong")

    gallery_root = resolve_gallery_dir(args.gallery_dir)
    person_dir = gallery_root / person_name
    person_dir.mkdir(parents=True, exist_ok=True)

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

    if not cap.isOpened():
        raise RuntimeError("Khong mo duoc camera")

    print(f"[INFO] Capture gallery cho: {person_name}")
    print(f"[INFO] Thu muc luu: {person_dir}")
    print("[INFO] Phim tat: S=save, Q/ESC=thoat")

    saved = 0
    last_save_ms = 0.0
    conf_thr = float(cfg.get("detection", {}).get("face_conf_threshold", 0.6))

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[WARN] Khong doc duoc frame tu camera")
            break

        faces = detect_faces(frame, conf_thr)
        primary_face = pick_primary_face(faces)

        if primary_face is not None:
            x1, y1, x2, y2 = clamp_box(primary_face["box"], frame.shape)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "Primary face", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Khong tim thay khuon mat", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2)

        cv2.putText(frame, f"Person: {person_name}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Saved: {saved}/{args.count}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Capture Face Gallery", frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (27, ord("q")):
            break

        if key == ord("s") and primary_face is not None:
            now_ms = time.perf_counter() * 1000.0
            if now_ms - last_save_ms < args.cooldown_ms:
                continue

            x1, y1, x2, y2 = clamp_box(primary_face["box"], frame.shape)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = frame[y1:y2, x1:x2].copy()
            ts = int(time.time() * 1000)
            file_path = person_dir / f"{person_name}_{ts}.jpg"
            ok_write = cv2.imwrite(str(file_path), crop)
            if ok_write:
                saved += 1
                last_save_ms = now_ms
                print(f"[INFO] Da luu: {file_path.name} ({saved}/{args.count})")

        if saved >= args.count:
            print("[INFO] Da dat so anh muc tieu")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
