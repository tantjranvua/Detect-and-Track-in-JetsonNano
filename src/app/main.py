import time
from pathlib import Path

import cv2
import yaml

from src.detection.face_detector import detect_faces
from src.detection.object_detector import detect_objects
from src.input.camera import open_camera
from src.utils.metrics import FpsCounter
from src.utils.logger import get_logger


def load_config() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "default.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    cfg = load_config()
    logger = get_logger()
    cap = open_camera(
        index=cfg["runtime"]["camera_index"],
        width=cfg["runtime"]["width"],
        height=cfg["runtime"]["height"],
        fps=cfg["runtime"]["input_fps"],
    )

    fps_counter = FpsCounter(window_sec=1.0)
    start = time.perf_counter()

    while True:
        ok, frame = cap.read()
        if not ok:
            logger.warning("Khong doc duoc frame tu camera")
            break
        faces = detect_faces(frame, cfg["detection"]["face_conf_threshold"])
        for face in faces:
            (startX, startY, endX, endY) = face["box"]
            confidence = face["confidence"]
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            text = f"{confidence:.2f}"
            y = startY - 10 if startY - 10 > 10 else startY + 10
            cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
        
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
