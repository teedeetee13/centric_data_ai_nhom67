# Kết quả kiểm thử

Ngày kiểm tra 08/11/2026. Môi trường: Windows 11, Python 3.12, thư viện cài mới từ `requirements-dev.txt`.

## Kết quả

- 61/61 kiểm thử tự động qua (`python -m unittest discover -s tests -t .`): dữ liệu, SQLite, mô hình thật, giao diện bằng AppTest, ticket theo quy trình, phân quyền, bảo mật và công cụ bảo trì.
- `ruff check .` không báo lỗi. `pip-audit` không phát hiện lỗ hổng đã biết trong các thư viện.
- `bandit`: còn 2 cảnh báo mức trung bình về `urlopen` (địa chỉ Ollama do người vận hành cấu hình) và 1 cảnh báo về chuỗi lọc ký tự vô hình; đã xem xét, không phải lỗi.
- Nhấp đúp `CHAY_DEMO_WINDOWS.bat` trên Windows: tự tạo môi trường, cài thư viện trong khoảng 3,5 phút, ứng dụng mở được.
- Chế độ mạng nội bộ `run_mvp.py --lan`: từ chối chạy khi thiếu mật khẩu; có mật khẩu thì trả lời endpoint health.
- Mô hình ngôn ngữ thật (qwen2.5:3b, GPU 4GB): 10 câu thử, 9 bản nháp qua kiểm tra bám nguồn, 1 bản bị loại; khoảng 2,5 giây mỗi bản nháp khi model đã nạp.

## Hiệu năng đo được (không gọi mô hình ngôn ngữ)

| Chỉ số | Kết quả |
| :--- | :--- |
| Xử lý một câu | trung vị 3,8 ms, p95 5,1 ms |
| Xử lý 500 câu | khoảng 3,1 giây |
| Làm sạch và khử trùng 424 dòng | 0,28 giây (trước tối ưu 8,91 giây) |
| Làm sạch và khử trùng 1.500 dòng | 1,72 giây (trước tối ưu 51,64 giây) |
| Bộ nhớ tiến trình sau khi nạp mô hình | khoảng 175 MB |

## Chưa kiểm tra

- Chạy `CHAY_DEMO_WINDOWS.bat` trên máy chưa có Python 3.12.
- Truy cập từ một máy khác thật trong mạng (tường lửa Windows có thể chặn cổng).
- Gửi email thật qua SMTP.
- Thử với dữ liệu thật của sinh viên.

Các kiểm thử dùng CSDL tạm riêng, không chạm dữ liệu người dùng.
