# -*- coding: utf-8 -*-
"""
Module: src.email_service
Dịch vụ gửi email giải đáp & thông báo học vụ thông minh cho sinh viên EAUT.
Hỗ trợ:
- Định dạng kép (MIME Multipart Alternative): Văn bản thuần (Plain Text) & Giao diện HTML Responsive chuẩn Sapphire Academic & Slate
- Đa dạng kịch bản giải đáp:
  1. Email Giải quyết / Phê duyệt tự động bởi AI hoặc Cán bộ duyệt
  2. Email Hướng dẫn bổ sung hồ sơ / Từ chối có căn cứ & định hướng khắc phục
  3. Email Tiếp nhận hồ sơ & Cam kết thời gian xử lý (SLA Receipt)
- Tích hợp thông tin thực thể: Họ tên, MSSV, Quy trình chuẩn (PROC_...), và Dữ liệu CSDL thời gian thực (Thư viện/Công nợ)
- Gửi thực tế qua máy chủ SMTP (Gmail TLS/SSL) hoặc Ghi nhật ký mô phỏng (Mock Dispatch)
- Lưu vết kiểm toán toàn diện vào bảng email_dispatches trong CSDL SQLite
Tuyệt đối không sử dụng emoji, tuân thủ chuẩn mực phong cách đại học.
"""

import html
import os
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.config import TOPICS, ROOT
try:
    from src.config import DEFAULT_TEST_EMAIL
except ImportError:
    DEFAULT_TEST_EMAIL = os.environ.get("DEFAULT_TEST_EMAIL", "kennysk114239@gmail.com")
from src.database import get_connection
try:
    from src.app_logger import app_log
except ImportError:
    def app_log(*args, **kwargs):
        pass

# ==============================================================================
# THÔNG TIN LIÊN HỆ CÁC PHÒNG BAN CHUYÊN MÔN EAUT
# ==============================================================================

DEPARTMENT_CONTACTS = {
    "Phòng Quản lý Đào tạo": {
        "office": "Bộ phận Một cửa - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 101)",
        "email": "daotao@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    },
    "Phòng Quản lý Đào tạo & Khảo thí": {
        "office": "Bộ phận Một cửa - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 101)",
        "email": "daotao@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    },
    "Phòng Công tác sinh viên": {
        "office": "Bộ phận Một cửa - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 102)",
        "email": "ctsv@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    },
    "Bộ phận Một cửa - Phòng CTSV": {
        "office": "Bộ phận Một cửa - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 102)",
        "email": "ctsv@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    },
    "Phòng Tài chính - Kế toán": {
        "office": "Phòng Kế toán - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 103)",
        "email": "taichinh@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    },
    "Phòng Quản trị - Cơ sở vật chất": {
        "office": "Phòng Quản trị CSVC - Tầng 1, Tòa nhà B, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 104)",
        "email": "csvc@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    },
    "Trung tâm Thông tin - Thư viện EAUT": {
        "office": "Quầy Thủ thư - Tầng 2, Tòa nhà B, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 105)",
        "email": "thuvien@eaut.edu.vn",
        "hours": "07:30 - 20:30 (Thứ Hai đến Thứ Bảy)"
    },
    "Trung tâm CNTT & Truyền thông": {
        "office": "Phòng Kỹ thuật CNTT - Tầng 4, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
        "hotline": "(024) 6262-7797 (Nhánh 106)",
        "email": "cntt@eaut.edu.vn",
        "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
    }
}

DEFAULT_CONTACT = {
    "office": "Bộ phận Tiếp nhận Một cửa - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á",
    "hotline": "(024) 6262-7797",
    "email": "hotro.sinhvien@eaut.edu.vn",
    "hours": "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)"
}

def get_dept_contact(dept_name: str) -> Dict[str, str]:
    """Lấy thông tin liên hệ chính thức của phòng ban xử lý."""
    for key, val in DEPARTMENT_CONTACTS.items():
        if key in dept_name or dept_name in key:
            return val
    return DEFAULT_CONTACT

def load_dotenv_file(filepath=None) -> None:
    """Tự động nạp các biến cấu hình từ file .env vào os.environ."""
    path = Path(filepath) if filepath else ROOT / ".env"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k:
                            os.environ[k] = v
        except Exception:
            pass

def save_smtp_credentials(user: str, password: str, env_path=None) -> None:
    """Lưu thông tin tài khoản SMTP vào file .env và cập nhật ngay vào os.environ."""
    user = user.strip()
    password = password.strip().replace(" ", "")  # Loại bỏ khoảng trắng định dạng của Google App Password
    os.environ["GMAIL_USER"] = user
    os.environ["SMTP_USER"] = user
    os.environ["GMAIL_APP_PASSWORD"] = password
    os.environ["SMTP_PASSWORD"] = password

    path = Path(env_path) if env_path else ROOT / ".env"
    lines = []
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for l in f:
                    if not any(l.strip().startswith(prefix) for prefix in ["GMAIL_USER=", "SMTP_USER=", "GMAIL_APP_PASSWORD=", "SMTP_PASSWORD="]):
                        lines.append(l)
        except Exception:
            pass
    lines.append(f"GMAIL_USER={user}\n")
    lines.append(f"SMTP_USER={user}\n")
    lines.append(f"GMAIL_APP_PASSWORD={password}\n")
    lines.append(f"SMTP_PASSWORD={password}\n")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        pass

def test_smtp_connection(user: str, password: str, server: str = "smtp.gmail.com", port: Any = 587) -> Tuple[bool, str]:
    """Kiểm tra kết nối và xác thực tài khoản SMTP thực tế."""
    user = user.strip()
    password = password.strip().replace(" ", "")
    if not user or not password:
        return False, "Vui lòng nhập đầy đủ Tài khoản Gmail và Mật khẩu ứng dụng."
    if "@" not in user:
        return False, "Địa chỉ email người gửi không hợp lệ (cần có ký tự '@', ví dụ: your_name@gmail.com)."
    try:
        port_num = int(port)
        if port_num == 465:
            s = smtplib.SMTP_SSL(server, port_num, timeout=10)
        else:
            s = smtplib.SMTP(server, port_num, timeout=10)
            s.starttls()
        s.login(user, password)
        s.quit()
        return True, f"Xác thực máy chủ SMTP ({server}:{port_num}) thành công cho tài khoản {user}!"
    except Exception as e:
        err = str(e)
        if "BadCredentials" in err or "Username and Password not accepted" in err or "535" in err:
            return False, "Tài khoản hoặc Mật khẩu ứng dụng không đúng. Lưu ý: Phải dùng Mật khẩu ứng dụng 16 ký tự của Google (không phải mật khẩu đăng nhập thông thường)."
        return False, f"Không thể kết nối đến máy chủ SMTP ({server}): {err}"

def get_smtp_config() -> Dict[str, str]:
    """Lấy thông tin cấu hình máy chủ SMTP từ biến môi trường hoặc file .env."""
    load_dotenv_file()
    return {
        "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "port": str(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", os.environ.get("GMAIL_USER", "")),
        "password": os.environ.get("SMTP_PASSWORD", os.environ.get("GMAIL_APP_PASSWORD", "")),
        "sender_name": os.environ.get("SMTP_SENDER_NAME", "EduSupportAI - Cổng Hỗ trợ Học vụ EAUT"),
    }

def init_email_table(db_path=None):
    """Khởi tạo bảng email_dispatches nếu chưa tồn tại và tự động bổ sung cột body_html."""
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
        cursor = conn.execute("PRAGMA table_info(email_dispatches)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'body_html' not in cols:
            conn.execute("ALTER TABLE email_dispatches ADD COLUMN body_html TEXT DEFAULT ''")

def record_dispatch(
    recipient_email: str,
    subject: str,
    body_text: str,
    dispatch_mode: str,
    status: str,
    error_message: str = "",
    record_id: Optional[str] = None,
    body_html: str = "",
    db_path=None
) -> int:
    """Ghi nhận bản ghi gửi email vào CSDL SQLite."""
    init_email_table(db_path)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            '''INSERT INTO email_dispatches
               (record_id, recipient_email, subject, body_text, dispatch_mode, status, error_message, sent_at, body_html)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (record_id or "", recipient_email, subject, body_text, dispatch_mode, status, error_message, stamp, body_html or "")
        )
        row_id = cursor.lastrowid

    app_log("EMAIL", "Ghi nhận tiến trình gửi email giải quyết",
            f"Mã: [{record_id}], Người nhận: [{recipient_email}], Chế độ: {dispatch_mode}, Trạng thái: {status}",
            level="SUCCESS" if status == "success" else "WARN")
    return row_id

def list_email_dispatches(limit: int = 50, db_path=None) -> List[Dict]:
    """Truy vấn danh sách lịch sử email đã gửi."""
    init_email_table(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM email_dispatches ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

# ==============================================================================
# HÀM DỰNG TEMPLATE EMAIL HTML CHUẨN SAPPHIRE ACADEMIC & SLATE
# ==============================================================================

def _wrap_email_html(
    title_banner: str,
    status_badge_html: str,
    greeting_html: str,
    summary_table_rows: List[Tuple[str, str]],
    content_blocks_html: str,
    contact_dict: Dict[str, str],
    record_id: str
) -> str:
    """Khung HTML dùng chung, tương thích tối đa với Gmail và mọi ứng dụng email client."""
    table_rows_html = "".join([
        f"""<tr>
            <td style="padding: 9px 14px; background: #f8fafc; color: #475569; font-size: 13px; font-weight: 600; width: 32%; border-bottom: 1px solid #e2e8f0;">{html.escape(k)}</td>
            <td style="padding: 9px 14px; background: #ffffff; color: #0f172a; font-size: 13px; border-bottom: 1px solid #e2e8f0;">{v}</td>
        </tr>"""
        for k, v in summary_table_rows
    ])

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{html.escape(title_banner)}</title>
</head>
<body style="margin: 0; padding: 24px 10px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; line-height: 1.6; color: #1e293b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
    <tr>
      <td align="center">
        <!-- Main Card Container -->
        <table role="presentation" width="100%" style="max-width: 680px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);" cellspacing="0" cellpadding="0" border="0">
          <!-- Header Banner -->
          <tr>
            <td style="background: #0f172a; padding: 22px 28px; border-bottom: 3px solid #2563eb;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td>
                    <div style="font-size: 11px; font-weight: 700; letter-spacing: 1.2px; color: #94a3b8; text-transform: uppercase;">TRƯỜNG ĐẠI HỌC CÔNG NGHỆ ĐÔNG Á (EAUT)</div>
                    <div style="font-size: 17px; font-weight: 700; color: #ffffff; margin-top: 4px;">CỔNG TIẾP NHẬN & GIẢI QUYẾT PHẢN ÁNH HỌC VỤ (EDUSUPPORT-AI)</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Status Badge -->
          <tr>
            <td style="padding: 20px 28px 0 28px;">
              {status_badge_html}
            </td>
          </tr>

          <!-- Main Body -->
          <tr>
            <td style="padding: 16px 28px 24px 28px;">
              <!-- Greeting -->
              <div style="font-size: 15px; color: #0f172a; margin-bottom: 16px;">
                {greeting_html}
              </div>

              <!-- Summary Metadata Table -->
              <table role="presentation" width="100%" style="border-collapse: collapse; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; margin-bottom: 22px;" cellspacing="0" cellpadding="0" border="0">
                {table_rows_html}
              </table>

              <!-- Dynamic Content Blocks -->
              {content_blocks_html}

              <!-- Official Contact Box -->
              <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px 18px; margin-top: 24px;">
                <div style="font-size: 12px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">ĐỊA ĐIỂM & KÊNH HỖ TRỢ TRỰC TIẾP:</div>
                <table role="presentation" width="100%" style="font-size: 13px; color: #334155; line-height: 1.6;" cellspacing="0" cellpadding="0" border="0">
                  <tr><td style="width: 25px; vertical-align: top;">•</td><td><strong>Văn phòng:</strong> {html.escape(contact_dict.get('office', ''))}</td></tr>
                  <tr><td style="width: 25px; vertical-align: top;">•</td><td><strong>Giờ làm việc:</strong> {html.escape(contact_dict.get('hours', ''))}</td></tr>
                  <tr><td style="width: 25px; vertical-align: top;">•</td><td><strong>Điện thoại:</strong> {html.escape(contact_dict.get('hotline', ''))} &nbsp;|&nbsp; <strong>Email:</strong> <a href="mailto:{html.escape(contact_dict.get('email', ''))}" style="color: #2563eb; text-decoration: none;">{html.escape(contact_dict.get('email', ''))}</a></td></tr>
                </table>
              </div>

              <div style="margin-top: 22px; font-size: 13px; color: #475569; border-top: 1px dashed #cbd5e1; padding-top: 14px;">
                Nếu vấn đề của bạn đã được giải quyết trọn vẹn, bạn không cần thực hiện thêm thao tác phản hồi nào. Trường hợp cần giải thích thêm, vui lòng phản hồi lại email này kèm Mã hồ sơ <strong>{html.escape(record_id)}</strong>.
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 18px 28px; text-align: center; font-size: 12px; color: #64748b; line-height: 1.5;">
              <div>Hệ thống Tiếp nhận & Giải quyết Phản ánh Học vụ Sinh viên (EduSupportAI)</div>
              <div>Trường Đại học Công nghệ Đông Á (EAUT) — Tòa nhà Polyco, Đường Trịnh Văn Bô, Nam Từ Liêm, Hà Nội</div>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">Email thông báo tự động. Thông tin trong thư mang tính chất hướng dẫn học vụ chính thức.</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

# ==============================================================================
# BỘ TẠO NỘI DUNG GIẢI ĐÁP QUA EMAIL (RESOLUTION, REJECTION, INTAKE)
# ==============================================================================

def _format_student_recipient_text(student_name: Optional[str], student_id: Optional[str]) -> str:
    """Định dạng chuỗi xưng danh sinh viên trang trọng cho văn bản email."""
    if student_name and student_id:
        return f"{student_name} (MSSV: {student_id})"
    elif student_name:
        return student_name
    elif student_id:
        return f"Sinh viên (MSSV: {student_id})"
    return "Quý Sinh viên"

def build_rich_resolution_email(
    record_id: str,
    topic: str,
    department: str,
    resolution_text: str,
    confidence_score: Optional[float] = None,
    is_auto_approved: bool = False,
    student_name: Optional[str] = None,
    student_id: Optional[str] = None,
    procedure_info: Optional[Dict[str, Any]] = None,
    library_info: Optional[Dict[str, Any]] = None,
    officer_notes: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Soạn thảo email giải quyết phản ánh hoàn chỉnh.
    Trả về Tuple: (subject, plain_text_body, html_body)
    """
    topic_name = TOPICS.get(topic, topic)
    subject = f"[EduSupportAI] Kết quả giải quyết phản ánh học vụ - Mã số {record_id}"
    contact = get_dept_contact(department)

    # --- 1. XÂY DỰNG PLAIN TEXT BODY ---
    recipient_greeting = _format_student_recipient_text(student_name, student_id)
    method_str = (
        f"- Phương thức phê duyệt: Tự động bởi AI (Mức độ chắc chắn: {confidence_score:.1%})"
        if is_auto_approved and confidence_score is not None
        else "- Phương thức phê duyệt: Cán bộ chuyên môn kiểm tra và xác nhận"
    )

    proc_lines = []
    if procedure_info:
        proc_lines.append("\nQUY TRÌNH NGHIỆP VỤ LIÊN QUAN:")
        proc_lines.append(f"- Mã quy trình: [{procedure_info.get('proc_id')}] {procedure_info.get('title')}")
        proc_lines.append(f"- Căn cứ pháp lý: {procedure_info.get('legal_basis', 'Quy định Nhà trường')}")
        proc_lines.append(f"- Thời hạn xử lý (SLA): {procedure_info.get('processing_time', 'Theo quy định')}")
        proc_lines.append(f"- Biểu mẫu yêu cầu: {procedure_info.get('forms_required', 'Không yêu cầu')}")

    plain_body = f"""Kính gửi {recipient_greeting},

Hệ thống EduSupportAI xin gửi thông báo kết quả giải quyết phản ánh học vụ của bạn:

THÔNG TIN YÊU CẦU:
- Mã yêu cầu: {record_id}
- Đơn vị phụ trách xử lý: {department}
- Nhóm vấn đề phân loại: {topic_name}
{method_str}
{"".join(proc_lines)}

HƯỚNG DẪN VÀ GIẢI PHÁP XỬ LÝ:
--------------------------------------------------
{resolution_text.strip()}
--------------------------------------------------

{"Ý KIẾN DẶN DÒ CỦA CÁN BỘ:" + chr(10) + officer_notes + chr(10) + "--------------------------------------------------" if officer_notes else ""}

ĐỊA CHỈ VĂN PHÒNG & LIÊN HỆ:
- Văn phòng: {contact.get('office')}
- Giờ làm việc: {contact.get('hours')}
- Hotline: {contact.get('hotline')} | Email: {contact.get('email')}

LƯU Ý DÀNH CHO SINH VIÊN:
- Nếu vấn đề đã được giải quyết thỏa đáng, bạn không cần thực hiện thêm thao tác nào.
- Trường hợp cần bổ sung hồ sơ hoặc hỗ trợ thêm, sinh viên vui lòng liên hệ trực tiếp với {department} trong giờ hành chính hoặc phản hồi kèm Mã yêu cầu {record_id}.

Trân trọng thông báo,
EduSupportAI - Cổng tiếp nhận, phân loại và xử lý phản ánh học vụ sinh viên
Trường Đại học Công nghệ Đông Á (EAUT)
""".strip()

    # --- 2. XÂY DỰNG HTML BODY ---
    if is_auto_approved:
        conf_badge_text = f"TỰ ĐỘNG PHÊ DUYỆT BỞI AI (ĐỘ TIN CẬY: {confidence_score:.1%})" if confidence_score else "TỰ ĐỘNG PHÊ DUYỆT BỞI AI"
        badge_html = f"""<div style="background: #ecfdf5; border: 1px solid #10b981; color: #065f46; font-size: 12px; font-weight: 700; padding: 7px 14px; border-radius: 6px; display: inline-block;">
            [XỬ LÝ TỰ ĐỘNG BỞI AI] &nbsp; {conf_badge_text}
        </div>"""
    else:
        badge_html = """<div style="background: #eff6ff; border: 1px solid #3b82f6; color: #1e40af; font-size: 12px; font-weight: 700; padding: 7px 14px; border-radius: 6px; display: inline-block;">
            [KIỂM DUYỆT BỞI CÁN BỘ CHUYÊN TRÁCH] &nbsp; HỒ SƠ ĐÃ ĐƯỢC XÁC THỰC VÀ PHÊ DUYỆT
        </div>"""

    st_display = f"<strong>{html.escape(student_name)}</strong> " if student_name else "<strong>Quý Sinh viên</strong>"
    if student_id:
        st_display += f" (Mã sinh viên: <strong>{html.escape(student_id)}</strong>)"
    greeting_html = f"Kính gửi {st_display},<br/><br/>Hệ thống EduSupportAI xin gửi văn bản hướng dẫn và kết quả xử lý chính thức cho yêu cầu học vụ của bạn:"

    summary_rows = [
        ("Mã hồ sơ tiếp nhận", f"<strong>{html.escape(record_id)}</strong>"),
        ("Chuyên môn phân loại", html.escape(topic_name)),
        ("Đơn vị thụ lý", f"<strong>{html.escape(department)}</strong>"),
        ("Phương thức xử lý", "Tự động gửi thẳng khi AI đủ độ tin cậy" if is_auto_approved else "Cán bộ chuyên môn kiểm tra và ký duyệt")
    ]

    if procedure_info:
        summary_rows.append(("Quy trình chuẩn hóa", f"<strong>[{html.escape(procedure_info.get('proc_id', ''))}]</strong> {html.escape(procedure_info.get('title', ''))}"))
        summary_rows.append(("Thời hạn giải quyết (SLA)", html.escape(procedure_info.get('processing_time', 'Theo quy định'))))
        if procedure_info.get('forms_required'):
            summary_rows.append(("Biểu mẫu yêu cầu", html.escape(procedure_info.get('forms_required', ''))))

    # Xử lý đoạn văn bản giải đáp
    escaped_res = html.escape(resolution_text.strip()).replace("\n", "<br/>")
    content_blocks = f"""
    <div style="font-size: 13px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">NỘI DUNG HƯỚNG DẪN & GIẢI PHÁP THỰC HIỆN:</div>
    <div style="background: #f8fafc; border-left: 4px solid #2563eb; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-radius: 4px; padding: 18px 20px; font-size: 14px; color: #1e293b; line-height: 1.7; margin-bottom: 20px;">
      {escaped_res}
    </div>
    """

    if officer_notes:
        content_blocks += f"""
        <div style="background: #fffbeb; border-left: 4px solid #f59e0b; border: 1px solid #fef3c7; border-radius: 4px; padding: 14px 18px; font-size: 13px; color: #92400e; margin-bottom: 20px;">
          <strong>Ý kiến dặn dò bổ sung từ cán bộ chuyên môn:</strong><br/>
          {html.escape(officer_notes)}
        </div>
        """

    # Nếu có dữ liệu CSDL Thư viện thời gian thực
    if library_info and library_info.get("has_live_data"):
        b_list = library_info.get("books_found", [])
        br_list = library_info.get("student_borrows", [])
        lib_html_parts = []
        if b_list:
            lib_html_parts.append("<div style='font-weight: 700; margin-bottom: 6px; color: #1e40af;'>Danh mục sách trên giá Thư viện EAUT:</div>")
            for b in b_list[:3]:
                avail_txt = f"<span style='color: #16a34a; font-weight: 700;'>Còn {b['available_copies']}/{b['total_copies']} cuốn</span>" if b['available_copies'] > 0 else "<span style='color: #dc2626; font-weight: 700;'>Đang mượn hết</span>"
                lib_html_parts.append(f"""<div style='background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 14px; margin-bottom: 6px; font-size: 13px;'>
                    <strong>[{html.escape(b['book_id'])}] {html.escape(b['title'])}</strong><br/>
                    Vị trí: <strong>{html.escape(b['location'])}</strong> (Mã: {html.escape(b['call_number'])}) &nbsp;|&nbsp; Tình trạng: {avail_txt}
                </div>""")
        if br_list:
            lib_html_parts.append("<div style='font-weight: 700; margin-top: 10px; margin-bottom: 6px; color: #1e40af;'>Hồ sơ mượn trả cá nhân của sinh viên:</div>")
            for br in br_list:
                st_color = "#dc2626" if br['status'] == 'Quá hạn' else "#16a34a"
                fine_str = f" — Phí phạt quá hạn: <strong>{br.get('fine_amount', 0):,} VNĐ</strong>" if br['status'] == 'Quá hạn' else ""
                lib_html_parts.append(f"""<div style='background: #ffffff; border-left: 3px solid {st_color}; border: 1px solid #e2e8f0; border-radius: 4px; padding: 8px 12px; margin-bottom: 6px; font-size: 13px;'>
                    Sách: <strong>{html.escape(br['book_title'])}</strong> | Trạng thái: <span style='font-weight: 700; color: {st_color};'>{html.escape(br['status'])}</span> | Hạn trả: <strong>{html.escape(br['due_date'])}</strong>{fine_str}
                </div>""")

        if lib_html_parts:
            content_blocks += f"""
            <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
              <div style="font-size: 12px; font-weight: 700; color: #1e40af; text-transform: uppercase; margin-bottom: 8px;">DỮ LIỆU ĐỐI SOÁT THỜI GIAN THỰC TỪ CSDL THƯ VIỆN EAUT:</div>
              {''.join(lib_html_parts)}
            </div>
            """

    html_body = _wrap_email_html(
        title_banner=f"Kết quả giải quyết phản ánh học vụ - {record_id}",
        status_badge_html=badge_html,
        greeting_html=greeting_html,
        summary_table_rows=summary_rows,
        content_blocks_html=content_blocks,
        contact_dict=contact,
        record_id=record_id
    )

    return subject, plain_body, html_body

def build_rejection_email(
    record_id: str,
    topic: str,
    department: str,
    reason_notes: str,
    student_name: Optional[str] = None,
    student_id: Optional[str] = None,
    procedure_info: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, str]:
    """
    Soạn thảo email thông báo từ chối thụ lý hoặc yêu cầu bổ sung hồ sơ một cách trang trọng,
    có hướng dẫn khắc phục cụ thể, không dùng ngôn từ cộc lốc.
    Trả về Tuple: (subject, plain_text_body, html_body)
    """
    topic_name = TOPICS.get(topic, topic)
    subject = f"[EduSupportAI] Thông báo kết quả rà soát hồ sơ học vụ - Mã số {record_id}"
    contact = get_dept_contact(department)

    recipient_greeting = _format_student_recipient_text(student_name, student_id)

    plain_body = f"""Kính gửi {recipient_greeting},

Hệ thống EduSupportAI xin gửi thông báo kết quả thẩm định hồ sơ phản ánh học vụ mã số {record_id}:

THÔNG TIN HỒ SƠ:
- Mã yêu cầu: {record_id}
- Đơn vị phụ trách xử lý: {department}
- Nhóm vấn đề phân loại: {topic_name}
- Trạng thái: Tạm dừng thụ lý / Cần bổ sung thông tin hoặc giải trình

LÝ DO CHƯA ĐỦ ĐIỀU KIỆN THỤ LÝ:
--------------------------------------------------
{reason_notes.strip()}
--------------------------------------------------

HƯỚNG DẪN KHẮC PHỤC DÀNH CHO SINH VIÊN:
1. Kiểm tra lại thông tin cá nhân (Họ tên, Mã sinh viên, Lớp, Số điện thoại liên hệ).
2. Trường hợp thiếu giấy tờ / minh chứng (Biên lai nộp tiền, Đơn xin gia hạn, Giấy xác nhận y tế...), sinh viên vui lòng chuẩn bị đầy đủ bản chụp rõ nét.
3. Sinh viên có thể gửi lại yêu cầu mới kèm đầy đủ minh chứng qua Cổng thông tin học vụ, hoặc đến trực tiếp văn phòng phụ trách trong giờ hành chính.

ĐỊA CHỈ HỖ TRỢ TRỰC TIẾP:
- Văn phòng: {contact.get('office')}
- Giờ làm việc: {contact.get('hours')}
- Hotline: {contact.get('hotline')} | Email: {contact.get('email')}

Trân trọng thông báo,
EduSupportAI - Cổng tiếp nhận, phân loại và xử lý phản ánh học vụ sinh viên
Trường Đại học Công nghệ Đông Á (EAUT)
""".strip()

    badge_html = """<div style="background: #fef2f2; border: 1px solid #ef4444; color: #991b1b; font-size: 12px; font-weight: 700; padding: 7px 14px; border-radius: 6px; display: inline-block;">
        [THÔNG BÁO TẠM DỪNG THỤ LÝ] &nbsp; HỒ SƠ CẦN BỔ SUNG MINH CHỨNG HOẶC CHƯA PHÙ HỢP QUY ĐỊNH
    </div>"""

    st_display = f"<strong>{html.escape(student_name)}</strong> " if student_name else "<strong>Quý Sinh viên</strong>"
    if student_id:
        st_display += f" (Mã sinh viên: <strong>{html.escape(student_id)}</strong>)"
    greeting_html = f"Kính gửi {st_display},<br/><br/>Hệ thống EduSupportAI đã chuyển hồ sơ phản ánh của bạn đến cán bộ chuyên trách thuộc <strong>{html.escape(department)}</strong> để thẩm định. Sau khi rà soát hồ sơ, đơn vị xin thông báo kết quả như sau:"

    summary_rows = [
        ("Mã hồ sơ tiếp nhận", f"<strong>{html.escape(record_id)}</strong>"),
        ("Chuyên môn phân loại", html.escape(topic_name)),
        ("Đơn vị thẩm định", f"<strong>{html.escape(department)}</strong>"),
        ("Kết quả rà soát", "<span style='color: #dc2626; font-weight: 700;'>Tạm dừng thụ lý / Cần bổ sung</span>")
    ]

    content_blocks = f"""
    <div style="font-size: 13px; font-weight: 700; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">LÝ DO CHƯA ĐỦ ĐIỀU KIỆN THỤ LÝ / CĂN CỨ TỪ CHỐI:</div>
    <div style="background: #fef2f2; border-left: 4px solid #ef4444; border: 1px solid #fee2e2; border-radius: 4px; padding: 16px 18px; font-size: 14px; color: #7f1d1d; line-height: 1.6; margin-bottom: 20px;">
      {html.escape(reason_notes.strip()).replace(chr(10), '<br/>')}
    </div>

    <div style="font-size: 13px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">HƯỚNG DẪN KHẮC PHỤC & BỔ SUNG HỒ SƠ:</div>
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px 18px; font-size: 13px; color: #334155; line-height: 1.7; margin-bottom: 20px;">
      <div style="margin-bottom: 6px;">1. <strong>Kiểm tra lại thông tin:</strong> Đảm bảo Mã sinh viên, Lớp học phần và số điện thoại liên lạc chính xác.</div>
      <div style="margin-bottom: 6px;">2. <strong>Chuẩn bị minh chứng:</strong> Bổ sung ảnh chụp biên lai ngân hàng, đơn xin phép có xác nhận hoặc giấy tờ y tế hợp lệ theo quy chế.</div>
      <div>3. <strong>Nộp lại yêu cầu:</strong> Bạn có thể tạo phản ánh mới trên cổng EduSupportAI hoặc mang giấy tờ trực tiếp đến quầy Một cửa để được cán bộ hỗ trợ ngay.</div>
    </div>
    """

    html_body = _wrap_email_html(
        title_banner=f"Thông báo kết quả rà soát hồ sơ học vụ - {record_id}",
        status_badge_html=badge_html,
        greeting_html=greeting_html,
        summary_table_rows=summary_rows,
        content_blocks_html=content_blocks,
        contact_dict=contact,
        record_id=record_id
    )

    return subject, plain_body, html_body

def build_intake_confirmation_email(
    record_id: str,
    topic: str,
    department: str,
    clean_text: str,
    priority_level: str = "Bình thường",
    student_name: Optional[str] = None,
    student_id: Optional[str] = None,
    estimated_sla: str = "24 - 48 giờ làm việc"
) -> Tuple[str, str, str]:
    """
    Soạn thảo email xác nhận đã tiếp nhận phản ánh vào hàng đợi xử lý.
    Trả về Tuple: (subject, plain_text_body, html_body)
    """
    topic_name = TOPICS.get(topic, topic)
    subject = f"[EduSupportAI] Xác nhận tiếp nhận phản ánh học vụ - Mã số {record_id}"
    contact = get_dept_contact(department)

    recipient_greeting = _format_student_recipient_text(student_name, student_id)

    plain_body = f"""Kính gửi {recipient_greeting},

Hệ thống EduSupportAI xác nhận đã tiếp nhận yêu cầu phản ánh của bạn vào hệ thống:

THÔNG TIN TIẾP NHẬN:
- Mã hồ sơ: {record_id}
- Lĩnh vực: {topic_name}
- Đơn vị được giao thụ lý: {department}
- Mức độ ưu tiên xử lý: {priority_level}
- Thời gian dự kiến hoàn tất (SLA): {estimated_sla}

TÓM TẮT NỘI DUNG PHẢN ÁNH:
--------------------------------------------------
{clean_text.strip()}
--------------------------------------------------

TIẾN TRÌNH XỬ LÝ TIẾP THEO:
1. Hồ sơ của bạn đã được chuyển đến Bàn làm việc của cán bộ chuyên trách tại {department}.
2. Cán bộ sẽ đối soát quy chế và thẩm tra dữ liệu hồ sơ theo thời hạn cam kết.
3. Kết quả giải quyết hoặc yêu cầu bổ sung sẽ được gửi trực tiếp về email này.

LIÊN HỆ KHI CẦN XỬ LÝ GẤP:
- Văn phòng: {contact.get('office')}
- Hotline: {contact.get('hotline')} | Email: {contact.get('email')}

Trân trọng,
EduSupportAI - Trường Đại học Công nghệ Đông Á (EAUT)
""".strip()

    badge_html = f"""<div style="background: #f8fafc; border: 1px solid #64748b; color: #1e293b; font-size: 12px; font-weight: 700; padding: 7px 14px; border-radius: 6px; display: inline-block;">
        [XÁC NHẬN TIẾP NHẬN YÊU CẦU] &nbsp; HỒ SƠ ĐÃ VÀO HÀNG ĐỢI XỬ LÝ (MỨC ƯU TIÊN: {html.escape(priority_level.upper())})
    </div>"""

    st_display = f"<strong>{html.escape(student_name)}</strong> " if student_name else "<strong>Quý Sinh viên</strong>"
    if student_id:
        st_display += f" (Mã sinh viên: <strong>{html.escape(student_id)}</strong>)"
    greeting_html = f"Kính gửi {st_display},<br/><br/>Hệ thống EduSupportAI xác nhận đã ghi nhận yêu cầu phản ánh của bạn. Thông tin hồ sơ đã được đồng bộ vào hệ thống quản lý học vụ:"

    summary_rows = [
        ("Mã hồ sơ tiếp nhận", f"<strong>{html.escape(record_id)}</strong>"),
        ("Chuyên môn phân loại", html.escape(topic_name)),
        ("Đơn vị thụ lý", f"<strong>{html.escape(department)}</strong>"),
        ("Mức độ ưu tiên", html.escape(priority_level)),
        ("Thời gian dự kiến xử lý", f"<strong>{html.escape(estimated_sla)}</strong>")
    ]

    content_blocks = f"""
    <div style="font-size: 13px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">TÓM TẮT NỘI DUNG ĐÃ GỬI:</div>
    <div style="background: #f8fafc; border-left: 4px solid #64748b; border: 1px solid #e2e8f0; border-radius: 4px; padding: 14px 18px; font-size: 13px; color: #334155; line-height: 1.6; margin-bottom: 20px;">
      {html.escape(clean_text.strip()).replace(chr(10), '<br/>')}
    </div>
    """

    html_body = _wrap_email_html(
        title_banner=f"Xác nhận tiếp nhận phản ánh học vụ - {record_id}",
        status_badge_html=badge_html,
        greeting_html=greeting_html,
        summary_table_rows=summary_rows,
        content_blocks_html=content_blocks,
        contact_dict=contact,
        record_id=record_id
    )

    return subject, plain_body, html_body

def build_resolution_email(
    record_id: str,
    topic: str,
    department: str,
    resolution_text: str,
    confidence_score: Optional[float] = None,
    is_auto_approved: bool = False,
    student_name: Optional[str] = None,
    student_id: Optional[str] = None,
    procedure_info: Optional[Dict[str, Any]] = None,
    library_info: Optional[Dict[str, Any]] = None,
    officer_notes: Optional[str] = None
) -> Tuple[str, str]:
    """
    Soạn tiêu đề và nội dung email thông báo giải quyết phản ánh học vụ.
    Bảo toàn tương thích ngược 100% với các mã nguồn gọi cũ (trả về 2 phần tử: subject, plain_body).
    """
    subj, plain_body, _ = build_rich_resolution_email(
        record_id=record_id,
        topic=topic,
        department=department,
        resolution_text=resolution_text,
        confidence_score=confidence_score,
        is_auto_approved=is_auto_approved,
        student_name=student_name,
        student_id=student_id,
        procedure_info=procedure_info,
        library_info=library_info,
        officer_notes=officer_notes
    )
    return subj, plain_body

# ==============================================================================
# HÀM GỬI EMAIL ĐA ĐỊNH DẠNG (SMTP THỰC TẾ & MOCK DISPATCH)
# ==============================================================================

def send_resolution_email(
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    record_id: Optional[str] = None,
    smtp_override: Optional[Dict[str, str]] = None,
    db_path=None
) -> Tuple[bool, str]:
    """
    Gửi email thông báo giải quyết phản ánh hỗ trợ cả Plain Text và HTML.
    - Nếu có cấu hình tài khoản và mật khẩu SMTP: Thực hiện gửi thật qua SMTP với MIME multipart/alternative.
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

            # Đính kèm phần Plain Text cho các ứng dụng đọc text
            part_plain = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part_plain)

            # Đính kèm phần HTML nếu có
            if body_html:
                part_html = MIMEText(body_html, "html", "utf-8")
                msg.attach(part_html)

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
                body_html=body_html or "",
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
                body_html=body_html or "",
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
            body_html=body_html or "",
            db_path=db_path
        )
        return True, (
            f"Đã ghi nhận gửi email thành công tới {recipient} (Chế độ mô phỏng kiểm thử). "
            "Để kích hoạt gửi thực qua máy chủ Gmail, bạn có thể thiết lập biến môi trường GMAIL_APP_PASSWORD."
        )
