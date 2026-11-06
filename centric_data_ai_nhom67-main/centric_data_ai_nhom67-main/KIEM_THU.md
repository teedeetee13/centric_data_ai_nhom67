# Kết quả kiểm thử bản MVP

Ngày kiểm tra 16/10/2026. Môi trường chạy kiểm tra: Linux, Python 3.12.14; phiên bản thư viện trong requirements.txt. File BAT dành cho Windows được cung cấp để chạy trên máy nhóm; chưa chạy trực tiếp file BAT trên Windows trong môi trường kiểm tra này.

## Kết quả

- 16/16 kiểm thử tự động qua: 13 ca dịch vụ/dữ liệu/SQLite và ba ca thao tác giao diện Streamlit bằng AppTest.
- Launcher khởi động máy chủ local, endpoint health trả HTTP 200 và nội dung ok; trang chính trả HTTP 200 cùng HTML.
- Tập dữ liệu xuất mới có 424 dòng; 202 dòng được bộ làm sạch hiện tại đánh dấu dùng được. Khác số 240 của pipeline cũ vì bộ mới kiểm tra gần trùng trên toàn bộ các câu trước đó, thay vì chỉ 50 câu gần nhất, và bổ sung các mẫu che thông tin.
- Evaluator mới: train/test không giao nhóm mẫu, không có cặp gần trùng train/test ở ngưỡng 0,93. Tập test dùng được có 28 dòng mô phỏng; kết quả chưa chứng minh hiệu quả trên dữ liệu thật.

## Các ca đã chạy

| Nhóm kiểm tra | Kết quả cần đạt |
| --- | --- |
| Nhập và lưu | Mô hình thật phân loại câu học phí; có mã và một bản ghi chờ duyệt |
| Nhấn lại | Không thêm dòng trùng trong cùng phiên |
| Sửa nháp | Lưu được nội dung, giữ xuống dòng, bàn duyệt đọc được bản mới |
| Duyệt | Câu rời hàng đợi, lưu nhãn ban đầu và nhãn cuối riêng |
| Duyệt lặp | Không tạo thêm log và không thay kết quả đã lưu |
| Nạp mẫu | Ba mã cố định không bị tạo lại hoặc đặt lại trạng thái |
| Che thông tin | Các ca điện thoại liền/cách/+84, email, mã SV và URL đã thử |
| Thiếu thông tin | Câu ngắn không nhận tài liệu, đề nghị bổ sung |
| Không có căn cứ | Điểm thưởng nhãn không ép câu vô nghĩa khớp KB |
| NaN | Một dòng thiếu chỉ tính một lần là rỗng |
| CSV | Không xuất cột gốc; nội dung thử nghiệm được che; cột dùng chung định nghĩa chất lượng |
| Nguồn tài liệu | Tài liệu chưa xác minh được gắn nhãn minh họa, không tự hẹn trả lời trong 24h |

Chạy lại: python -m unittest discover -s tests -v

Các kiểm thử dùng DB tạm riêng, không xóa dữ liệu người dùng. AppTest kiểm tra thao tác và trạng thái phía Streamlit; không thay thế việc nhóm tự thử bố cục, trình duyệt và máy chiếu trước buổi demo.
