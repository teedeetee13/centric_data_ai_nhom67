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
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.cleaner import mask_pii
from src.config import KB_PATH, TOPICS, database_path

class ClosingConnection(sqlite3.Connection):
    """Đảm bảo kết nối CSDL luôn được đóng an toàn khi ra khỏi context manager."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

def now():
    """Lấy thời điểm hiện tại dạng chuỗi ISO UTC."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def get_connection(db_path=None):
    """Khởi tạo kết nối SQLite với row_factory và ClosingConnection."""
    path = Path(db_path) if db_path is not None else database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn

def safe_text(value):
    """Chuẩn hóa văn bản và bảo đảm mọi thông tin PII đều được che trước khi lưu CSDL."""
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize('NFC', value)
    text = '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.split('\n')).strip()
    return mask_pii(text)[0]

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

def save_request(result, record_id=None, source_type='manual_demo', db_path=None):
    """Lưu yêu cầu phản ánh mới sau khi qua xử lý vào CSDL."""
    record_id = record_id or ('REQ_' + uuid4().hex[:12].upper())
    flags = result.get('quality_flags', [])
    if not isinstance(flags, str):
        flags = ';'.join(flags) if flags else 'CLEAN'
    with get_connection(db_path) as conn:
        conn.execute('''INSERT INTO processed_requests
          (record_id, clean_text, quality_flags, is_usable, predicted_topic, confidence_score,
           priority_level, priority_reason, department, matched_kb_id, articles_json, draft_response,
           source_type, status, processed_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'pending_review',?)
          ON CONFLICT(record_id) DO NOTHING''',
          (record_id, safe_text(result['clean_text']), flags, int(result['is_usable']),
           result['predicted_topic'], result['confidence_score'], result['priority_level'],
           result.get('priority_reason', 'Rà soát thường quy'), result['department'],
           result.get('matched_kb_id'), json.dumps(result.get('articles', []), ensure_ascii=False),
           safe_text(result['draft_response']), source_type, now()))
    return record_id

def get_request(record_id, db_path=None):
    """Truy vấn thông tin một yêu cầu theo mã record_id."""
    with get_connection(db_path) as conn:
        row = conn.execute('SELECT * FROM processed_requests WHERE record_id=?', (record_id,)).fetchone()
    return dict(row) if row else None

def list_requests(pending_only=False, db_path=None):
    """Lấy danh sách các yêu cầu trong CSDL, sắp xếp theo mức ưu tiên nghiệp vụ."""
    where = "WHERE status='pending_review'" if pending_only else ''
    with get_connection(db_path) as conn:
        rows = conn.execute(f'''SELECT * FROM processed_requests {where}
          ORDER BY CASE priority_level WHEN 'Khẩn cấp' THEN 1 WHEN 'Cao' THEN 2
          WHEN 'Bình thường' THEN 3 ELSE 4 END, processed_at DESC, id DESC''').fetchall()
    return [dict(row) for row in rows]

def save_draft(record_id, draft_text, db_path=None):
    """Lưu bản nháp phản hồi đã được chỉnh sửa cho một yêu cầu đang chờ duyệt."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE processed_requests SET draft_response=? WHERE record_id=? AND status='pending_review'",
            (safe_text(draft_text), record_id)
        )
        if cur.rowcount != 1:
            raise ValueError('Yêu cầu đã được duyệt hoặc không còn tồn tại. Hãy tải lại danh sách.')

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

def review_history(db_path=None):
    """Lấy toàn bộ lịch sử kiểm toán cán bộ duyệt từ bảng review_logs."""
    with get_connection(db_path) as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM review_logs ORDER BY id DESC').fetchall()]

if __name__ == "__main__":
    init_db()
    sync_kb_from_csv()
    print("[*] CSDL SQLite đã khởi tạo và đồng bộ thành công.")
