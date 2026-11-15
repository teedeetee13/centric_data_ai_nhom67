# HƯỚNG DẪN KẾT NỐI VÀ QUẢN TRỊ MYSQL (DOCKER) TRÊN DBEAVER
## Dành cho Hệ thống EduSupportAI — Centric Data AI 2026

Hệ thống **EduSupportAI** đã được tích hợp toàn diện với cơ sở dữ liệu **MySQL 8.0 (Docker)** và đồng bộ 100% dữ liệu với cơ chế **Dual-Engine (SQLite & MySQL)**. Bạn có thể mở **DBeaver** để xem, chỉnh sửa và quản lý trực tiếp dữ liệu theo hướng dẫn dưới đây.

---

### 1. THÔNG SỐ KẾT NỐI DBEAVER

Khi mở ứng dụng **DBeaver**, bạn tạo một kết nối mới (**New Connection**) chọn loại **MySQL**:

| Thông số cấu hình | Giá trị cài đặt | Ghi chú |
| :--- | :--- | :--- |
| **Connection Type** | **MySQL** | Chọn driver MySQL 8.0 mặc định trong DBeaver |
| **Host / Server** | `127.0.0.1` (hoặc `localhost`) | Địa chỉ Docker MySQL đang chạy |
| **Port** | `3306` | Cổng mặc định đã được ánh xạ |
| **Database** | `edusupport_db` | Tên cơ sở dữ liệu chính thức của dự án |
| **Authentication** | Database native / Password | |
| **Username** | `root` | Tài khoản quản trị |
| **Password** | `Skipper11423` | Mật khẩu truy cập |

> **Mẹo trên DBeaver:** Nếu gặp lỗi *Public Key Retrieval is not allowed*, trong cửa sổ kết nối DBeaver: chọn tab **Driver properties** -> tìm thuộc tính `allowPublicKeyRetrieval` và chuyển thành `true`, chọn `useSSL` thành `false`.

---

### 2. CẤU TRÚC 6 BẢNG DỮ LIỆU ĐÃ CÓ TRONG MYSQL

Cơ sở dữ liệu `edusupport_db` bao gồm đầy đủ 6 bảng nghiệp vụ:

1. **`procedures_kb` (Kho 15 quy trình nghiệp vụ chuẩn EAUT từ data-doc):**
   * Lưu trữ toàn bộ 15 quy trình chính thức trích xuất từ 3 file docx (`bao_cao_tong_hop_quy_trinh_dao_tao.docx`, `baocao-quanly-csvc-eaut.docx`, `bao_cao_quy_trinh_nghiep_vu_sinh_vien_eaut.docx`).
   * Chứa số Quyết định/Thông báo pháp lý, thời gian giải quyết cam kết, biểu mẫu cần nộp (`BM_CN01`, `BM01a`...), các bước tuần tự 1, 2, 3... dưới dạng JSON.
2. **`processed_requests` (Danh sách Ticket phản ánh học vụ sinh viên):**
   * Chứa hơn 420+ bản ghi yêu cầu đã được làm sạch và che giấu PII (`[PHONE]`, `[EMAIL]`, `[STUDENT_ID]`), nhãn chuyên môn phân loại, độ tự tin (Confidence), mức ưu tiên, và trạng thái duyệt.
3. **`review_logs` (Nhật ký kiểm toán cán bộ duyệt — Human-in-the-Loop):**
   * Lưu vết mọi thao tác duyệt của cán bộ: Duyệt & gửi, Đổi nhãn chuyên môn, Từ chối/Spam, kèm ghi chú nghiệp vụ và thời gian chính xác.
4. **`execution_traces` (Nhật ký thực thi minh bạch của Local Machine & LLM):**
   * Lưu vết toàn bộ tiến trình đo lường 5 bước kỹ thuật tính bằng mili-giây và toàn bộ văn bản **Terminal Console Log** của mỗi lần máy học suy luận.
5. **`knowledge_base` (Kho câu hỏi FAQ điều khoản quy chế):**
   * Danh mục câu hỏi đáp quy chế học vụ mẫu (`KB001` - `KB015`).
6. **`email_dispatches` (Lịch sử gửi email thông báo):**
   * Lưu vết toàn bộ email giải pháp tự động hoặc cán bộ duyệt đã gửi tới sinh viên.

---

### 3. CÁC CÂU LỆNH SQL HỮU ÍCH ĐỂ TRA CỨU TRÊN DBEAVER

Mở **SQL Editor** trong DBeaver và chạy các truy vấn mẫu sau:

#### A. Tra cứu 15 Quy trình nghiệp vụ EAUT từ data-doc:
```sql
USE edusupport_db;

-- Xem danh sách tất cả các quy trình nghiệp vụ EAUT
SELECT 
    proc_id,
    title AS 'Tên quy trình',
    department AS 'Đơn vị thụ lý',
    legal_basis AS 'Căn cứ văn bản',
    processing_time AS 'Thời hạn xử lý',
    forms_required AS 'Biểu mẫu yêu cầu'
FROM procedures_kb
ORDER BY proc_id ASC;
```

#### B. Xem Hàng đợi Bàn duyệt cán bộ (Review Queue - Các ca chờ duyệt):
```sql
USE edusupport_db;

-- Lọc các yêu cầu đang chờ cán bộ rà soát, sắp xếp theo mức độ khẩn cấp
SELECT 
    record_id,
    clean_text AS 'Nội dung (Đã che PII)',
    predicted_topic AS 'Chuyên môn dự đoán',
    ROUND(confidence_score * 100, 1) AS 'Độ tin cậy (%)',
    priority_level AS 'Ưu tiên',
    department AS 'Phòng ban phụ trách',
    quality_flags AS 'Cờ chất lượng',
    processed_at AS 'Thời điểm gửi'
FROM processed_requests
WHERE status = 'pending_review'
ORDER BY 
    CASE priority_level 
        WHEN 'Khẩn cấp' THEN 1 
        WHEN 'Cao' THEN 2 
        WHEN 'Bình thường' THEN 3 
        ELSE 4 
    END,
    processed_at DESC;
```

#### C. Xem Nhật ký Trace Log của Local Machine & LLM:
```sql
USE edusupport_db;

-- Xem nhật ký đo lường và suy luận gần nhất
SELECT 
    id,
    record_id,
    trace_id,
    created_at,
    terminal_log
FROM execution_traces
ORDER BY id DESC
LIMIT 5;
```

#### D. Thống kê tỷ lệ phản ánh theo từng phòng ban và mức ưu tiên:
```sql
USE edusupport_db;

SELECT 
    department AS 'Phòng ban thụ lý',
    COUNT(*) AS 'Tổng số yêu cầu',
    SUM(CASE WHEN priority_level = 'Khẩn cấp' THEN 1 ELSE 0 END) AS 'Khẩn cấp',
    SUM(CASE WHEN priority_level = 'Cao' THEN 1 ELSE 0 END) AS 'Cao',
    ROUND(AVG(confidence_score) * 100, 1) AS 'Độ tin cậy TB (%)'
FROM processed_requests
GROUP BY department
ORDER BY COUNT(*) DESC;
```

---

### 4. ĐỒNG BỘ HOẶC CHẠY LẠI MIGRATION KHI CẦN

Nếu bạn muốn nạp lại toàn bộ dữ liệu mới nhất từ file Word trong `data-doc` hoặc từ SQLite vào MySQL:
```bash
/home/kennysk/centric_data_ai_nhom67/venv/bin/python /home/kennysk/centric_data_ai_nhom67/scripts/migrate_to_mysql.py
```
Script sẽ tự động kiểm tra đối soát và đồng bộ toàn bộ bảng vào MySQL.
Mọi yêu cầu mới gửi qua Streamlit Web App (`app/main.py`) sẽ được tự động ghi nhận song song vào cả SQLite và Docker MySQL theo thời gian thực!
