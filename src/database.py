# -*- coding: utf-8 -*-
"""
Module: src.database
Quản trị cơ sở dữ liệu SQLite cục bộ cho EduSupportAI.
Bao gồm các bảng:
- raw_requests: Tiếp nhận dữ liệu thô ban đầu
- processed_requests: Lưu trữ kết quả sau khi qua Quality Engine & Model
- knowledge_base: Bảng tri thức quy chế học vụ (KB001 - KB015)
- review_logs: Lưu vết kiểm toán hành vi cán bộ duyệt/sửa (Human-in-the-Loop)
"""

import os
import sqlite3
import csv
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "edusupport.db")

def get_connection(db_path=DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    """Khởi tạo toàn bộ cấu trúc các bảng CSDL."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Bảng dữ liệu thô
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT UNIQUE NOT NULL,
        raw_text TEXT NOT NULL,
        source_type TEXT DEFAULT 'controlled_demo',
        created_at TEXT,
        target_label_gold TEXT,
        priority_gold TEXT,
        note TEXT
    );
    """)

    # 2. Bảng dữ liệu đã qua tiền xử lý & suy luận AI
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT UNIQUE NOT NULL,
        raw_text TEXT NOT NULL,
        clean_text TEXT NOT NULL,
        quality_flags TEXT,
        is_usable INTEGER DEFAULT 1,
        predicted_topic TEXT,
        confidence_score REAL,
        priority_level TEXT,
        matched_kb_id TEXT,
        draft_response TEXT,
        status TEXT DEFAULT 'pending_review',
        processed_at TEXT
    );
    """)

    # 3. Bảng tri thức quy chế
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_base (
        kb_id TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        question_standard TEXT NOT NULL,
        content_extract TEXT NOT NULL,
        department TEXT NOT NULL,
        effective_date TEXT
    );
    """)

    # 4. Bảng lưu vết kiểm toán duyệt của cán bộ (Human-in-the-Loop)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT NOT NULL,
        officer_action TEXT NOT NULL, -- 'approve', 'edit_label', 'reject'
        original_predicted_topic TEXT,
        final_topic TEXT,
        final_response TEXT,
        officer_notes TEXT,
        reviewed_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    print(f"[*] CSDL SQLite đã khởi tạo thành công tại: {db_path}")

def sync_kb_from_csv(csv_path="data/kb/eaut_faq_kb.csv", db_path=DB_PATH):
    """Đồng bộ kho tri thức quy chế từ CSV vào SQLite."""
    if not os.path.exists(csv_path):
        return
    conn = get_connection(db_path)
    cursor = conn.cursor()
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
            INSERT OR REPLACE INTO knowledge_base (kb_id, topic, question_standard, content_extract, department, effective_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row["kb_id"],
                row["topic"],
                row["question_standard"],
                row["content_extract"],
                row["department"],
                row.get("effective_date", "2025-08-15")
            ))
    conn.commit()
    conn.close()
    print(f"[*] Đã đồng bộ kho tri thức quy chế từ {csv_path} vào SQLite.")

def log_review_action(record_id, officer_action, original_topic, final_topic, final_response, notes="", db_path=DB_PATH):
    """Ghi nhận hành vi phê duyệt / hiệu chỉnh của cán bộ vào review_logs."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO review_logs (record_id, officer_action, original_predicted_topic, final_topic, final_response, officer_notes, reviewed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (record_id, officer_action, original_topic, final_topic, final_response, notes, now_str))

    cursor.execute("""
    UPDATE processed_requests
    SET status = ?, predicted_topic = ?
    WHERE record_id = ?
    """, (f"reviewed_{officer_action}", final_topic, record_id))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    sync_kb_from_csv()
