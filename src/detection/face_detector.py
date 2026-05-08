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


def _iou_xywh(box_a: List[int], box_b: List[int]) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh

    inter_x1 = max(ax, bx)
    inter_y1 = max(ay, by)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(1, aw * ah)
    area_b = max(1, bw * bh)
    union = area_a + area_b - inter_area
    return float(inter_area) / float(max(1, union))


def _nms_fallback_indices(raw_boxes: List[List[int]], raw_scores: List[float], nms_iou_threshold: float) -> List[int]:
    order = sorted(range(len(raw_scores)), key=lambda i: raw_scores[i], reverse=True)
    kept: List[int] = []
    while order:
        current = order.pop(0)
        kept.append(current)
        order = [
            idx for idx in order
            if _iou_xywh(raw_boxes[current], raw_boxes[idx]) < float(nms_iou_threshold)
        ]
    return kept


def _safe_nms_indices(
    raw_boxes: List[List[int]],
    raw_scores: List[float],
    conf_threshold: float,
    nms_iou_threshold: float,
) -> List[int]:
    try:
        keep_indices = cv2.dnn.NMSBoxes(raw_boxes, raw_scores, conf_threshold, nms_iou_threshold)
    except (cv2.error, SystemError, TypeError):
        return _nms_fallback_indices(raw_boxes, raw_scores, nms_iou_threshold)

    if keep_indices is None:
        return []

    try:
        return [int(i) for i in np.array(keep_indices).reshape(-1)]
    except (ValueError, TypeError):
        return _nms_fallback_indices(raw_boxes, raw_scores, nms_iou_threshold)


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
    cuda_backend = getattr(cv2.dnn, "DNN_BACKEND_CUDA", None)
    cuda_target = getattr(cv2.dnn, "DNN_TARGET_CUDA", None)
    if cuda_backend is not None and cuda_target is not None:
        try:
            net.setPreferableBackend(cuda_backend)
            net.setPreferableTarget(cuda_target)
            _using_cuda = True
        except cv2.error:
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            _using_cuda = False
    else:
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        _using_cuda = False

    _net = net
    return _net


def detect_faces(frame, conf_threshold: float, nms_iou_threshold: float = 0.35) -> List[Dict[str, Any]]:
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
    
    raw_boxes: List[List[int]] = []
    raw_scores: List[float] = []
    # Bước 3: Duyệt qua các kết quả nhận diện
    for i in range(0, detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            startX = max(0, min(w - 1, startX))
            startY = max(0, min(h - 1, startY))
            endX = max(0, min(w, endX))
            endY = max(0, min(h, endY))

            bw = endX - startX
            bh = endY - startY
            if bw <= 0 or bh <= 0:
                continue

            raw_boxes.append([startX, startY, bw, bh])
            raw_scores.append(confidence)

    results: List[Dict[str, Any]] = []
    if not raw_boxes:
        return results

    keep_indices = _safe_nms_indices(raw_boxes, raw_scores, conf_threshold, nms_iou_threshold)
    if len(keep_indices) == 0:
        return results

    for idx in keep_indices:
        x, y, bw, bh = raw_boxes[int(idx)]
        results.append(
            {
                "box": (x, y, x + bw, y + bh),
                "confidence": float(raw_scores[int(idx)]),
            }
        )

    return results