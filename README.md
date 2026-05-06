# Dự án Tracking Khuôn Mặt Và Vật Thể

## Mục tiêu
Xây dựng hệ thống nhận diện khuôn mặt + vật thể, cho phép chọn 1 mục tiêu để theo dõi. Ở giai đoạn hiện tại, cơ cấu điều khiển phần cứng chưa tích hợp; hệ thống chỉ mô phỏng hướng quay camera trên màn hình hoặc console.

## Cấu trúc dự án
- src/: mã nguồn chính.
- config/: cấu hình runtime, tracking, PID.
- scripts/: script chạy nhanh cho phát triển/triển khai.
- logs/: log benchmark và log runtime.
- artifacts/: video test, ảnh minh chứng, kết quả benchmark.
- docs/: tài liệu kỹ thuật và quyết định triển khai.
- tests/: test cơ bản.

## Khởi động nhanh (Ngày 1 -> Ngày 2)
1. Cài Python và thư viện theo requirements.txt.
2. Cập nhật cấu hình trong config/default.yaml.
3. Chạy ứng dụng baseline để kiểm tra camera, FPS và log bằng `scripts\run_day1.cmd`.

## Cách chạy được dùng chính thức
Phương thức được giữ lại là file `.cmd` vì:
- Chạy trực tiếp được trong `cmd` và terminal mặc định của Windows.
- Không bị chặn bởi `ExecutionPolicy` như PowerShell.
- Phù hợp hơn khi bạn chỉ cần gõ một lệnh để tạo `venv`, cài thư viện và chạy chương trình.

Lệnh sử dụng:
1. Mở terminal tại thư mục dự án.
2. Chạy lệnh: `scripts\run_day1.cmd`

Lần chạy đầu:
- Tự tạo môi trường ảo `.venv` nếu chưa có.
- Tự kiểm tra thư viện bắt buộc.
- Nếu thiếu thư viện, tự cài từ `requirements.txt`.

Các lần chạy sau:
- Chỉ kiểm tra nhanh thư viện rồi chạy chương trình.

Nếu bạn muốn tự kích hoạt `venv` thủ công trước khi chạy:
1. Trong `cmd`: `.venv\Scripts\activate.bat`
2. Sau đó chạy: `python -m src.app.main`

## Ghi chú
- Jetson Nano (JetPack 4.6) thường dùng Python 3.6.x.
- Các giá trị quyết định ban đầu nằm trong docs/day1-decisions.md.
- Tất cả tài liệu trong dự án dùng tiếng Việt có dấu.
