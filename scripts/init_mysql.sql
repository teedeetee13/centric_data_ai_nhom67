-- =======================================================================
-- EDUSUPPORT-AI :: HE THONG CO SO DU LIEU MYSQL 8.0 CHO DOCKER & DBEAVER
-- Database: edusupport_db
-- User: root / Password: Skipper11423
-- Character set: utf8mb4 (ho tro tieng Viet co dau, teencode va bieu tuong)
-- =======================================================================

CREATE DATABASE IF NOT EXISTS `edusupport_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `edusupport_db`;

-- 1. BẢNG TIẾP NHẬN & PHÂN LOẠI PHẢN ÁNH SINH VIÊN
CREATE TABLE IF NOT EXISTS `processed_requests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `record_id` VARCHAR(64) UNIQUE NOT NULL COMMENT 'Mã định danh yêu cầu duy nhất',
    `clean_text` TEXT NOT NULL COMMENT 'Nội dung sau khi đã che PII (SĐT, Email, MSSV)',
    `quality_flags` VARCHAR(255) NOT NULL DEFAULT 'CLEAN' COMMENT 'Các cờ chất lượng dữ liệu: has_phone, has_student_id...',
    `is_usable` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1: Hợp lệ để xử lý, 0: Quá ngắn hoặc rỗng',
    `predicted_topic` VARCHAR(64) NOT NULL COMMENT 'Chủ đề học vụ máy học phân loại',
    `confidence_score` FLOAT NOT NULL COMMENT 'Độ tự tin phân loại (0.0 đến 1.0)',
    `priority_level` VARCHAR(32) NOT NULL DEFAULT 'Bình thường' COMMENT 'Khẩn cấp / Cao / Bình thường / Thấp',
    `priority_reason` TEXT NULL COMMENT 'Căn cứ từ khóa phân cấp ưu tiên',
    `department` VARCHAR(128) NOT NULL COMMENT 'Phòng ban / Đơn vị chuyên môn thụ lý',
    `matched_kb_id` VARCHAR(64) NULL COMMENT 'Mã quy trình hoặc điều khoản KB khớp',
    `articles_json` JSON NULL COMMENT 'Chi tiết các điều khoản tương đồng',
    `draft_response` MEDIUMTEXT NOT NULL COMMENT 'Bản nháp câu trả lời tự động hoặc cán bộ soạn',
    `final_topic` VARCHAR(64) NULL COMMENT 'Chủ đề chính thức sau khi cán bộ duyệt',
    `final_response` MEDIUMTEXT NULL COMMENT 'Nội dung phản hồi chính thức gửi sinh viên',
    `source_type` VARCHAR(64) NOT NULL DEFAULT 'portal_student' COMMENT 'portal_student / file_batch / manual_demo',
    `status` VARCHAR(64) NOT NULL DEFAULT 'pending_review' COMMENT 'pending_review / reviewed_approve / reviewed_reject / reviewed_edit_label',
    `processed_at` DATETIME NOT NULL COMMENT 'Thời điểm tiếp nhận',
    `reviewed_at` DATETIME NULL COMMENT 'Thời điểm cán bộ phê duyệt',
    INDEX `idx_req_status` (`status`),
    INDEX `idx_req_topic` (`predicted_topic`),
    INDEX `idx_req_priority` (`priority_level`),
    INDEX `idx_req_department` (`department`),
    INDEX `idx_req_processed_at` (`processed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bảng lưu trữ phản ánh sinh viên';

-- 2. BẢNG LƯU VẾT KIỂM TOÁN CÁN BỘ PHÊ DUYỆT (HUMAN-IN-THE-LOOP AUDIT TRAIL)
CREATE TABLE IF NOT EXISTS `review_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `record_id` VARCHAR(64) NOT NULL COMMENT 'Mã yêu cầu được duyệt',
    `officer_action` VARCHAR(64) NOT NULL COMMENT 'approve / reject / edit_label',
    `original_predicted_topic` VARCHAR(64) NOT NULL COMMENT 'Chủ đề ban đầu máy dự đoán',
    `final_topic` VARCHAR(64) NOT NULL COMMENT 'Chủ đề sau khi cán bộ chốt',
    `final_response` MEDIUMTEXT NOT NULL COMMENT 'Nội dung trả lời chính thức',
    `officer_notes` TEXT NULL COMMENT 'Ghi chú nghiệp vụ của cán bộ',
    `reviewed_at` DATETIME NOT NULL COMMENT 'Thời điểm duyệt',
    INDEX `idx_rev_record` (`record_id`),
    INDEX `idx_rev_action` (`officer_action`),
    INDEX `idx_rev_reviewed_at` (`reviewed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Nhật ký kiểm toán thao tác duyệt của cán bộ';

-- 3. BẢNG KHO TRI THỨC ĐIỀU KHOẢN QUY CHẾ HỌC VỤ (FAQ KNOWLEDGE BASE)
CREATE TABLE IF NOT EXISTS `knowledge_base` (
    `kb_id` VARCHAR(64) PRIMARY KEY COMMENT 'Mã điều khoản quy chế KB001-KB015...',
    `topic` VARCHAR(64) NOT NULL COMMENT 'Chủ đề quy chế',
    `question_standard` TEXT NOT NULL COMMENT 'Tiêu đề câu hỏi chuẩn hóa',
    `content_extract` MEDIUMTEXT NOT NULL COMMENT 'Trích dẫn nội dung quy định',
    `department` VARCHAR(128) NOT NULL COMMENT 'Đơn vị phụ trách',
    `effective_date` VARCHAR(32) NULL DEFAULT '2025-08-15' COMMENT 'Ngày ban hành',
    `source_url` TEXT NULL COMMENT 'Căn cứ văn bản pháp lý',
    `verified` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1: Đã xác minh chính thức, 0: Minh họa',
    INDEX `idx_kb_topic` (`topic`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Kho tri thức quy chế mẫu';

-- 4. BẢNG QUY TRÌNH NGHIỆP VỤ CHÍNH THỨC TRÍCH XUẤT TỪ DATA-DOC (PROCEDURES CATALOG)
CREATE TABLE IF NOT EXISTS `procedures_kb` (
    `proc_id` VARCHAR(64) PRIMARY KEY COMMENT 'Mã quy trình: PROC_DT_01, PROC_CTSV_01...',
    `title` VARCHAR(255) NOT NULL COMMENT 'Tên quy trình nghiệp vụ',
    `topic` VARCHAR(64) NOT NULL COMMENT 'Lĩnh vực phụ trách',
    `department` VARCHAR(128) NOT NULL COMMENT 'Phòng ban đầu mối giải quyết',
    `legal_basis` VARCHAR(255) NOT NULL COMMENT 'Căn cứ văn bản: Quyết định số 348, QĐ 118...',
    `processing_time` VARCHAR(128) NOT NULL COMMENT 'Thời hạn giải quyết: 02 ngày, 22 ngày...',
    `forms_required` TEXT NOT NULL COMMENT 'Mã biểu mẫu cần chuẩn bị: BM01a, BM_CN01...',
    `target_users` TEXT NOT NULL COMMENT 'Đối tượng sinh viên áp dụng',
    `steps_json` JSON NOT NULL COMMENT 'Chi tiết các bước thực hiện tuần tự 1, 2, 3...',
    `sample_queries_json` JSON NOT NULL COMMENT 'Mẫu câu hỏi huấn luyện mô hình',
    `content_extract` MEDIUMTEXT NOT NULL COMMENT 'Trích đoạn hướng dẫn giải quyết',
    `updated_at` DATETIME NOT NULL COMMENT 'Thời điểm cập nhật quy trình',
    INDEX `idx_proc_topic` (`topic`),
    INDEX `idx_proc_dept` (`department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Kho 15 quy trình nghiệp vụ chuẩn hóa từ data-doc';

-- 5. BẢNG NHẬT KÝ THỰC THI & TRUY VẾT MINH BẠCH (EXECUTION & LLM TRACE LOGS)
CREATE TABLE IF NOT EXISTS `execution_traces` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `record_id` VARCHAR(64) NOT NULL COMMENT 'Mã yêu cầu tương ứng',
    `trace_id` VARCHAR(64) NOT NULL COMMENT 'Mã Trace định danh duy nhất',
    `steps_json` JSON NOT NULL COMMENT 'Dữ liệu đo lường 5 bước kỹ thuật dạng JSON',
    `terminal_log` MEDIUMTEXT NOT NULL COMMENT 'Toàn bộ nội dung Terminal Console Log',
    `created_at` DATETIME NOT NULL COMMENT 'Thời điểm ghi nhận trace',
    INDEX `idx_tr_record` (`record_id`),
    INDEX `idx_tr_trace` (`trace_id`),
    INDEX `idx_tr_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Nhật ký đo lường và suy luận minh bạch của Local Machine & LLM';

-- 6. BẢNG NHẬT KÝ GỬI EMAIL PHẢN HỒI KẾT QUẢ CHO SINH VIÊN
CREATE TABLE IF NOT EXISTS `email_dispatches` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `record_id` VARCHAR(64) NULL,
    `recipient_email` VARCHAR(255) NOT NULL COMMENT 'Địa chỉ email người nhận',
    `subject` VARCHAR(255) NOT NULL COMMENT 'Tiêu đề email',
    `body_text` MEDIUMTEXT NOT NULL COMMENT 'Nội dung thông báo giải quyết',
    `dispatch_mode` VARCHAR(64) NOT NULL COMMENT 'auto_approved / officer_approved / test_manual',
    `status` VARCHAR(64) NOT NULL COMMENT 'sent / simulation / failed',
    `error_message` TEXT NULL,
    `sent_at` DATETIME NOT NULL,
    INDEX `idx_em_record` (`record_id`),
    INDEX `idx_em_email` (`recipient_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lịch sử gửi email tự động';
