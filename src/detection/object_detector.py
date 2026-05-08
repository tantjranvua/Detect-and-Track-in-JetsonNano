from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "object detector model"
MODEL_PATH = MODEL_DIR / "frozen_inference_graph.pb"
CONFIG_PATH = MODEL_DIR / "ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"

# COCO official IDs (TensorFlow COCO label map, sparse 1..90).
COCO_ID_TO_LABEL: Dict[int, str] = {
    1: "person", 2: "bicycle", 3: "car", 4: "motorcycle", 5: "airplane",
    6: "bus", 7: "train", 8: "truck", 9: "boat", 10: "traffic light",
    11: "fire hydrant", 13: "stop sign", 14: "parking meter", 15: "bench", 16: "bird",
    17: "cat", 18: "dog", 19: "horse", 20: "sheep", 21: "cow",
    22: "elephant", 23: "bear", 24: "zebra", 25: "giraffe", 27: "backpack",
    28: "umbrella", 31: "handbag", 32: "tie", 33: "suitcase", 34: "frisbee",
    35: "skis", 36: "snowboard", 37: "sports ball", 38: "kite", 39: "baseball bat",
    40: "baseball glove", 41: "skateboard", 42: "surfboard", 43: "tennis racket", 44: "bottle",
    46: "wine glass", 47: "cup", 48: "fork", 49: "knife", 50: "spoon",
    51: "bowl", 52: "banana", 53: "apple", 54: "sandwich", 55: "orange",
    56: "broccoli", 57: "carrot", 58: "hot dog", 59: "pizza", 60: "donut",
    61: "cake", 62: "chair", 63: "couch", 64: "potted plant", 65: "bed",
    67: "dining table", 70: "toilet", 72: "tv", 73: "laptop", 74: "mouse",
    75: "remote", 76: "keyboard", 77: "cell phone", 78: "microwave", 79: "oven",
    80: "toaster", 81: "sink", 82: "refrigerator", 84: "book", 85: "clock",
    86: "vase", 87: "scissors", 88: "teddy bear", 89: "hair drier", 90: "toothbrush",
}

# IDs theo nhu cau du an.
ALLOWED_CLASS_IDS: Set[int] = {47, 77}  # cup, cell phone

_net: Optional[cv2.dnn_Net] = None
_warned_missing_model = False
_using_cuda = False


def _iou(box_a: tuple, box_b: tuple) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    union = area_a + area_b - inter
    return inter / max(1, union)


def _containment_ratio(inner: tuple, outer: tuple) -> float:
    ix1, iy1, ix2, iy2 = inner
    ox1, oy1, ox2, oy2 = outer

    x1 = max(ix1, ox1)
    y1 = max(iy1, oy1)
    x2 = min(ix2, ox2)
    y2 = min(iy2, oy2)
    iw = max(0, x2 - x1)
    ih = max(0, y2 - y1)
    inter = iw * ih
    area_inner = max(1, (ix2 - ix1) * (iy2 - iy1))
    return inter / area_inner


def _box_area(box: tuple) -> int:
    x1, y1, x2, y2 = box
    return max(1, (x2 - x1) * (y2 - y1))


def _is_connected(det_a: Dict[str, Any], det_b: Dict[str, Any], iou_thr: float, contain_thr: float) -> bool:
    if det_a["label"] != det_b["label"]:
        return False
    iou_val = _iou(det_a["box"], det_b["box"])
    if iou_val >= iou_thr:
        return True
    if _containment_ratio(det_a["box"], det_b["box"]) >= contain_thr:
        return True
    if _containment_ratio(det_b["box"], det_a["box"]) >= contain_thr:
        return True
    return False


def _build_components(candidates: List[Dict[str, Any]], iou_thr: float, contain_thr: float) -> List[List[int]]:
    n = len(candidates)
    visited = [False] * n
    components: List[List[int]] = []

    for i in range(n):
        if visited[i]:
            continue
        stack = [i]
        visited[i] = True
        comp: List[int] = []

        while stack:
            u = stack.pop()
            comp.append(u)
            for v in range(n):
                if visited[v]:
                    continue
                if _is_connected(candidates[u], candidates[v], iou_thr, contain_thr):
                    visited[v] = True
                    stack.append(v)

        components.append(comp)

    return components


def _suppress_nested_boxes(
    candidates: List[Dict[str, Any]],
    iou_thr: float = 0.45,
    contain_thr: float = 0.85,
    area_ratio_thr: float = 0.60,
) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    components = _build_components(candidates, iou_thr=iou_thr, contain_thr=contain_thr)
    kept: List[Dict[str, Any]] = []

    for comp in components:
        comp_dets = [candidates[idx] for idx in comp]
        # Anchor: highest confidence in the connected component.
        anchor = max(comp_dets, key=lambda d: d["confidence"])
        kept.append(anchor)

        anchor_area = _box_area(anchor["box"])
        for det in comp_dets:
            if det is anchor:
                continue

            # If box is strongly overlapped/contained and has similar size,
            # treat it as duplicate and suppress it.
            iou_val = _iou(det["box"], anchor["box"])
            contain_val = _containment_ratio(det["box"], anchor["box"])
            det_area = _box_area(det["box"])
            area_ratio = min(det_area, anchor_area) / max(det_area, anchor_area)

            is_duplicate = (iou_val >= iou_thr or contain_val >= contain_thr) and area_ratio >= area_ratio_thr
            if not is_duplicate:
                kept.append(det)

    # Final order: stable draw (high confidence first).
    kept.sort(key=lambda d: d["confidence"], reverse=True)
    return kept


def _load_model() -> Optional[cv2.dnn_Net]:
    global _net
    global _warned_missing_model
    global _using_cuda

    if _net is not None:
        return _net

    if not MODEL_PATH.exists() or not CONFIG_PATH.exists():
        if not _warned_missing_model:
            print(
                "[WARN] Khong tim thay model object detector. "
                f"Can co: {MODEL_PATH} va {CONFIG_PATH}"
            )
            _warned_missing_model = True
        return None

    net = cv2.dnn.readNetFromTensorflow(str(MODEL_PATH), str(CONFIG_PATH))

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


def _decode_tf_detections(output: Any, frame_shape: Tuple[int, int, int], conf_threshold: float) -> List[Dict[str, Any]]:
    h, w = frame_shape[:2]
    results: List[Dict[str, Any]] = []

    if output is None or not hasattr(output, "shape"):
        return results

    # SSD TensorFlow output layout: [1, 1, N, 7]
    # fields: [image_id, class_id, confidence, x1, y1, x2, y2]
    if len(output.shape) != 4 or output.shape[3] < 7:
        return results

    for i in range(output.shape[2]):
        confidence = float(output[0, 0, i, 2])
        if confidence < float(conf_threshold):
            continue

        class_id = int(output[0, 0, i, 1])
        if class_id not in ALLOWED_CLASS_IDS:
            continue

        x1 = int(float(output[0, 0, i, 3]) * w)
        y1 = int(float(output[0, 0, i, 4]) * h)
        x2 = int(float(output[0, 0, i, 5]) * w)
        y2 = int(float(output[0, 0, i, 6]) * h)

        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(0, min(w, x2))
        y2 = max(0, min(h, y2))
        if x2 <= x1 or y2 <= y1:
            continue

        results.append(
            {
                "type": "object",
                "label": COCO_ID_TO_LABEL.get(class_id, "unknown"),
                "box": (x1, y1, x2, y2),
                "confidence": confidence,
            }
        )

    return results


def _detect_objects_legacy(net: cv2.dnn_Net, frame: Any, conf_threshold: float, nms_threshold: float) -> List[Dict[str, Any]]:
    blob = cv2.dnn.blobFromImage(
        frame,
        scalefactor=1.0 / 127.5,
        size=(320, 320),
        mean=(127.5, 127.5, 127.5),
        swapRB=True,
        crop=False,
    )

    net.setInput(blob)
    try:
        output = net.forward()
    except cv2.error:
        global _using_cuda
        if _using_cuda:
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            _using_cuda = False
            net.setInput(blob)
            output = net.forward()
        else:
            raise

    decoded = _decode_tf_detections(output, frame.shape, conf_threshold)
    return _suppress_nested_boxes(decoded, iou_thr=max(0.35, nms_threshold), contain_thr=0.8)


def detect_objects(frame, conf_threshold: float, nms_threshold: float) -> List[Dict[str, Any]]:
    net = _load_model()
    if net is None:
        return []

    if not hasattr(cv2, "dnn_DetectionModel"):
        return _detect_objects_legacy(net, frame, conf_threshold, nms_threshold)

    model = cv2.dnn_DetectionModel(net)
    model.setInputParams(size=(320, 320), scale=1.0 / 127.5, mean=(127.5, 127.5, 127.5), swapRB=True)

    try:
        class_ids, confidences, boxes = model.detect(frame, confThreshold=conf_threshold, nmsThreshold=nms_threshold)
    except cv2.error:
        global _using_cuda
        if _using_cuda:
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            _using_cuda = False
            class_ids, confidences, boxes = model.detect(frame, confThreshold=conf_threshold, nmsThreshold=nms_threshold)
        else:
            raise

    if class_ids is None or len(class_ids) == 0:
        return []

    results: List[Dict[str, Any]] = []
    for class_id, confidence, box in zip(class_ids.flatten(), confidences.flatten(), boxes):
        class_id = int(class_id)
        if class_id not in ALLOWED_CLASS_IDS:
            continue

        x, y, w, h = [int(v) for v in box]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = max(0, x + w)
        y2 = max(0, y + h)

        results.append(
            {
                "type": "object",
                "label": COCO_ID_TO_LABEL.get(class_id, "unknown"),
                "box": (x1, y1, x2, y2),
                "confidence": float(confidence),
            }
        )

    # A second pass helps reduce duplicated / nested boxes that still remain
    # after model.detect() NMS in noisy webcam streams.
    return _suppress_nested_boxes(results, iou_thr=max(0.35, nms_threshold), contain_thr=0.8)
