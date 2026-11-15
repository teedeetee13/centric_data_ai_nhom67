# -*- coding: utf-8 -*-
"""
Script: scripts.migrate_to_mysql
Tự động khởi tạo database edusupport_db trên MySQL (Docker) và di chuyển
toàn bộ dữ liệu từ SQLite (data/edusupport.db) sang MySQL:
- processed_requests (Ticket phản ánh)
- review_logs (Lịch sử cán bộ duyệt)
- knowledge_base (Kho tri thức FAQ)
- procedures_kb (15 quy trình chính thức từ data-doc)
- execution_traces (Nhật ký thực thi & suy luận của Local Machine / LLM)
- email_dispatches (Lịch sử gửi email)
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pymysql

from src.config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    database_path
)
from src.doc_parser import build_procedure_catalog

SQL_INIT_FILE = ROOT_DIR / "scripts" / "init_mysql.sql"

def get_mysql_admin_conn():
    """Kết nối MySQL không chỉ định DB để tạo DB nếu chưa có."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset='utf8mb4',
        autocommit=True
    )

def get_mysql_db_conn():
    """Kết nối MySQL trực tiếp vào database edusupport_db."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset='utf8mb4',
        autocommit=True
    )

def parse_iso_datetime(dt_str):
    """Chuyển đổi chuỗi ISO sang định dạng DATETIME chuẩn của MySQL 'YYYY-MM-DD HH:MM:SS'."""
    if not dt_str:
        return None
    try:
        clean = dt_str.replace("T", " ").replace("Z", "").split("+")[0]
        # Bỏ phần phân số giây nếu có
        if "." in clean:
            clean = clean.split(".")[0]
        return clean
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_migration():
    print("=" * 75)
    print(" BẮT ĐẦU DI CHUYỂN DỮ LIỆU SANG MYSQL (DOCKER) & DBEAVER")
    print(f" Target Host: {MYSQL_HOST}:{MYSQL_PORT} | User: {MYSQL_USER} | DB: {MYSQL_DB}")
    print("=" * 75)

    # 1. Khởi tạo CSDL MySQL từ script init_mysql.sql
    print("\n[Bước 1/4] Thực thi tạo CSDL và bảng trong MySQL...")
    with get_mysql_admin_conn() as conn:
        with conn.cursor() as cur:
            with open(SQL_INIT_FILE, "r", encoding="utf-8") as f:
                sql_content = f.read()
            # Tách các lệnh SQL theo dấu chấm phẩy
            statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
            for stmt in statements:
                cur.execute(stmt)
    print("[OK] CSDL edusupport_db và 6 bảng nghiệp vụ đã sẵn sàng trên MySQL.")

    # 2. Đọc dữ liệu từ SQLite
    sqlite_file = database_path()
    sqlite_exists = sqlite_file.exists()
    print(f"\n[Bước 2/4] Kiểm tra dữ liệu SQLite tại: {sqlite_file} (Tồn tại: {sqlite_exists})")

    sqlite_data = {
        "knowledge_base": [],
        "procedures_kb": [],
        "processed_requests": [],
        "review_logs": [],
        "execution_traces": [],
        "email_dispatches": []
    }

    if sqlite_exists:
        s_conn = sqlite3.connect(sqlite_file)
        s_conn.row_factory = sqlite3.Row
        cur = s_conn.cursor()

        for tbl in sqlite_data.keys():
            try:
                rows = cur.execute(f"SELECT * FROM {tbl}").fetchall()
                sqlite_data[tbl] = [dict(r) for r in rows]
                print(f"  • Đọc từ SQLite [{tbl}]: {len(sqlite_data[tbl])} bản ghi")
            except Exception as e:
                print(f"  • Bảng SQLite [{tbl}] chưa có hoặc lỗi: {e}")
        s_conn.close()

    # 3. Đồng bộ danh mục 15 quy trình data-doc nếu chưa có
    catalog = build_procedure_catalog()
    print(f"\n[Bước 3/4] Đồng bộ danh mục {len(catalog)} quy trình trích xuất từ data-doc...")

    with get_mysql_db_conn() as m_conn:
        with m_conn.cursor() as m_cur:
            # A. procedures_kb
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for p in catalog:
                m_cur.execute("""
                    INSERT INTO procedures_kb
                    (proc_id, title, topic, department, legal_basis, processing_time, forms_required, target_users, steps_json, sample_queries_json, content_extract, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    title=VALUES(title), topic=VALUES(topic), department=VALUES(department),
                    legal_basis=VALUES(legal_basis), processing_time=VALUES(processing_time),
                    forms_required=VALUES(forms_required), target_users=VALUES(target_users),
                    steps_json=VALUES(steps_json), sample_queries_json=VALUES(sample_queries_json),
                    content_extract=VALUES(content_extract), updated_at=VALUES(updated_at)
                """, (
                    p["proc_id"], p["title"], p["topic"], p["department"],
                    p.get("legal_basis", ""), p.get("processing_time", ""),
                    p.get("forms_required", ""), p.get("target_users", ""),
                    json.dumps(p.get("steps", []), ensure_ascii=False),
                    json.dumps(p.get("sample_queries", []), ensure_ascii=False),
                    p.get("content_extract", ""),
                    now_str
                ))

            # B. knowledge_base
            for r in sqlite_data["knowledge_base"]:
                m_cur.execute("""
                    INSERT INTO knowledge_base
                    (kb_id, topic, question_standard, content_extract, department, effective_date, source_url, verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    topic=VALUES(topic), question_standard=VALUES(question_standard),
                    content_extract=VALUES(content_extract), department=VALUES(department),
                    effective_date=VALUES(effective_date), source_url=VALUES(source_url),
                    verified=VALUES(verified)
                """, (
                    r["kb_id"], r["topic"], r["question_standard"], r["content_extract"],
                    r["department"], r.get("effective_date", "2025-08-15"),
                    r.get("source_url", ""), int(r.get("verified", 0))
                ))

            # C. processed_requests
            for r in sqlite_data["processed_requests"]:
                p_at = parse_iso_datetime(r.get("processed_at"))
                r_at = parse_iso_datetime(r.get("reviewed_at"))
                m_cur.execute("""
                    INSERT INTO processed_requests
                    (record_id, clean_text, quality_flags, is_usable, predicted_topic, confidence_score,
                     priority_level, priority_reason, department, matched_kb_id, articles_json,
                     draft_response, final_topic, final_response, source_type, status, processed_at, reviewed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    status=VALUES(status), final_topic=VALUES(final_topic), final_response=VALUES(final_response),
                    reviewed_at=VALUES(reviewed_at)
                """, (
                    r["record_id"], r["clean_text"], r.get("quality_flags", "CLEAN"),
                    int(r.get("is_usable", 1)), r["predicted_topic"], float(r.get("confidence_score", 0.0)),
                    r.get("priority_level", "Bình thường"), r.get("priority_reason", ""),
                    r.get("department", "Bộ phận tiếp nhận"), r.get("matched_kb_id"),
                    r.get("articles_json", "[]"), r["draft_response"],
                    r.get("final_topic"), r.get("final_response"),
                    r.get("source_type", "manual_demo"), r.get("status", "pending_review"),
                    p_at, r_at
                ))

            # D. review_logs
            for r in sqlite_data["review_logs"]:
                r_at = parse_iso_datetime(r.get("reviewed_at"))
                m_cur.execute("""
                    INSERT INTO review_logs
                    (record_id, officer_action, original_predicted_topic, final_topic, final_response, officer_notes, reviewed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    r["record_id"], r["officer_action"], r["original_predicted_topic"],
                    r["final_topic"], r["final_response"], r.get("officer_notes", ""),
                    r_at
                ))

            # E. execution_traces
            for r in sqlite_data["execution_traces"]:
                c_at = parse_iso_datetime(r.get("created_at"))
                m_cur.execute("""
                    INSERT INTO execution_traces
                    (record_id, trace_id, steps_json, terminal_log, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    r["record_id"], r["trace_id"], r["steps_json"],
                    r["terminal_log"], c_at
                ))

            # F. email_dispatches
            for r in sqlite_data["email_dispatches"]:
                s_at = parse_iso_datetime(r.get("sent_at"))
                m_cur.execute("""
                    INSERT INTO email_dispatches
                    (record_id, recipient_email, subject, body_text, dispatch_mode, status, error_message, sent_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    r.get("record_id"), r["recipient_email"], r["subject"],
                    r["body_text"], r["dispatch_mode"], r["status"],
                    r.get("error_message"), s_at
                ))

    # 4. Thống kê kết quả trên MySQL
    print("\n[Bước 4/4] Kiểm tra số lượng bản ghi thực tế trên MySQL:")
    with get_mysql_db_conn() as m_conn:
        with m_conn.cursor() as m_cur:
            for tbl in ["procedures_kb", "knowledge_base", "processed_requests", "review_logs", "execution_traces", "email_dispatches"]:
                m_cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                cnt = m_cur.fetchone()[0]
                print(f"  ✔ Bảng `{tbl}`: {cnt} bản ghi")

    print("\n" + "=" * 75)
    print(" DI CHUYỂN DỮ LIỆU THÀNH CÔNG VÀO DOCKER MYSQL!")
    print(" BẠN CÓ THỂ MỞ DBEAVER VÀ KẾT NỐI:")
    print("   • Server / Host: 127.0.0.1 (hoặc localhost)")
    print("   • Port: 3306")
    print("   • Database: edusupport_db")
    print("   • Username: root")
    print(f"   • Password: {MYSQL_PASSWORD}")
    print("=" * 75)

if __name__ == "__main__":
    run_migration()
