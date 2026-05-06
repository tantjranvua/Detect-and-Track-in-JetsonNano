from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "face detector model"
MODEL_PATH = MODEL_DIR / "res10_300x300_ssd_iter_140000.caffemodel"
CONFIG_PATH = MODEL_DIR / "deploy.prototxt.txt"

_net: Optional[cv2.dnn_Net] = None
_warned_missing_model = False
_using_cuda = False


def _load_model() -> Optional[cv2.dnn_Net]:
    global _net
    global _warned_missing_model
    global _using_cuda

    if _net is not None:
        return _net

    if not MODEL_PATH.exists() or not CONFIG_PATH.exists():
        if not _warned_missing_model:
            print(
                "[WARN] Khong tim thay model face detector. "
                f"Can co: {MODEL_PATH} va {CONFIG_PATH}"
            )
            _warned_missing_model = True
        return None

    net = cv2.dnn.readNetFromCaffe(str(CONFIG_PATH), str(MODEL_PATH))
    try:
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        _using_cuda = True
    except cv2.error:
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        _using_cuda = False

    _net = net
    return _net


def detect_faces(frame, conf_threshold: float) -> List[Dict[str, Any]]:
    """
    Hàm thực hiện nhận diện khuôn mặt từ frame hình ảnh.
    Trả về danh sách các dict chứa tọa độ box và độ tin cậy.
    """
    net = _load_model()
    if net is None:
        return []

    h, w = frame.shape[:2]
    # Bước 1: Tiền xử lý - Tạo blob từ hình ảnh (ResNet-10 SSD yêu cầu 300x300)
    # Mean subtraction values cho mô hình này là (104.0, 177.0, 123.0)

    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
                                  (300, 300), (104.0, 177.0, 123.0))
    # Bước 2: Đưa blob vào mạng và thực hiện suy luận (Inference)
    net.setInput(blob)
    try:
        detections = net.forward()
    except cv2.error:
        # Fallback runtime: một số máy nhận set CUDA nhưng lỗi khi forward.
        global _using_cuda
        if _using_cuda:
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            _using_cuda = False
            net.setInput(blob)
            detections = net.forward()
        else:
            raise
    
    results: List[Dict[str, Any]] = []
    # Bước 3: Duyệt qua các kết quả nhận diện
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            results.append({
                "box": (startX, startY, endX, endY),
                "confidence": confidence
            })

    return results