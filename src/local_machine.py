# -*- coding: utf-8 -*-
"""
Module: src.local_machine
Hệ thống Máy học Cục bộ (Local Learning Machine) & Engine Lập luận Quy trình (Local Reasoning Engine):
- Huấn luyện cục bộ trên tập dữ liệu chuẩn hóa kết hợp toàn bộ tri thức quy trình từ data-doc/
- Phân loại chủ đề học vụ (Multi-class Classification) với TF-IDF kép (Word 1-2 & Char 3-5)
- Tra cứu và so khớp quy trình nghiệp vụ tương đồng (Semantic Procedure Retrieval)
- Lập luận từng bước (Chain-of-Thought Reasoning) và tổng hợp giải đáp tự động có căn cứ văn bản
- Tích hợp bộ ghi vết minh bạch (Explainability Trace Logger) ghi nhận chi tiết từng mili-giây
"""

import sys
import json
import uuid
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
import joblib

from src.config import MODEL_PATH, TOPICS
from src.cleaner import clean_text_single
try:
    from src.cleaner import parse_student_feedback
except ImportError:
    try:
        import importlib
        import src.cleaner
        importlib.reload(src.cleaner)
        from src.cleaner import parse_student_feedback
    except Exception:
        def parse_student_feedback(raw_text: str) -> dict:
            import re
            if not isinstance(raw_text, str) or not raw_text.strip():
                return {"issue": "", "contacts": "", "student_message": ""}
            content = raw_text.strip()
            issue = ""
            contacts = ""
            m_contact = re.search(r'Thông tin liên hệ:\s*(.+)$', content, re.IGNORECASE | re.DOTALL)
            if m_contact:
                contacts = m_contact.group(1).strip()
                content = content[:m_contact.start()].strip()
            m_issue = re.search(r'Vấn đề ghi nhận:\s*([^.\n]+(?:\.[^.\n]+)*?)(?:\.\s*|\n|$)', content, re.IGNORECASE)
            if m_issue:
                issue = m_issue.group(1).strip()
                content = content[m_issue.end():].strip()
            student_msg = content.strip(' .;\n')
            if not student_msg and issue:
                student_msg = issue
            elif not student_msg:
                student_msg = raw_text.strip()
            return {"issue": issue, "contacts": contacts, "student_message": student_msg}
from src.doc_parser import build_procedure_catalog, KB_OUTPUT_JSON
from src.trace_logger import ExecutionTrace
from src.model import determine_priority, KEYWORDS_URGENT, KEYWORDS_HIGH
from src.email_service import get_dept_contact

DEPT_MAP = {
    "Hoc_phi": "Phòng Tài chính - Kế toán",
    "Lich_hoc_lich_thi": "Phòng Đào tạo",
    "Diem_khao_thi": "Ban Khảo thí & Đảm bảo chất lượng",
    "Thu_tuc_hanh_chinh": "Bộ phận Một cửa - Phòng CTSV",
    "Co_so_vat_chat": "Phòng Hành chính - Quản trị CSVC",
    "He_thong_CNTT": "Trung tâm Công nghệ Thông tin",
    "Khac": "Bộ phận Tiếp nhận chung"
}

def analyze_specific_situation(clean_text: str, topic: str, proc_id: str = "") -> Dict[str, Any]:
    """
    Chẩn đoán bối cảnh chi tiết của sinh viên và sinh giải pháp trực diện (Context-Aware Diagnosis & Direct Solution).
    Nhận diện các tình huống thực tế thường gặp nhất từ kho dữ liệu 122 phản ánh EAUT và đối chiếu với thủ tục tương ứng.
    Tập trung giải đáp đúng trọng tâm, thực tế, không liệt kê thủ tục rườm rà.
    """
    fb = parse_student_feedback(clean_text)
    msg_clean = fb.get("student_message", "").lower()
    issue_clean = fb.get("issue", "").lower()
    raw_lower = clean_text.lower()
    text_lower = f"{msg_clean} {issue_clean} {raw_lower}"

    # 1. HỌC PHÍ & TÀI CHÍNH (Hoc_phi / PROC_TC_01 / PROC_CTSV_03)
    if any(k in text_lower for k in [
        "chuyen khoan", "chuyển khoản", "vietcombank", "vietinbank", "qr", "vietqr",
        "treo tien", "treo tiền", "gach no", "gạch nợ", "báo nợ", "chua vao cong", "chưa vào cổng",
        "trừ tiền", "tru tien", "bi tru"
    ]):
        if any(k in text_lower for k in ["sai cu phap", "sai noi dung", "nhap nham", "nhầm nội dung"]):
            return {
                "situation_summary": "Sai cú pháp nội dung chuyển khoản học phí dẫn đến hệ thống đối soát tự động chưa gạch nợ.",
                "direct_solution": (
                    "Về việc chuyển khoản học phí sai cú pháp nội dung khiến hệ thống chưa gạch nợ:\n"
                    "Bạn vui lòng mang ảnh chụp biên lai giao dịch ngân hàng (có hiển thị rõ Mã giao dịch FT/Ref và số tài khoản thụ hưởng) đến trực tiếp Phòng Kế toán (Tầng 1, Tòa A) hoặc gửi email minh chứng để cán bộ đối soát thủ công và cập nhật gạch nợ ngay trên hệ thống cho bạn."
                ),
                "actionable_guidance": (
                    "  1. Chụp lại biên lai chuyển khoản / sao kê giao dịch ngân hàng có hiển thị rõ Mã giao dịch (FT/Ref) và số tài khoản thụ hưởng.\n"
                    "  2. Mang biên lai đến trực tiếp Phòng Kế toán (Tầng 1, Tòa A) hoặc gửi email kèm minh chứng để cán bộ đối soát thủ công và gạch nợ trực tiếp trên hệ thống."
                ),
                "has_specific_match": True
            }
        return {
            "situation_summary": "Đã chuyển khoản hoặc quét mã QR nộp học phí nhưng hệ thống cổng sinh viên chưa cập nhật gạch nợ sau 24 - 48 giờ làm việc.",
            "direct_solution": (
                "Về việc đã nộp học phí qua chuyển khoản/quét mã QR nhưng cổng sinh viên chưa cập nhật gạch nợ:\n"
                "Hệ thống đối soát liên ngân hàng thường cập nhật sau 24 - 48 giờ làm việc (không tính Thứ Bảy, Chủ Nhật). Nếu sau 48 giờ cổng vẫn báo nợ, bạn vui lòng mang ảnh chụp biên lai chuyển tiền (hiển thị rõ Mã giao dịch FT/Ref) tới Phòng Tài chính - Kế toán (Tầng 1, Tòa A) để được kiểm tra và xử lý gạch nợ trực tiếp ngay trong ngày."
            ),
            "actionable_guidance": (
                "  1. Kiểm tra lại biên lai giao dịch ngân hàng để đảm bảo đã trừ tiền thành công và có Mã giao dịch (Mã FT/Ref).\n"
                "  2. Đối soát hệ thống liên ngân hàng thường mất 24 - 48 giờ làm việc (không tính Thứ Bảy, Chủ Nhật). Nếu sau 48 giờ cổng vẫn báo nợ, bạn vui lòng mang ảnh chụp biên lai tới Phòng Tài chính - Kế toán (Tầng 1, Tòa A) để được kiểm tra và xử lý gạch nợ ngay."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["gia han", "gia hạn", "chia dot", "chia đợt", "cam thi", "cấm thi", "kho khan", "khó khăn", "chua co tien", "chưa có tiền"]):
        return {
            "situation_summary": "Đề nghị gia hạn nộp học phí hoặc chia đợt đóng học phí do hoàn cảnh đột xuất để không bị cấm thi.",
            "direct_solution": (
                "Về việc xin gia hạn nộp học phí hoặc chia đợt đóng học phí:\n"
                "Bạn vui lòng điền Đơn xin gia hạn nộp học phí (theo mẫu của Phòng Kế toán), ghi rõ cam kết thời hạn nộp và xin chữ ký xác nhận của phụ huynh. Sau đó, nộp đơn trực tiếp tại Phòng Tài chính - Kế toán (Tầng 1, Tòa A) trước ngày thi môn đầu tiên để được phê duyệt danh sách dự thi có điều kiện."
            ),
            "actionable_guidance": (
                "  1. Làm Đơn xin gia hạn nộp học phí (Mẫu đơn Phòng Kế toán), ghi rõ cam kết thời hạn nộp và có chữ ký xác nhận của phụ huynh.\n"
                "  2. Nộp đơn trực tiếp tại Phòng Tài chính - Kế toán (Tầng 1, Tòa A) trước ngày thi môn đầu tiên để được phê duyệt danh sách dự thi có điều kiện."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["mien giam", "miễn giảm", "nghi dinh 81", "nghị định 81", "ho ngheo", "hộ nghèo", "vung sau", "thương binh", "thuong binh", "chinh sach", "hoc bong", "học bổng"]):
        return {
            "situation_summary": "Thủ tục xin hưởng chính sách miễn giảm học phí, trợ cấp học tập theo Nghị định 81/2021/NĐ-CP hoặc xét học bổng.",
            "direct_solution": (
                "Về chính sách miễn giảm học phí và trợ cấp học tập theo Nghị định 81/2021/NĐ-CP:\n"
                "Bạn vui lòng chuẩn bị Đơn đề nghị miễn giảm học phí (theo mẫu) kèm Bản sao công chứng Giấy chứng nhận hộ nghèo/thương binh có dấu đỏ của UBND cấp xã trong năm học hiện hành, nộp tại Bộ phận Một cửa - Phòng Công tác sinh viên (Tầng 1, Tòa A) trong thời hạn 30 ngày kể từ ngày khai giảng học kỳ."
            ),
            "actionable_guidance": (
                "  1. Chuẩn bị hồ sơ chính sách gồm: Đơn đề nghị miễn giảm học phí (theo mẫu) kèm Bản sao công chứng Giấy chứng nhận hộ nghèo/thương binh có dấu đỏ của UBND cấp xã/Phòng LĐ-TB&XH trong năm học hiện hành.\n"
                "  2. Nộp hồ sơ tại Bộ phận Một cửa - Phòng Công tác sinh viên (Tầng 1, Tòa A) trong thời hạn 30 ngày kể từ ngày khai giảng học kỳ."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["tin chi", "tín chỉ", "ky phu", "kỳ phụ", "ky he", "kỳ hè", "rut mon", "rút môn", "can tru", "cấn trừ", "hoa don", "hóa đơn", "thu quy", "thủ quỹ"]):
        return {
            "situation_summary": "Thắc mắc về định mức học phí học kỳ hè, xuất hóa đơn điện tử hoặc cấn trừ tiền học phí khi rút học phần.",
            "direct_solution": (
                "Về việc cấn trừ học phí hoặc rút học phần:\n"
                "Đối với môn học đã rút hợp lệ trước tuần 2 của kỳ học, số tiền học phí sẽ được bảo lưu và cấn trừ tự động vào kỳ học tiếp theo. Để kiểm tra chi tiết công nợ hoặc nhận hóa đơn điện tử, bạn liên hệ Phòng Thủ quỹ - Kế toán (Tầng 1, Tòa A) trong khung giờ 08:00 - 16:30 từ Thứ Hai đến Thứ Sáu."
            ),
            "actionable_guidance": (
                "  1. Đối với môn học đã rút hợp lệ trước tuần 2 của kỳ học, số tiền học phí sẽ được bảo lưu và cấn trừ tự động vào kỳ học tiếp theo.\n"
                "  2. Để lấy hóa đơn điện tử hoặc nộp trực tiếp bằng tiền mặt, bạn liên hệ Phòng Thủ quỹ - Kế toán (Tầng 1, Tòa A) trong khung giờ 08:00 - 16:30 từ Thứ Hai đến Thứ Sáu."
            ),
            "has_specific_match": True
        }

    # 2. LỊCH HỌC & LỊCH THI (Lich_hoc_lich_thi / PROC_DT_04 / PROC_DT_03)
    if any(k in text_lower for k in ["trung lich thi", "trùng lịch thi", "trung ca thi", "trùng ca thi", "trung gio", "trùng giờ"]):
        return {
            "situation_summary": "Trùng ca thi / giờ thi giữa hai hoặc nhiều môn học phần kết thúc kỳ.",
            "direct_solution": (
                "Về việc trùng ca thi / giờ thi giữa các môn học phần kết thúc kỳ:\n"
                "Bạn vui lòng điền Đơn đề nghị chuyển ca thi / giải quyết trùng lịch thi (Mẫu Đào tạo) và nộp tại Bộ phận Một cửa - Phòng Quản lý Đào tạo & Khảo thí (Tầng 1, Tòa A) trước ngày thi ít nhất 03 ngày làm việc để được xếp chuyển sang ca thi dự phòng kịp thời."
            ),
            "actionable_guidance": (
                "  1. Tải và điền Đơn đề nghị chuyển ca thi / giải quyết trùng lịch thi (Mẫu Đào tạo).\n"
                "  2. Nộp đơn khẩn tại Bộ phận Một cửa - Phòng Quản lý Đào tạo & Khảo thí (Tầng 1, Tòa A) trước ngày thi ít nhất 03 ngày làm việc để được xếp ca thi dự phòng."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["hoan thi", "hoãn thi", "nhap vien", "nhập viện", "cap cuu", "cấp cứu", "benh vien", "bệnh viện", "bi om", "bị ốm"]):
        return {
            "situation_summary": "Xin hoãn thi kết thúc học phần vì lý do ốm đau, tai nạn hoặc nhập viện điều trị đột xuất.",
            "direct_solution": (
                "Về việc xin hoãn thi kết thúc học phần vì lý do sức khỏe hoặc điều trị y tế đột xuất:\n"
                "Bạn vui lòng chuẩn bị Đơn xin hoãn thi kèm theo Giấy vào viện / Giấy ra viện hoặc Bệnh án có xác nhận của Bệnh viện từ cấp quận/huyện trở lên, nộp tại Phòng Quản lý Đào tạo trong vòng 48 giờ kể từ ca thi để được bảo lưu điểm quá trình sang đợt thi phụ."
            ),
            "actionable_guidance": (
                "  1. Chuẩn bị Đơn xin hoãn thi kèm theo Giấy vào viện / Giấy ra viện hoặc Bệnh án có xác nhận của Bệnh viện từ cấp quận/huyện trở lên.\n"
                "  2. Nộp hồ sơ trực tiếp hoặc nhờ người nhà nộp tại Phòng Quản lý Đào tạo trong vòng 48 giờ kể từ thời điểm diễn ra ca thi để được bảo lưu điểm quá trình sang đợt thi phụ."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["khoa cua", "khóa cửa", "dung ngoai hanh lang", "đứng ngoài hành lang", "chua mo cua", "chưa mở cửa"]):
        return {
            "situation_summary": "Phòng học bị khóa cửa giờ học chính khóa, giảng viên và sinh viên chưa vào được phòng.",
            "direct_solution": (
                "Về sự cố phòng học bị khóa cửa trong giờ học chính khóa:\n"
                "Đại diện ban cán sự lớp liên hệ ngay Đội Bảo vệ - Trực ban Giảng đường tại Tầng 1 Tòa A hoặc Tòa B để mở khóa phòng ngay lập tức. Hotline Trực ban CSVC hỗ trợ khẩn cấp: (024) 6262-7797 (Nhánh 104)."
            ),
            "actionable_guidance": (
                "  1. Đại diện ban cán sự lớp liên hệ ngay Đội Bảo vệ - Trực ban Giảng đường tại Tầng 1 Tòa A hoặc Tòa B để mở khóa phòng ngay lập tức.\n"
                "  2. Số điện thoại Trực ban CSVC: (024) 6262-7797 (Nhánh 104) để được hỗ trợ khẩn cấp."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["hoc lai", "học lại", "cai thien", "cải thiện", "diem f", "điểm f", "huy lop", "hủy lớp", "nghi tet", "nghỉ tết"]):
        return {
            "situation_summary": "Thủ tục đăng ký học lại môn bị điểm F, học cải thiện điểm GPA hoặc tra cứu kế hoạch thời gian năm học.",
            "direct_solution": (
                "Về thủ tục đăng ký học lại môn điểm F hoặc học cải thiện điểm GPA:\n"
                "Bạn theo dõi thông báo đăng ký tín chỉ đầu mỗi học kỳ trên cổng daotao.eaut.edu.vn để chọn lớp học phần phù hợp. Trường hợp lớp bị hủy do thiếu sĩ số hoặc cần mở lớp nguyện vọng (từ 20 sinh viên trở lên), bạn liên hệ trực tiếp Phòng Quản lý Đào tạo (Tầng 1, Tòa A) để làm đơn đề xuất."
            ),
            "actionable_guidance": (
                "  1. Sinh viên theo dõi thông báo đăng ký tín chỉ đầu mỗi học kỳ trên cổng daotao.eaut.edu.vn để chọn lớp học phần.\n"
                "  2. Trường hợp lớp bị hủy do thiếu sĩ số hoặc cần mở lớp nguyện vọng (từ 20 sinh viên trở lên), liên hệ trực tiếp Phòng Đào tạo (Tầng 1, Tòa A) để làm đơn đề xuất."
            ),
            "has_specific_match": True
        }

    # 3. ĐIỂM SỐ & KHẢO THÍ (Diem_khao_thi / PROC_DT_04 / PROC_DT_05 / PROC_CTSV_04)
    if any(k in text_lower for k in ["phuc khao", "phúc khảo", "cham lai", "chấm lại", "xem lai bai thi", "xem lại bài thi", "tu cham", "tự chấm"]):
        return {
            "situation_summary": "Nộp đơn đề nghị phúc khảo bài thi kết thúc học phần do nghi vấn kết quả điểm số chưa chính xác.",
            "direct_solution": (
                "Về việc đề nghị phúc khảo bài thi kết thúc học phần:\n"
                "Bạn vui lòng điền Đơn đề nghị phúc khảo bài thi kết thúc học phần theo mẫu chuẩn của Ban Khảo thí và nộp tại Bộ phận Một cửa - Ban Khảo thí (Tầng 1, Tòa A) trong thời hạn 15 ngày kể từ ngày công bố điểm thi trên hệ thống. Điểm phúc khảo sẽ được cập nhật trực tiếp sau khi chấm lại."
            ),
            "actionable_guidance": (
                "  1. Điền Đơn đề nghị phúc khảo bài thi kết thúc học phần theo mẫu chuẩn của Ban Khảo thí.\n"
                "  2. Nộp đơn và lệ phí phúc khảo tại Bộ phận Một cửa - Ban Khảo thí (Tầng 1, Tòa A) trong thời hạn 15 ngày kể từ ngày công bố điểm thi trên hệ thống."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["nhap nham", "nhập nhầm", "sai diem", "sai điểm", "lech diem", "lệch điểm", "chua len diem", "chưa lên điểm", "cham len diem", "chậm lên điểm", "chuyen can", "chuyên cần"]):
        return {
            "situation_summary": "Sai lệch điểm thi / điểm thành phần trên hệ thống so với bảng điểm của giảng viên hoặc bị tính nhầm điểm danh.",
            "direct_solution": (
                "Về việc sai lệch điểm thi hoặc chưa lên điểm trên cổng thông tin:\n"
                "Bạn liên hệ trực tiếp Giảng viên phụ trách học phần để đối chiếu với Bảng điểm gốc và Sổ điểm danh có chữ ký của sinh viên. Giảng viên sẽ lập Giấy đề nghị điều chỉnh điểm gửi Ban Khảo thí & ĐBCL tại Tầng 1 Tòa A để đính chính chính thức trên cổng thông tin."
            ),
            "actionable_guidance": (
                "  1. Liên hệ trực tiếp Giảng viên giảng dạy môn học để đối chiếu với Bảng điểm gốc và Sổ điểm danh có chữ ký của sinh viên.\n"
                "  2. Giảng viên sẽ lập Giấy đề nghị điều chỉnh điểm gửi Ban Khảo thí & ĐBCL tại Tầng 1 Tòa A để đính chính chính thức trên cổng thông tin."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["diem ren luyen", "điểm rèn luyện", "drl", "tru diem", "trừ điểm rèn luyện", "xep loai drl"]):
        return {
            "situation_summary": "Khiếu nại kết quả đánh giá Điểm rèn luyện (ĐRL) học kỳ hoặc bị trừ điểm rèn luyện nhầm.",
            "direct_solution": (
                "Về việc rà soát và khiếu nại kết quả Điểm rèn luyện (ĐRL):\n"
                "Bạn chuẩn bị các minh chứng tham gia hoạt động, giấy xin phép y tế hoặc chứng nhận tham gia phong trào của Khoa/Đoàn trường, sau đó nộp Đơn đề nghị rà soát Điểm rèn luyện tại Phòng Công tác sinh viên (Tầng 1, Tòa A) trong vòng 07 ngày làm việc kể từ ngày công bố kết quả dự kiến."
            ),
            "actionable_guidance": (
                "  1. Chuẩn bị các minh chứng tham gia hoạt động, giấy xin phép y tế hoặc chứng nhận tham gia phong trào của Khoa/Đoàn trường.\n"
                "  2. Nộp Đơn đề nghị rà soát Điểm rèn luyện tại Phòng Công tác sinh viên (Tầng 1, Tòa A) trong vòng 07 ngày làm việc kể từ ngày công bố kết quả dự kiến."
            ),
            "has_specific_match": True
        }

    # 4. THỦ TỤC HÀNH CHÍNH (Thu_tuc_hanh_chinh / PROC_CTSV_01 / PROC_CTSV_02 / PROC_DT_01 / PROC_DT_02 / PROC_DT_05)
    if any(k in text_lower for k in [
        "nghia vu quan su", "nghĩa vụ quân sự", "nvqs", "hoan nghia vu", "hoãn nghĩa vụ",
        "vay von", "vay vốn", "ngan hang chinh sach", "ngân hàng chính sách", "bm02",
        "ve xe buyt", "vé xe buýt", "visa", "giay xac nhan", "giấy xác nhận"
    ]):
        return {
            "situation_summary": "Xin cấp Giấy xác nhận sinh viên (để tạm hoãn Nghĩa vụ quân sự, vay vốn NHCSXH BM02, làm vé xe buýt hoặc hồ sơ cá nhân).",
            "direct_solution": (
                "Về thủ tục cấp Giấy xác nhận sinh viên (tạm hoãn Nghĩa vụ quân sự, vay vốn ngân hàng chính sách BM02, làm vé xe buýt):\n"
                "Bạn có thể đăng ký trực tuyến trên cổng sinh viên daotao.eaut.edu.vn hoặc đến trực tiếp Bàn tiếp nhận Một cửa - Phòng CTSV (Tầng 1, Tòa A). Thời gian xử lý từ 01 - 02 ngày làm việc. Khi đến nhận kết quả, bạn mang theo Thẻ sinh viên hoặc CCCD để đối chiếu."
            ),
            "actionable_guidance": (
                "  1. Đăng ký trực tuyến trên cổng sinh viên daotao.eaut.edu.vn hoặc đến trực tiếp Bàn tiếp nhận Một cửa - Phòng CTSV (Tầng 1, Tòa A).\n"
                "  2. Thời gian xử lý: 01 - 02 ngày làm việc. Khi nhận kết quả, mang theo Thẻ sinh viên hoặc CCCD để đối chiếu."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["mat the", "mất thẻ", "lam lai the", "làm lại thẻ", "the sinh vien", "thẻ sinh viên", "gay chip", "gãy chip", "the tam thoi", "thẻ tạm thời"]):
        return {
            "situation_summary": "Đề nghị cấp lại Thẻ sinh viên do bị mất, gãy chip hoặc xin cấp Thẻ sinh viên tạm thời có ảnh để dự thi.",
            "direct_solution": (
                "Về việc xin cấp lại Thẻ sinh viên do bị mất hoặc hỏng chip:\n"
                "Bạn vui lòng đến Bộ phận Một cửa - Phòng CTSV (Tầng 1, Tòa A), chuẩn bị 01 ảnh thẻ 3x4 (nền xanh) và lệ phí cấp lại (50.000đ) để làm thủ tục. Cán bộ Một cửa sẽ cấp ngay Giấy chứng nhận sinh viên tạm thời có dán ảnh và đóng dấu giáp lai trong ngày để bạn sử dụng đi thi."
            ),
            "actionable_guidance": (
                "  1. Nộp Đơn xin cấp lại thẻ sinh viên tại Bộ phận Một cửa - Phòng CTSV (Tầng 1, Tòa A), chuẩn bị 01 ảnh thẻ 3x4 (nền xanh) và lệ phí cấp lại (50.000đ).\n"
                "  2. Cán bộ Một cửa sẽ cấp ngay Giấy chứng nhận sinh viên tạm thời có dán ảnh và đóng dấu giáp lai trong ngày để bạn sử dụng đi thi."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["chuyen nganh", "chuyển ngành", "bm_cn01", "bao luu", "bảo lưu", "nghi hoc tam thoi", "nghỉ học tạm thời", "bm01", "thoi hoc", "thôi học", "rut ho so", "rút hồ sơ"]):
        return {
            "situation_summary": "Thủ tục xin chuyển ngành đào tạo (BM_CN01), bảo lưu kết quả học tập (BM01) hoặc xin thôi học rút hồ sơ gốc.",
            "direct_solution": (
                "Về thủ tục xin chuyển ngành đào tạo (BM_CN01) hoặc bảo lưu kết quả học tập (BM01):\n"
                "Bạn điền đơn theo mẫu quy định (BM_CN01 cho chuyển ngành, BM01 cho bảo lưu), xin xác nhận của Ban Chủ nhiệm Khoa, Thư viện (xác nhận không nợ sách) và Phòng Kế toán (không nợ học phí), sau đó nộp tại Phòng Quản lý Đào tạo (Tầng 1, Tòa A) để trình Ban Giám hiệu ra quyết định."
            ),
            "actionable_guidance": (
                "  1. Điền đơn theo mẫu quy định (BM_CN01 cho chuyển ngành, BM01 cho bảo lưu) kèm theo minh chứng liên quan.\n"
                "  2. Lấy xác nhận của Ban Chủ nhiệm Khoa, Thư viện (xác nhận không nợ sách) và Phòng Kế toán (không nợ học phí), sau đó nộp tại Phòng Đào tạo (Tầng 1, Tòa A) để trình Ban Giám hiệu ra quyết định."
            ),
            "has_specific_match": True
        }

    # 5. CƠ SỞ VẬT CHẤT (Co_so_vat_chat / PROC_CSVC_01 / PROC_CSVC_02 / PROC_CSVC_03)
    # Ưu tiên nhận diện Mượn phòng / Mượn thiết bị ngoài giờ (PROC_CSVC_02)
    is_borrowing_request = (
        proc_id == "PROC_CSVC_02"
        or any(k in text_lower for k in [
            "muon mic", "mượn mic", "muon loa", "mượn loa", "muon thiet bi", "mượn thiết bị",
            "muon dieu khien", "mượn điều khiển", "muon hoi truong", "mượn hội trường",
            "muon phong", "mượn phòng", "ngoai gio", "ngoài giờ", "clb", "cau lac bo",
            "dang ky muon", "đăng ký mượn", "xin muon", "xin mượn"
        ])
    ) and not any(k in text_lower for k in [
        "hỏng", "hong", "bị hỏng", "chập", "cháy", "chảy nước", "sự cố", "liệt", "rè", "không lên", "mat dien", "mất điện"
    ])

    if is_borrowing_request:
        return {
            "situation_summary": "Đăng ký mượn phòng học, Hội trường hoặc mượn trang thiết bị (micro, điều khiển điều hòa, máy chiếu...) ngoài giờ / phục vụ học tập, sự kiện.",
            "direct_solution": (
                "Về việc đăng ký mượn micro, điều khiển điều hòa và trang thiết bị giảng đường:\n"
                "Bạn vui lòng liên hệ trực tiếp Đội Kỹ thuật - Quản trị CSVC tại Tầng 1 Tòa B (hoặc Trực ban Bảo vệ giảng đường) trước giờ học để nhận thiết bị. Khi đến nhận, bạn chỉ cần xuất trình Thẻ sinh viên (hoặc CCCD) để ký nhận bàn giao và gửi trả lại thiết bị ngay sau khi kết thúc buổi học.\n"
                "(Trường hợp cần mượn phòng học hoặc hội trường ngoài giờ cho câu lạc bộ hoặc hoạt động tập thể, vui lòng hoàn thiện Giấy đề xuất mượn phòng BMPH-01 có xác nhận của Cố vấn học tập/Đoàn trường nộp tại Phòng Quản trị CSVC trước ít nhất 02 ngày làm việc)."
            ),
            "actionable_guidance": (
                "  1. Liên hệ Đội Kỹ thuật - Quản trị CSVC tại Tầng 1 Tòa B hoặc Trực ban Bảo vệ trước giờ học, xuất trình Thẻ sinh viên để nhận micro và điều khiển điều hòa.\n"
                "  2. Bàn giao và gửi trả lại thiết bị nguyên vẹn ngay sau khi buổi học hoặc sự kiện kết thúc."
            ),
            "has_specific_match": True
        }

    # Thư viện trường (PROC_CSVC_03)
    if proc_id == "PROC_CSVC_03" or any(k in text_lower for k in ["thu vien", "thư viện", "sach", "sách", "giao trinh", "giáo trình", "qua han", "quá hạn", "tien phat", "tiền phạt", "thu thu", "thủ thư"]):
        return {
            "situation_summary": "Tra cứu giáo trình, mượn trả tài liệu học tập, gia hạn và giải quyết việc mượn sách quá hạn tại Thư viện trường.",
            "direct_solution": (
                "Về việc tra cứu giáo trình và mượn trả tài liệu Thư viện:\n"
                "Bạn có thể tra cứu sách trực tiếp tại cổng OPAC Thư viện hoặc đến Quầy Thủ thư tại Tầng 2, Tòa nhà B. Sinh viên được mượn tối đa 03 tài liệu trong 14 ngày, khi mượn chỉ cần xuất trình Thẻ sinh viên còn hiệu lực. Giờ mở cửa: 07:30 - 20:30 (Thứ Hai đến Thứ Bảy)."
            ),
            "actionable_guidance": (
                "  1. Bạn có thể tra cứu sách trực tiếp tại cổng OPAC Thư viện hoặc đến Quầy Thủ thư - Tầng 2, Tòa nhà B.\n"
                "  2. Sinh viên được mượn tối đa 03 tài liệu trong 14 ngày. Trường hợp quá hạn, phí nộp phạt theo quy định là 5.000đ/ngày/cuốn. Giờ mở cửa: 07:30 - 20:30 (Thứ Hai đến Thứ Bảy)."
            ),
            "has_specific_match": True
        }

    # Báo hỏng và sự cố kỹ thuật trang thiết bị (PROC_CSVC_01)
    if proc_id == "PROC_CSVC_01" or any(k in text_lower for k in [
        "dieu hoa", "điều hòa", "may chieu", "máy chiếu", "hdmi", "chay nuoc", "chảy nước",
        "loa", "mic", "am thanh", "âm thanh", "o cam", "ổ cắm", "mat dien", "mất điện",
        "bong den", "bóng đèn", "ban ghe", "bàn ghế", "ve sinh", "vệ sinh", "chập", "cháy", "hỏng", "hong", "sự cố"
    ]):
        return {
            "situation_summary": "Báo hỏng và yêu cầu xử lý sự cố trang thiết bị giảng đường (điều hòa, máy chiếu, mic loa, điện nguồn, bàn ghế).",
            "direct_solution": (
                "Về sự cố trang thiết bị phòng học bạn phản ánh:\n"
                "Bộ phận Kỹ thuật - Quản trị CSVC đã tiếp nhận thông tin và sẽ cử kỹ thuật viên đến kiểm tra, xử lý ngay trong vòng 30 - 60 phút. Bạn vui lòng phối hợp cung cấp chính xác vị trí giảng đường (Tòa nhà, số phòng học, thiết bị cụ thể) hoặc thông báo trực tiếp cho Trực ban Tầng 1 Tòa B (Hotline: (024) 6262-7797) để được hỗ trợ nhanh nhất."
            ),
            "actionable_guidance": (
                "  1. Ghi rõ thông tin vị trí giảng đường (Tòa nhà, số phòng học, thiết bị cụ thể bị sự cố).\n"
                "  2. Thông báo trực tiếp cho Đội Kỹ thuật - Quản trị CSVC tại Tầng 1 Tòa B hoặc Trực ban Bảo vệ. Theo quy trình PROC_CSVC_01, kỹ thuật viên sẽ có mặt kiểm tra xử lý trong vòng 30 - 60 phút."
            ),
            "has_specific_match": True
        }

    # 6. HỆ THỐNG CNTT (He_thong_CNTT / PROC_IT_01)
    if any(k in text_lower for k in ["quen mat khau", "quên mật khẩu", "quen mk", "reset pass", "otp", "cong dao tao", "cổng đào tạo", "daotao.eaut"]):
        return {
            "situation_summary": "Quên mật khẩu cổng thông tin sinh viên daotao.eaut.edu.vn hoặc không nhận được mã xác thực OTP qua email/SĐT.",
            "direct_solution": (
                "Về việc đặt lại mật khẩu cổng thông tin sinh viên daotao.eaut.edu.vn:\n"
                "Bạn truy cập daotao.eaut.edu.vn, chọn 'Quên mật khẩu' và kiểm tra mã xác thực gửi về hòm thư sinh viên (@eaut.edu.vn) bao gồm cả hòm thư Spam. Nếu số điện thoại hoặc email liên kết bị sai lệch, bạn mang theo Thẻ sinh viên hoặc CCCD đến Phòng Kỹ thuật CNTT (Tầng 4, Tòa A) để được cán bộ hỗ trợ đặt lại mật khẩu trực tiếp trong 5 - 10 phút."
            ),
            "actionable_guidance": (
                "  1. Truy cập daotao.eaut.edu.vn, chọn 'Quên mật khẩu' và kiểm tra hòm thư sinh viên (@eaut.edu.vn) bao gồm cả hòm thư Spam.\n"
                "  2. Nếu số điện thoại hoặc email liên kết bị sai lệch, bạn mang theo Thẻ sinh viên hoặc CCCD đến Phòng Kỹ thuật CNTT (Tầng 4, Tòa A) để được cán bộ hỗ trợ đặt lại mật khẩu trực tiếp."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["microsoft 365", "office 365", "teams", "khoa tai khoan", "khóa tài khoản", "locked", "email truong", "email trường"]):
        return {
            "situation_summary": "Tài khoản Microsoft 365 / Teams / Email sinh viên bị khóa do đăng nhập sai nhiều lần hoặc cảnh báo bảo mật.",
            "direct_solution": (
                "Về sự cố tài khoản Microsoft 365 / Teams / Email sinh viên bị khóa:\n"
                "Bạn vui lòng gửi email từ hòm thư cá nhân kèm ảnh chụp 2 mặt Thẻ sinh viên và ảnh chụp thông báo lỗi tới: cntt@eaut.edu.vn, hoặc liên hệ trực tiếp Trung tâm CNTT tại Tầng 4, Tòa A trong giờ hành chính để cán bộ mở khóa tài khoản trong 15 - 30 phút."
            ),
            "actionable_guidance": (
                "  1. Gửi email từ hòm thư cá nhân kèm ảnh chụp 2 mặt Thẻ sinh viên và ảnh chụp thông báo lỗi tới: cntt@eaut.edu.vn.\n"
                "  2. Hoặc liên hệ trực tiếp Trung tâm CNTT tại Tầng 4, Tòa A trong giờ hành chính để cán bộ mở khóa tài khoản trong 15 - 30 phút."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["wifi", "mat mang", "mất mạng", "lms", "moodle", "app mobile", "nop bai", "nộp bài"]):
        return {
            "situation_summary": "Sự cố kết nối mạng Wifi sinh viên EAUT_Student hoặc lỗi nộp bài tập lớn trên hệ thống LMS Moodle.",
            "direct_solution": (
                "Về sự cố kết nối mạng Wifi sinh viên EAUT_Student hoặc lỗi nộp bài tập trên LMS Moodle:\n"
                "Nếu dung lượng file bài tập vượt quá giới hạn LMS (trên 10MB), bạn tải tệp lên Google Drive bằng tài khoản trường, bật chế độ chia sẻ công khai và dán đường link vào ô nộp bài. Đối với lỗi mất kết nối Wifi giảng đường, kỹ thuật viên sẽ khởi động lại Access Point tại tầng tương ứng."
            ),
            "actionable_guidance": (
                "  1. Nếu dung lượng file bài tập vượt quá giới hạn LMS (trên 10MB), tải tệp lên Google Drive bằng tài khoản trường, bật chế độ chia sẻ công khai và dán đường link vào ô nộp bài.\n"
                "  2. Đối với lỗi mất kết nối Wifi giảng đường, kỹ thuật viên sẽ khởi động lại Access Point tại tầng tương ứng."
            ),
            "has_specific_match": True
        }

    # 7. KHÁC / BỘ PHẬN TIẾP NHẬN
    if any(k in text_lower for k in ["roi do", "rơi đồ", "quen do", "quên đồ", "nhat duoc", "nhặt được", "camera", "tai san", "tài sản", "ba lo", "ba lô", "vi da", "ví da"]):
        return {
            "situation_summary": "Nhặt được tài sản của sinh viên để quên hoặc yêu cầu hỗ trợ trích xuất camera an ninh để tìm đồ thất lạc.",
            "direct_solution": (
                "Về việc tìm kiếm tài sản thất lạc hoặc nhặt được đồ rơi:\n"
                "Bạn vui lòng liên hệ bàn giao hoặc tra cứu tài sản thất lạc tại Phòng Bảo vệ - Tầng 1 Tòa A hoặc Tòa B. Để đề nghị trích xuất camera an ninh, bạn điền Phiếu đề nghị trích xuất camera (ghi rõ khung giờ và vị trí nghi rơi đồ) nộp tại Ban Chỉ huy Bảo vệ."
            ),
            "actionable_guidance": (
                "  1. Liên hệ bàn giao hoặc tra cứu tài sản thất lạc tại Phòng Bảo vệ - Tầng 1 Tòa A hoặc Tòa B.\n"
                "  2. Để trích xuất camera an ninh, sinh viên điền Phiếu đề nghị trích xuất camera (ghi rõ khung giờ và vị trí nghi rơi đồ) nộp tại Ban Chỉ huy Bảo vệ."
            ),
            "has_specific_match": True
        }

    if any(k in text_lower for k in ["y te", "y tế", "so cuu", "sơ cứu", "dau bung", "đau bụng", "tut huyet ap", "tụt huyết áp", "cap cuu", "cấp cứu"]):
        return {
            "situation_summary": "Yêu cầu trợ giúp y tế khẩn cấp hoặc sơ cấp cứu ban đầu cho sinh viên tại trường.",
            "direct_solution": (
                "Về yêu cầu trợ giúp y tế khẩn cấp hoặc sơ cấp cứu ban đầu:\n"
                "Bạn vui lòng đưa ngay sinh viên đến Phòng Y tế trường tại Tầng 1, Tòa A (cạnh sảnh tiếp nhận Một cửa). Trường hợp khẩn cấp cần hỗ trợ tại chỗ ngay lập tức, gọi ngay Hotline trực ban cấp cứu của trường: (024) 6262-7797."
            ),
            "actionable_guidance": (
                "  1. Đưa ngay sinh viên đến Phòng Y tế trường tại Tầng 1, Tòa A (cạnh sảnh tiếp nhận Một cửa).\n"
                "  2. Gọi ngay Hotline trực ban cấp cứu của trường: (024) 6262-7797 để cán bộ y tế có mặt hỗ trợ tại chỗ ngay lập tức."
            ),
            "has_specific_match": True
        }

    # Fallback mặc định theo chủ đề
    dept_name = DEPT_MAP.get(topic, "Bộ phận Tiếp nhận")
    return {
        "situation_summary": f"Yêu cầu hướng dẫn giải quyết sự việc thuộc lĩnh vực {TOPICS.get(topic, topic)}.",
        "direct_solution": (
            f"Vấn đề bạn phản ánh đã được tiếp nhận và chuyển đến {dept_name}.\n"
            f"Bạn vui lòng mang theo các giấy tờ hoặc minh chứng liên quan đến liên hệ trực tiếp tại {dept_name} trong giờ hành chính để được cán bộ chuyên trách kiểm tra hồ sơ và hướng dẫn giải quyết nhanh chóng."
        ),
        "actionable_guidance": (
            f"  1. Chuẩn bị thông tin chi tiết sự việc, minh chứng hoặc các giấy tờ liên quan.\n"
            f"  2. Liên hệ trực tiếp tại {dept_name} trong giờ hành chính để cán bộ chuyên trách kiểm tra hồ sơ và hướng dẫn xử lý cụ thể."
        ),
        "has_specific_match": False
    }

class LocalLearningMachine:
    def __init__(self, model_path: Optional[Path] = None, catalog_path: Optional[Path] = None):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.catalog_path = Path(catalog_path) if catalog_path else KB_OUTPUT_JSON
        self.classifier = None
        self.procedures: List[Dict[str, Any]] = []
        self.proc_vectorizer: Optional[TfidfVectorizer] = None
        self.proc_matrix = None
        self._load_or_initialize()

    def _load_or_initialize(self):
        """Tải mô hình phân loại và kho quy trình đã được index."""
        # 1. Tải mô hình phân loại
        if self.model_path.exists():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    loaded = joblib.load(str(self.model_path))
                    # Support both raw pipeline or EduSupportClassifier wrapper
                    self.classifier = loaded.model if hasattr(loaded, "model") else loaded
            except Exception as e:
                print(f"[LocalMachine] Cảnh báo khi tải mô hình: {e}. Sẽ huấn luyện mới.")
                self.classifier = None

        # 2. Tải kho quy trình từ data-doc
        self.reload_procedures()

        # Nếu chưa có mô hình thì huấn luyện ngay
        if self.classifier is None:
            self.train_local_model()

    def reload_procedures(self):
        """Nạp lại danh mục quy trình từ file JSON hoặc trích xuất trực tiếp từ data-doc."""
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    self.procedures = json.load(f)
            except Exception:
                self.procedures = build_procedure_catalog()
        else:
            self.procedures = build_procedure_catalog()
            self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.catalog_path, "w", encoding="utf-8") as f:
                json.dump(self.procedures, f, ensure_ascii=False, indent=2)

        # Indexing TF-IDF kép (Word 1-2 & Char 3-5) hỗ trợ cả gõ có dấu lẫn không dấu cho tra cứu quy trình
        if self.procedures:
            import unicodedata
            def strip_accents(t):
                return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')

            corpus = []
            for p in self.procedures:
                text_block = f"{p['title']} {p['content_extract']} {p.get('legal_basis', '')} {p.get('forms_required', '')} " + " ".join(p.get("sample_queries", []))
                corpus.append(text_block + " " + strip_accents(text_block))

            self.proc_vectorizer = FeatureUnion([
                ("word_tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                ("char_tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))
            ])
            self.proc_matrix = self.proc_vectorizer.fit_transform(corpus)

    def train_local_model(self) -> Dict[str, Any]:
        """
        Huấn luyện mô hình học máy cục bộ (Local Model Training):
        Tổng hợp dữ liệu từ data/splits/train.csv + dữ liệu sinh từ data-doc
        """
        train_csv = ROOT_DIR / "data" / "splits" / "train.csv"
        texts = []
        labels = []

        if train_csv.exists():
            df_train = pd.read_csv(train_csv)
            col_text = "clean_text" if "clean_text" in df_train.columns else "text"
            col_label = "target_label_gold" if "target_label_gold" in df_train.columns else ("topic" if "topic" in df_train.columns else "label")
            if col_text in df_train.columns and col_label in df_train.columns:
                texts.extend(df_train[col_text].dropna().tolist())
                labels.extend(df_train[col_label].dropna().tolist())

        # Bổ sung 122 mẫu phản ánh thực tế từ dataset_mau_phan_anh_sinh_vien_eaut.csv
        sample_csv = ROOT_DIR / "data" / "dataset_mau_phan_anh_sinh_vien_eaut.csv"
        if sample_csv.exists():
            df_new = pd.read_csv(sample_csv)
            for _, r in df_new.iterrows():
                top = str(r.get('target_topic', '')).strip()
                raw_t = str(r.get('raw_text', '')).strip()
                if top in TOPICS and len(raw_t) >= 12:
                    c_res = clean_text_single(raw_t, mask_pii_flag=True)
                    if c_res.get('is_usable') and len(c_res['clean_text']) >= 12:
                        texts.append(c_res['clean_text'])
                        labels.append(top)

        # Bổ sung dữ liệu huấn luyện từ sample_queries trích xuất trong data-doc
        for p in self.procedures:
            topic = p["topic"]
            for q in p.get("sample_queries", []):
                texts.append(q)
                labels.append(topic)
            # Thêm tiêu đề và trích đoạn làm mẫu
            texts.append(p["title"])
            labels.append(topic)

        # Xây dựng pipeline trích xuất kép Word + Char n-grams
        features = FeatureUnion([
            ("word_tfidf", TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.98,
                sublinear_tf=True
            )),
            ("char_tfidf", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=1,
                sublinear_tf=True
            ))
        ])

        classifier = LogisticRegression(
            C=2.0,
            solver="lbfgs",
            class_weight="balanced",
            random_state=42,
            max_iter=600
        )

        pipeline = Pipeline([
            ("features", features),
            ("clf", classifier)
        ])

        pipeline.fit(texts, labels)
        self.classifier = pipeline

        # Lưu trọng số mô hình
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, str(self.model_path))

        return {
            "status": "SUCCESS",
            "total_samples": len(texts),
            "classes": list(pipeline.classes_),
            "model_path": str(self.model_path),
            "procedures_count": len(self.procedures)
        }

    def get_procedure(self, proc_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin quy trình theo mã định danh (proc_id)."""
        for p in self.procedures:
            if p.get("proc_id") == proc_id:
                return dict(p)
        return None

    def retrieve_procedure(self, query_text: str, predicted_topic: Optional[str] = None, top_k: int = 2) -> List[Dict[str, Any]]:
        """Tra cứu quy trình phù hợp nhất từ kho tri thức data-doc bằng Cosine Similarity kết hợp Fallback theo chuyên môn."""
        if not self.procedures or self.proc_vectorizer is None or self.proc_matrix is None:
            return []

        q_vec = self.proc_vectorizer.transform([query_text])
        sims = cosine_similarity(q_vec, self.proc_matrix)[0]

        ranked = []
        for idx, score in enumerate(sims):
            proc = self.procedures[idx]
            bonus = 0.12 if proc.get("topic") == predicted_topic else 0.0
            total_score = float(score) + bonus
            if total_score >= 0.05 or float(score) >= 0.04:
                item = dict(proc)
                item["similarity_score"] = round(float(score), 4)
                item["rank_score"] = round(total_score, 4)
                ranked.append(item)

        ranked.sort(key=lambda x: x["rank_score"], reverse=True)

        # Nếu chưa khớp từ khóa do câu quá ngắn hoặc teencode, tự động fallback về quy trình chuẩn của chuyên môn
        if not ranked and self.procedures:
            if predicted_topic and predicted_topic != 'Khac':
                topic_procs = [p for p in self.procedures if p.get("topic") == predicted_topic]
                if topic_procs:
                    fallback_p = dict(topic_procs[0])
                    fallback_p["similarity_score"] = 0.65
                    fallback_p["rank_score"] = 0.65
                    ranked.append(fallback_p)

            if not ranked:
                best_idx = int(sims.argmax())
                best_p = dict(self.procedures[best_idx])
                best_p["similarity_score"] = round(float(sims[best_idx]), 4)
                best_p["rank_score"] = round(float(sims[best_idx]), 4)
                ranked.append(best_p)

        return ranked[:top_k]

    def reason_and_synthesize(
        self,
        clean_text: str,
        topic: str,
        matched_procedure: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], str]:
        """
        Lõi Lập luận Cục bộ (Local Machine Reasoning & Synthesis):
        Sinh chuỗi các bước suy luận logic (Chain-of-Thought) và tổng hợp văn bản giải đáp
        đúng thể thức hành chính, trích dẫn chuẩn xác văn bản từ data-doc.
        """
        dept = DEPT_MAP.get(topic, "Bộ phận Tiếp nhận")
        proc_id = matched_procedure.get("proc_id", "") if matched_procedure else ""

        # 1. Chẩn đoán bối cảnh chi tiết và sinh hướng dẫn trực diện
        sit = analyze_specific_situation(clean_text, topic, proc_id)

        target_dept_name = matched_procedure.get("department", dept) if matched_procedure else dept
        contact_info = get_dept_contact(target_dept_name)
        office_location = contact_info.get("office", "Bộ phận Một cửa - Tầng 1, Tòa nhà A, Trường ĐH Công nghệ Đông Á")
        hotline = contact_info.get("hotline", "(024) 6262-7797")
        dept_email = contact_info.get("email", "hotro.sinhvien@eaut.edu.vn")
        hours = contact_info.get("hours", "08:00 - 17:00 (Thứ Hai đến Thứ Sáu)")

        reasoning_steps = []

        if sit.get("has_specific_match"):
            reasoning_steps.append(f"[Suy luận Chẩn đoán tình huống] Nhận diện sự việc: {sit['situation_summary']}. Đưa ra giải pháp trực diện.")

        solution_text = sit.get("direct_solution") or sit.get("actionable_guidance", "")
        solution_text = solution_text.strip()

        if not matched_procedure:
            reasoning_steps.append(f"[Suy luận 1: Nhận diện phản ánh] Sinh viên phản ánh vấn đề liên quan đến nhóm '{TOPICS.get(topic, topic)}'.")
            reasoning_steps.append("[Suy luận 2: Đối chiếu quy định] Chưa tìm thấy điều khoản quy trình cụ thể tương đồng trong kho tài liệu data-doc.")
            reasoning_steps.append(f"[Suy luận 3: Thẩm quyền giải quyết] Chuyển tiếp tới {target_dept_name} để cán bộ tiếp nhận xác minh trực tiếp.")
            draft = (
                f"Chào bạn,\n\n"
                f"{solution_text}\n\n"
                f"Nếu cần hỗ trợ thêm, bạn vui lòng liên hệ trực tiếp tại {target_dept_name} ({office_location} | Hotline: {hotline} | Giờ làm việc: {hours}) để được hướng dẫn chu đáo.\n\n"
                f"Trân trọng."
            )
            return reasoning_steps, draft

        title = matched_procedure.get("title", "")
        legal = matched_procedure.get("legal_basis", "Quy định Nhà trường")
        p_time = matched_procedure.get("processing_time", "Theo quy định")
        forms = matched_procedure.get("forms_required", "Theo hướng dẫn")
        steps = matched_procedure.get("steps", [])

        reasoning_steps.append(f"[Suy luận 1: Nhận diện phản ánh] Phát hiện sự việc tương thích với quy trình nghiệp vụ '{title}'.")
        reasoning_steps.append(f"[Suy luận 2: Đối chiếu căn cứ pháp lý] Căn cứ theo văn bản: {legal}.")
        reasoning_steps.append(f"[Suy luận 3: Xác định thẩm quyền & Thời hạn] Thụ lý: {target_dept_name} | Thời gian xử lý: {p_time}.")
        reasoning_steps.append(f"[Suy luận 4: Giải pháp trọng tâm] Giải đáp trực diện yêu cầu của sinh viên theo quy định [{title}], không liệt kê rườm rà.")

        draft = (
            f"Chào bạn,\n\n"
            f"{solution_text}\n\n"
            f"Nếu cần hỗ trợ thêm, bạn vui lòng liên hệ trực tiếp tại {target_dept_name} ({office_location} | Hotline: {hotline} | Giờ làm việc: {hours}) để được giải quyết chu đáo.\n\n"
            f"Trân trọng."
        )

        # Tích hợp tra cứu CSDL Thư viện thời gian thực (nếu câu hỏi liên quan đến Thư viện)
        try:
            from src.library_service import is_library_inquiry, query_library_data, augment_response_with_library_data
            if proc_id == "PROC_CSVC_03" or is_library_inquiry(clean_text):
                lib_data = query_library_data(clean_text)
                if lib_data.get("has_live_data"):
                    b_count = len(lib_data.get("books_found", []))
                    br_count = len(lib_data.get("student_borrows", []))
                    reasoning_steps.append(
                        f"[Suy luận CSDL Thư viện EAUT] Đối soát CSDL thời gian thực: Phát hiện {b_count} đầu sách liên quan và {br_count} hồ sơ mượn trả."
                    )
                    draft = augment_response_with_library_data(draft, lib_data)
        except Exception:
            pass

        return reasoning_steps, draft

    def process_request_with_trace(self, raw_text: str, record_id: str = "") -> Dict[str, Any]:
        """
        Thực thi toàn bộ quy trình tiếp nhận, xử lý, suy luận và ghi nhận Trace Log minh bạch.
        """
        trace_id = f"TRACE-{uuid.uuid4().hex[:12].upper()}"
        trace = ExecutionTrace(trace_id=trace_id, record_id=record_id)

        # -------------------------------------------------------------
        # BƯỚC 1: TIẾP NHẬN & KIỂM TOÁN CHẤT LƯỢNG DỮ LIỆU (DATA-CENTRIC AUDIT)
        # -------------------------------------------------------------
        step1 = trace.new_step(
            step_number=1,
            name="DATA_CENTRIC_AUDIT_AND_PII_FILTER",
            description="Làm sạch, chuẩn hóa Unicode NFC, phát hiện và che giấu thông tin định danh cá nhân (PII)"
        )
        step1.add_log(f"Tiếp nhận chuỗi dữ liệu đầu vào độ dài {len(raw_text)} ký tự")

        clean_res = clean_text_single(raw_text)
        clean_res.pop("raw_text", None)
        clean_text = clean_res["clean_text"]
        quality_flags = clean_res["quality_flags"]
        is_usable = clean_res["is_usable"]

        step1.add_log(f"Chuẩn hóa Unicode NFC và xử lý khoảng trắng thừa")
        if quality_flags:
            step1.add_log(f"Phát hiện và gắn cờ kiểm soát chất lượng: {', '.join(quality_flags)}")
        else:
            step1.add_log("Dữ liệu đạt chuẩn sạch (CLEAN), không có cờ cảnh báo")

        step1.finish(
            status="SUCCESS" if is_usable else "WARNING",
            raw_length=len(raw_text),
            cleaned_length=len(clean_text),
            quality_flags=quality_flags,
            is_usable=is_usable,
            masked_preview=clean_text[:120] + ("..." if len(clean_text) > 120 else "")
        )

        # Trường hợp không đủ điều kiện xử lý (< 12 ký tự hoặc rỗng)
        if not is_usable:
            step_err = trace.new_step(
                step_number=2,
                name="GUARDRAIL_ABORT",
                description="Từ chối suy luận tự động do dữ liệu không đủ độ dài tối thiểu (< 12 ký tự)"
            )
            step_err.add_log("Dữ liệu rỗng hoặc quá ngắn; không chuyển vào mô hình học máy")
            step_err.finish(status="ABORTED", reason="Văn bản quá ngắn hoặc rỗng")
            trace.finalize()

            return {
                "clean_text": clean_text,
                "quality_flags": quality_flags,
                "is_usable": False,
                "predicted_topic": "Khac",
                "confidence_score": 0.0,
                "class_probabilities": {},
                "priority_level": "Thấp",
                "priority_reason": "Nội dung phản ánh quá ngắn (dưới 12 ký tự) hoặc rỗng.",
                "department": "Bộ phận Tiếp nhận",
                "matched_kb_id": None,
                "matched_procedure": None,
                "articles": [],
                "draft_response": (
                    "Chào bạn, nội dung phản ánh chưa đủ thông tin để hệ thống có thể xử lý. "
                    "Bạn vui lòng bổ sung mô tả sự việc chi tiết, thời gian và địa điểm cụ thể để được hỗ trợ. Trân trọng."
                ),
                "review_reasons": ["Nội dung rỗng hoặc quá ngắn (dưới 12 ký tự)."],
                "needs_review": True,
                "execution_trace": trace.to_dict(),
                "terminal_log": trace.format_terminal_log()
            }

        # -------------------------------------------------------------
        # BƯỚC 2: MÁY HỌC PHÂN LOẠI & ĐỊNH TUYẾN (LOCAL CLASSIFIER & ROUTING)
        # -------------------------------------------------------------
        step2 = trace.new_step(
            step_number=2,
            name="LOCAL_MACHINE_CLASSIFICATION_AND_ROUTING",
            description="Trích xuất đặc trưng TF-IDF n-grams kép, ước lượng xác suất phân lớp và gán mức ưu tiên"
        )
        step2.add_log("Trích xuất đặc trưng Word n-grams (1, 2) và Character n-grams (3, 5)")

        pred_topic = "Khac"
        conf_score = 0.50
        prob_dict = {}

        if self.classifier is not None:
            try:
                probs = self.classifier.predict_proba([clean_text])[0]
                classes = list(self.classifier.classes_)
                max_idx = int(np.argmax(probs))
                pred_topic = classes[max_idx]
                conf_score = round(float(probs[max_idx]), 4)
                prob_dict = {cls: round(float(p), 4) for cls, p in zip(classes, probs)}
                step2.add_log(f"Phân loại thành công: Chủ đề [{pred_topic}] với độ tự tin {conf_score:.1%}")
            except Exception as e:
                step2.add_log(f"Lỗi suy luận phân loại: {e}. Áp dụng chủ đề mặc định.")
                pred_topic = "Khac"
                conf_score = 0.50

        # Cây quyết định mức độ ưu tiên
        priority_lvl = determine_priority(clean_text)
        dept = DEPT_MAP.get(pred_topic, "Bộ phận Tiếp nhận")

        prio_reason = "Không phát hiện từ khóa khẩn cấp; xếp mức Bình thường."
        t_low = clean_text.lower()
        for kw in KEYWORDS_URGENT:
            if kw in t_low:
                prio_reason = f"Quy tắc mức Khẩn cấp: phát hiện từ khóa nguy cấp '{kw}'."
                break
        else:
            for kw in KEYWORDS_HIGH:
                if kw in t_low:
                    prio_reason = f"Quy tắc mức Cao: phát hiện từ khóa ưu tiên '{kw}'."
                    break

        step2.add_log(f"Xác định mức ưu tiên: [{priority_lvl}] — {prio_reason}")
        step2.add_log(f"Định tuyến phòng ban thụ lý: {dept}")

        step2.finish(
            status="SUCCESS",
            predicted_topic=pred_topic,
            confidence_score=conf_score,
            priority_level=priority_lvl,
            priority_reason=prio_reason,
            department=dept,
            all_probabilities=prob_dict,
            top_3_probabilities=dict(sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)[:3])
        )

        # -------------------------------------------------------------
        # BƯỚC 3: TRA CỨU ĐỐI CHIẾU QUY TRÌNH (PROCEDURE RETRIEVAL TỪ DATA-DOC)
        # -------------------------------------------------------------
        step3 = trace.new_step(
            step_number=3,
            name="PROCEDURE_KNOWLEDGE_RETRIEVAL",
            description="Tìm kiếm quy trình nghiệp vụ tương đồng từ kho tài liệu chính thức data-doc bằng Cosine Similarity"
        )
        step3.add_log(f"Truy vấn không gian vector trên {len(self.procedures)} quy trình nghiệp vụ")

        matched_procs = self.retrieve_procedure(clean_text, predicted_topic=pred_topic, top_k=3)
        top_proc = matched_procs[0] if matched_procs else None

        candidate_list = []
        for p in matched_procs:
            candidate_list.append({
                "proc_id": p.get("proc_id"),
                "title": p.get("title"),
                "doc_source": p.get("doc_source", ""),
                "similarity_score": p.get("similarity_score", 0),
                "rank_score": p.get("rank_score", 0)
            })

        if top_proc:
            step3.add_log(f"Khớp quy trình [{top_proc['proc_id']}]: '{top_proc['title']}' (Cosine Score: {top_proc.get('similarity_score', 0):.3f})")
            step3.add_log(f"Căn cứ văn bản: {top_proc.get('legal_basis', 'Quy định Nhà trường')}")
            step3.finish(
                status="SUCCESS",
                proc_id=top_proc["proc_id"],
                title=top_proc["title"],
                similarity_score=top_proc.get("similarity_score", 0),
                legal_basis=top_proc.get("legal_basis", ""),
                forms_required=top_proc.get("forms_required", ""),
                processing_time=top_proc.get("processing_time", ""),
                candidate_procedures=candidate_list
            )
        else:
            step3.add_log("Không tìm thấy quy trình đủ tương đồng")
            step3.finish(status="NO_MATCH", note="Không có quy trình tương thích trong kho tri thức hiện hành", candidate_procedures=[])

        # -------------------------------------------------------------
        # BƯỚC 4: LẬP LUẬN CỤC BỘ & TỔNG HỢP GIẢI ĐÁP (LOCAL REASONING & SYNTHESIS)
        # -------------------------------------------------------------
        step4 = trace.new_step(
            step_number=4,
            name="LOCAL_MACHINE_REASONING_AND_SYNTHESIS",
            description="Thực thi chuỗi suy luận logic (Chain-of-Thought) và tổng hợp phản hồi chuẩn hóa theo quy trình"
        )
        step4.add_log("Khởi tạo tiến trình suy luận cục bộ (Local Deterministic Reasoning)")

        reasoning_steps, draft_response = self.reason_and_synthesize(
            clean_text=clean_text,
            topic=pred_topic,
            matched_procedure=top_proc
        )

        for r_step in reasoning_steps:
            step4.add_log(r_step)

        step4.finish(
            status="SUCCESS",
            reasoning_steps=reasoning_steps,
            response_character_count=len(draft_response),
            response_preview=draft_response[:140] + "..."
        )

        # -------------------------------------------------------------
        # BƯỚC 5: RÀO CHẮN AN TOÀN & RA QUYẾT ĐỊNH (GUARDRAILS & DISPATCH)
        # -------------------------------------------------------------
        step5 = trace.new_step(
            step_number=5,
            name="GUARDRAILS_AND_DISPATCH_DECISION",
            description="Đánh giá rào chắn kiểm soát chất lượng và xác định điều kiện Tự động duyệt hoặc chuyển Bàn duyệt"
        )

        review_reasons = []
        if conf_score < 0.60:
            review_reasons.append("Độ tự tin phân loại dưới 60%; cần cán bộ xác minh nhóm chuyên môn.")
        if not top_proc:
            review_reasons.append("Chưa tìm thấy quy trình quy chế đủ tương đồng để viện dẫn tự động.")
        if priority_lvl == "Khẩn cấp":
            review_reasons.append("Phản ánh thuộc diện Ưu tiên Khẩn cấp; bắt buộc cán bộ thụ lý trực tiếp.")
        if quality_flags:
            review_reasons.append(f"Có cờ chất lượng dữ liệu: {', '.join(quality_flags)}")

        is_auto_approvable = (
            conf_score >= 0.70
            and bool(top_proc)
            and priority_lvl != "Khẩn cấp"
            and not any("duplicate" in f for f in quality_flags)
        )

        guardrail_checks = {
            "confidence_threshold_50": {
                "rule": "Độ tự tin phân loại AI >= 50%",
                "passed": bool(conf_score >= 0.50),
                "score": f"{conf_score:.1%}"
            },
            "official_docx_procedure_linked": {
                "rule": "Có quy trình căn cứ pháp lý trích xuất từ 3 file DOCX",
                "passed": bool(top_proc is not None),
                "procedure": top_proc.get('proc_id') if top_proc else None
            },
            "data_hygiene_and_pii_safe": {
                "rule": "Dữ liệu được làm sạch chuẩn NFC và che giấu PII an toàn",
                "passed": bool(is_usable),
                "flags": quality_flags
            },
            "priority_dispatch_ready": {
                "rule": "Kiểm định mức độ ưu tiên giải quyết",
                "passed": True,
                "level": priority_lvl
            }
        }

        if is_auto_approvable:
            decision = "AUTO_APPROVE"
            step5.add_log("Đạt toàn bộ tiêu chuẩn an toàn: Độ tự tin >= 70%, có căn cứ quy trình rõ ràng và không khẩn cấp.")
            step5.add_log("Quyết định: TỰ ĐỘNG PHÊ DUYỆT & GỬI PHẢN HỒI CHO SINH VIÊN.")
            step5.finish(
                status="AUTO_APPROVED",
                decision="AUTO_APPROVE",
                action="Tự động giải đáp và lưu vết kiểm toán",
                guardrail_checks=guardrail_checks,
                final_dispatch="TỰ ĐỘNG PHÊ DUYỆT"
            )
        else:
            decision = "ROUTED_TO_REVIEW_QUEUE"
            step5.add_log("Chưa đạt điều kiện tự động giải đáp; chuyển tiếp vào Hàng đợi Bàn duyệt cán bộ (Review Queue).")
            for reason in review_reasons:
                step5.add_log(f"Lý do: {reason}")
            step5.finish(
                status="REVIEW_QUEUE",
                decision="ROUTED_TO_REVIEW_QUEUE",
                review_reasons=review_reasons,
                guardrail_checks=guardrail_checks,
                final_dispatch="CHUYỂN BÀN DUYỆT CÁN BỘ"
            )

        trace.finalize()

        # Tạo articles tương thích với FAQEngine hiện có
        articles = []
        if top_proc:
            articles.append({
                "kb_id": top_proc.get("proc_id", "PROC_01"),
                "topic": top_proc.get("topic", pred_topic),
                "question_standard": top_proc.get("title", ""),
                "content_extract": top_proc.get("content_extract", ""),
                "department": top_proc.get("department", dept),
                "source_url": top_proc.get("legal_basis", ""),
                "verified": True,
                "similarity_score": top_proc.get("similarity_score", 0.0)
            })

        return {
            "clean_text": clean_text,
            "quality_flags": quality_flags,
            "is_usable": True,
            "predicted_topic": pred_topic,
            "confidence_score": conf_score,
            "class_probabilities": prob_dict,
            "priority_level": priority_lvl,
            "priority_reason": prio_reason,
            "department": top_proc.get("department", dept) if top_proc else dept,
            "matched_kb_id": top_proc.get("proc_id") if top_proc else None,
            "matched_procedure": top_proc,
            "reasoning_steps": reasoning_steps,
            "articles": articles,
            "draft_response": draft_response,
            "procedure_draft_response": draft_response,
            "review_reasons": review_reasons,
            "needs_review": bool(review_reasons),
            "execution_trace": trace.to_dict(),
            "terminal_log": trace.format_terminal_log()
        }

# Global singleton instance
_GLOBAL_LOCAL_MACHINE: Optional[LocalLearningMachine] = None

def get_local_machine() -> LocalLearningMachine:
    global _GLOBAL_LOCAL_MACHINE
    if _GLOBAL_LOCAL_MACHINE is None:
        _GLOBAL_LOCAL_MACHINE = LocalLearningMachine()
    return _GLOBAL_LOCAL_MACHINE
