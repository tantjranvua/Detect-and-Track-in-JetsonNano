# Hướng Dẫn Copilot (Workspace)

## Quy trình
1. Đọc file này trước khi thêm/sửa code.
2. Cập nhật file này nếu quy trình hoặc phạm vi thay đổi.
3. Mọi thay đổi code phải bám đúng phạm vi trong kế hoạch.

## Phạm vi hiện tại
- Giai đoạn hiện tại tập trung vào nhận diện trước (khuôn mặt + vật thể).
- Nâng cấp theo dõi khuôn mặt từ placeholder sang multi-face tracker theo track_id để ổn định bounding box khi có che khuất ngắn hạn.
- Áp dụng cơ chế làm mượt box theo thời gian và giữ track trong một số frame bị mất để giảm hiện tượng nhấp nháy.
- Nhận diện danh tính theo từng track với voting cửa sổ 3 frame/track nhằm giảm nhảy tên giữa các khuôn mặt gần nhau hoặc bị che một phần.
- Bổ sung lọc trùng bounding box (NMS) cho face detector để giảm sinh nhiều track giả trên cùng một khuôn mặt.
- Hiệu chỉnh ngưỡng recognize theo hướng cân bằng giữa chống nhầm tên và tránh bị unknown toàn bộ.
- Điều chỉnh logic score_margin theo cấp nhãn (label-level) thay vì theo từng ảnh mẫu để tránh loại nhầm khi một người có nhiều ảnh gallery.
- Bổ sung chỉ số pixel_similarity trong face-recognize và in console theo chu kỳ để quan sát độ ổn định khi che khuôn mặt một phần.
- Tổng hợp tài liệu README theo dạng hướng dẫn cho người mới: cài đặt, vận hành, debug và chỉnh sửa theo từng bước.
- Chưa tích hợp điều khiển phần cứng servo.
- Điều khiển tạm thời ở dạng mô phỏng: hiển thị hướng quay cần thiết LEFT/RIGHT/UP/DOWN trên console hoặc overlay.
- Bổ sung demo điều khiển camera theo tâm mục tiêu: tính sai lệch tâm khung hình và in lệnh hướng UP/DOWN/LEFT/RIGHT ra console thay cho xuất lệnh servo thật.
- Bổ sung khả năng chay tren Jetson Nano: them script khoi dong Linux va ho tro camera CSI qua GStreamer.
- Bo sung camera profile (usb_webcam/csi_camera) de chuyen doi nhanh bang 1 dong active_camera_profile.
- Bổ sung giai đoạn face-recognize theo hướng on-device, không phụ thuộc dịch vụ cloud.
- Face-recognize ưu tiên cơ chế gallery cục bộ (ảnh mẫu theo từng người), cho phép nhận diện "unknown" khi dưới ngưỡng.
- Cần có công cụ thu thập ảnh gallery trực tiếp từ camera để tạo dữ liệu mẫu nhanh trong thực địa.

## Quy ước tài liệu
- Tất cả tài liệu hiện tại và tài liệu tạo mới phải viết bằng tiếng Việt có dấu.
- Nội dung tài liệu cần ngắn gọn, rõ ràng, có checklist khi phù hợp.

## Ghi chú coding
- Ưu tiên code dễ đọc, module hóa theo src/input, src/detection, src/tracking, src/control, src/hardware, src/utils.
- Mọi tham số threshold/PID phải đưa vào config.
- Ghi log tối thiểu: FPS, latency, target_loss_count, target_switch_count.
