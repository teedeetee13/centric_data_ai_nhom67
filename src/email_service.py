# -*- coding: utf-8 -*-
"""
Module: src.email_service
Dịch vụ gửi email thông báo giải quyết phản ánh sinh viên.
Hỗ trợ:
- Gửi email thực tế qua máy chủ SMTP (Gmail TLS cổng 587 hoặc SSL cổng 465)
- Gửi mô phỏng (Mock Dispatch Log) khi chưa cấu hình mật khẩu ứng dụng Gmail
- Lưu vết kiểm toán toàn bộ email đã gửi vào bảng email_dispatches trong CSDL SQLite
- Tự động hóa gửi kết quả khi AI tự động phê duyệt hoặc Cán bộ duyệt trên Bàn làm việc
Tuyệt đối không sử dụng emoji, tuân thủ chuẩn phong cách Sapphire Academic & Slate.
"""

import os
import smtplib
from datetime import datetime, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import TOPICS, database_path
try:
    from src.config import DEFAULT_TEST_EMAIL
except ImportError:
    import os
    DEFAULT_TEST_EMAIL = os.environ.get("DEFAULT_TEST_EMAIL", "kennysk114239@gmail.com")
from src.database import ClosingConnection, get_connection

def get_smtp_config() -> Dict[str, str]:
    """
    Lấy thông tin cấu hình máy chủ SMTP từ biến môi trường.
    Mặc định hỗ trợ máy chủ Gmail smtp.gmail.com.
    """
    return {
        "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "port": str(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", os.environ.get("GMAIL_USER", "")),
        "password": os.environ.get("SMTP_PASSWORD", os.environ.get("GMAIL_APP_PASSWORD", "")),
        "sender_name": os.environ.get("SMTP_SENDER_NAME", "EduSupportAI - Cổng Hỗ trợ Học vụ"),
    }

def init_email_table(db_path=None):
    """Khởi tạo bảng email_dispatches nếu chưa tồn tại."""
    with get_connection(db_path) as conn:
        conn.execute('''
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
        ''')

def record_dispatch(
    recipient_email: str,
    subject: str,
    body_text: str,
    dispatch_mode: str,
    status: str,
    error_message: str = "",
    record_id: Optional[str] = None,
    db_path=None
) -> int:
    """Ghi nhận bản ghi gửi email vào CSDL SQLite."""
    init_email_table(db_path)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            '''INSERT INTO email_dispatches
               (record_id, recipient_email, subject, body_text, dispatch_mode, status, error_message, sent_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (record_id or "", recipient_email, subject, body_text, dispatch_mode, status, error_message, stamp)
        )
        return cursor.lastrowid

def list_email_dispatches(limit: int = 50, db_path=None) -> List[Dict]:
    """Truy vấn danh sách lịch sử email đã gửi."""
    init_email_table(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM email_dispatches ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def build_resolution_email(
    record_id: str,
    topic: str,
    department: str,
    resolution_text: str,
    confidence_score: Optional[float] = None,
    is_auto_approved: bool = False
) -> Tuple[str, str]:
    """
    Soạn tiêu đề và nội dung email thông báo giải quyết phản ánh học vụ.
    Trình bày trang trọng, rõ ràng, không dùng emoji.
    """
    topic_name = TOPICS.get(topic, topic)
    subject = f"[EduSupportAI] Kết quả giải quyết phản ánh học vụ - Mã số {record_id}"

    method_line = (
        f"- Phương thức phê duyệt: Tự động bởi AI (Mức độ chắc chắn: {confidence_score:.1%})"
        if is_auto_approved and confidence_score is not None
        else "- Phương thức phê duyệt: Cán bộ chuyên môn kiểm tra và xác nhận"
    )

    body = f"""Kính gửi Quý Sinh viên,

Hệ thống EduSupportAI xin gửi thông báo kết quả giải quyết phản ánh của bạn:

THÔNG TIN YÊU CẦU:
- Mã yêu cầu: {record_id}
- Đơn vị phụ trách xử lý: {department}
- Nhóm vấn đề phân loại: {topic_name}
{method_line}

HƯỚNG DẪN VÀ GIẢI PHÁP XỬ LÝ:
--------------------------------------------------
{resolution_text.strip()}
--------------------------------------------------

LƯU Ý DÀNH CHO SINH VIÊN:
- Nếu vấn đề đã được giải quyết thỏa đáng, bạn không cần thực hiện thêm thao tác nào.
- Trường hợp cần bổ sung hồ sơ hoặc hỗ trợ thêm, sinh viên vui lòng liên hệ trực tiếp với {department} trong giờ hành chính hoặc phản hồi qua Cổng thông tin học vụ.

Trân trọng thông báo,
EduSupportAI - Cổng tiếp nhận, phân loại và xử lý phản ánh học vụ sinh viên
""".strip()

    return subject, body

def send_resolution_email(
    recipient_email: str,
    subject: str,
    body_text: str,
    record_id: Optional[str] = None,
    smtp_override: Optional[Dict[str, str]] = None,
    db_path=None
) -> Tuple[bool, str]:
    """
    Gửi email thông báo giải quyết phản ánh.
    - Nếu có cấu hình tài khoản và mật khẩu SMTP: Thực hiện gửi thật qua SMTP.
    - Nếu chưa cấu hình mật khẩu ứng dụng Gmail: Ghi nhật ký mô phỏng (Mock Dispatch) để thử nghiệm.
    """
    recipient = recipient_email.strip()
    if not recipient or "@" not in recipient:
        return False, f"Địa chỉ email không hợp lệ: '{recipient}'"

    cfg = get_smtp_config()
    if smtp_override:
        cfg.update(smtp_override)

    has_credentials = bool(cfg.get("user") and cfg.get("password"))

    if has_credentials:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = f"{cfg.get('sender_name', 'EduSupportAI')} <{cfg['user']}>"
            msg["To"] = recipient

            part = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part)

            server_host = cfg.get("server", "smtp.gmail.com")
            port = int(cfg.get("port", 587))

            if port == 465:
                server = smtplib.SMTP_SSL(server_host, port, timeout=10)
            else:
                server = smtplib.SMTP(server_host, port, timeout=10)
                server.starttls()

            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], [recipient], msg.as_string())
            server.quit()

            record_dispatch(
                recipient_email=recipient,
                subject=subject,
                body_text=body_text,
                dispatch_mode="smtp_real",
                status="success",
                record_id=record_id,
                db_path=db_path
            )
            return True, f"Đã gửi email thực tế thành công qua máy chủ SMTP tới {recipient}."

        except Exception as exc:
            err_msg = str(exc)
            record_dispatch(
                recipient_email=recipient,
                subject=subject,
                body_text=body_text,
                dispatch_mode="smtp_real",
                status="failed",
                error_message=err_msg,
                record_id=record_id,
                db_path=db_path
            )
            return False, f"Lỗi gửi email qua SMTP: {err_msg}"
    else:
        # Chế độ Mock Dispatch: Lưu vết kiểm toán và thông báo trạng thái
        record_dispatch(
            recipient_email=recipient,
            subject=subject,
            body_text=body_text,
            dispatch_mode="simulated",
            status="success",
            error_message="Chưa cấu hình mật khẩu SMTP, bản ghi đã được ghi nhận vào nhật ký gửi.",
            record_id=record_id,
            db_path=db_path
        )
        return True, (
            f"Đã ghi nhận gửi email thành công tới {recipient} (Chế độ mô phỏng kiểm thử). "
            "Để kích hoạt gửi thực qua máy chủ Gmail, bạn có thể thiết lập biến môi trường GMAIL_APP_PASSWORD."
        )
