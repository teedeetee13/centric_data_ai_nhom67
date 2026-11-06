# Quy ước làm việc chung

Mục tiêu: dự án lớn dần mà vẫn dễ đọc, dễ tìm, người mới mở ra là biết thứ gì ở đâu.

## 1. Code đặt ở đâu

| Loại thay đổi | Đặt ở | Ghi chú |
| :--- | :--- | :--- |
| Logic nghiệp vụ, mô hình, xử lý dữ liệu | `EduSupportAI/src/` | Không import `streamlit` trong `src/`; `src/` phải chạy được không cần giao diện |
| Luồng xử lý một yêu cầu | `src/service.py` | Giao diện chỉ gọi `RequestService.process()`, không tự ghép các bước |
| Một màn hình / khối giao diện | `app/components/<ten>.py` | Mỗi tệp một hàm `render_...`; `app/main.py` chỉ ghép tab |
| Màu sắc, kiểu chữ | `app/styles.css` | Không viết CSS trong Python; khối HTML chỉ dùng class |
| Đường dẫn, ngưỡng, tên model, biến môi trường | `src/config.py` | Không viết cứng đường dẫn hay địa chỉ email trong code |
| Tri thức: quy trình, FAQ | `data/kb/` | Xem mục 3 |
| Thực nghiệm, đánh giá | `experiments/` | Mỗi thực nghiệm ghi kết quả ra `experiments/*_report.json` |
| Kiểm thử | `tests/test_<chu_de>.py` | Dùng `unittest`; không gọi Ollama hay mạng thật (dùng mô hình giả) |
| Tài liệu thuyết minh, kế hoạch | `docs/` | Tài liệu kỹ thuật của app để trong `EduSupportAI/` |

Gợi ý kích thước: một tệp vượt khoảng **350 dòng** thì tách theo chức năng (như đã tách `app/main.py`).

## 2. Phong cách code

- Python 3.12, thụt lề 4 dấu cách, tên `snake_case`, hằng số `UPPER_CASE`.
- Docstring và chú thích bằng tiếng Việt, ngắn, giải thích **vì sao** hơn là **cái gì**.
- Giao diện không dùng emoji; câu chữ hành chính, lịch sự.
- Trước khi commit, chạy hai lệnh trong thư mục `EduSupportAI` (cài bằng `pip install -r requirements-dev.txt`):

```bash
ruff check .
python -m unittest discover -s tests -t .
```

## 3. Thêm tri thức

**Thêm một quy trình** vào `data/kb/eaut_quy_trinh.json`:

1. Thêm một phần tử vào `procedures` với `id` tiếp theo (`QT34`, ...), đủ các trường như quy trình có sẵn:
   `name`, `topic` (một trong 7 khóa của `TOPICS` trong `src/config.py`), `receiving_unit`, `legal_basis`,
   `source` (khóa trong `sources`), `aliases` (3 đến 6 câu hỏi mẫu, có ít nhất 1 câu không dấu),
   `keywords` (từ khóa neo, viết có dấu), `conditions`, `documents`, `submit_window`, `steps`, `max_days`,
   `result_time`, `requires_student_id`.
2. Chỉ ghi nội dung có trong tài liệu gốc; không tự thêm số ngày, mức tiền hay mã biểu mẫu.
3. Chạy `python -m experiments.eval_procedure_routing` và kiểm thử. Không sửa `keywords` chỉ để làm đẹp
   số liệu trên `procedure_eval.csv`; muốn đo lại thì viết thêm câu đánh giá mới.
4. Huấn luyện lại mô hình phân loại (`python -m src.model`) vì câu mẫu quy trình là dữ liệu huấn luyện.

**Thêm hoặc sửa FAQ** trong `data/kb/eaut_faq_kb.csv`: chỉ đặt `verified=true` khi có `source_url` trỏ tới
tài liệu chính thức.

**Thêm câu hỏi mẫu cho demo**: thêm một dòng vào `SAMPLES` trong `app/components/demo_guide.py`.

## 4. Dữ liệu và bảo mật

- Không commit dữ liệu thật của sinh viên, tệp `.env`, mật khẩu hay khóa API.
- `data/edusupport.db` là CSDL sinh ra khi chạy, đã nằm trong `.gitignore`; app tự tạo lại khi thiếu.
- Số liệu đưa vào tài liệu và slide phải chạy lại được từ mã nguồn.

## 5. Nhánh, commit, Pull Request

- Không commit thẳng vào `main`. Mỗi người làm trên nhánh riêng, đặt tên không dấu, không cách,
  ví dụ `nhanh-cua-Truong` hoặc `ten/tinh-nang` (`truong/them-quy-trinh-hoc-bong`).
- Mỗi commit một việc, câu tóm tắt tiếng Việt ngắn gọn ở dòng đầu, ví dụ: `Thêm quy trình xét học bổng (QT34)`.
- Gộp vào `main` qua Pull Request: CI (kiểm tra lỗi và kiểm thử) phải qua, có ít nhất một thành viên khác xem.
