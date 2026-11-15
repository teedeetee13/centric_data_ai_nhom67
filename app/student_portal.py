# -*- coding: utf-8 -*-
"""
Module: app.student_portal
Cổng Tiếp Nhận & Hỗ Trợ Học Vụ Sinh Viên EAUT (Student Service Portal)
Dành riêng cho Sinh viên / Phụ huynh:
- Gửi phiếu phản ánh, đề xuất và thắc mắc học vụ trực tuyến
- Tra cứu tiến độ và kết quả giải quyết hồ sơ theo Mã phiếu hoặc MSSV
- Hoàn toàn tách biệt với phân hệ Bàn duyệt & Quản trị của Cán bộ Nhà trường.

Khởi chạy độc lập:
    streamlit run app/student_portal.py --server.port 8502
"""

from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import hashlib
import re
import html
import pandas as pd
import streamlit as st

from src.config import TOPICS, MODEL_PATH, KB_PATH, AUTO_APPROVE_CONFIDENCE_THRESHOLD
try:
    from src.config import DEFAULT_TEST_EMAIL
except ImportError:
    DEFAULT_TEST_EMAIL = os.environ.get("DEFAULT_TEST_EMAIL", "kennysk114239@gmail.com")

from src.database import init_db, save_request, get_request, list_requests, format_datetime_vn, log_review_action
from src.service import RequestService
from src.cleaner import parse_student_feedback
from src.email_service import (
    build_rich_resolution_email,
    build_intake_confirmation_email,
    send_resolution_email
)
from src.app_logger import app_log

def extract_text_from_upload(uploaded_file):
    """Trích xuất nội dung văn bản từ tệp đơn từ tải lên (.txt, .docx, .pdf)."""
    if uploaded_file is None:
        return ""
    uploaded_file.seek(0)
    name = uploaded_file.name.lower()
    try:
        if name.endswith('.txt'):
            return uploaded_file.read().decode('utf-8', errors='ignore').strip()
        elif name.endswith('.docx'):
            import docx
            doc = docx.Document(uploaded_file)
            return '\n'.join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        elif name.endswith('.pdf'):
            from pypdf import PdfReader
            reader = PdfReader(uploaded_file)
            texts = [page.extract_text() or '' for page in reader.pages]
            return '\n'.join(t.strip() for t in texts if t.strip())
    except Exception as e:
        return f"Lỗi trích xuất tệp: {e}"
    return ""

# Khởi tạo Streamlit Page Configuration
st.set_page_config(
    page_title="Cổng Tiếp Nhận Hỗ Trợ Sinh Viên | EAUT",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Nhúng mã CSS giao diện chuẩn EAUT Sapphire Slate
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0f172a;
    }
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Navbar Cổng sinh viên */
    .portal-navbar {
        background: linear-gradient(135deg, #1a508b 0%, #1e3a8a 100%);
        color: #ffffff;
        padding: 18px 24px;
        border-radius: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(26, 80, 139, 0.15);
    }
    .portal-brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .portal-logo {
        background: #ffffff;
        color: #1a508b;
        font-weight: 900;
        font-size: 1.15rem;
        padding: 6px 12px;
        border-radius: 8px;
        letter-spacing: 0.05em;
    }
    .portal-title {
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        line-height: 1.2;
    }
    .portal-sub {
        font-size: 0.8rem;
        color: #bfdbfe;
        margin-top: 2px;
    }
    .portal-meta {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .portal-badge-online {
        background: rgba(255, 255, 255, 0.15);
        color: #ffffff;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 9999px;
        border: 1px solid rgba(255, 255, 255, 0.25);
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #4ade80;
        border-radius: 50%;
        box-shadow: 0 0 8px #4ade80;
    }
    
    /* Khung thẻ chứa giao diện */
    .portal-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo CSDL
init_db()

@st.cache_resource
def load_service(m_time, kb_time):
    return RequestService()

try:
    service = load_service(MODEL_PATH.stat().st_mtime_ns, KB_PATH.stat().st_mtime_ns)
except Exception as e:
    st.error("Không thể kết nối mô hình học máy tiếp nhận học vụ.")
    st.code(str(e))
    st.stop()

# Header Cổng sinh viên
st.markdown("""
<div class="portal-navbar">
    <div class="portal-brand">
        <span class="portal-logo">EAUT</span>
        <div>
            <div class="portal-title">Cổng Tiếp Nhận & Hỗ Trợ Học Vụ Sinh Viên</div>
            <div class="portal-sub">Trường Đại học Công nghệ Đông Á · Tiếp nhận và giải đáp trực tuyến 24/7</div>
        </div>
    </div>
    <div class="portal-meta">
        <span class="portal-badge-online">
            <span class="pulse-dot"></span> Hệ thống sẵn sàng tiếp nhận
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

col_form, col_info = st.columns([5.5, 4.5], gap="large")

with col_form:
    st.markdown("""
    <div style="background: #cfdce8; border: 1px solid #b8cad8; border-radius: 12px; padding: 16px 20px 8px 20px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
        <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b;">Phiếu Tiếp Nhận & Hỗ Trợ Học Vụ</div>
        <div style="font-size: 0.8rem; color: #475569; margin-top: 2px;">Vui lòng điền đầy đủ thông tin để được bộ phận chức năng xử lý theo đúng quy chế</div>
    </div>
    """, unsafe_allow_html=True)

    service_topic_map = {
        'Học tập, học vụ và cảnh báo': ('Lich_hoc_lich_thi', 'PROC_DT_03'),
        'Hồ sơ và thủ tục sinh viên': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_01'),
        'Cơ sở vật chất & Giảng đường': ('Co_so_vat_chat', 'PROC_CSVC_01'),
        'Học bổng, chế độ và chính sách': ('Hoc_phi', 'PROC_CTSV_03'),
        'Rèn luyện, khen thưởng và kỷ luật': ('Diem_khao_thi', 'PROC_CTSV_04'),
        'Dịch vụ phục vụ sinh viên': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_02'),
        'Ký túc xá và cư trú': ('Co_so_vat_chat', 'PROC_CSVC_01'),
        'Hoạt động và phát triển sinh viên': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_05'),
        'Khó khăn cá nhân và hỗ trợ đặc biệt': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_01'),
        'Phản ánh, kiến nghị và khiếu nại': ('Khac', None),
        'Khác': ('Khac', None),
    }

    service_options = ['-- Chọn dịch vụ cần hỗ trợ --'] + list(service_topic_map.keys())

    with st.form('student_intake_form', clear_on_submit=False):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            in_fullname = st.text_input('Họ và tên sinh viên *', placeholder='Ví dụ: Nguyễn Văn A', key='sp_fullname')
        with c_f2:
            in_mssv = st.text_input('Mã sinh viên *', placeholder='Ví dụ: 2022601234', key='sp_mssv')

        c_f3, c_f4 = st.columns(2)
        with c_f3:
            in_phone = st.text_input('Số điện thoại liên hệ *', placeholder='Ví dụ: 0987654321', key='sp_phone')
        with c_f4:
            in_email = st.text_input('Email nhận kết quả *', placeholder='Ví dụ: sinhvien@eaut.edu.vn', key='sp_email')

        in_service = st.selectbox('Nhóm dịch vụ cần hỗ trợ *', options=service_options, key='sp_service')
        in_issue = st.text_input('Tóm tắt vấn đề *', placeholder='Ví dụ: Đề nghị phúc khảo điểm thi môn Toán, Mượn phòng học...', key='sp_issue')

        prefill_text = st.session_state.get("student_portal_req_text", "")
        user_text = st.text_area(
            'Mô tả chi tiết nội dung',
            value=prefill_text,
            key='sp_text',
            height=110,
            placeholder='Mô tả cụ thể sự việc, địa điểm (phòng học, tòa nhà), thời gian xảy ra hoặc nguyện vọng cụ thể của bạn...'
        )

        in_file = st.file_uploader('Tệp đính kèm (Biên lai / Đơn từ / Ảnh minh chứng nếu có):', type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'], key='sp_file')

        submitted = st.form_submit_button('Gửi phiếu hỗ trợ', type='primary', width='stretch')

with col_info:
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); margin-bottom: 12px;">
        <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b; margin-bottom: 12px;">
            ℹ️ Đầu Mối Tiếp Nhận & Cam Kết Phục Vụ
        </div>
        <div style="font-size: 0.86rem; color: #334155; line-height: 1.65;">
            <p style="margin-bottom: 8px;">🏛️ <strong>Bộ phận Một cửa Sinh viên:</strong> Tầng 1 Tòa nhà Hiệu bộ (Cơ sở Hà Nội & Cơ sở Bắc Ninh)</p>
            <p style="margin-bottom: 8px;">📞 <strong>Tổng đài hỗ trợ:</strong> <code>024.3768.9999</code> &nbsp;|&nbsp; ✉️ <strong>Email:</strong> <code>hotro@eaut.edu.vn</code></p>
            <p style="margin-bottom: 8px;">⏱️ <strong>Giờ làm việc:</strong> Thứ 2 - Thứ 6 (08:00 - 17:00), Thứ 7 (08:00 - 12:00)</p>
            <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 10px 14px; border-radius: 6px; margin: 12px 0;">
                <strong style="color: #1e40af;">⚡ Cam kết thời hạn xử lý (SLA):</strong>
                <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 0.82rem; color: #1e3a8a;">
                    <li>Tiếp nhận & đối soát quy chế: <strong>Tức thì</strong></li>
                    <li>Giải quyết thủ tục hành chính, điểm số: <strong>24 - 48 giờ làm việc</strong></li>
                    <li>Trường hợp khẩn cấp (sự cố CSVC, y tế): <strong>Ưu tiên xử lý trong 04 - 12 giờ</strong></li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📋 Tra cứu phạm vi 10 nhóm dịch vụ hỗ trợ sinh viên", expanded=False):
        st.markdown("""
        <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
            <thead>
                <tr style="background: #1a508b; color: #ffffff; text-align: left;">
                    <th style="padding: 8px 10px; width: 40%;">DỊCH VỤ</th>
                    <th style="padding: 8px 10px; width: 60%;">PHẠM VI NỘI DUNG</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Học tập & Học vụ</td><td style="padding: 6px 10px;">Lịch học, lịch thi, học phần, kết quả học tập</td></tr>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Hồ sơ & Thủ tục SV</td><td style="padding: 6px 10px;">Giấy xác nhận sinh viên, thủ tục hành chính</td></tr>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Cơ sở vật chất</td><td style="padding: 6px 10px;">Báo hỏng thiết bị phòng học, mượn giảng đường</td></tr>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Học bổng & Chính sách</td><td style="padding: 6px 10px;">Học phí, miễn giảm, chế độ chính sách</td></tr>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Rèn luyện & Khen thưởng</td><td style="padding: 6px 10px;">Điểm rèn luyện, đánh giá thi đua, khen thưởng</td></tr>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Dịch vụ sinh viên</td><td style="padding: 6px 10px;">Thẻ sinh viên, bảo hiểm y tế, đồng phục</td></tr>
                <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Ký túc xá & Cư trú</td><td style="padding: 6px 10px;">Đăng ký nội trú, đời sống ký túc xá</td></tr>
            </tbody>
        </table>
        """, unsafe_allow_html=True)

# XỬ LÝ KHI NHẤN NÚT GỬI PHIẾU
if submitted:
    parts = []
    topic_hint = None
    proc_hint = None

    if in_service in service_topic_map:
        topic_hint, proc_hint = service_topic_map[in_service]

    if in_issue.strip():
        parts.append(f"Vấn đề ghi nhận: {in_issue.strip()}.")
    if user_text.strip():
        parts.append(user_text.strip())

    contacts = []
    if in_fullname.strip():
        contacts.append(f"Họ tên {in_fullname.strip()}")
    if in_mssv.strip():
        contacts.append(f"Mã sinh viên {in_mssv.strip()}")
    if in_phone.strip():
        contacts.append(f"Số điện thoại {in_phone.strip()}")
    if in_email.strip():
        contacts.append(f"Email {in_email.strip()}")

    if contacts:
        parts.append(f"Thông tin liên hệ: {', '.join(contacts)}.")

    if in_file is not None:
        extracted_f = extract_text_from_upload(in_file)
        if extracted_f and not extracted_f.startswith("Lỗi"):
            parts.append(f"Tệp đính kèm ({in_file.name}): {extracted_f}")

    combined_input = "\n".join(parts) if parts else user_text

    if not combined_input.strip():
        st.warning("Vui lòng điền nội dung yêu cầu hoặc chọn vấn đề trước khi gửi.")
    else:
        fingerprint = hashlib.sha256(combined_input.strip().encode()).hexdigest()
        try:
            app_log("STUDENT_PORTAL", "Sinh viên gửi phiếu tiếp nhận", f"Dịch vụ: [{in_service}], Vấn đề: {in_issue.strip()}, MSSV: {in_mssv.strip()}")
            result = service.process(combined_input, topic_hint=topic_hint, proc_hint=proc_hint, mask_pii=False)
            rid = save_request(result, source_type='portal_student', mask_pii=False)

            st.session_state["sp_last_rid"] = rid
            st.session_state["student_portal_req_text"] = ""

            target_email = in_email.strip()
            if not target_email:
                target_email = DEFAULT_TEST_EMAIL

            thresh = float(AUTO_APPROVE_CONFIDENCE_THRESHOLD)
            is_auto_approved = (
                result['confidence_score'] >= thresh
                and bool(result.get('is_usable'))
                and (bool(result.get('matched_kb_id')) or bool(result.get('matched_procedure')))
                and result.get('priority_level') != 'Khẩn cấp'
            )

            if is_auto_approved:
                best_response = result.get('procedure_draft_response') or result.get('draft_response', '')
                subj, body_plain, body_html = build_rich_resolution_email(
                    record_id=rid,
                    topic=result['predicted_topic'],
                    department=result['department'],
                    resolution_text=best_response,
                    confidence_score=result['confidence_score'],
                    is_auto_approved=True,
                    student_name=in_fullname.strip() or "Sinh viên",
                    student_id=in_mssv.strip() or None,
                    procedure_info=result.get('matched_procedure'),
                    library_info=result.get('library_lookup')
                )
                send_resolution_email(
                    recipient_email=target_email,
                    subject=subj,
                    body_text=body_plain,
                    body_html=body_html,
                    record_id=rid
                )
                log_review_action(
                    record_id=rid,
                    officer_action='approve',
                    original_topic=result['predicted_topic'],
                    final_topic=result['predicted_topic'],
                    final_response=best_response,
                    notes="AI tự động duyệt và gửi email giải quyết ngay khi đủ độ tin cậy"
                )
                st.success(f"🎉 **Tiếp nhận & Giải quyết tự động thành công!** Văn bản giải quyết đã được gửi tới email **{target_email}**.")
            else:
                conf_subj, conf_plain, conf_html = build_intake_confirmation_email(
                    record_id=rid,
                    topic=result['predicted_topic'],
                    department=result['department'],
                    clean_text=combined_input,
                    priority_level=result.get('priority_level', 'Bình thường'),
                    student_id=in_mssv.strip() or None,
                    estimated_sla="Trong 24 - 48 giờ làm việc theo quy định"
                )
                send_resolution_email(
                    recipient_email=target_email,
                    subject=conf_subj,
                    body_text=conf_plain,
                    body_html=conf_html,
                    record_id=rid
                )
                st.success(f"✅ **Đã tiếp nhận hồ sơ thành công!** Mã hồ sơ của bạn là **{rid}**. Email xác nhận đã gửi tới **{target_email}**.")

            st.rerun()
        except Exception as exc:
            st.error(f"Lỗi khi gửi phiếu: {exc}")

# HIỂN THỊ PHIẾU BIÊN NHẬN NGAY SAU KHI GỬI THÀNH CÔNG
last_sp_rid = st.session_state.get("sp_last_rid")
if last_sp_rid:
    req_item = get_request(last_sp_rid)
    if req_item:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        prio = req_item.get('priority_level', 'Bình thường')
        is_done = (req_item.get('status') == 'reviewed_approve')
        status_text = "🟢 ĐÃ ĐƯỢC PHÊ DUYỆT & GỬI EMAIL" if is_done else ("🔴 TIẾP NHẬN ƯU TIÊN KHẨN CẤP" if prio == "Khẩn cấp" else "🔵 ĐANG CHỜ PHÒNG BAN THẨM ĐỊNH")
        status_color = "#15803d" if is_done else ("#dc2626" if prio == "Khẩn cấp" else "#2563eb")
        sla_text = "Ưu tiên trong 04 - 12 giờ làm việc" if prio == "Khẩn cấp" else "Trong 24 - 48 giờ làm việc"

        receipt_card = (
            f'<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-top: 5px solid {status_color}; border-radius: 12px; padding: 18px 22px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
            f'<div style="display: flex; align-items: center; gap: 8px;">'
            f'<span style="background: #eff6ff; color: {status_color}; font-weight: 800; font-size: 0.76rem; padding: 3px 10px; border-radius: 6px;">{status_text}</span>'
            f'<span style="font-size: 1.1rem; font-weight: 800; color: #1a508b; font-family: monospace;">{last_sp_rid}</span>'
            f'</div>'
            f'<span style="font-size: 0.8rem; color: #64748b;">Thời điểm gửi: {format_datetime_vn(req_item.get("processed_at"), fmt="%d/%m/%Y %H:%M")}</span>'
            f'</div>'
            f'<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-top: 10px;">'
            f'<div><div style="font-size: 0.72rem; color: #64748b; font-weight: 600;">ĐƠN VỊ PHỤ TRÁCH</div><div style="font-weight: 700; color: #1a508b; font-size: 0.88rem; margin-top: 2px;">{req_item["department"]}</div></div>'
            f'<div><div style="font-size: 0.72rem; color: #64748b; font-weight: 600;">CHUYÊN MÔN HỌC VỤ</div><div style="font-weight: 700; color: #0f172a; font-size: 0.88rem; margin-top: 2px;">{TOPICS.get(req_item["predicted_topic"], req_item["predicted_topic"])}</div></div>'
            f'<div><div style="font-size: 0.72rem; color: #64748b; font-weight: 600;">CAM KẾT THỜI HẠN (SLA)</div><div style="font-weight: 700; color: #15803d; font-size: 0.88rem; margin-top: 2px;">⏱️ {sla_text}</div></div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(receipt_card, unsafe_allow_html=True)

        sol_text = req_item.get('final_response') or req_item.get('draft_response')
        if sol_text:
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.95rem; font-weight: 700; color: #1a508b; margin-bottom: 6px;">
                    📋 Hướng dẫn giải quyết & Trình tự thực hiện
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; border-radius: 8px; padding: 12px 16px; font-size: 0.9rem; color: #1e293b; line-height: 1.6; white-space: pre-wrap;">
{sol_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

