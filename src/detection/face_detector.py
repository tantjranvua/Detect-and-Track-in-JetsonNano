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
_trt_face_session = None  # Được khởi tạo bởi configure_face_detector()


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


# ---------------------------------------------------------------------------
# TensorRT inference (chỉ hoạt động khi tensorrt + pycuda được cài trên Jetson)
# ---------------------------------------------------------------------------

class _TRTFaceSession:
    """Wrapper TensorRT cho ResNet-10 SSD face detector.

    Chỉ dùng trên Jetson Nano sau khi đã chạy scripts/convert_to_trt.sh.
    Tương thích TensorRT 7.x (JetPack 4.4) và 8.x (JetPack 4.6).
    """

    def __init__(self, engine_path: str) -> None:
        import tensorrt as trt  # type: ignore
        import pycuda.driver as cuda  # type: ignore
        import pycuda.autoinit  # noqa: F401  # type: ignore

        self._cuda = cuda
        self._trt = trt
        logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f:
            engine = trt.Runtime(logger).deserialize_cuda_engine(f.read())
        self._context = engine.create_execution_context()

        self._h_inputs: list = []
        self._h_outputs: list = []
        self._d_buffers: list = []

        for i in range(engine.num_bindings):
            shape = engine.get_binding_shape(i)
            dtype = trt.nptype(engine.get_binding_dtype(i))
            size = max(1, abs(int(trt.volume(shape))))
            h_buf = cuda.pagelocked_empty(size, dtype)
            d_buf = cuda.mem_alloc(h_buf.nbytes)
            self._d_buffers.append(int(d_buf))
            entry = {"host": h_buf, "device": d_buf, "shape": shape}
            if engine.binding_is_input(i):
                self._h_inputs.append(entry)
            else:
                self._h_outputs.append(entry)

    def run(self, blob: np.ndarray) -> np.ndarray:
        """Chạy inference và trả về numpy array (1, 1, N, 7)."""
        cuda = self._cuda
        h_in = self._h_inputs[0]["host"]
        d_in = self._h_inputs[0]["device"]
        np.copyto(h_in, blob.ravel().astype(h_in.dtype))
        cuda.memcpy_htod(d_in, h_in)
        self._context.execute_v2(bindings=self._d_buffers)
        h_out = self._h_outputs[0]["host"]
        d_out = self._h_outputs[0]["device"]
        cuda.memcpy_dtoh(h_out, d_out)
        return np.array(h_out).reshape(self._h_outputs[0]["shape"])


def configure_face_detector(detection_cfg: dict) -> None:
    """Khởi tạo TRT engine nếu use_tensorrt=true và file .engine tồn tại.

    Gọi một lần trong main() ngay sau load_config().
    Nếu TRT không khả dụng hoặc engine không tìm thấy, tự động fallback về cv2.dnn.
    """
    global _trt_face_session
    if not detection_cfg.get("use_tensorrt", False):
        return

    engine_path = Path(__file__).resolve().parents[2] / detection_cfg.get(
        "face_engine_path", "models/face_detector.engine"
    )
    if not engine_path.exists():
        print(f"[WARN] TRT face engine khong tim thay: {engine_path}. Dung lai cv2.dnn.")
        return

    try:
        _trt_face_session = _TRTFaceSession(str(engine_path))
        print(f"[INFO] TRT face detector da tai: {engine_path}")
    except Exception as exc:
        print(f"[WARN] Khong the khoi tao TRT face detector: {exc}. Dung lai cv2.dnn.")
        _trt_face_session = None


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
    Ưu tiên TRT nếu đã configure, ngược lại dùng cv2.dnn.
    """
    # --- TRT path ---
    if _trt_face_session is not None:
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
        )
        try:
            output = _trt_face_session.run(blob)
        except Exception as exc:
            print(f"[WARN] TRT face inference loi: {exc}. Dung lai cv2.dnn.")
            # Fall through to cv2.dnn path below
        else:
            # Output: (1, 1, N, 7) same layout as Caffe net.forward()
            if output.ndim == 1:
                n = len(output) // 7
                output = output.reshape(1, 1, n, 7)
            raw_boxes: List[List[int]] = []
            raw_scores: List[float] = []
            for i in range(output.shape[2]):
                confidence = float(output[0, 0, i, 2])
                if confidence > conf_threshold:
                    box = output[0, 0, i, 3:7] * np.array([w, h, w, h])
                    startX, startY, endX, endY = box.astype("int")
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
            if raw_boxes:
                for idx in _safe_nms_indices(raw_boxes, raw_scores, conf_threshold, nms_iou_threshold):
                    x, y, bw, bh = raw_boxes[int(idx)]
                    results.append({
                        "box": (x, y, x + bw, y + bh),
                        "confidence": float(raw_scores[int(idx)]),
                    })
            return results

    # --- cv2.dnn path (CPU / OpenCV CUDA) ---
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