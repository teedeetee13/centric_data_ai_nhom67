# Kịch bản demo EduSupportAI khoảng năm phút

## Trước khi bắt đầu

Chạy app, mở trình duyệt tại localhost:8501, chọn tab Tiếp nhận yêu cầu. Chuẩn bị video dự phòng từ bản này. Không dùng thông tin sinh viên thật.

## Phút 0 đến 1

Nói: “EduSupportAI hỗ trợ cán bộ tiếp nhận yêu cầu sinh viên, phân loại và chuẩn bị bản nháp có tài liệu tham khảo. Cán bộ quyết định câu trả lời cuối cùng.”

Input: nội dung câu hỏi. Output: bản đã che thông tin, nhóm, confidence, ưu tiên, đơn vị gợi ý, tài liệu và bản nháp. Nêu rõ bản hiện tại dùng dữ liệu mô phỏng, chưa gửi email.

## Phút 1 đến 3

1. Chọn Học phí, bấm Phân tích và lưu.
2. Đọc đúng mã REQ trên màn hình. Chỉ ra [STUDENT_ID] và nhóm Học phí.
3. Nói: “Confidence là điểm mô hình, chưa phải độ chính xác thực tế. Cán bộ vẫn kiểm tra.”
4. Mở phần tham chiếu, chỉ rõ tài liệu minh họa chưa xác minh.
5. Sửa bản nháp thành: “Chào bạn, bộ phận hỗ trợ đã tiếp nhận yêu cầu kiểm tra công nợ. Cán bộ sẽ xác minh giao dịch và hướng dẫn bước tiếp theo. Trân trọng.” Bấm Lưu bản nháp.
6. Mở Bàn duyệt cán bộ, kiểm tra đúng mã và nội dung vừa sửa. Bấm Duyệt và lưu.
7. Mở Dữ liệu và lịch sử, chỉ ra bản ghi và nhật ký đã lưu. Không nói đã gửi email.

## Phút 3 đến 4

Chọn Tạm hoãn NVQS (thiếu MSSV), bấm Phân tích và lưu. Mở Phiếu xử lý ticket: chỉ ra đơn vị đầu mối (Bộ phận Một cửa P.CTSV), hồ sơ cần chuẩn bị, các bước theo tài liệu quy trình, hạn xử lý dự kiến và cảnh báo "Sinh viên cần bổ sung: Mã sinh viên". Nói: "Quy trình lấy từ tài liệu nghiệp vụ của trường; bản nháp do mô hình ngôn ngữ chạy ngay trên máy soạn, chỉ dựa trên quy trình đó. Nếu mô hình đưa ra con số hay mã biểu mẫu không có trong quy trình, hệ thống loại bản nháp và dùng bản theo mẫu."

Chọn Thiếu thông tin, bấm Phân tích và lưu. Chỉ ra hệ thống không tìm quy chế cho câu “Giúp em với” mà đề nghị bổ sung thông tin.

Nếu còn thời gian: mở tab Dữ liệu và lịch sử, bấm Kiểm tra và che thông tin, xem bảng và tải CSV đã che. Các số đếm được tính trên cùng pipeline; cờ lỗi có thể chồng nhau.

## Phút 4 đến 5

Nói: “Phân loại dùng TF-IDF từ và ký tự kết hợp Logistic Regression. Gợi ý nội dung dùng truy xuất TF-IDF/cosine và mẫu câu. Nhóm tập trung chất lượng dữ liệu và kiểm duyệt con người.”

Nói đúng giới hạn: bộ dữ liệu 424 dòng là mô phỏng; tài liệu chưa xác minh; tập đánh giá theo nhóm còn nhỏ. Thử nghiệm mới không cho thấy tăng F1 khi lọc dữ liệu. Vì vậy, chưa thể khẳng định hiệu quả thực tế hoặc AI chính xác 100%.

## Khi được hỏi

- Vì sao không dùng ChatGPT? Dữ liệu sinh viên không rời khỏi máy: mô hình ngôn ngữ (qwen2.5:3b qua Ollama) chạy cục bộ, không cần API key. Mô hình chỉ viết lại câu chữ từ quy trình đã truy xuất; con số, biểu mẫu, căn cứ được kiểm tra đối chiếu với quy trình, và bản nháp LLM luôn qua cán bộ duyệt.
- Data-centric thể hiện ở đâu? Giữ nguyên thuật toán, chỉ bổ sung 183 câu mẫu biên tập từ tài liệu quy trình: độ chính xác với câu hỏi công tác sinh viên tăng từ 40% lên 96,7%, tập niêm phong giữ nguyên, tập văn phong thực tế giảm nhẹ 1 câu (86,7% xuống 84,4%). Bảng số liệu có trong tab Dữ liệu và lịch sử.
- Định tuyến quy trình chính xác đến đâu? Trên 40 câu nhóm tự viết khác câu mẫu: đúng 28/30 câu trong phạm vi, từ chối đúng 10/10 câu ngoài phạm vi. Tập còn nhỏ, chưa phải dữ liệu thật.
- Đã kết nối Odoo/Gmail chưa? Chưa, input hiện nhập trực tiếp; tích hợp là giai đoạn sau.
- Có tự học từ log không? Chưa, log dùng để lưu vết và có thể hỗ trợ chuẩn bị dữ liệu cho lần huấn luyện sau.
- Dữ liệu trường ở đâu? Hiện là dữ liệu mô phỏng, nhóm cần xin dữ liệu đã ẩn danh và nguồn tài liệu để đánh giá tiếp.

Nếu buổi trình diễn gặp lỗi: nói rõ lỗi vận hành, mở video quay từ bản chạy thật. Không dùng bản dựng hoặc kết quả cố định để thay cho dự đoán mà không giải thích.
