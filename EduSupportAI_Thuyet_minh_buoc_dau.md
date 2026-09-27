# EduSupportAI

## Trợ lý hỗ trợ giải đáp sinh viên

*Cuộc thi Centric Data AI 2026 - Lĩnh vực Giáo dục và cộng đồng*

| Thông tin | Nội dung |
|---|---|
| Tên nhóm | Trải ây ai |
| Trưởng nhóm | Trần Đức Trường - 20233802 |
| Thành viên | Trần Long Vũ - 20233780 |
| Giảng viên hướng dẫn | ThS. Ngô Thùy Giang |
| Trạng thái | Bản thuyết minh bước đầu |

# Tóm tắt đề xuất

EduSupportAI hỗ trợ cố vấn học tập và cán bộ Công tác sinh viên xử lý yêu cầu của sinh viên nhanh và nhất quán hơn. Hệ thống tiếp nhận nội dung từ biểu mẫu, email hoặc tệp dữ liệu; phát hiện và che thông tin cá nhân; phân loại chủ đề; gợi ý mức ưu tiên và đơn vị xử lý; tìm nội dung liên quan trong kho tri thức; sau đó tạo bản nháp trả lời để cán bộ kiểm tra trước khi gửi.

Sản phẩm không phụ thuộc Odoo hay Gmail. MVP sử dụng giao diện web chạy trên máy cá nhân và nhập trực tiếp hoặc tải tệp CSV/XLSX. Sau cuộc thi, hệ thống có thể tích hợp với email, cổng sinh viên hoặc phần mềm quản lý yêu cầu khác.

Đóng góp Data Centric AI nằm ở việc tạo quy trình dữ liệu có thể kiểm tra: lưu dữ liệu thô và dữ liệu đã làm sạch, ghi nguồn, che PII, loại trùng, chuẩn hóa nhãn, đo chất lượng và lưu chỉnh sửa của cán bộ để cải thiện hệ thống.

## Bốn căn cứ của hồ sơ vòng loại

| Tiêu chí | Cách đề tài đáp ứng | Bằng chứng cần hoàn thành |
|---|---|---|
| Ý tưởng và tiềm năng | Giảm thời gian đọc, phân loại, tìm hướng dẫn và soạn trả lời | Một tình huống demo đi hết quy trình |
| Khả thi kỹ thuật | Dùng Python, Pandas, scikit-learn, Streamlit và SQLite; chạy cục bộ | MVP chạy được trên máy nhóm |
| Khả thi kế hoạch | Phạm vi giới hạn ở một luồng hỗ trợ có cán bộ phê duyệt | Backlog, người phụ trách và mốc kiểm tra |
| Khả thi dữ liệu | Có dữ liệu yêu cầu, kho tri thức, quy tắc nhãn và lịch sử chỉnh sửa | Dataset có nguồn, label guide và chỉ số trước/sau |

# Bài toán thực tế

Sinh viên gửi câu hỏi qua nhiều kênh với cách diễn đạt không thống nhất. Một yêu cầu có thể thiếu thông tin, viết tắt, không dấu, chứa dữ liệu cá nhân hoặc được gửi lặp lại. Người tiếp nhận phải đọc, xác định chủ đề, tìm quy định liên quan, chuyển đúng đơn vị và soạn câu trả lời. Công việc này lặp lại và dễ thiếu nhất quán khi số lượng yêu cầu tăng.

Người dùng chính của MVP là:

- Cố vấn học tập.
- Cán bộ Công tác sinh viên.
- Bộ phận tiếp nhận và phân luồng yêu cầu.

Sinh viên là người hưởng lợi nhưng không phải người phê duyệt câu trả lời của hệ thống.

## Tình huống demo cốt lõi

Sinh viên nhập: “Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 2023xxxx”.

Hệ thống phải tạo được kết quả:

1. Che mã sinh viên.
2. Phân loại `Học phí`.
3. Gợi ý mức ưu tiên và Phòng Tài chính - Kế toán.
4. Truy xuất hướng dẫn đối soát học phí trong kho tri thức.
5. Tạo bản nháp trả lời.
6. Cho cán bộ sửa và xác nhận trước khi gửi.
7. Lưu phần cán bộ đã sửa để làm dữ liệu cải thiện.

# Phạm vi MVP

## Chức năng bắt buộc

| Mã | Chức năng | Đạt khi |
|---|---|---|
| F01 | Nhập một yêu cầu hoặc tải CSV/XLSX | Đọc được dữ liệu mẫu và báo lỗi khi sai cấu trúc |
| F02 | Kiểm tra chất lượng | Phát hiện trống, quá ngắn, trùng và PII |
| F03 | Làm sạch và che PII | Tạo `clean_text` và `quality_flags` |
| F04 | Phân loại yêu cầu | Trả về chủ đề và confidence |
| F05 | Gợi ý ưu tiên và đơn vị | Có mức ưu tiên và lý do giải thích được |
| F06 | Tra cứu kho tri thức | Hiển thị tài liệu đã dùng để tạo gợi ý |
| F07 | Tạo bản nháp trả lời | Bản nháp có thể sửa, không gửi tự động |
| F08 | Human in the loop | Lưu nhãn hoặc câu trả lời đã sửa |
| F09 | Xuất kết quả | Tải được dữ liệu đã ẩn danh và nhật ký rà soát |

## Không làm trong phiên bản đầu

- Không tích hợp trực tiếp Odoo hoặc Gmail.
- Không tự gửi câu trả lời cho sinh viên.
- Không tự ra quyết định hành chính.
- Không xây ứng dụng di động.
- Không huấn luyện mô hình ngôn ngữ lớn riêng.
- Không tuyên bố nội dung demo là quy định chính thức của nhà trường.

# Thiết kế dữ liệu

## Dữ liệu yêu cầu sinh viên

| Trường | Ý nghĩa |
|---|---|
| request_id | Mã kỹ thuật không chứa danh tính |
| raw_text | Nội dung ban đầu |
| clean_text | Nội dung sau chuẩn hóa và che PII |
| category | Nhãn chủ đề chuẩn |
| priority | Mức ưu tiên |
| target_unit | Đơn vị tiếp nhận |
| source_type | Nguồn thật, nhóm biên soạn hoặc AI hỗ trợ |
| quality_flags | Lỗi dữ liệu được phát hiện |
| label_source | Người hoặc quy trình tạo nhãn |

## Kho tri thức

| Trường | Ý nghĩa |
|---|---|
| kb_id | Mã tài liệu |
| category | Chủ đề liên quan |
| title | Tên hướng dẫn |
| content | Nội dung dùng để tham khảo trả lời |
| source | Nguồn và người xác nhận |
| valid_from | Ngày bắt đầu hiệu lực nếu có |
| valid_to | Ngày hết hiệu lực nếu có |

## Lịch sử cán bộ rà soát

| Trường | Ý nghĩa |
|---|---|
| request_id | Yêu cầu được xử lý |
| predicted_category | Nhãn AI đề xuất |
| reviewed_category | Nhãn cán bộ xác nhận |
| draft_answer | Bản nháp hệ thống tạo |
| approved_answer | Nội dung sau khi cán bộ sửa |
| review_status | Phê duyệt, sửa hoặc từ chối |
| review_note | Lý do sửa |

## Bộ nhãn ban đầu

1. Học phí.
2. Lịch học và lịch thi.
3. Điểm và khảo thí.
4. Thủ tục hành chính.
5. Cơ sở vật chất.
6. Hệ thống kỹ thuật.
7. Khác.

Nhóm chỉ giữ bảy nhãn nếu mỗi nhãn có đủ ví dụ và ranh giới rõ. Nếu hai nhãn thường xuyên bị nhầm và không có đủ dữ liệu, nhóm sẽ gộp nhãn.

# Quy trình Data Centric AI

| Bước | Thao tác | Bằng chứng lưu lại |
|---|---|---|
| 1 | Thu thập và ghi nguồn | File thô và `source_type` |
| 2 | Phát hiện dữ liệu lỗi | `quality_flags` và báo cáo số lượng |
| 3 | Che email, số điện thoại, mã sinh viên | Dữ liệu đã ẩn danh |
| 4 | Chuẩn hóa văn bản | `clean_text` |
| 5 | Phát hiện trùng | Danh sách bản ghi gộp hoặc loại |
| 6 | Gán nhãn theo hướng dẫn | Label guide và lịch sử gán nhãn |
| 7 | Chia train/test sau khi loại trùng | Tập đánh giá không bị rò rỉ |
| 8 | Chạy baseline và các thí nghiệm | Kết quả E0-E3 |
| 9 | Lưu sửa đổi của cán bộ | Dữ liệu cải thiện cho vòng tiếp theo |

## Nguồn dữ liệu khả thi

- Các tình huống nhóm tự biên soạn để phát triển phần mềm; phải gắn `source_type=controlled_demo`.
- Các câu hỏi tự nguyện, đã thông báo mục đích và không yêu cầu danh tính.
- Các câu hỏi công khai hoặc nội dung quy định mà nhóm có quyền sử dụng; phải lưu nguồn.
- Dữ liệu do AI hỗ trợ chỉ dùng để tăng biến thể câu chữ, phải được người kiểm tra và không thay thế tập đánh giá thật.

## Chỉ số cần đo

| Nhóm | Chỉ số |
|---|---|
| Chất lượng dữ liệu | Tỷ lệ hợp lệ, trùng, PII còn sót, phân bố lớp |
| Chất lượng nhãn | Cohen Kappa trên phần hai người gán độc lập |
| Phân loại | Macro F1, F1 từng lớp và ma trận nhầm lẫn |
| Tra cứu | Tỷ lệ tài liệu liên quan nằm trong kết quả đầu |
| Bản nháp | Tỷ lệ được dùng, tỷ lệ phải sửa nhiều và lý do sửa |
| Hiệu quả | Thời gian xử lý một yêu cầu trước và sau khi dùng MVP |

# Công nghệ và phiên bản chạy được

| Thành phần | Lựa chọn |
|---|---|
| Giao diện | Streamlit |
| Xử lý dữ liệu | Python và Pandas |
| Phân loại | TF-IDF và Logistic Regression |
| Tra cứu ban đầu | Lọc theo chủ đề và điểm khớp từ khóa |
| Lưu rà soát | SQLite |
| Kiểm thử | unittest |
| Quản lý phiên bản | Git và GitHub |

Phiên bản khởi đầu đã có luồng kiểm tra dữ liệu, phân loại, gợi ý ưu tiên, tra cứu kho tri thức mẫu và tạo bản nháp trả lời. Kho tri thức hiện chỉ là dữ liệu minh họa và phải được thay bằng nội dung có nguồn, được người có trách nhiệm xác nhận trước khi trình bày như thông tin chính thức.

# Thí nghiệm

| Mã | Thay đổi dữ liệu | Câu hỏi cần trả lời |
|---|---|---|
| E0 | Dữ liệu gần nguyên bản | Baseline phân loại là bao nhiêu |
| E1 | Chuẩn hóa, che PII và loại trùng | Làm sạch cải thiện kết quả thế nào |
| E2 | Nhãn được hai người rà soát | Chất lượng nhãn đóng góp bao nhiêu |
| E3 | Bổ sung mẫu khó hoặc cân bằng lớp | Các lớp yếu có được cải thiện không |

Nhóm giữ nguyên tập kiểm thử giữa các thí nghiệm và không dùng dữ liệu kiểm thử để chỉnh quy tắc làm sạch.

# Kế hoạch thực hiện

| Thời gian | Công việc | Đầu ra kiểm tra được |
|---|---|---|
| 26-27/09 | Khóa phạm vi, tạo GitHub, chạy MVP mẫu | Repository và video/ảnh chạy đầu tiên |
| 27-28/09 | Chốt nhãn, data dictionary, tạo 50-100 mẫu kiểm soát | Dataset v0.1 và label guide |
| 28-29/09 | Chạy baseline, kiểm tra pipeline, bổ sung kho tri thức | Kết quả E0 và 10-20 mục kiến thức có nguồn |
| 29-30/09 | Cập nhật thuyết minh, kiểm thử demo | Bản nộp vòng loại và checklist lỗi |
| 01/10 | Nộp và gắn Git tag | Bản nộp được lưu cố định |
| 05-11/10 | Thu tối thiểu 300 mẫu tự nguyện đã ẩn danh | Dataset v1 |
| 08-15/10 | Gán chéo, giải quyết bất đồng | Label guide v1 và Cohen Kappa |
| 14-20/10 | Chạy E0-E3 và phân tích lỗi | Bảng kết quả và confusion matrix |
| 18-24/10 | Hoàn thiện giao diện và lưu sửa đổi | MVP ổn định |
| 25-26/10 | Slide, video dự phòng và luyện trả lời | Bộ chung kết |

# Phân công hai thành viên

| Người phụ trách | Công việc chính | Bằng chứng đóng góp |
|---|---|---|
| Trần Đức Trường | Quản lý GitHub, tích hợp app, báo cáo và demo | Pull Request, phiên bản chạy và tài liệu |
| Trần Long Vũ | Dataset, label guide, kho tri thức và kiểm thử tình huống | CSV, tài liệu nhãn, test case và Pull Request |

Hai thành viên cùng gán độc lập ít nhất 20% dữ liệu để đo độ thống nhất. Mọi công việc phải đi qua Issue và Pull Request; không gửi file qua lại bằng tên `final`, `final2` hoặc `mới nhất`.

# Rủi ro chính

| Rủi ro | Cách xử lý |
|---|---|
| Thiếu dữ liệu thật | Thu sớm; giảm số nhãn; không dùng dữ liệu demo để tuyên bố hiệu quả thật |
| Kho tri thức sai hoặc hết hạn | Lưu nguồn và ngày hiệu lực; bắt buộc cán bộ phê duyệt |
| Nhãn chồng lấn | Viết label guide, gán chéo và ghi quyết định xử lý trường hợp biên |
| Lộ PII | Không thu danh tính; che tự động; kiểm tra thủ công trước khi công bố |
| Điểm số cao giả tạo | Loại trùng trước khi chia train/test; giữ test cố định |
| Quá tải chức năng | Chỉ hoàn thiện F01-F09; hoãn tích hợp hệ thống bên ngoài |
| AI trả lời sai | Hiển thị nguồn; không gửi tự động; người phụ trách duyệt |

# Kết quả cần có khi trình diễn

1. Nhập một yêu cầu sinh viên có lỗi gõ và PII.
2. Hệ thống hiển thị dữ liệu đã che và cờ chất lượng.
3. Hệ thống dự đoán chủ đề, confidence, ưu tiên và đơn vị xử lý.
4. Hệ thống hiển thị tài liệu được truy xuất.
5. Hệ thống tạo bản nháp trả lời.
6. Cán bộ sửa hoặc từ chối bản nháp.
7. Hệ thống lưu kết quả rà soát.
8. Nhóm mở bảng E0-E3 để chứng minh dữ liệu được cải thiện có hệ thống.

# Giới hạn và nguyên tắc sử dụng

- EduSupportAI là công cụ hỗ trợ, không thay thế người chịu trách nhiệm.
- Không gửi bản nháp tự động cho sinh viên.
- Không sử dụng dữ liệu cá nhân thật trong bản công khai hoặc demo.
- Không trình bày dữ liệu demo là khảo sát thật.
- Không trình bày nội dung kho tri thức mẫu là quy định chính thức.
- Mọi kết quả thi phải tái lập được từ mã nguồn, phiên bản dữ liệu và lệnh chạy đã lưu.

# Thuật ngữ ngắn

| Thuật ngữ | Giải thích |
|---|---|
| Data Centric AI | Cải thiện AI bằng cách cải thiện dữ liệu có hệ thống |
| MVP | Phiên bản nhỏ nhất chứng minh luồng giá trị chính |
| PII | Thông tin có thể nhận diện cá nhân |
| Baseline | Kết quả ban đầu dùng làm mốc so sánh |
| Macro F1 | Điểm F1 trung bình của các lớp với trọng số bằng nhau |
| Human in the loop | Con người kiểm tra và sửa đầu ra hệ thống |
| Knowledge base | Kho thông tin có nguồn dùng để hỗ trợ trả lời |

