# -*- coding: utf-8 -*-
"""
Module: src.library_service
Dịch vụ Quản trị & Tra cứu CSDL Thư viện EAUT:
- Nhận diện các câu hỏi, phản ánh của sinh viên liên quan đến Thư viện
- Tự động trích xuất thực thể: Tên sách, từ khóa giáo trình, Mã sinh viên (MSSV)
- Truy vấn CSDL thời gian thực: Kho sách (library_books) và Sổ mượn trả (library_borrows)
- Tích hợp số liệu thực tế (vị trí kệ, số lượng còn sẵn, ngày hết hạn, tiền phạt) vào văn bản giải đáp
- Tăng cường quy trình chuẩn hóa PROC_CSVC_03 (Quyết định 101/QĐ-ĐHCNĐA)
"""

import re
import unicodedata
from typing import Optional, Dict, Any, List

from src.database import (
    search_library_books,
    get_library_book,
    get_student_library_borrows,
    strip_vietnamese_accents
)
try:
    from src.app_logger import app_log
except ImportError:
    def app_log(*args, **kwargs):
        pass

LIBRARY_KEYWORDS = [
    "thư viện", "thu vien", "mượn sách", "muon sach", "trả sách", "tra sach",
    "sách", "sach", "giáo trình", "giao trinh", "thủ thư", "thu thu",
    "kệ sách", "ke sach", "quá hạn sách", "qua han sach", "phòng đọc", "phong doc",
    "lib.cndonga.edu.vn", "tài liệu thư viện", "tai lieu thu vien", "thư viện số",
    "phòng tự học", "tra cứu sách", "tìm sách", "mượn tài liệu"
]

STOP_PHRASES = [
    "cho em hỏi", "cho minh hoi", "thầy cô cho em hỏi", "thay co cho em hoi",
    "em muốn hỏi", "em muon hoi", "em muốn mượn", "em muon muon",
    "thư viện trường mình", "thu vien truong minh", "thư viện eaut", "thu vien eaut",
    "thư viện", "thu vien", "còn sách", "con sach", "hết sách", "het sach",
    "ở kệ nào", "o ke nao", "tại tầng nào", "tai tang nao", "không ạ", "khong a",
    "không", "khong", "ạ", "a", "dạ", "da", "cuốn", "cuon", "quyển", "quyen",
    "sách", "sach", "giáo trình", "giao trinh", "tài liệu", "tai lieu",
    "tìm giúp em", "tim giup em", "tra cứu", "tra cuu", "kiểm tra", "kiem tra",
    "bị quá hạn", "bi qua han", "hạn trả", "han tra", "tiền phạt", "tien phat"
]

def is_library_inquiry(text: str) -> bool:
    """Kiểm tra xem câu hỏi hoặc phản ánh có liên quan đến Thư viện hay không."""
    if not text:
        return False
    t_clean = strip_vietnamese_accents(text.lower())
    return any(kw in t_clean for kw in LIBRARY_KEYWORDS)

def extract_student_id_from_text(text: str) -> Optional[str]:
    """Trích xuất Mã sinh viên (MSSV) từ nội dung phản ánh (định dạng EAUT thường 10 số, bắt đầu bằng 20xx)."""
    if not text:
        return None
    # Khớp tiền tố MSSV rõ ràng: "mssv 2022601234", "mã sinh viên: 2021600123"
    prefix_match = re.search(r'(?:mssv|mã\s+sinh\s+viên|ma\s+sinh\s+vien|sv)[\s:=_-]*([0-9]{8,12})', text, re.IGNORECASE)
    if prefix_match:
        return prefix_match.group(1).strip()
    
    # Khớp chuỗi 10 chữ số bắt đầu bằng 20 (khóa học EAUT: 2019 - 2026)
    year_match = re.search(r'\b(20[12][0-9]{7})\b', text)
    if year_match:
        return year_match.group(1).strip()
    return None

def extract_book_query(text: str) -> str:
    """Tách lọc tên sách hoặc từ khóa trọng tâm từ câu hỏi của sinh viên."""
    if not text:
        return ""
    
    # Tìm chuỗi trong ngoặc kép nếu có: cuốn "Kỹ thuật phần mềm"
    quote_match = re.search(r'["\']([^"\']{3,60})["\']', text)
    if quote_match:
        return quote_match.group(1).strip()

    # Làm sạch các từ dừng thông dụng
    cleaned = text
    # Bỏ thông tin liên hệ và MSSV
    cleaned = re.sub(r'(?:mssv|mã sinh viên|sđt|email|thông tin liên hệ).*', '', cleaned, flags=re.IGNORECASE)
    
    # Chuẩn hóa loại bỏ câu hỏi lịch sự
    for phrase in STOP_PHRASES:
        cleaned = re.sub(re.escape(phrase), ' ', cleaned, flags=re.IGNORECASE)

    # Loại bỏ ký tự đặc biệt thừa
    cleaned = re.sub(r'[,.\-?:;!_+=/\\]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def query_library_data(inquiry_text: str, student_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Truy vấn CSDL Thư viện EAUT theo nội dung câu hỏi và MSSV:
    1. Tra cứu tồn kho sách (vị trí kệ, số lượng có sẵn, bản số hóa)
    2. Tra cứu lịch sử mượn trả cá nhân (hạn trả, tiền phạt quá hạn)
    """
    if not is_library_inquiry(inquiry_text) and not student_id:
        return {
            "is_library": False,
            "has_live_data": False,
            "books_found": [],
            "student_borrows": [],
            "student_id": None
        }

    sid = student_id or extract_student_id_from_text(inquiry_text)
    borrows = get_student_library_borrows(sid) if sid else []

    # Nhận diện ý định tra cứu sách
    t_lower = inquiry_text.lower()
    is_borrow_status_intent = any(w in t_lower for w in [
        "đang mượn", "dang muon", "mượn những", "muon nhung", "hạn trả", "han tra",
        "tiền phạt", "tien phat", "quá hạn", "qua han"
    ])
    
    is_book_search_intent = any(w in t_lower for w in [
        "còn sách", "con sach", "hết sách", "het sach", "ở kệ nào", "o ke nao",
        "tìm sách", "tim sach", "tra cứu sách", "tra cuu sach", "cuốn", "cuon",
        "giáo trình", "giao trinh"
    ]) or (not is_borrow_status_intent and any(w in t_lower for w in ["sách", "sach", "tài liệu"]))

    # Tìm kiếm sách theo từ khóa
    book_q = extract_book_query(inquiry_text)
    books = []
    if is_book_search_intent and book_q and len(book_q) >= 2:
        books = search_library_books(query=book_q, limit=5)
    
    # Chỉ khi có ý định tìm sách cụ thể mà chưa thấy kết quả, mới dùng từ khóa dự phòng
    if is_book_search_intent and not books and len(book_q) >= 2:
        if "phần mềm" in t_lower or "phan mem" in t_lower:
            books = search_library_books(query="kỹ thuật phần mềm", limit=3)
        elif "cơ sở dữ liệu" in t_lower or "sql" in t_lower:
            books = search_library_books(query="cơ sở dữ liệu", limit=3)
        elif "python" in t_lower or "trí tuệ nhân tạo" in t_lower or "ai" in t_lower:
            books = search_library_books(query="python", limit=3)
        elif "kế toán" in t_lower or "ke toan" in t_lower:
            books = search_library_books(query="kế toán", limit=3)
        elif "kinh tế" in t_lower or "kinh te" in t_lower:
            books = search_library_books(query="kinh tế", limit=3)
        elif "chi tiết máy" in t_lower or "cơ khí" in t_lower:
            books = search_library_books(query="chi tiết máy", limit=3)
        elif "giải tích" in t_lower or "toán" in t_lower:
            books = search_library_books(query="giải tích", limit=3)
        elif "tiếng anh" in t_lower or "english" in t_lower:
            books = search_library_books(query="tiếng anh", limit=3)

    has_live_data = bool(books or borrows)
    if has_live_data:
        app_log("LIBRARY", "Truy vấn CSDL Thư viện thành công",
                f"Sách tìm thấy: {len(books)} cuốn, Bản ghi mượn trả (MSSV {sid or 'N/A'}): {len(borrows)} mục")

    return {
        "is_library": True,
        "has_live_data": has_live_data,
        "student_id": sid,
        "book_query_used": book_q,
        "books_found": books,
        "student_borrows": borrows
    }

def build_library_live_block(library_data: Dict[str, Any]) -> str:
    """Tạo khối văn bản dữ liệu thực tế từ CSDL Thư viện để ghép vào phản hồi cho sinh viên."""
    if not library_data.get("has_live_data"):
        return ""

    lines = []
    lines.append("🔍 THÔNG TIN TRA CỨU CSDL THƯ VIỆN EAUT (THỜI GIAN THỰC):")

    books = library_data.get("books_found", [])
    if books:
        lines.append("\n📚 Danh mục sách & Tình trạng trên giá:")
        for idx, b in enumerate(books, 1):
            avail = b.get("available_copies", 0)
            total = b.get("total_copies", 0)
            status_tag = f"✅ CÒN {avail}/{total} CUỐN SẴN SÀNG" if avail > 0 else "❌ TẠM HẾT TRÊN GIÁ (Đang mượn hết)"
            lines.append(f"  {idx}. [{b.get('book_id')}] {b.get('title')}")
            lines.append(f"     • Tác giả: {b.get('author')} | Năm XB: {b.get('publish_year')}")
            lines.append(f"     • Vị trí: {b.get('location')} (Mã xếp giá: {b.get('call_number')})")
            lines.append(f"     • Tình trạng: {status_tag}")
            if b.get("is_digital"):
                lines.append(f"     • Bản điện tử: Đã số hóa trên cổng Thư viện số {b.get('digital_url')}")

    borrows = library_data.get("student_borrows", [])
    sid = library_data.get("student_id")
    if borrows and sid:
        lines.append(f"\n👤 Hồ sơ mượn trả tài liệu của sinh viên [MSSV: {sid}]:")
        for idx, br in enumerate(borrows, 1):
            stt = br.get("status", "Đang mượn")
            if stt == "Quá hạn":
                fine = br.get("fine_amount", 0)
                overdue = br.get("overdue_days", 0)
                status_txt = f"⚠️ QUÁ HẠN {overdue} NGÀY — Tiền phạt tạm tính: {fine:,} VNĐ (5.000đ/ngày)"
            elif stt == "Đã trả":
                status_txt = f"✅ ĐÃ TRẢ NGÀY {br.get('return_date', '-')}"
            else:
                rem = br.get("days_remaining", 0)
                status_txt = f"📘 ĐANG MƯỢN — Hạn trả: {br.get('due_date')} (Còn {rem} ngày)"

            lines.append(f"  {idx}. Sách: '{br.get('book_title')}'")
            lines.append(f"     • Mã mượn: {br.get('borrow_id')} | Ngày mượn: {br.get('borrow_date')}")
            lines.append(f"     • Trạng thái: {status_txt}")
            if br.get("renew_count", 0) > 0:
                lines.append(f"     • Đã gia hạn: {br.get('renew_count')} lần (Tối đa 2 lần)")

    return "\n".join(lines)

def augment_response_with_library_data(base_draft: str, library_data: Dict[str, Any]) -> str:
    """Tích hợp thông tin tra cứu CSDL Thư viện vào bản nháp câu trả lời quy trình chuẩn."""
    if not library_data or not library_data.get("has_live_data"):
        return base_draft

    live_block = build_library_live_block(library_data)
    if not live_block:
        return base_draft

    # Tách phần mở đầu và phần quy trình
    greeting = "Chào bạn,\n\n"
    body = base_draft
    if base_draft.startswith("Chào bạn,\n\n"):
        body = base_draft[len("Chào bạn,\n\n"):]

    augmented = (
        f"{greeting}"
        f"{live_block}\n\n"
        f"{body}"
    )
    return augmented
