# Kế hoạch chi tiết: Nhận diện khuôn mặt, vật thể và điều khiển camera tracking

Ngày cập nhật: 2026-05-06

## 1. Mục tiêu dự án
Xây dựng một hệ thống chạy thời gian thực có khả năng:
- Phát hiện và nhận diện khuôn mặt.
- Phát hiện vật thể mục tiêu.
- Theo dõi mục tiêu ưu tiên (face hoặc object theo luật cấu hình).
- Giai đoạn hiện tại: mô phỏng điều khiển hướng quay camera trên console/màn hình (LEFT/RIGHT/UP/DOWN).
- Giai đoạn sau: tích hợp cơ cấu pan/tilt phần cứng và giao thức điều khiển.
- Phát triển trên laptop, sau đó đóng gói và triển khai trên Jetson Nano.

## 2. Ràng buộc nền tảng và phiên bản
- Thiết bị đích: Jetson Nano.
- Hệ điều hành: JetPack 4.6.
- Python: JetPack 4.6 thường đi với Python 3.6
- AI framework mục tiêu: PyTorch 1.10 (cần đúng bản wheel tương thích JetPack 4.6).

Lưu ý quan trọng:
- Với Jetson Nano, luôn ưu tiên xác minh tính tương thích torch/torchvision từ đầu dự án để tránh tắc ở giai đoạn triển khai.

## 3. Kiến trúc hệ thống đề xuất
## 3.1 Các module
1. Module Thu nhận hình ảnh (Video Input)
- Nguồn vào từ camera CSI hoặc USB.
- Chuẩn hóa kích thước frame theo profile hiệu năng.

2. Module Phát hiện khuôn mặt (Face Detection)
- Trả về bounding box khuôn mặt và độ tin cậy.
- Có nhận diện danh tính và nếu có người lạ thì để Unknown person.

3. Module Phát hiện vật thể (Object Detection)
- Trả về class, bounding box, confidence.
- Có thể lọc class quan trọng (ví dụ: person, car, dog).

4. Module Theo dõi (Tracking)
- Gán ID và theo dõi cùng một mục tiêu qua nhiều frame.
- Giúp giảm phụ thuộc vào việc detect lại ở mọi khung hình.

5. Module Chọn mục tiêu (Target Selection)
- Quy tắc ưu tiên: selected > face > object 
- Quy tắc ổn định mục tiêu (tránh nhảy mục tiêu liên tục).

6. Module Điều khiển camera (Control)
- Chuyển sai số tâm ảnh thành hướng điều khiển: LEFT/RIGHT/UP/DOWN.
- Hiển thị hướng quay trên overlay hoặc console để mô phỏng hành vi camera.
- PID vẫn được giữ để chuẩn bị cho giai đoạn phần cứng.

7. Module Giao tiếp phần cứng (Hardware I/O)
- Tạm thời để placeholder.
- Triển khai thực tế ở giai đoạn sau khi chốt giao thức (PWM/I2C/UART).

8. Module Giám sát và log
- Theo dõi FPS, latency, CPU/GPU, nhiệt độ, bộ nhớ.
- Ghi log lỗi để phục vụ debug và nghiệm thu.

## 3.2 Luồng dữ liệu
Capture frame -> Detect -> Track -> Chọn target -> PID -> Xuất lệnh servo -> Giám sát

## 4. Kế hoạch triển khai chi tiết theo giai đoạn

## Giai đoạn 1: Chốt yêu cầu, KPI và phạm vi (1-2 ngày)
Mục tiêu:
- Chốt chính xác bạn sẽ làm gì và đo kết quả bằng gì.

Việc bạn cần làm:
1. Chốt phạm vi nghiệp vụ.
- Theo dõi 1 mục tiêu tại một thời điểm hay nhiều mục tiêu? Theo dõi 1 mục tiêu tại 1 thời điểm
- Ưu tiên khuôn mặt hay vật thể? Đầu tiên sẽ hiển thị danh sách vật thể và khuôn mặt, sau đó cho phép người dùng tích chọn để theo dõi

2. Chốt điều kiện vận hành. ( Có thể cài đặt thông số này sau)
- Khoảng cách quan sát, ánh sáng, tốc độ chuyển động mục tiêu.
- Góc quay pan/tilt thực tế của cơ cấu.

3. Chốt KPI nghiệm thu.
- FPS tối thiểu trên Jetson Nano. 25 FPS
- Độ trễ tối đa từ frame đến lệnh servo. 200 ms
- Sai số giữ tâm mục tiêu (pixel hoặc độ). 200px

Đầu ra bắt buộc:
- Tài liệu yêu cầu 1 trang.
- Bảng KPI có ngưỡng đạt/không đạt.

## Giai đoạn 2: Dựng baseline trên laptop (5-7 ngày)
Mục tiêu:
- Có pipeline chạy end-to-end ổn định trước khi đụng phần cứng Jetson.

Việc bạn cần làm:
1. Xây bộ khung chương trình.
- Cấu trúc thư mục: input, detection, tracking, control, utils, config.
- Cơ chế file cấu hình để đổi ngưỡng mà không sửa code.

2. Tích hợp nhận diện khuôn mặt và vật thể.
- Chạy riêng từng module rồi mới ghép chung.
- Định nghĩa format đầu ra thống nhất: id, class, bbox, score.

3. Thêm tracker.
- Gán ID mục tiêu để theo dõi ổn định qua frame.
- Xử lý trường hợp target biến mất tạm thời.

4. Viết công cụ đo hiệu năng.
- Đo FPS trung bình, FPS thấp nhất, độ trễ trung bình.
- Log theo từng phiên chạy.

Đầu ra bắt buộc:
- Chương trình chạy được trên webcam laptop.
- Báo cáo benchmark baseline.

## Giai đoạn 3: Xây thuật toán điều khiển tracking mô phỏng (4-6 ngày)
Mục tiêu:
- Biến bbox mục tiêu thành lệnh hướng quay mô phỏng ổn định.

Việc bạn cần làm:
1. Xây công thức sai số điều khiển.
- Tâm ảnh: (cx, cy).
- Tâm mục tiêu: (tx, ty).
- Sai số: ex = tx - cx, ey = ty - cy.

2. Áp dụng PID cho 2 trục.
- Pan dùng PID riêng, tilt dùng PID riêng.
- Thêm deadband để giảm rung khi sai số nhỏ.

3. Tạo lớp an toàn điều khiển.
- Giới hạn góc min/max.
- Giới hạn tốc độ thay đổi góc.
- Khi mất target quá timeout: quay về vị trí home.

4. Chạy mô phỏng trước phần cứng thật.
- Hiển thị lệnh hướng quay LEFT/RIGHT/UP/DOWN trên màn hình và console.
- Tinh chỉnh PID ở chế độ giả lập để giảm rủi ro khi chuyển sang servo thật.

Đầu ra bắt buộc:
- Có bộ tham số PID khởi điểm.
- Tracking mượt trong mô phỏng.
- Có logic quyết định hướng quay rõ ràng theo ex, ey.

## Giai đoạn 4: Chuẩn bị môi trường Jetson Nano (3-5 ngày)
Mục tiêu:
- Port phần mềm từ laptop sang Jetson Nano mà vẫn chạy ổn định.

Việc bạn cần làm:
1. Cài và khóa phiên bản môi trường.
- Xác minh Python thực tế trên Jetson.
- Cài torch, torchvision đúng phiên bản tương thích.
- Cài OpenCV và các phụ thuộc camera.

2. Kiểm tra camera pipeline trên Jetson.
- Test CSI/USB ở các độ phân giải khác nhau.
- Chốt độ phân giải vừa đủ cho FPS mục tiêu.

3. Chạy lại baseline benchmark trên Jetson.
- So sánh với laptop để đánh giá mức giảm hiệu năng.
- Xác định nút thắt: detect, tracking hay render.

Đầu ra bắt buộc:
- Pipeline nhận diện chạy được trên Jetson.
- Báo cáo benchmark Jetson phiên bản đầu.

## Giai đoạn 5: Tích hợp phần cứng pan/tilt thật (5-7 ngày)
Mục tiêu:
- Camera bám mục tiêu trên cơ cấu thực tế.

Việc bạn cần làm:
1. Hoàn thiện sơ đồ nối dây an toàn.
- Servo dùng nguồn riêng.
- Nối chung GND giữa Jetson và mạch servo.
- Kiểm tra dòng tải cực đại của servo.

2. Viết lớp driver điều khiển servo.
- Hàm set góc pan/tilt.
- Hàm clamp góc và rate limit.
- Cơ chế fail-safe khi mất kết nối.

3. Hiệu chuẩn mapping ảnh sang góc quay.
- Xác định hệ số chuyển đổi pixel -> độ quay.
- Chạy test trái/phải, lên/xuống theo mốc cố định.

4. Tuning PID tại hiện trường.
- Tuning theo nhiều tốc độ di chuyển của mục tiêu.
- Kiểm tra rung, overshoot, độ trễ bám.

Đầu ra bắt buộc:
- Hệ thống bám mục tiêu trên phần cứng thật.
- Bộ tham số điều khiển ổn định ở môi trường thực.

## Giai đoạn 6: Tối ưu, đóng gói, vận hành (5-7 ngày)
Mục tiêu:
- Đạt hiệu năng mục tiêu và chạy bền nhiều giờ.

Việc bạn cần làm:
1. Tối ưu tốc độ suy luận.
- Dùng mô hình nhẹ hơn nếu cần.
- Thử FP16/TensorRT khi phù hợp.
- Giảm kích thước input có kiểm soát.

2. Tối ưu kiến trúc runtime.
- Tách luồng capture/inference/control.
- Bỏ frame hợp lý để giữ độ trễ thấp.

3. Đóng gói triển khai.
- Tạo script khởi động.
- Tạo service tự chạy khi bật máy.
- Lưu log và cơ chế tự phục hồi khi lỗi.

4. Kiểm thử độ bền.
- Chạy liên tục 8-24 giờ.
- Theo dõi nhiệt độ, rò rỉ bộ nhớ, treo tiến trình.

Đầu ra bắt buộc:
- Bản release có thể vận hành thực tế.
- Biên bản kiểm thử đạt KPI.

## 5. Danh sách việc cần làm theo tuần (thực thi nhanh)
Tuần 1:
- Chốt yêu cầu, KPI, quy tắc chọn target.
- Dựng skeleton code và cấu hình.

Tuần 2:
- Tích hợp face/object detection.
- Tích hợp tracker và benchmark laptop.

Tuần 3:
- Hoàn thiện PID, deadband, fail-safe.
- Chạy mô phỏng điều khiển.

Tuần 4:
- Cài môi trường Jetson.
- Chạy pipeline và benchmark Jetson.

Tuần 5:
- Tích hợp servo thật, calibration, tuning.
- Kiểm thử nhiều tình huống mục tiêu.

Tuần 6:
- Tối ưu hiệu năng.
- Đóng gói service + stress test + nghiệm thu.

## 6. Tiêu chí nghiệm thu chi tiết
1. Hiệu năng:
- FPS trung bình trên Jetson đạt mục tiêu (ví dụ >= 12 FPS).
- Độ trễ trung bình đạt mục tiêu (ví dụ <= 200 ms).

2. Chất lượng tracking:
- Giữ mục tiêu trong vùng trung tâm với sai số cho phép.
- Không nhảy target liên tục khi có nhiều đối tượng gần nhau.

3. Độ ổn định:
- Chạy liên tục 8-24 giờ không treo.
- Không phát sinh reset servo bất thường.

4. Khả năng phục hồi:
- Mất target thì về chế độ tìm lại sau timeout.
- Mất camera tạm thời có log lỗi và tự phục hồi.

## 7. Rủi ro chính và cách xử lý
1. Rủi ro tương thích thư viện trên Jetson.
- Cách xử lý: khóa phiên bản từ sớm, test môi trường ngay tuần 1-2.

2. Rủi ro FPS thấp.
- Cách xử lý: giảm input size, giảm tần suất detect, ưu tiên tracker giữa các frame.

3. Rủi ro servo rung hoặc nóng.
- Cách xử lý: deadband, rate limit, nguồn riêng đủ dòng, giới hạn góc an toàn.

4. Rủi ro sai lệch khi đổi môi trường sáng.
- Cách xử lý: tinh chỉnh threshold và bổ sung dữ liệu test ánh sáng yếu/mạnh.

## 8. Checklist triển khai hằng ngày
- [ ] Kiểm tra log lỗi của phiên chạy trước.
- [ ] Chạy test nhanh 5 phút: nhận diện + tracking + điều khiển.
- [ ] Ghi lại FPS và độ trễ trung bình.
- [ ] Ghi thay đổi tham số (threshold, PID, độ phân giải).
- [ ] Chụp 1 video minh chứng kết quả sau chỉnh sửa.
- [ ] Cập nhật tài liệu trước khi kết thúc ngày.

## 9. Danh sách tài liệu bạn nên duy trì
- Tài liệu yêu cầu và KPI.
- Sơ đồ kiến trúc module.
- Nhật ký benchmark theo từng phiên bản.
- Nhật ký tuning PID.
- Hướng dẫn triển khai trên Jetson Nano.
- Hướng dẫn vận hành và xử lý sự cố nhanh.

## 10. Quyết định kỹ thuật cần chốt sớm
- Chỉ phát hiện khuôn mặt hay cần nhận diện danh tính?
- Danh sách class vật thể cần theo dõi.
- Mục tiêu ưu tiên khi face và object xuất hiện cùng lúc.
- FPS mục tiêu tối thiểu để chấp nhận triển khai.
- Chọn giao thức điều khiển servo: PWM trực tiếp hay qua PCA9685.

## 11. Giá trị khởi điểm đề xuất (dùng ngay khi chưa có dữ liệu thử nghiệm)
Mục đích: đặt tham số đủ an toàn để bắt đầu chạy, sau đó tinh chỉnh theo log thực tế.

1. KPI tạm thời (bản khởi động)
- FPS mục tiêu trên laptop: >= 18 FPS.
- FPS mục tiêu trên Jetson Nano: >= 10 FPS (mức tối thiểu để tracking ổn định ban đầu).
- Độ trễ trung bình end-to-end: <= 250 ms.
- Sai số giữ tâm mục tiêu: <= 80 px với khung hình 640x480.
- Tỷ lệ mất target trong 5 phút: <= 5 lần.

2. Cấu hình camera và mô hình ban đầu
- Độ phân giải vào: 640x480.
- FPS camera đầu vào: 30.
- Face detection confidence threshold: 0.55.
- Object detection confidence threshold: 0.45.
- NMS IoU threshold: 0.50.
- Danh sách class theo dõi object bản đầu: person, car, dog, cat.

3. Luật chọn mục tiêu mặc định
- Nếu người dùng đã chọn tay: luôn bám target đã chọn.
- Nếu chưa chọn: ưu tiên face có score cao nhất.
- Nếu không có face: chọn object có score cao nhất trong danh sách class cho phép.
- Chống nhảy mục tiêu: chỉ đổi target khi target hiện tại mất quá 15 frame liên tiếp.

4. PID khởi điểm cho mô phỏng (cần tune lại khi gắn servo thật)
- Pan: Kp=0.012, Ki=0.000, Kd=0.004.
- Tilt: Kp=0.010, Ki=0.000, Kd=0.003.
- Deadband: |ex| < 15 px và |ey| < 15 px thì không phát lệnh.
- Giới hạn tốc độ lệnh: tối đa 3 độ mỗi chu kỳ điều khiển.

Ghi chú:
- Giá trị Jetson 25 FPS thường khó ổn định với pipeline face+object+tracking trên Nano khi chưa tối ưu TensorRT.
- Mục tiêu khởi động nên thực tế, sau đó nâng dần khi đã tối ưu.

## 12. Ma trận kiểm thử tối thiểu (bắt buộc chạy)
1. Điều kiện ánh sáng
- Test A: đủ sáng trong phòng.
- Test B: ánh sáng yếu.
- Test C: ngược sáng nhẹ.

2. Điều kiện chuyển động
- Test D: mục tiêu di chuyển chậm.
- Test E: mục tiêu di chuyển nhanh.
- Test F: mục tiêu đổi hướng đột ngột.

3. Điều kiện phức tạp
- Test G: có 2-3 đối tượng cùng lúc.
- Test H: mục tiêu bị che khuất 1-2 giây.
- Test I: mục tiêu ra khỏi khung rồi quay lại.

Mẫu ghi kết quả mỗi test:
- FPS trung bình.
- Latency trung bình.
- Số lần mất target.
- Mức rung servo (thấp/vừa/cao).
- Kết luận đạt/chưa đạt.

## 13. Điều kiện qua cổng từng giai đoạn (Gate)
Gate 1 (qua Giai đoạn 1 -> 2):
- Đã khóa KPI tạm thời, danh sách class, luật chọn target.

Gate 2 (qua Giai đoạn 2 -> 3):
- Pipeline detect + track chạy ổn định 30 phút trên laptop.
- Có log FPS/latency theo thời gian.

Gate 3 (qua Giai đoạn 3 -> 4):
- Mô phỏng pan/tilt mượt, không dao động mạnh.
- Có bộ PID khởi điểm và log tuning.

Gate 4 (qua Giai đoạn 4 -> 5):
- Jetson chạy được detect + track với FPS >= 10 ổn định.
- Camera hoạt động liên tục không crash tối thiểu 30 phút.

Gate 5 (qua Giai đoạn 5 -> 6):
- Servo thật bám mục tiêu liên tục 10 phút.
- Không rung mạnh kéo dài, không quá nhiệt bất thường.

## 14. Bảng khóa phiên bản môi trường (điền dần khi cài đặt)
Laptop (Dev):
- Python: [điền]
- torch: [điền]
- torchvision: [điền]
- opencv-python: [điền]
- numpy: [điền]

Jetson Nano (Deploy):
- JetPack: 4.6
- Python: 3.6.x (xác minh thực tế)
- torch: 1.10.x (wheel tương thích JetPack)
- torchvision: bản tương thích torch
- OpenCV: bản tương thích camera pipeline
- CUDA/cuDNN: theo JetPack 4.6

## 15. BOM phần cứng khuyến nghị bản đầu
- Jetson Nano + nguồn ổn định 5V-4A.
- Camera CSI hoặc USB UVC.
- Cơ cấu pan/tilt 2 trục.
- 2 servo cùng loại, mô-men phù hợp tải camera.
- Mạch PCA9685 (khuyến nghị để điều khiển PWM ổn định).
- Nguồn riêng cho servo (tách khỏi nguồn Jetson).
- Dây nguồn và dây tín hiệu có tiết diện phù hợp, nối GND chung.

## 16. Bước tiếp theo bạn phải làm ngay (72 giờ)
Ngày 1:
- Tạo cấu trúc thư mục dự án và file config trung tâm.
- Nhập các giá trị khởi điểm ở Mục 11 vào config.
- Dựng pipeline camera -> detect -> vẽ bbox trên laptop.

Ngày 2:
- Thêm tracking ID và luật chọn target theo Mục 11.
- Bổ sung log FPS, latency, số lần mất target.
- Chạy 3 test đầu tiên: A, D, G trong Mục 12.

Ngày 3:
- Thêm mô phỏng điều khiển pan/tilt (chưa xuất lệnh servo thật).
- Áp dụng PID khởi điểm + deadband + rate limit.
- Chạy lại test A, E, H và ghi kết quả đạt/chưa đạt.

Đầu ra bắt buộc sau 72 giờ:
- Video minh chứng pipeline chạy ổn định.
- 1 file log benchmark.
- 1 bảng kết quả test ngắn gọn theo Mục 12.

## 17. Trạng thái hiện tại và bước tiếp theo sau Day 1
Trạng thái hiện tại:
- Bạn đã hoàn thành tài liệu Day 1.
- Phạm vi ưu tiên đã rõ: tập trung nhận diện trước, chưa tích hợp phần cứng.

Bước tiếp theo cần làm ngay (ưu tiên từ cao xuống thấp):
1. Hoàn thiện detect khuôn mặt + object chạy thời gian thực trên webcam.
2. Hiển thị danh sách mục tiêu nhận diện được và cho phép chọn 1 mục tiêu.
3. Tính sai số ex, ey và hiển thị hướng quay cần thiết:
- ex > ngưỡng: RIGHT
- ex < -ngưỡng: LEFT
- ey > ngưỡng: DOWN
- ey < -ngưỡng: UP
4. Ghi log FPS, latency, target_loss_count và target_switch_count.
5. Chạy tối thiểu 3 bài test: A, D, G và lưu kết quả.

Tiêu chí hoàn thành bước này:
- Có thể chọn một target và giữ theo dõi liên tục.
- Hệ thống hiển thị hướng quay đúng theo chuyển động mục tiêu.
- Có log đo được hiệu năng, đủ để tối ưu ở vòng tiếp theo.

---

Gợi ý sử dụng tài liệu này:
- Mỗi giai đoạn chỉ chuyển bước khi đã có đủ đầu ra bắt buộc.
- Khi thay đổi mô hình hoặc phần cứng, cập nhật lại KPI và benchmark ngay trong ngày.
