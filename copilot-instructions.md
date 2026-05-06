# Hướng Dẫn Copilot (Workspace)

## Quy trình
1. Đọc file này trước khi thêm/sửa code.
2. Cập nhật file này nếu quy trình hoặc phạm vi thay đổi.
3. Mọi thay đổi code phải bám đúng phạm vi trong kế hoạch.

## Phạm vi hiện tại
- Giai đoạn hiện tại tập trung vào nhận diện trước (khuôn mặt + vật thể).
- Theo dõi 1 mục tiêu tại 1 thời điểm, cho phép người dùng chọn mục tiêu.
- Chưa tích hợp điều khiển phần cứng servo.
- Điều khiển tạm thời ở dạng mô phỏng: hiển thị hướng quay cần thiết LEFT/RIGHT/UP/DOWN trên console hoặc overlay.

## Quy ước tài liệu
- Tất cả tài liệu hiện tại và tài liệu tạo mới phải viết bằng tiếng Việt có dấu.
- Nội dung tài liệu cần ngắn gọn, rõ ràng, có checklist khi phù hợp.

## Ghi chú coding
- Ưu tiên code dễ đọc, module hóa theo src/input, src/detection, src/tracking, src/control, src/hardware, src/utils.
- Mọi tham số threshold/PID phải đưa vào config.
- Ghi log tối thiểu: FPS, latency, target_loss_count, target_switch_count.
