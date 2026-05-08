#!/usr/bin/env bash
# =============================================================================
# convert_to_trt.sh — Chuyển đổi model sang TensorRT engine trên Jetson Nano
# Chạy MỘT LẦN trên Jetson Nano sau khi cài JetPack.
# Sau khi hoàn thành, đặt use_tensorrt: true trong config/default.yaml.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_ROOT/models"
TRTEXEC="/usr/src/tensorrt/bin/trtexec"

echo "=== Kiểm tra môi trường ==="
if [ ! -f "$TRTEXEC" ]; then
    echo "[LỖI] Không tìm thấy trtexec tại $TRTEXEC"
    echo "      Đảm bảo JetPack đã được cài đặt đầy đủ."
    exit 1
fi
python3 -c "import tensorrt; print('[OK] TensorRT', tensorrt.__version__)" || {
    echo "[LỖI] tensorrt không import được. Chạy: sudo apt-get install python3-libnvinfer-dev"
    exit 1
}
python3 -c "import pycuda; print('[OK] pycuda', pycuda.VERSION)" 2>/dev/null || {
    echo "[WARN] pycuda chưa cài. Chạy: pip install pycuda"
    echo "       Tiếp tục convert engine (không cần pycuda để convert)..."
}

echo ""
echo "=== [1/2] Chuyển đổi Face Detector (ResNet-10 SSD Caffe → TRT FP16) ==="
FACE_MODEL="$MODELS_DIR/face detector model/res10_300x300_ssd_iter_140000.caffemodel"
FACE_CONFIG="$MODELS_DIR/face detector model/deploy.prototxt.txt"
FACE_ENGINE="$MODELS_DIR/face_detector.engine"

if [ ! -f "$FACE_MODEL" ] || [ ! -f "$FACE_CONFIG" ]; then
    echo "[LỖI] Không tìm thấy file Caffe model. Kiểm tra lại models/face detector model/"
    exit 1
fi

echo "  Input:  $FACE_MODEL"
echo "  Output: $FACE_ENGINE"
"$TRTEXEC" \
    --deploy="$FACE_CONFIG" \
    --model="$FACE_MODEL" \
    --output=prob \
    --saveEngine="$FACE_ENGINE" \
    --fp16 \
    2>&1 | tail -20

echo "[OK] Face detector engine đã tạo: $FACE_ENGINE"

echo ""
echo "=== [2/2] Chuyển đổi Object Detector (SSD MobileNet V2 COCO) ==="
# Phần này yêu cầu file ONNX đã được tạo trước từ TF frozen graph.
# Nếu chưa có file ONNX, chạy các bước sau trên laptop (cần Python 3.7+):
#
#   pip install tf2onnx tensorflow==2.x
#   python3 -m tf2onnx.convert \
#       --saved-model <path_to_ssd_mobilenet_v2_coco_saved_model> \
#       --output models/object_detector_v2.onnx \
#       --opset 11
#
# Hoặc tải ONNX Model Zoo: https://github.com/onnx/models
#   Model: ssd-mobilenetv1-10.onnx (COCO 80 classes)

OBJECT_ONNX="$MODELS_DIR/object_detector.onnx"
OBJECT_ENGINE="$MODELS_DIR/object_detector.engine"

if [ ! -f "$OBJECT_ONNX" ]; then
    echo "[SKIP] Không tìm thấy $OBJECT_ONNX"
    echo "       Xem hướng dẫn trong script để tạo file ONNX trước."
    echo "       Face detector TRT đã sẵn sàng. Bật bằng cách sửa config/default.yaml:"
    echo "         use_tensorrt: true"
    echo "       (Object detector sẽ tiếp tục bị tắt cho đến khi có engine)"
else
    echo "  Input:  $OBJECT_ONNX"
    echo "  Output: $OBJECT_ENGINE"
    "$TRTEXEC" \
        --onnx="$OBJECT_ONNX" \
        --saveEngine="$OBJECT_ENGINE" \
        --fp16 \
        2>&1 | tail -20
    echo "[OK] Object detector engine đã tạo: $OBJECT_ENGINE"
fi

echo ""
echo "=== HOÀN THÀNH ==="
echo "Các bước tiếp theo:"
echo "  1. Sửa config/default.yaml:"
echo "       use_tensorrt: true"
echo "  2. Chạy lại ứng dụng: bash scripts/run_day1.sh"
echo "  3. Kiểm tra console thấy '[INFO] TRT face detector da tai: ...'"
echo ""
echo "Lưu ý:"
echo "  - File .engine chỉ dùng được trên Jetson Nano này (device-specific)."
echo "  - Không commit file .engine vào git."
