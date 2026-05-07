# Face Gallery

Thư mục này chứa ảnh mẫu cho module face-recognize.

Cấu trúc đề xuất:
- `data/face_gallery/<ten_nguoi>/anh_1.jpg`
- `data/face_gallery/<ten_nguoi>/anh_2.jpg`

Ví dụ:
- `data/face_gallery/an/an_1.jpg`
- `data/face_gallery/binh/binh_1.jpg`

Lưu ý:
- Ảnh nên rõ mặt, đủ sáng, kích thước tối thiểu 100x100.
- Nên có 10-30 ảnh cho mỗi người, đa dạng góc nhìn.
- Tên thư mục con sẽ được dùng làm nhãn hiển thị nhận diện.

Thu thap nhanh bang script:
- Chay: `scripts\capture_gallery.cmd <ten_nguoi> <so_anh>`
- Trong cua so camera, nhan `S` de luu anh, `Q`/`ESC` de thoat.
