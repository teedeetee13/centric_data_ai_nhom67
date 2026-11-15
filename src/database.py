# -*- coding: utf-8 -*-
"""
Module: src.database
Quản trị cơ sở dữ liệu SQLite cục bộ cho EduSupportAI.
Tích hợp cơ chế phòng thủ:
- Tự động che giấu PII (safe_text) trước khi lưu dữ liệu tự do
- Giao dịch nguyên tử (atomic verification) chống bấm đúp khi duyệt
- Lưu vết kiểm toán toàn diện (audit trail) phục vụ Human-in-the-Loop & Active Learning
"""

import os
import csv
import json
import sqlite3
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.cleaner import mask_pii
from src.config import KB_PATH, TOPICS, database_path
try:
    from src.app_logger import app_log
except ImportError:
    def app_log(*args, **kwargs):
        pass

class ClosingConnection(sqlite3.Connection):
    """Đảm bảo kết nối CSDL luôn được đóng an toàn khi ra khỏi context manager."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

def now():
    """Lấy thời điểm hiện tại dạng chuỗi ISO múi giờ địa phương (UTC+7)."""
    return datetime.now().astimezone().isoformat(timespec='seconds')

def format_datetime_vn(val, fmt='%Y-%m-%d %H:%M:%S'):
    """Chuyển đổi chuỗi thời gian (ISO UTC hoặc địa phương) sang giờ chuẩn Việt Nam."""
    if not val:
        return "-"
    val = str(val).strip()
    try:
        if 'T' in val or '+' in val or val.endswith('Z'):
            clean_iso = val.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_iso)
            if dt.tzinfo is not None:
                dt = dt.astimezone()
            return dt.strftime(fmt)
        else:
            return val[:19]
    except Exception:
        return val.replace('T', ' ')[:19]

def get_connection(db_path=None):
    """Khởi tạo kết nối SQLite với row_factory và ClosingConnection."""
    path = Path(db_path) if db_path is not None else database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn

def safe_text(value, mask_pii_flag=True):
    """Chuẩn hóa văn bản. Nếu mask_pii_flag=True, che giấu PII; nếu False, bảo toàn nguyên vẹn nội dung."""
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize('NFC', value)
    text = '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.split('\n')).strip()
    if mask_pii_flag:
        return mask_pii(text)[0]
    return text

def init_db(db_path=None):
    """Khởi tạo toàn bộ cấu trúc các bảng CSDL SQLite."""
    with get_connection(db_path) as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS processed_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE NOT NULL,
            clean_text TEXT NOT NULL,
            quality_flags TEXT NOT NULL,
            is_usable INTEGER NOT NULL,
            predicted_topic TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            priority_level TEXT NOT NULL,
            priority_reason TEXT NOT NULL,
            department TEXT NOT NULL,
            matched_kb_id TEXT,
            articles_json TEXT NOT NULL,
            draft_response TEXT NOT NULL,
            final_topic TEXT,
            final_response TEXT,
            source_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_review',
            processed_at TEXT NOT NULL,
            reviewed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS review_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            officer_action TEXT NOT NULL,
            original_predicted_topic TEXT NOT NULL,
            final_topic TEXT NOT NULL,
            final_response TEXT NOT NULL,
            officer_notes TEXT NOT NULL,
            reviewed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS knowledge_base (
            kb_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            question_standard TEXT NOT NULL,
            content_extract TEXT NOT NULL,
            department TEXT NOT NULL,
            effective_date TEXT,
            source_url TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS email_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_text TEXT NOT NULL,
            dispatch_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            sent_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS execution_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            steps_json TEXT NOT NULL,
            terminal_log TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS procedures_kb (
            proc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            topic TEXT NOT NULL,
            department TEXT NOT NULL,
            legal_basis TEXT NOT NULL,
            processing_time TEXT NOT NULL,
            forms_required TEXT NOT NULL,
            target_users TEXT NOT NULL,
            steps_json TEXT NOT NULL,
            sample_queries_json TEXT NOT NULL,
            content_extract TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS library_books (
            book_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            publisher TEXT NOT NULL,
            publish_year INTEGER NOT NULL,
            location TEXT NOT NULL,
            call_number TEXT NOT NULL,
            total_copies INTEGER NOT NULL,
            available_copies INTEGER NOT NULL,
            is_digital INTEGER DEFAULT 1,
            digital_url TEXT DEFAULT 'https://lib.cndonga.edu.vn',
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS library_borrows (
            borrow_id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            book_id TEXT NOT NULL,
            book_title TEXT NOT NULL,
            borrow_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL,
            renew_count INTEGER DEFAULT 0,
            fine_amount INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (book_id) REFERENCES library_books (book_id)
        );
        ''')

        # Tự động di chuyển (migration) cấu trúc bảng nếu dùng tệp CSDL cũ
        cursor = conn.execute("PRAGMA table_info(knowledge_base)")
        kb_cols = [r[1] for r in cursor.fetchall()]
        if kb_cols and 'source_url' not in kb_cols:
            conn.execute("ALTER TABLE knowledge_base ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
        if kb_cols and 'verified' not in kb_cols:
            conn.execute("ALTER TABLE knowledge_base ADD COLUMN verified INTEGER NOT NULL DEFAULT 0")

        cursor = conn.execute("PRAGMA table_info(processed_requests)")
        req_cols = [r[1] for r in cursor.fetchall()]
        if 'raw_text' in req_cols:
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS processed_requests_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                clean_text TEXT NOT NULL,
                quality_flags TEXT NOT NULL,
                is_usable INTEGER NOT NULL,
                predicted_topic TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                priority_level TEXT NOT NULL,
                priority_reason TEXT NOT NULL DEFAULT '',
                department TEXT NOT NULL DEFAULT '',
                matched_kb_id TEXT,
                articles_json TEXT NOT NULL DEFAULT '[]',
                draft_response TEXT NOT NULL,
                final_topic TEXT,
                final_response TEXT,
                source_type TEXT NOT NULL DEFAULT 'manual_demo',
                status TEXT NOT NULL DEFAULT 'pending_review',
                processed_at TEXT NOT NULL,
                reviewed_at TEXT
            );
            INSERT OR IGNORE INTO processed_requests_new (id, record_id, clean_text, quality_flags, is_usable, predicted_topic, confidence_score, priority_level, matched_kb_id, draft_response, status, processed_at)
            SELECT id, record_id, clean_text, quality_flags, is_usable, predicted_topic, confidence_score, priority_level, matched_kb_id, draft_response, status, processed_at
            FROM processed_requests;
            DROP TABLE processed_requests;
            ALTER TABLE processed_requests_new RENAME TO processed_requests;
            ''')
        elif req_cols:
            for col_name, col_def in [
                ('priority_reason', "TEXT NOT NULL DEFAULT ''"),
                ('department', "TEXT NOT NULL DEFAULT ''"),
                ('articles_json', "TEXT NOT NULL DEFAULT '[]'"),
                ('final_topic', "TEXT DEFAULT NULL"),
                ('final_response', "TEXT DEFAULT NULL"),
                ('source_type', "TEXT NOT NULL DEFAULT 'manual_demo'"),
                ('reviewed_at', "TEXT DEFAULT NULL")
            ]:
                if col_name not in req_cols:
                    conn.execute(f"ALTER TABLE processed_requests ADD COLUMN {col_name} {col_def}")
        
    # Tự động nạp dữ liệu mẫu Thư viện (OPAC & Sổ mượn trả) nếu bảng còn trống
    seed_library_data_if_empty(db_path=db_path)

def sync_kb_from_csv(csv_path=None, db_path=None):
    """Đồng bộ kho tri thức quy chế từ CSV vào SQLite."""
    path = Path(csv_path) if csv_path else KB_PATH
    if not path.exists():
        return
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    with get_connection(db_path) as conn:
        for row in rows:
            source = str(row.get('source_url', '')).strip()
            verified = str(row.get('verified', '')).lower() in ('true', '1', 'yes') and bool(source)
            conn.execute('''INSERT INTO knowledge_base (kb_id, topic, question_standard, content_extract, department, effective_date, source_url, verified)
              VALUES (?,?,?,?,?,?,?,?)
              ON CONFLICT(kb_id) DO UPDATE SET topic=excluded.topic,
              question_standard=excluded.question_standard,content_extract=excluded.content_extract,
              department=excluded.department,effective_date=excluded.effective_date,
              source_url=excluded.source_url,verified=excluded.verified''',
              (row['kb_id'], row['topic'], row['question_standard'], row['content_extract'],
               row['department'], row.get('effective_date', '2025-08-15'), source, int(verified)))

def mysql_now():
    """Lấy thời điểm hiện tại dạng chuỗi DATETIME chuẩn MySQL theo giờ địa phương."""
    return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')

def sync_record_to_mysql(table: str, data: dict):
    """Đồng bộ một bản ghi sang Docker MySQL nếu dịch vụ MySQL đang mở."""
    if os.environ.get("EDUSUPPORT_DB_PATH"):
        # Đang trong phiên test biệt lập SQLite, không ghi vào MySQL
        return
    try:
        from src.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
            password=MYSQL_PASSWORD, database=MYSQL_DB, charset='utf8mb4',
            connect_timeout=1, autocommit=True
        )
        with conn.cursor() as cur:
            keys = list(data.keys())
            placeholders = ", ".join(["%s"] * len(keys))
            cols = ", ".join(f"`{k}`" for k in keys)
            updates = ", ".join(f"`{k}`=VALUES(`{k}`)" for k in keys if k not in ('id', 'created_at', 'processed_at'))
            query = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"
            cur.execute(query, list(data.values()))
        conn.close()
    except Exception:
        pass

def save_request(result, record_id=None, source_type='manual_demo', mask_pii=None, db_path=None):
    """Lưu yêu cầu phản ánh mới sau khi qua xử lý vào CSDL (SQLite & MySQL).
    Hỗ trợ tùy chọn mask_pii: Mặc định không che đối với cổng sinh viên (source_type='portal_student') hoặc khi mask_pii=False."""
    record_id = record_id or ('REQ_' + uuid4().hex[:12].upper())
    flags = result.get('quality_flags', [])
    if not isinstance(flags, str):
        flags = ';'.join(flags) if flags else 'CLEAN'

    should_mask = True
    if mask_pii is False or result.get('mask_pii') is False or source_type == 'portal_student':
        should_mask = False

    clean_content = safe_text(result['clean_text'], mask_pii_flag=should_mask)
    draft_content = safe_text(result.get('procedure_draft_response') or result.get('draft_response', ''), mask_pii_flag=should_mask)

    with get_connection(db_path) as conn:
        conn.execute('''INSERT INTO processed_requests
          (record_id, clean_text, quality_flags, is_usable, predicted_topic, confidence_score,
           priority_level, priority_reason, department, matched_kb_id, articles_json, draft_response,
           source_type, status, processed_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'pending_review',?)
          ON CONFLICT(record_id) DO NOTHING''',
          (record_id, clean_content, flags, int(result['is_usable']),
           result['predicted_topic'], result['confidence_score'], result['priority_level'],
           result.get('priority_reason', 'Rà soát thường quy'), result['department'],
           result.get('matched_kb_id'), json.dumps(result.get('articles', []), ensure_ascii=False),
           draft_content, source_type, now()))

    # Tự động đồng bộ sang MySQL (Docker)
    sync_record_to_mysql("processed_requests", {
        "record_id": record_id,
        "clean_text": clean_content,
        "quality_flags": flags,
        "is_usable": int(result['is_usable']),
        "predicted_topic": result['predicted_topic'],
        "confidence_score": float(result['confidence_score']),
        "priority_level": result['priority_level'],
        "priority_reason": result.get('priority_reason', 'Rà soát thường quy'),
        "department": result['department'],
        "matched_kb_id": result.get('matched_kb_id'),
        "articles_json": json.dumps(result.get('articles', []), ensure_ascii=False),
        "draft_response": draft_content,
        "source_type": source_type,
        "status": "pending_review",
        "processed_at": mysql_now()
    })

    # Lưu vết Execution Trace nếu có
    if 'execution_trace' in result or 'terminal_log' in result:
        trace_data = result.get('execution_trace', {})
        t_id = trace_data.get('trace_id', f"TRACE_{uuid4().hex[:8].upper()}")
        t_log = result.get('terminal_log', '')
        save_execution_trace(record_id, t_id, json.dumps(trace_data, ensure_ascii=False), t_log, db_path=db_path)

    app_log("DATABASE", "Lưu bản ghi yêu cầu mới vào CSDL", f"Mã: [{record_id}], Chuyên môn: [{result.get('predicted_topic')}], Độ tin cậy: {result.get('confidence_score', 0):.1%}, Nguồn: {source_type}", level="SUCCESS")
    return record_id

def save_execution_trace(record_id, trace_id, steps_json, terminal_log, db_path=None):
    """Lưu nhật ký thực thi minh bạch (Trace Log) của máy học vào CSDL (SQLite & MySQL)."""
    with get_connection(db_path) as conn:
        conn.execute('''INSERT INTO execution_traces
          (record_id, trace_id, steps_json, terminal_log, created_at)
          VALUES (?,?,?,?,?)''',
          (record_id, trace_id, steps_json, terminal_log, now()))

    # Tự động đồng bộ sang MySQL (Docker)
    sync_record_to_mysql("execution_traces", {
        "record_id": record_id,
        "trace_id": trace_id,
        "steps_json": steps_json if isinstance(steps_json, str) else json.dumps(steps_json, ensure_ascii=False),
        "terminal_log": terminal_log,
        "created_at": mysql_now()
    })

def get_execution_trace(record_id, db_path=None):
    """Lấy Trace Log gần nhất của một bản ghi yêu cầu."""
    with get_connection(db_path) as conn:
        row = conn.execute('SELECT * FROM execution_traces WHERE record_id=? ORDER BY id DESC LIMIT 1', (record_id,)).fetchone()
    return dict(row) if row else None

def list_execution_traces(limit=50, db_path=None):
    """Lấy danh sách các Trace Logs gần nhất của hệ thống."""
    with get_connection(db_path) as conn:
        rows = conn.execute('SELECT * FROM execution_traces ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return [dict(row) for row in rows]

def sync_procedures_kb(procedures=None, db_path=None):
    """Đồng bộ danh mục quy trình nghiệp vụ từ data-doc vào bảng procedures_kb."""
    if procedures is None:
        from src.doc_parser import build_procedure_catalog
        procedures = build_procedure_catalog()
    stamp = now()
    with get_connection(db_path) as conn:
        for p in procedures:
            conn.execute('''INSERT INTO procedures_kb
              (proc_id, title, topic, department, legal_basis, processing_time, forms_required, target_users, steps_json, sample_queries_json, content_extract, updated_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(proc_id) DO UPDATE SET
                title=excluded.title, topic=excluded.topic, department=excluded.department,
                legal_basis=excluded.legal_basis, processing_time=excluded.processing_time,
                forms_required=excluded.forms_required, target_users=excluded.target_users,
                steps_json=excluded.steps_json, sample_queries_json=excluded.sample_queries_json,
                content_extract=excluded.content_extract, updated_at=excluded.updated_at''',
              (p['proc_id'], p['title'], p['topic'], p['department'], p.get('legal_basis', ''),
               p.get('processing_time', ''), p.get('forms_required', ''), p.get('target_users', ''),
               json.dumps(p.get('steps', []), ensure_ascii=False),
               json.dumps(p.get('sample_queries', []), ensure_ascii=False),
               p.get('content_extract', ''), stamp))

def list_procedures_kb(topic=None, db_path=None):
    """Truy vấn danh mục quy trình đã nạp từ data-doc."""
    where = "WHERE topic=?" if topic else ""
    params = (topic,) if topic else ()
    with get_connection(db_path) as conn:
        rows = conn.execute(f"SELECT * FROM procedures_kb {where} ORDER BY proc_id ASC", params).fetchall()
    return [dict(row) for row in rows]

def get_request(record_id, db_path=None):
    """Truy vấn thông tin một yêu cầu theo mã record_id."""
    with get_connection(db_path) as conn:
        row = conn.execute('SELECT * FROM processed_requests WHERE record_id=?', (record_id,)).fetchone()
    return dict(row) if row else None

def list_requests(pending_only=False, db_path=None, order_by='date_desc'):
    """Lấy danh sách các yêu cầu trong CSDL, mặc định sắp xếp theo thứ tự ngày đăng mới nhất."""
    where = "WHERE status='pending_review'" if pending_only else ''
    if order_by == 'priority':
        order_clause = "CASE priority_level WHEN 'Khẩn cấp' THEN 1 WHEN 'Cao' THEN 2 WHEN 'Bình thường' THEN 3 ELSE 4 END, processed_at DESC, id DESC"
    elif order_by == 'date_asc':
        order_clause = "processed_at ASC, id ASC"
    elif order_by == 'date_desc':
        order_clause = "processed_at DESC, id DESC"
    else:
        order_clause = order_by

    with get_connection(db_path) as conn:
        rows = conn.execute(f'''SELECT * FROM processed_requests {where}
          ORDER BY {order_clause}''').fetchall()
    return [dict(row) for row in rows]

def save_draft(record_id, draft_text, db_path=None):
    """Lưu bản nháp phản hồi đã được chỉnh sửa cho một yêu cầu đang chờ duyệt."""
    cleaned_draft = safe_text(draft_text)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE processed_requests SET draft_response=? WHERE record_id=? AND status='pending_review'",
            (cleaned_draft, record_id)
        )
        if cur.rowcount != 1:
            raise ValueError('Yêu cầu đã được duyệt hoặc không còn tồn tại. Hãy tải lại danh sách.')

    sync_record_to_mysql("processed_requests", {
        "record_id": record_id,
        "draft_response": cleaned_draft
    })
    app_log("WORKBENCH", "Cán bộ cập nhật bản nháp phản hồi", f"Mã yêu cầu: [{record_id}], Độ dài nháp: {len(cleaned_draft)} ký tự", level="INFO")

def log_review_action(record_id, officer_action, original_topic, final_topic, final_response, notes='', db_path=None):
    """
    Ghi nhận hành động phê duyệt / hiệu chỉnh của cán bộ vào bảng review_logs.
    Thực hiện kiểm tra nguyên tử để ngăn chặn việc duyệt lặp lại.
    """
    if officer_action not in ('approve', 'edit_label', 'reject') or final_topic not in TOPICS:
        raise ValueError('Thao tác hoặc nhóm phân loại không hợp lệ.')
    if officer_action != 'reject' and not final_response.strip():
        raise ValueError('Cần có nội dung trả lời trước khi duyệt.')
    
    response = safe_text(final_response)
    notes_clean = safe_text(notes)
    stamp = now()
    
    with get_connection(db_path) as conn:
        cur = conn.execute('''UPDATE processed_requests
          SET status=?, final_topic=?, final_response=?, reviewed_at=?
          WHERE record_id=? AND status='pending_review' ''',
          ('reviewed_' + officer_action, final_topic, response, stamp, record_id))
        if cur.rowcount != 1:
            raise ValueError('Yêu cầu đã được duyệt. Không ghi thêm nhật ký trùng.')
        
        actual_row = conn.execute('SELECT predicted_topic FROM processed_requests WHERE record_id=?', (record_id,)).fetchone()
        actual = actual_row[0] if actual_row else original_topic
        
        conn.execute('''INSERT INTO review_logs
          (record_id, officer_action, original_predicted_topic, final_topic, final_response, officer_notes, reviewed_at)
          VALUES (?,?,?,?,?,?,?)''',
          (record_id, officer_action, actual, final_topic, response, notes_clean, stamp))

    # Tự động đồng bộ hành động duyệt sang MySQL (Docker)
    sync_record_to_mysql("review_logs", {
        "record_id": record_id,
        "officer_action": officer_action,
        "original_predicted_topic": actual,
        "final_topic": final_topic,
        "final_response": response,
        "officer_notes": notes_clean,
        "reviewed_at": mysql_now()
    })
    app_log("WORKBENCH", f"Cán bộ hoàn tất kiểm duyệt [{officer_action}]", f"Mã yêu cầu: [{record_id}], Chuyên môn cuối: [{final_topic}]", level="SUCCESS")
    sync_record_to_mysql("processed_requests", {
        "record_id": record_id,
        "status": 'reviewed_' + officer_action,
        "final_topic": final_topic,
        "final_response": response,
        "reviewed_at": mysql_now()
    })

def review_history(db_path=None):
    """Lấy toàn bộ lịch sử kiểm toán cán bộ duyệt từ bảng review_logs."""
    with get_connection(db_path) as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM review_logs ORDER BY id DESC').fetchall()]

# ==============================================================================
# PHÂN HỆ CSDL THƯ VIỆN EAUT (LIBRARY DATABASE & OPAC CATALOG)
# Phục vụ tra cứu dữ liệu thời gian thực theo đúng quy trình PROC_CSVC_03
# ==============================================================================

SAMPLE_LIBRARY_BOOKS = [
    {
        "book_id": "BK_IT_001",
        "title": "Giáo trình Kỹ thuật phần mềm",
        "author": "PGS.TS. Trần Đình Quế",
        "category": "Công nghệ thông tin",
        "publisher": "NXB Bách Khoa Hà Nội",
        "publish_year": 2022,
        "location": "Kệ A3 - Tầng 2 Thư viện EAUT",
        "call_number": "005.1 / GT-KTPM",
        "total_copies": 10,
        "available_copies": 3,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/ky-thuat-phan-mem",
        "description": "Chu trình phát triển phần mềm, quy trình Agile/Scrum, thiết kế kiến trúc và kiểm thử phần mềm."
    },
    {
        "book_id": "BK_IT_002",
        "title": "Giáo trình Hệ quản trị Cơ sở dữ liệu và SQL",
        "author": "TS. Nguyễn Kim Anh",
        "category": "Công nghệ thông tin",
        "publisher": "NXB ĐHQG Hà Nội",
        "publish_year": 2021,
        "location": "Kệ A2 - Tầng 2 Thư viện EAUT",
        "call_number": "005.74 / GT-CSDL",
        "total_copies": 12,
        "available_copies": 5,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/co-so-du-lieu",
        "description": "Mô hình thực thể kết hợp ERD, chuẩn hóa dữ liệu 1NF-3NF, tối ưu hóa câu lệnh SQL và quản trị giao dịch."
    },
    {
        "book_id": "BK_IT_003",
        "title": "Lập trình Python căn bản và ứng dụng Trí tuệ nhân tạo (AI)",
        "author": "TS. Lê Hoàng Sơn",
        "category": "Công nghệ thông tin",
        "publisher": "NXB Khoa học Kỹ thuật",
        "publish_year": 2023,
        "location": "Kệ A4 - Tầng 2 Thư viện EAUT",
        "call_number": "005.13 / PY-AI",
        "total_copies": 8,
        "available_copies": 2,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/python-ai",
        "description": "Lập trình Python từ cơ bản, tiền xử lý dữ liệu với Pandas, trực quan hóa và huấn luyện Machine Learning."
    },
    {
        "book_id": "BK_IT_004",
        "title": "Giáo trình Cấu trúc dữ liệu và Giải thuật",
        "author": "PGS. Đỗ Xuân Lôi",
        "category": "Công nghệ thông tin",
        "publisher": "NXB ĐHQG Hà Nội",
        "publish_year": 2020,
        "location": "Kệ A2 - Tầng 2 Thư viện EAUT",
        "call_number": "005.1 / GT-CTDL",
        "total_copies": 15,
        "available_copies": 0,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/ctdl-gt",
        "description": "Các cấu trúc dữ liệu mảng, danh sách liên kết, cây nhị phân, đồ thị và giải thuật tìm kiếm, sắp xếp."
    },
    {
        "book_id": "BK_IT_005",
        "title": "Giáo trình Mạng máy tính và An toàn thông tin",
        "author": "ThS. Vũ Đức Anh",
        "category": "Công nghệ thông tin",
        "publisher": "NXB Thông tin & Truyền thông",
        "publish_year": 2022,
        "location": "Kệ A5 - Tầng 2 Thư viện EAUT",
        "call_number": "004.6 / MMT-ATTT",
        "total_copies": 8,
        "available_copies": 4,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/mang-may-tinh",
        "description": "Mô hình phân tầng OSI/TCP-IP, cấu hình mạng LAN/VLAN, mã hóa SSL và bảo vệ hệ thống trước tấn công mạng."
    },
    {
        "book_id": "BK_KT_001",
        "title": "Giáo trình Nguyên lý Kế toán",
        "author": "PGS.TS. Nguyễn Phú Giang",
        "category": "Kinh tế & Quản trị",
        "publisher": "NXB Tài chính",
        "publish_year": 2022,
        "location": "Kệ B1 - Tầng 2 Thư viện EAUT",
        "call_number": "657 / GT-NLKT",
        "total_copies": 14,
        "available_copies": 6,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/nguyen-ly-ke-toan",
        "description": "Bản chất kế toán, phương pháp chứng từ, tài khoản kế toán, tính giá thành và lập báo cáo tài chính."
    },
    {
        "book_id": "BK_KT_002",
        "title": "Giáo trình Quản trị Kinh doanh đại cương",
        "author": "GS.TS. Nguyễn Thành Độ",
        "category": "Kinh tế & Quản trị",
        "publisher": "NXB ĐH Kinh tế Quốc dân",
        "publish_year": 2021,
        "location": "Kệ B2 - Tầng 2 Thư viện EAUT",
        "call_number": "658 / GT-QTKD",
        "total_copies": 10,
        "available_copies": 4,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/quan-tri-kinh-doanh",
        "description": "Môi trường kinh doanh, hoạch định chiến lược, thiết kế cơ cấu tổ chức và quản trị chuỗi cung ứng."
    },
    {
        "book_id": "BK_KT_003",
        "title": "Giáo trình Kinh tế vi mô",
        "author": "PGS.TS. Vũ Kim Dũng",
        "category": "Kinh tế & Quản trị",
        "publisher": "NXB ĐH Kinh tế Quốc dân",
        "publish_year": 2023,
        "location": "Kệ B1 - Tầng 2 Thư viện EAUT",
        "call_number": "338.5 / GT-KTVM",
        "total_copies": 12,
        "available_copies": 7,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/kinh-te-vi-mo",
        "description": "Cung cầu thị trường, hành vi tiêu dùng và sản xuất, các mô hình thị trường độc quyền và cạnh tranh hoàn hảo."
    },
    {
        "book_id": "BK_CK_001",
        "title": "Giáo trình Nguyên lý và Chi tiết máy",
        "author": "PGS.TS. Nguyễn Trọng Hiệp",
        "category": "Kỹ thuật - Cơ khí",
        "publisher": "NXB Giáo dục",
        "publish_year": 2021,
        "location": "Kệ C1 - Tầng 2 Thư viện EAUT",
        "call_number": "621.8 / GT-CTM",
        "total_copies": 8,
        "available_copies": 3,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/chi-tiet-may",
        "description": "Tính toán và thiết kế bộ truyền đai, xích, bánh răng, trục, ổ lăn và các mối ghép hàn, then, bulông."
    },
    {
        "book_id": "BK_CK_002",
        "title": "Giáo trình Vẽ kỹ thuật cơ khí & CAD 2D/3D",
        "author": "TS. Trần Hữu Quế",
        "category": "Kỹ thuật - Cơ khí",
        "publisher": "NXB Khoa học Kỹ thuật",
        "publish_year": 2022,
        "location": "Kệ C2 - Tầng 2 Thư viện EAUT",
        "call_number": "604.2 / GT-VKT",
        "total_copies": 10,
        "available_copies": 5,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/ve-ky-thuat-cad",
        "description": "Tiêu chuẩn bản vẽ kỹ thuật, quy tắc biểu diễn hình chiếu, mặt cắt, dung sai lắp ghép và thực hành vẽ CAD."
    },
    {
        "book_id": "BK_NN_001",
        "title": "Tiếng Anh chuyên ngành Công nghệ thông tin (English for IT)",
        "author": "Khoa Ngoại ngữ & CNTT EAUT",
        "category": "Ngoại ngữ & Kỹ năng",
        "publisher": "NXB ĐHQG Hà Nội",
        "publish_year": 2023,
        "location": "Kệ D1 - Tầng 2 Thư viện EAUT",
        "call_number": "428.24 / ENG-IT",
        "total_copies": 20,
        "available_copies": 11,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/english-for-it",
        "description": "Thuật ngữ tiếng Anh chuyên ngành CNTT, kỹ năng đọc tài liệu API, viết email công việc và tài liệu kỹ thuật."
    },
    {
        "book_id": "BK_CB_001",
        "title": "Giáo trình Toán Giải tích 1 & 2 dành cho sinh viên kỹ thuật",
        "author": "GS.TS. Nguyễn Đình Trí",
        "category": "Khoa học cơ bản",
        "publisher": "NXB Giáo dục",
        "publish_year": 2022,
        "location": "Kệ E1 - Tầng 2 Thư viện EAUT",
        "call_number": "515 / GT-GT1",
        "total_copies": 18,
        "available_copies": 8,
        "is_digital": 1,
        "digital_url": "https://lib.cndonga.edu.vn/tai-lieu/giai-tich-ky-thuat",
        "description": "Hàm một biến, đạo hàm vi phân, tích phân suy rộng, chuỗi số và phương trình vi phân ứng dụng trong kỹ thuật."
    }
]

SAMPLE_LIBRARY_BORROWS = [
    {
        "borrow_id": "BOR_2026_001",
        "student_id": "2022601234",
        "student_name": "Nguyễn Văn An",
        "book_id": "BK_IT_001",
        "book_title": "Giáo trình Kỹ thuật phần mềm",
        "borrow_date": "2026-11-10",
        "due_date": "2026-11-17",
        "return_date": None,
        "status": "Đang mượn",
        "renew_count": 0,
        "fine_amount": 0,
        "notes": "Mượn trực tiếp tại quầy thủ thư Tầng 2"
    },
    {
        "borrow_id": "BOR_2026_002",
        "student_id": "2022601234",
        "student_name": "Nguyễn Văn An",
        "book_id": "BK_IT_003",
        "book_title": "Lập trình Python căn bản và ứng dụng Trí tuệ nhân tạo (AI)",
        "borrow_date": "2026-11-08",
        "due_date": "2026-11-15",
        "return_date": None,
        "status": "Đang mượn",
        "renew_count": 1,
        "fine_amount": 0,
        "notes": "Đã gia hạn trực tuyến 1 lần qua cổng lib.cndonga.edu.vn"
    },
    {
        "borrow_id": "BOR_2026_003",
        "student_id": "2021600123",
        "student_name": "Trần Thị Mai",
        "book_id": "BK_KT_001",
        "book_title": "Giáo trình Nguyên lý Kế toán",
        "borrow_date": "2026-10-20",
        "due_date": "2026-10-27",
        "return_date": None,
        "status": "Quá hạn",
        "renew_count": 0,
        "fine_amount": 90000,
        "notes": "Quá hạn 18 ngày, tài khoản tạm thời khóa quyền mượn sách mới đến khi nộp phạt"
    },
    {
        "borrow_id": "BOR_2026_004",
        "student_id": "2023602111",
        "student_name": "Lê Hoàng Long",
        "book_id": "BK_CB_001",
        "book_title": "Giáo trình Toán Giải tích 1 & 2 dành cho sinh viên kỹ thuật",
        "borrow_date": "2026-10-15",
        "due_date": "2026-10-22",
        "return_date": "2026-10-21",
        "status": "Đã trả",
        "renew_count": 0,
        "fine_amount": 0,
        "notes": "Đã hoàn trả tài liệu nguyên vẹn tại quầy thủ thư"
    },
    {
        "borrow_id": "BOR_2026_005",
        "student_id": "2022605555",
        "student_name": "Phạm Minh Đức",
        "book_id": "BK_CK_001",
        "book_title": "Giáo trình Nguyên lý và Chi tiết máy",
        "borrow_date": "2026-10-29",
        "due_date": "2026-11-05",
        "return_date": None,
        "status": "Quá hạn",
        "renew_count": 0,
        "fine_amount": 45000,
        "notes": "Quá hạn 9 ngày, cần hoàn trả và thanh toán phí phạt 45.000đ tại quầy thủ thư"
    }
]

def strip_vietnamese_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để tìm kiếm mờ không phân biệt dấu và chữ hoa/thường."""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    return text.replace('đ', 'd').replace('Đ', 'D').lower()

def seed_library_data_if_empty(db_path=None):
    """Nạp danh mục sách và sổ mượn trả mẫu nếu bảng còn trống."""
    with get_connection(db_path) as conn:
        book_count = conn.execute("SELECT count(*) FROM library_books").fetchone()[0]
        if book_count == 0:
            for b in SAMPLE_LIBRARY_BOOKS:
                conn.execute('''INSERT OR IGNORE INTO library_books
                  (book_id, title, author, category, publisher, publish_year, location, call_number, total_copies, available_copies, is_digital, digital_url, description)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (b['book_id'], b['title'], b['author'], b['category'], b['publisher'], b['publish_year'],
                   b['location'], b['call_number'], b['total_copies'], b['available_copies'],
                   b['is_digital'], b['digital_url'], b['description']))

        borrow_count = conn.execute("SELECT count(*) FROM library_borrows").fetchone()[0]
        if borrow_count == 0:
            for br in SAMPLE_LIBRARY_BORROWS:
                conn.execute('''INSERT OR IGNORE INTO library_borrows
                  (borrow_id, student_id, student_name, book_id, book_title, borrow_date, due_date, return_date, status, renew_count, fine_amount, notes)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (br['borrow_id'], br['student_id'], br['student_name'], br['book_id'], br['book_title'],
                   br['borrow_date'], br['due_date'], br['return_date'], br['status'],
                   br['renew_count'], br['fine_amount'], br['notes']))

def search_library_books(query: str = '', category: str = None, limit: int = 10, db_path=None):
    """
    Tìm kiếm sách trong CSDL Thư viện EAUT:
    Hỗ trợ tìm kiếm theo tiêu đề, tác giả, chuyên ngành, vị trí kệ, hỗ trợ cả có dấu và không dấu.
    """
    with get_connection(db_path) as conn:
        if not query and not category:
            rows = conn.execute("SELECT * FROM library_books ORDER BY category, title LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

        clean_q = query.strip() if query else ''
        clean_q_unaccent = strip_vietnamese_accents(clean_q)

        sql = "SELECT * FROM library_books WHERE 1=1"
        params = []

        if category and category != 'Tất cả':
            sql += " AND category = ?"
            params.append(category)

        all_rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

        if not clean_q:
            return all_rows[:limit]

        # Lọc kết hợp: khớp chuỗi gốc và khớp không dấu
        matched = []
        for book in all_rows:
            raw_target = f"{book['title']} {book['author']} {book['category']} {book['call_number']} {book['description']}".lower()
            unaccent_target = strip_vietnamese_accents(raw_target)

            if clean_q.lower() in raw_target or clean_q_unaccent in unaccent_target:
                matched.append(book)
                continue

            # Khớp từng từ khóa nếu cụm từ dài
            words = [w for w in clean_q_unaccent.split() if len(w) > 2]
            if words and all(w in unaccent_target for w in words):
                matched.append(book)

        return matched[:limit]

def get_library_book(book_id: str, db_path=None):
    """Lấy thông tin chi tiết một đầu sách theo mã tài liệu."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM library_books WHERE book_id = ?", (book_id,)).fetchone()
        return dict(row) if row else None

def get_student_library_borrows(student_id: str, db_path=None):
    """
    Tra cứu lịch sử và tình trạng mượn sách của sinh viên theo MSSV.
    Tự động cập nhật số ngày quá hạn và tiền phạt (5.000 VNĐ / ngày theo PROC_CSVC_03).
    """
    clean_sid = str(student_id).strip()
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM library_borrows WHERE student_id = ? ORDER BY borrow_date DESC",
            (clean_sid,)
        ).fetchall()

        results = []
        today = datetime.now().date()
        for r in rows:
            item = dict(r)
            status = item.get('status', 'Đang mượn')
            due_str = item.get('due_date', '')

            if status != 'Đã trả' and due_str:
                try:
                    due_d = datetime.strptime(due_str, '%Y-%m-%d').date()
                    if today > due_d:
                        overdue_days = (today - due_d).days
                        item['status'] = 'Quá hạn'
                        item['overdue_days'] = overdue_days
                        item['fine_amount'] = overdue_days * 5000
                    else:
                        item['days_remaining'] = (due_d - today).days
                        item['fine_amount'] = 0
                except Exception:
                    pass
            results.append(item)
        return results

def list_library_categories(db_path=None):
    """Lấy danh sách các chuyên ngành sách trong Thư viện."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT DISTINCT category FROM library_books ORDER BY category ASC").fetchall()
        return [r[0] for r in rows if r[0]]

if __name__ == "__main__":
    init_db()
    sync_kb_from_csv()
    print("[*] CSDL SQLite đã khởi tạo và đồng bộ thành công.")
