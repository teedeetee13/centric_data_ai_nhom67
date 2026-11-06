# BẢNG TIẾN ĐỘ CÔNG VIỆC (TODO LIST) — DỰ ÁN EDUSUPPORTAI
## Cuộc thi: Centric Data AI 2026 — Khoa CNTT, Trường Đại học Công nghệ Đông Á (EAUT)
**Phương pháp:** Data-Centric AI (DCAI) kết hợp Human-in-the-Loop (HITL)

---

## 1. BẢNG THEO DÕI TIẾN ĐỘ TỔNG QUAN (PROGRESS TRACKER)

| Sprint / Hạng mục | Tổng số tác vụ | Đã hoàn thành | Đang thực hiện | Chưa bắt đầu | Tỷ lệ hoàn thành |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Giai đoạn nền tảng (Vòng 1 PoC)** | 8 | 8 | 0 | 0 | **100%** |
| **Sprint 1: Mở rộng Dữ liệu & Quy chế** | 5 | 0 | 1 | 4 | **0%** |
| **Sprint 2: Lõi AI & Active Learning** | 4 | 0 | 0 | 4 | **0%** |
| **Sprint 3: Cổng Sinh viên & Báo cáo** | 4 | 0 | 0 | 4 | **0%** |
| **Sprint 4: Kiểm chuẩn & Diễn tập Bảo vệ** | 5 | 0 | 0 | 5 | **0%** |
| **TỔNG CỘNG** | **26** | **8** | **1** | **17** | **34.6%** |

---

## 2. PHÂN VAI TRÁCH NHIỆM

- **TV1 (Thành viên 1 - Data & Product Lead):** Phụ trách Dữ liệu, Kho quy chế EAUT, Giao diện Cổng sinh viên & Bàn làm việc cán bộ, Slide thuyết trình và Pitching.
- **TV2 (Thành viên 2 - ML & Architecture Lead):** Phụ trách Pipeline tiền xử lý, Lõi học máy, Active Learning, Webhook Bot tự động, Đo lường kiểm chuẩn kỹ thuật.

---

## 3. CHECKLIST CÔNG VIỆC ĐÃ HOÀN THÀNH (FOUNDATION ASSETS)

- [x] **Tài liệu Thuyết minh Vòng 1:** Hoàn thiện văn bản Word `KCNTT_Mau thuyet minh vong 1.docx` (14 bảng biểu, 6 sơ đồ kiến trúc 200 DPI). *(Cả 2)*
- [x] **Module Tiền xử lý & Che PII:** `src/cleaner.py` chuẩn hóa Unicode NFC, khử trùng MD5/SequenceMatcher, che PII `[PHONE]`, `[EMAIL]`, `[STUDENT_ID]`. *(TV1)*
- [x] **Lõi phân loại học máy:** `src/model.py` trích xuất TF-IDF kép + Logistic Regression đa lớp, lưu tại `models/best_classifier.joblib`. *(TV2)*
- [x] **Engine tri thức quy chế:** `src/faq_engine.py` lập chỉ mục Cosine Similarity 15 điều khoản EAUT, tự động tạo bản nháp có trích dẫn. *(TV2)*
- [x] **Quản trị CSDL Lưu vết:** `src/database.py` khởi tạo SQLite với 4 bảng (`raw_requests`, `processed_requests`, `knowledge_base`, `review_logs`). *(TV1)*
- [x] **Giao diện Bàn làm việc tối giản:** `app/main.py` Streamlit 3 tab không emoji, cơ chế duyệt 1 chạm và kiểm toán hành động cán bộ. *(TV1)*
- [x] **Thống kê dữ liệu thực tế 100%:** `app/components/dashboard.py` phân tích động từ tệp CSV/Excel tải lên hoặc SQLite, không bịa số liệu. *(TV1 & TV2)*
- [x] **Đồng bộ kho mã nguồn:** Dọn dẹp thư mục gốc, đưa tệp phụ trợ vào `docs_tools/`, cấu hình `.gitignore` và push lên GitHub. *(Cả 2)*

---

## 4. CHECKLIST KẾ HOẠCH PHÁT TRIỂN TIẾP THEO THEO SPRINT

### SPRINT 1: MỞ RỘNG DỮ LIỆU THỰC TẾ & KHO TRI THỨC QUY CHẾ (TUẦN 1)

- [ ] **Tác vụ 1.1: Mở rộng kho tri thức quy chế EAUT lên 50 điều khoản**
  - **Người phụ trách:** TV1
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Khảo sát các quy định đào tạo chính thức của EAUT, biên tập thêm 35 điều khoản mới (GPA, cảnh báo học vụ, học bổng khuyến khích, miễn giảm học phí, chuẩn đầu ra, thực tập doanh nghiệp).
  - **Đầu ra:** Tệp `data/kb/eaut_faq_kb.csv` đạt $\ge 50$ bản ghi (`KB001` - `KB050`).
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [/] **Tác vụ 1.2: Thu thập log câu hỏi thực tế ẩn danh tại EAUT**
  - **Người phụ trách:** Cả 2 thành viên
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Tiếp cận các đầu mối Khoa CNTT, Cổng một cửa hỗ trợ sinh viên hoặc các group sinh viên các khóa K12–K15 để thu thập mẫu câu hỏi thực tế.
  - **Đầu ra:** Tệp `data/raw/eaut_real_queries_raw.csv`.
  - **Trạng thái:** `[/] Đang thực hiện`

- [ ] **Tác vụ 1.3: Nâng cấp bộ lọc PII cho văn phong tiếng Việt tự do**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Mở rộng regex trong `src/cleaner.py` bắt các biến thể số điện thoại có khoảng trắng/chấm (`0987 654 321`, `0987.654.321`), các đuôi email khác nhau và MSSV linh hoạt.
  - **Đầu ra:** Tỷ lệ nhận diện và che PII đạt $\ge 98\%$ trên tập câu hỏi gõ tự do.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 1.4: Biên soạn Quy chuẩn gán nhãn (Annotation Guidelines) & Gán nhãn chéo**
  - **Người phụ trách:** TV1 chủ trì, TV2 phản biện
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Xây dựng quy tắc gán nhãn nhất quán cho 7 nhóm chuyên môn; 2 thành viên gán nhãn độc lập trên 100 câu mẫu đầu tiên và tính chỉ số đồng thuận Cohen's Kappa $\ge 0.85$.
  - **Đầu ra:** Tài liệu `docs/annotation_guidelines.md` và tập dữ liệu gán nhãn `data/processed/eaut_labeled_data.csv`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 1.5: Phân chia và niêm phong tập kiểm chuẩn thực tế (Sealed Test Set)**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Tách riêng tập Test Set thực tế phân tầng đều 7 nhóm, niêm phong cố định để đánh giá khách quan cho toàn bộ các mô hình sau này.
  - **Đầu ra:** Tệp `data/splits/test_real_sealed.csv`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

---

### SPRINT 2: VÒNG LẶP ACTIVE LEARNING & TỐI ƯU HÓA LÕI HỌC MÁY (TUẦN 2)

- [ ] **Tác vụ 2.1: Lập trình Module Active Learning tự động trích xuất nhãn từ SQLite**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Viết module `src/active_learning.py` tự động đọc các ca cán bộ chọn `Đổi nhãn & Duyệt` từ bảng `review_logs`, tích lũy thành tập dữ liệu tái huấn luyện mới.
  - **Đầu ra:** Tệp `src/active_learning.py` hoạt động độc lập và sinh `data/splits/retrain_pool.csv`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 2.2: Thiết lập nút Tái huấn luyện 1 chạm trên Bàn làm việc Streamlit**
  - **Người phụ trách:** TV1
  - **Mức ưu tiên:** Trung bình
  - **Mô tả:** Bổ sung nút bấm `Tái huấn luyện mô hình từ dữ liệu đã duyệt` trên giao diện Bàn làm việc, cập nhật trọng số `models/best_classifier.joblib` trong vài giây.
  - **Đầu ra:** Tính năng tái huấn luyện trực tiếp trên Web UI kèm thông báo số lượng mẫu mới học được.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 2.3: Thực nghiệm đối chuẩn các bộ phân loại nâng cao**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Trung bình
  - **Mô tả:** Chạy thực nghiệm so sánh `LogisticRegression`, `LinearSVC (SGDClassifier)` và `LightGBM` trên tập kiểm thử niêm phong thực tế; đo Macro F1 và độ trễ suy luận.
  - **Đầu ra:** Tệp báo cáo `experiments/model_benchmark_comparison.json`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 2.4: Tối ưu hóa Engine tra cứu quy chế học vụ (BM25 + Cosine)**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Kết hợp thuật toán tìm kiếm từ khóa trọng yếu (BM25) với ma trận TF-IDF trong `src/faq_engine.py` để nâng độ chính xác tìm đúng điều khoản quy chế lên $> 90\%$.
  - **Đầu ra:** `src/faq_engine.py` nâng cấp, trả về bản nháp sát nội dung hơn.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

---

### SPRINT 3: CỔNG TIẾP NHẬN SINH VIÊN & BÁO CÁO QUẢN TRỊ (TUẦN 3)

- [ ] **Tác vụ 3.1: Xây dựng Cổng tiếp nhận Sinh viên độc lập (Student Portal Webform)**
  - **Người phụ trách:** TV1
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Lập trình trang webform riêng cho sinh viên gửi phản ánh (giao diện tối giản, thân thiện với điện thoại di động), tự động sinh mã phiếu `Ticket ID (EAUT-2026-XXXX)`.
  - **Đầu ra:** Phân hệ Webform tiếp nhận phản ánh dành cho sinh viên.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 3.2: Tính năng tra cứu trạng thái phản ánh theo mã Ticket ID**
  - **Người phụ trách:** TV1
  - **Mức ưu tiên:** Trung bình
  - **Mô tả:** Cho phép sinh viên nhập mã Ticket để xem trạng thái phản ánh: `Đang xử lý`, `Đã trả lời`, và đọc câu trả lời chính thức từ phòng ban.
  - **Đầu ra:** Chức năng tra cứu phiếu hỗ trợ trực tuyến trên Cổng sinh viên.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 3.3: Tích hợp Webhook tiếp nhận tự động (Telegram Bot / Zalo)**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Trung bình
  - **Mô tả:** Cấu hình bot tiếp nhận tin nhắn sinh viên gửi từ Telegram/Zalo, chạy qua pipeline làm sạch và lưu thẳng vào CSDL SQLite để cán bộ duyệt.
  - **Đầu ra:** Script `src/bot_webhook.py` tiếp nhận tin nhắn tự động.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 3.4: Module Xuất báo cáo quản trị cấp trường (PDF / Excel)**
  - **Người phụ trách:** Cả 2 thành viên
  - **Mức ưu tiên:** Trung bình
  - **Mô tả:** Tổng hợp các xu hướng phản ánh nổi cộm theo tuần/tháng, phân bổ theo từng đơn vị; tạo nút xuất báo cáo tổng hợp dạng PDF/Excel có biểu đồ phục vụ Ban Giám hiệu.
  - **Đầu ra:** Tính năng tải báo cáo quản trị định kỳ tại Tab `Thống kê & Dữ liệu`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

---

### SPRINT 4: KIỂM CHUẨN TOÀN DIỆN, ĐÓNG GÓI SLIDE & LIVE DEMO (TUẦN 4)

- [ ] **Tác vụ 4.1: Đo lường KPI thực nghiệm toàn diện trên Test Set thực tế**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Thực thi chuỗi kiểm chuẩn chính thức, ghi nhận chính xác: Macro F1, Weighted F1, Accuracy, Ma trận nhầm lẫn (Confusion Matrix), Độ trễ (Latency $\le 50$ms), Thông lượng (Throughput).
  - **Đầu ra:** Báo cáo khoa học `experiments/final_kpi_evaluation_report.json`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 4.2: Kiểm thử tải và Thiết lập môi trường chạy 100% Offline**
  - **Người phụ trách:** TV2
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Đảm bảo toàn bộ hệ thống (Streamlit, Model, SQLite, FAQ Engine) có thể khởi chạy và hoạt động trơn tru cục bộ không cần Internet (phòng ngừa rủi ro mất mạng khi bảo vệ).
  - **Đầu ra:** Quy trình đóng gói chạy offline độc lập trên laptop thi đấu.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 4.3: Soạn kịch bản Demo trực tiếp 5 phút trước Giám khảo**
  - **Người phụ trách:** Cả 2 thành viên
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Xây dựng kịch bản 5 phút phân vai rõ ràng: Sinh viên gửi câu hỏi teencode $\rightarrow$ Hệ thống che PII & trích dẫn quy chế $\rightarrow$ Cán bộ duyệt 1 chạm $\rightarrow$ Tải Excel xem Dashboard động $\rightarrow$ Vòng lặp Active Learning tự học.
  - **Đầu ra:** Tài liệu `docs/live_demo_storyboard.md`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 4.4: Thiết kế Slide thuyết trình chuyên nghiệp (Pitch Deck)**
  - **Người phụ trách:** TV1
  - **Mức ưu tiên:** Cao
  - **Mô tả:** Soạn Slide bảo vệ đề tài (15–18 slides) chuẩn nhận diện thương hiệu EAUT (Xanh dương & Cam), làm nổi bật giá trị thực tiễn và tính khả thi của giải pháp.
  - **Đầu ra:** Tệp trình chiếu `EduSupportAI_Pitch_Deck_Centric_AI_2026.pptx` (và PDF).
  - **Trạng thái:** `[ ] Chưa bắt đầu`

- [ ] **Tác vụ 4.5: Quay video clip Demo giới thiệu sản phẩm (3 phút)**
  - **Người phụ trách:** Cả 2 thành viên
  - **Mức ưu tiên:** Trung bình
  - **Mô tả:** Quay video màn hình chất lượng cao kèm thuyết minh tóm tắt luồng hoạt động chính của EduSupportAI phục vụ nộp kèm hồ sơ và dự phòng rủi ro kỹ thuật.
  - **Đầu ra:** Video clip `EduSupportAI_Demo_Video_3Min.mp4`.
  - **Trạng thái:** `[ ] Chưa bắt đầu`

---

## 5. HƯỚNG DẪN CẬP NHẬT TRẠNG THÁI TODO

Khi thực hiện công việc, bạn cập nhật trực tiếp ký hiệu vào ô vuông trong tệp này:
- Chưa bắt đầu: `- [ ]`
- Đang làm: `- [/]`
- Đã hoàn thành: `- [x]`
