# Kịch bản video demo vòng 2 (2 phút 45 giây)

## Chuẩn bị trước khi quay (10 phút)

1. Đóng cửa sổ đen của app nếu đang mở. Đổi tên `EduSupportAI/data/edusupport.db` thành `edusupport_cu.db` để video bắt đầu với hàng chờ trống (không mất dữ liệu cũ).
2. Nhấp đúp `CHAY_DEMO_WINDOWS.bat`, đợi trình duyệt mở. Thanh trạng thái phải ghi **"Mô hình ngôn ngữ cục bộ: bật"**. Nếu chưa, mở ứng dụng Ollama rồi tải lại trang.
3. Gửi thử một câu mẫu bất kỳ để model nạp sẵn (lần đầu chậm), rồi đổi tên lại tệp CSDL như bước 1 và mở lại app để hàng chờ trống.
4. Trình duyệt toàn màn hình (F11), phóng to 110%. Quay bằng Win + Alt + R (Xbox Game Bar) hoặc OBS, 1080p.
5. Mỗi cảnh có thể quay riêng rồi ghép; lời thoại đọc chậm, rõ.

## Kịch bản

| Thời gian | Màn hình | Lời thoại |
| :--- | :--- | :--- |
| 0:00 – 0:15 | Trang chủ app | "Mỗi ngày cố vấn học tập và Phòng Công tác sinh viên nhận rất nhiều câu hỏi về thủ tục: bảo lưu, giấy xác nhận, tạm hoãn nghĩa vụ quân sự. Câu trả lời đúng nằm rải rác trong nhiều văn bản quy trình. EduSupportAI giúp cán bộ trả lời nhanh và đúng quy trình." |
| 0:15 – 0:35 | Mở "Hướng dẫn nhanh", lướt 6 bước | "Nhóm biên tập tài liệu quy trình của trường thành kho 33 quy trình có cấu trúc: điều kiện, hồ sơ, các bước, đơn vị, thời hạn. Đây là trọng tâm data-centric của sản phẩm." |
| 0:35 – 1:15 | Bấm câu mẫu **NVQS (thiếu MSSV)** → Gửi → cuộn qua phiếu ticket và bản nháp | "Sinh viên hỏi về tạm hoãn nghĩa vụ quân sự. Hệ thống ghép đúng quy trình QT19, chỉ ra đơn vị đầu mối, hồ sơ cần chuẩn bị, các bước, hạn xử lý, và nhắc sinh viên còn thiếu mã sinh viên. Bản nháp do mô hình ngôn ngữ chạy ngay trên máy soạn, chỉ dựa vào quy trình; nếu nó đưa ra con số hay tên đơn vị không có trong quy trình, hệ thống tự loại." |
| 1:15 – 1:35 | Bấm **Đối soát học phí** → Gửi → chỉ vào ô nội dung đã che | "Số điện thoại và mã sinh viên được che trước khi lưu. Hệ thống che cả số căn cước, số tài khoản và họ tên." |
| 1:35 – 1:50 | Bấm **Gõ không dấu**, rồi **Ngoài quy trình** | "Câu gõ không dấu vẫn ghép đúng quy trình. Câu không thuộc quy trình nào thì hệ thống không ép ghép, mà chuyển cán bộ xác minh." |
| 1:50 – 2:15 | Tab **Bàn duyệt cán bộ** → chọn yêu cầu → sửa một câu → **Duyệt và lưu** | "Cán bộ xem tài liệu tham chiếu, sửa bản nháp và duyệt. Cán bộ luôn là người quyết định; mọi thao tác được lưu nhật ký." |
| 2:15 – 2:35 | Tab **Dữ liệu và lịch sử** → mở "Kết quả thực nghiệm" | "Giữ nguyên thuật toán, chỉ bổ sung dữ liệu từ quy trình, độ chính xác với câu hỏi công tác sinh viên tăng từ 40% lên 96,7%. Định tuyến đúng 28 trên 30 câu và từ chối đúng 10 trên 10 câu ngoài phạm vi. Mọi số liệu chạy lại được từ mã nguồn." |
| 2:35 – 2:45 | Trang chủ | "EduSupportAI chạy nội bộ, dữ liệu không rời máy chủ của trường, sẵn sàng thí điểm tại Bộ phận Một cửa. Cảm ơn thầy cô đã theo dõi." |

## Lưu ý

- Không dùng thông tin thật của sinh viên trong video; các câu mẫu đều là dữ liệu mô phỏng.
- Nếu bản nháp ra "Bản nháp theo mẫu" thay vì mô hình ngôn ngữ, vẫn quay tiếp và nói "khi không có mô hình ngôn ngữ, hệ thống dùng mẫu câu từ quy trình".
- Quay xong, đổi tên `edusupport_cu.db` về lại nếu muốn giữ dữ liệu cũ.
