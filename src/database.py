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
    draft_content = safe_text(result['draft_response'], mask_pii_flag=should_mask)

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

if __name__ == "__main__":
    init_db()
    sync_kb_from_csv()
    print("[*] CSDL SQLite đã khởi tạo và đồng bộ thành công.")
