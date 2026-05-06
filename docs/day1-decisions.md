# Quyết Định Bạn Cần Chốt Trong Ngày 1

## A. Camera và phần cứng
- [x] Loại camera: sử dụng webcam.
- [x] Độ phân giải khởi điểm: 1280x720.
- [x] Cơ cấu pan/tilt đã có chưa: chưa có.
- [x] Mạch điều khiển servo: xác định ở giai đoạn sau.

## B. Logic nghiệp vụ
- [x] Có nhận diện danh tính khuôn mặt ngay phase 1: có.
- [x] Danh sách class object ưu tiên theo dõi: person, phone, cup.
- [x] Tình huống ưu tiên:
	- Luôn bám theo target đã chọn (target có thể là người hoặc vật thể).
	- Nếu target bị che khuất dưới 5 giây hoặc ra ngoài khung hình dưới 2 giây thì giữ nguyên target.
	- Nếu vượt quá các ngưỡng trên thì yêu cầu chọn lại target.
	- Vì chọn target theo object cụ thể (instance) nên không cần thêm luật chọn giữa nhiều đối tượng cùng class.

## C. KPI tạm thời
- [x] FPS laptop tối thiểu: 10 FPS.
- [x] Latency tối đa: 400 ms.
- [x] Sai số tâm cho phép: 200 px.

## D. Phạm vi triển khai hiện tại
- [x] Ưu tiên nhận diện trước, chưa điều khiển phần cứng.
- [x] Mô phỏng lệnh điều khiển bằng hiển thị hướng quay trên màn hình/console: LEFT, RIGHT, UP, DOWN.

## E. Việc cần chốt thêm trước khi vào Ngày 2
- [x] Class object theo dõi bản đầu: person, cup, phone.
- [x] Ngưỡng confidence face/object bản đầu: 0.5.
- [x] Luật đổi mục tiêu khi target đang theo dõi bị mất: thực hiện lại quy trình như lúc bắt đầu (yêu cầu chọn lại target).

## F. Trạng thái
- [x] Hoàn tất quyết định Ngày 1.
