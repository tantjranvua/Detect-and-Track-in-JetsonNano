# Dự án Nhận Diện Khuôn Mặt Và Vật Thể (Jetson Nano / Windows)

## 1. Dự án này làm gì?
Dự án hiện tại tập trung vào:
- Nhận diện khuôn mặt từ camera.
- Nhận diện một số vật thể ưu tiên (mặc định: `cup`, `cell phone`).
- Gán danh tính khuôn mặt theo gallery cục bộ (`data/face_gallery`).
- Theo dõi nhiều khuôn mặt theo `track_id` để giảm nhấp nháy box.
- Ổn định tên hiển thị bằng voting theo từng track (cửa sổ 3 frame).

Trạng thái hiện tại:
- Chưa tích hợp điều khiển servo thực tế.
- Phần điều khiển chỉ ở mức mô phỏng/chuẩn bị.

## 2. Cấu trúc thư mục chính
- `src/app`: điểm vào chương trình (`main.py`) và công cụ thu gallery (`capture_gallery.py`).
- `src/detection`: face detector, face recognizer, object detector.
- `src/tracking`: tracker theo `track_id` cho khuôn mặt.
- `src/input`: mở camera.
- `src/control`, `src/hardware`: khung chuẩn bị cho điều khiển pan/tilt.
- `config/default.yaml`: toàn bộ thông số runtime, detection, tracking.
- `scripts/run_day1.cmd`: lệnh chạy chính.
- `scripts/capture_gallery.cmd`: lệnh thu thập ảnh gallery.
- `data/face_gallery`: dữ liệu ảnh mẫu theo từng người.

## 3. Yêu cầu môi trường
- Hệ điều hành: Windows (đã có script `.cmd` sẵn).
- Python: 3.6 (theo script hiện tại).
- Dependency chính trong `requirements.txt`:
	- `opencv-python==4.5.5.64`
	- `numpy==1.19.5`
	- `PyYAML==6.0.1`
	- `psutil==5.9.5`

## 4. Khởi động nhanh cho người mới
### Bước 1: Chạy chương trình lần đầu
Mở terminal tại thư mục dự án, chạy:

```bat
scripts\run_day1.cmd
```

Script sẽ tự:
1. Tạo `.venv` bằng Python 3.6 nếu chưa có.
2. Kiểm tra version Python trong `.venv`.
3. Kiểm tra và cài thư viện từ `requirements.txt` nếu còn thiếu.
4. Chạy ứng dụng `python -m src.app.main`.

### Bước 2: Thử camera
Khi cửa sổ hiển thị mở lên:
1. Đưa mặt vào khung hình.
2. Kiểm tra có box khuôn mặt và text nhận diện không.
3. Nhấn `Q` hoặc `ESC` để thoát.

## 5. Thu thập dữ liệu khuôn mặt (gallery)
### Cấu trúc dữ liệu
Mỗi người là một thư mục con:

```text
data/face_gallery/
	Tan/
		Tan_....jpg
	Binh/
		Binh_....jpg
```

### Cách thu ảnh nhanh
Chạy lệnh:

```bat
scripts\capture_gallery.cmd <ten_nguoi> <so_anh>
```

Ví dụ:

```bat
scripts\capture_gallery.cmd Tan 30
```

Trong cửa sổ capture:
- `S`: lưu ảnh khuôn mặt chính.
- `Q` hoặc `ESC`: thoát.

Khuyến nghị dữ liệu:
1. Mỗi người 20-50 ảnh.
2. Có ảnh trực diện, nghiêng trái/phải, thay đổi ánh sáng nhẹ.
3. Có một số ảnh che một phần (tay, khẩu trang nhẹ) để tăng độ bền.

## 6. Luồng xử lý hiện tại
1. `src/app/main.py` đọc `config/default.yaml`.
2. Face detector phát hiện khuôn mặt và lọc trùng bằng NMS.
3. Tracker gán `track_id` (T1, T2, ...), làm mượt box, giữ track ngắn hạn khi mất detection.
4. Face recognizer tính điểm tương đồng với gallery.
5. Voting theo từng track (mặc định 3 frame, cần tối thiểu 2 phiếu) để ổn định tên.
6. Vẽ overlay + in log debug similarity ra console.

## 7. Ý nghĩa các chỉ số log `[SIM]`
Ví dụ:

```text
[SIM] track=T1 raw_label=Tan known=True sim=0.8451 pixel_sim=0.7920 rival=0.7013
```

- `sim`: điểm tương đồng chính (cosine trên embedding) dùng cho quyết định known/unknown.
- `pixel_sim`: điểm tương đồng mức pixel (gray đã chuẩn hóa), dùng để debug chất lượng frame.
- `rival`: điểm cao nhất của nhãn đối thủ (label khác) để kiểm tra margin.

Diễn giải nhanh:
1. `sim` thấp: frame xấu, che mặt, góc quá khó hoặc box không tốt.
2. `sim` cao nhưng `rival` sát: dễ dao động/unknown do khó phân biệt nhãn.
3. `pixel_sim` tụt mạnh khi che mặt: đúng dấu hiệu mất thông tin ảnh.

## 8. Các tham số quan trọng trong `config/default.yaml`
### Runtime
- `runtime.camera_index`: camera index.
- `runtime.width`, `runtime.height`, `runtime.input_fps`: chất lượng stream đầu vào.

### Face detection / recognition
- `detection.face_conf_threshold`: ngưỡng detector khuôn mặt.
- `detection.face_nms_iou_threshold`: ngưỡng NMS để gộp box trùng.
- `detection.face_recognize.similarity_threshold`: ngưỡng `sim`.
- `detection.face_recognize.score_margin`: khoảng cách tối thiểu giữa `sim` và `rival`.
- `detection.face_recognize.min_face_size`: bỏ qua mặt quá nhỏ.
- `detection.face_recognize.console_similarity_log_enabled`: bật/tắt log `[SIM]`.
- `detection.face_recognize.console_similarity_log_interval_sec`: chu kỳ in log.

### Tracking / voting
- `tracking.max_missing_frames`: số frame được phép mất detection trước khi xóa track.
- `tracking.face_iou_match_threshold`: ngưỡng ghép detection vào track.
- `tracking.face_box_smooth_alpha`: độ mượt box.
- `tracking.identity_vote_window_frames`: cửa sổ voting theo frame.
- `tracking.identity_vote_min_count`: số phiếu tối thiểu để chốt tên.

## 9. Quy trình tuning từng bước (khuyến nghị)
### Bước A: Ổn định detection trước
1. Chỉnh `face_conf_threshold` để bớt box nhiễu.
2. Chỉnh `face_nms_iou_threshold` để không sinh nhiều track giả trên cùng 1 mặt.

### Bước B: Ổn định recognize
1. Quan sát log `[SIM]`.
2. Nếu hay `unknown` dù đúng người: giảm nhẹ `similarity_threshold` (ví dụ 0.82 -> 0.80).
3. Nếu hay nhầm người: tăng `score_margin` hoặc bổ sung gallery tốt hơn.

### Bước C: Ổn định trải nghiệm theo thời gian
1. Tăng `identity_vote_min_count` nếu muốn ít nhảy tên hơn.
2. Giảm `identity_vote_min_count` nếu muốn phản ứng nhanh hơn sau khi bị che mặt.
3. Điều chỉnh `max_missing_frames` nếu cần giữ track lâu hơn khi bị che tạm thời.

## 10. Các hiện tượng thường gặp và cách xử lý
### Hiện tượng 1: `T1 unknown` kéo dài
1. Kiểm tra gallery có đủ ảnh và đúng thư mục người đó chưa.
2. Giảm nhẹ `similarity_threshold`.
3. Đảm bảo ánh sáng đủ và khuôn mặt không quá nhỏ.

### Hiện tượng 2: che mặt 1 phần thì mất tên khoảng 1 giây rồi nhận lại
1. Đây là hành vi có thể xảy ra do score dao động + voting theo cửa sổ.
2. Giảm `identity_vote_min_count` nếu muốn hồi tên nhanh hơn.
3. Bổ sung ảnh gallery có trạng thái che nhẹ để tăng độ bền.

### Hiện tượng 3: xuất hiện nhiều track T1/T2/T3 trên cùng 1 người
1. Kiểm tra ngưỡng `face_nms_iou_threshold`.
2. Tăng nhẹ `face_iou_match_threshold` để tracker ghép ổn định hơn.

## 11. Hướng dẫn chỉnh sửa code cho người mới
### Chỉnh luồng chính
- File chính: `src/app/main.py`.
- Tại đây bạn có thể thay đổi:
	- Luật voting.
	- Cách hiển thị overlay.
	- Cách in log debug.

### Chỉnh nhận diện khuôn mặt
- Detector: `src/detection/face_detector.py`.
- Recognizer: `src/detection/face_recognizer.py`.

### Chỉnh tracking
- Tracker: `src/tracking/tracker.py`.
- Dùng để quản lý `track_id`, làm mượt box, giữ track khi mất detection ngắn hạn.

## 12. Lệnh vận hành nhanh
### Chạy ứng dụng

```bat
scripts\run_day1.cmd
```

### Thu gallery

```bat
scripts\capture_gallery.cmd Tan 30
```

## 13. Giới hạn hiện tại và roadmap ngắn
Giới hạn hiện tại:
1. Face recognizer đang dùng embedding đơn giản (gray + edge), chưa phải model SOTA.
2. Chưa có quality gate rõ ràng (blur/occlusion) trước recognize.
3. Chưa tích hợp servo điều khiển thực.

Roadmap đề xuất:
1. Thêm quality gate (blur, diện tích mặt, mức che khuất) trước recognize.
2. Thêm cơ chế giữ nhãn ngắn hạn khi che mặt nhẹ để giảm nhấp nháy tên.
3. Nâng cấp embedding model (ArcFace/FaceNet on-device).
4. Sau khi ổn định vision mới nối sang điều khiển pan/tilt phần cứng.

## 14. Tài liệu liên quan
- Quyết định kỹ thuật ban đầu: `docs/day1-decisions.md`.
- Cấu hình runtime: `config/default.yaml`.
- Hướng dẫn nội bộ workspace: `copilot-instructions.md`.
