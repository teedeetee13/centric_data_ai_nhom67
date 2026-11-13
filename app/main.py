# -*- coding: utf-8 -*-
"""
EduSupportAI - Cổng tiếp nhận & Xử lý phản ánh học vụ sinh viên
Giao diện tối giản, trực quan, chuyên nghiệp theo phong cách Sapphire Academic & Slate.
Không emoji - Loại bỏ hoàn toàn cấu phần kỹ thuật nội bộ không cần thiết.
Tích hợp phòng thủ toàn diện: bảo mật PII, chống trùng lặp, chống Spreadsheet Formula Injection.
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import re
import importlib
import pandas as pd
import streamlit as st

import src.config as config_mod
try:
    importlib.reload(config_mod)
except Exception:
    pass

import src.database as db_mod
try:
    importlib.reload(db_mod)
except Exception:
    pass

import src.app_logger as logger_mod
try:
    importlib.reload(logger_mod)
except Exception:
    pass
from src.app_logger import app_log, get_recent_logs, clear_logs, export_logs_text, render_log_terminal_html

from src.config import KB_PATH, MODEL_PATH, TOPICS, describe_flags
AUTO_APPROVE_CONFIDENCE_THRESHOLD = getattr(config_mod, "AUTO_APPROVE_CONFIDENCE_THRESHOLD", float(os.environ.get("AUTO_APPROVE_CONFIDENCE_THRESHOLD", "0.70")))
DEFAULT_TEST_EMAIL = getattr(config_mod, "DEFAULT_TEST_EMAIL", os.environ.get("DEFAULT_TEST_EMAIL", "kennysk114239@gmail.com"))

from src.database import init_db, sync_kb_from_csv, sync_procedures_kb, save_request, get_request, save_draft, log_review_action
from src.email_service import build_resolution_email, send_resolution_email
from src.service import RequestService
import app.components.workbench as _wb_mod
importlib.reload(_wb_mod)
from app.components.workbench import render_workbench

from app.components.dashboard import render_dashboard

import app.components.knowledge_center as _kc_mod
importlib.reload(_kc_mod)
from app.components.knowledge_center import render_knowledge_center

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

st.set_page_config(
    page_title='EduSupportAI - Cổng xử lý phản ánh sinh viên',
    layout='wide',
    initial_sidebar_state='collapsed'
)

# Custom CSS phong cách Sapphire Academic & Slate chuyên nghiệp
st.markdown("""
<style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1220px;
    }
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0.9rem;
        margin-bottom: 1.4rem;
    }
    .app-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.025em;
    }
    .app-subtitle {
        font-size: 0.88rem;
        color: #475569;
        margin-top: 3px;
    }
    .status-badge {
        font-size: 0.78rem;
        font-weight: 600;
        color: #047857;
        background-color: #ecfdf5;
        border: 1px solid #a7f3d0;
        padding: 4px 11px;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.8rem;
        border-bottom: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 2px 12px 2px;
        font-size: 0.94rem;
        font-weight: 500;
        color: #64748b;
        background-color: transparent !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1d4ed8 !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #1d4ed8 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #1d4ed8 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1e40af !important;
        color: #ffffff !important;
    }
    .stButton > button:not([kind="primary"]) {
        background-color: #ffffff !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 13px 16px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }
    .metric-label {
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
    }
    .badge-urgent {
        color: #991b1b;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        padding: 3px 9px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-high {
        color: #9a3412;
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
        padding: 3px 9px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-normal {
        color: #075985;
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        padding: 3px 9px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-low {
        color: #334155;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 3px 9px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] {
        display: none;
    }
    .terminal-box {
        background-color: #0b1120;
        color: #38bdf8;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.81rem;
        padding: 14px;
        border-radius: 8px;
        border: 1px solid #1e293b;
        white-space: pre-wrap;
        line-height: 1.45;
        overflow-x: auto;
        max-height: 480px;
    }
    .cot-card {
        background-color: #f8fafc;
        border-left: 4px solid #2563eb;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-bottom: 8px;
        font-size: 0.88rem;
        color: #1e293b;
    }
    .procedure-box {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 4px solid #059669;
        border-radius: 6px;
        padding: 14px;
        margin-top: 10px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

init_db()
sync_procedures_kb()

@st.cache_resource
def load_service(model_stamp, kb_stamp):
    return RequestService()

try:
    service = load_service(MODEL_PATH.stat().st_mtime_ns, KB_PATH.stat().st_mtime_ns)
    sync_kb_from_csv()
except Exception as exc:
    st.error('Không nạp được mô hình phân loại hoặc kho tài liệu quy chế.')
    st.code(str(exc))
    st.stop()

# Header ứng dụng nghiệp vụ
st.markdown("""
<div class="app-header">
    <div>
        <div class="app-title">EduSupportAI</div>
        <div class="app-subtitle">Cổng tiếp nhận, phân loại và xử lý phản ánh học vụ sinh viên</div>
    </div>
    <div class="status-badge">Hệ thống sẵn sàng</div>
</div>
""", unsafe_allow_html=True)

# Sidebar: Live Server & Web Console Logs
with st.sidebar:
    st.markdown("### 🖥️ Console Nhật Ký Web & Server")
    st.caption("Ghi nhận thời gian thực: gọi hàm gì, làm những gì, kết quả ra sao.")

    comp_options = ["TẤT CẢ", "INTAKE", "CLEANER", "AI-MODEL", "RAG-DOCX", "SYNTHESIS", "GUARDRAILS", "DATABASE", "EMAIL", "WORKBENCH"]
    selected_comp = st.selectbox("Lọc thành phần:", options=comp_options, key="sb_filter_comp")

    recent_logs = get_recent_logs(limit=40, component_filter=selected_comp)
    st.markdown(render_log_terminal_html(recent_logs, height_px=380), unsafe_allow_html=True)

    c_sb1, c_sb2 = st.columns(2)
    with c_sb1:
        if st.button("🔄 Làm mới", key="sb_btn_refresh_log", width="stretch"):
            st.rerun()
    with c_sb2:
        if st.button("🗑️ Xóa log", key="sb_btn_clear_log", width="stretch"):
            clear_logs()
            st.rerun()

    st.download_button(
        "📥 Tải log (.txt)",
        data=export_logs_text(),
        file_name="app_server_logs.txt",
        mime="text/plain",
        key="sb_btn_dl_logs",
        width="stretch"
    )

if st.session_state.get('notice'):
    st.success(st.session_state.pop('notice'))

samples = {
    'Học phí': 'Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.',
    'Lỗi đăng nhập': 'Em không đăng nhập được cổng sinh viên, số điện thoại 0912 345 678.',
    'Thiếu thông tin': 'Giúp em với',
}

tabs = st.tabs(['Tiếp nhận yêu cầu', 'Bàn duyệt cán bộ', 'Trung tâm tri thức', 'Dữ liệu và lịch sử'])

with tabs[0]:
    st.subheader('Tiếp nhận phản ánh sinh viên')

    # Chọn nhanh tình huống thực tế theo quy trình EAUT
    with st.expander('Chọn nhanh tình huống mẫu chuẩn hóa', expanded=False):
        scenarios = {
            'Hỏng điều hòa / Vệ sinh CSVC': 'Điều hòa phòng học 402 nhà B bị hỏng chảy nước lênh láng không mát, phòng học có rác chưa được dọn dẹp, đề nghị tổ CSVC kiểm tra.',
            'Mượn phòng học / Hội trường': 'Câu lạc bộ sinh viên muốn làm thủ tục nộp giấy đề xuất BMPH-01 mượn Hội trường lớn để tổ chức tọa đàm khoa học ngoài giờ.',
            'Cấp giấy xác nhận SV hoãn NVQS': 'Em cần xin Giấy xác nhận sinh viên tại Bộ phận Một cửa để nộp cho ban chỉ huy quân sự phường xin tạm hoãn nghĩa vụ quân sự năm 2026.',
            'Làm lại thẻ sinh viên bị mất': 'Em bị rơi mất thẻ sinh viên trên xe buýt, em muốn làm thủ tục cấp lại thẻ sinh viên và xin giấy xác nhận tạm thời để đi thi.',
            'Đơn đề nghị phúc khảo bài thi': 'Em làm đơn đề nghị phúc khảo bài thi kết thúc học phần môn Toán cao cấp 2, điểm hiện tại báo 4.0 em thấy không chính xác.',
            'Thủ tục xin chuyển ngành học': 'Em muốn làm thủ tục chuyển ngành đào tạo từ Quản trị kinh doanh sang CNTT theo mẫu BM_CN01, mã sinh viên 2023605678.'
        }
        sc_cols = st.columns(3)
        for idx, (label, text) in enumerate(scenarios.items()):
            with sc_cols[idx % 3]:
                if st.button(f"Mẫu: {label}", key=f"quick_sc_{idx}", width="stretch"):
                    app_log("INTAKE", "Người dùng chọn tình huống mẫu chuẩn hóa", f"Mẫu: [{label}]")
                    st.session_state["request_text"] = text
                    st.rerun()

    # 3 Nhóm chuyên môn chính thức tương ứng 3 tài liệu trong data-doc/
    three_doc_domains = {
        'Cơ sở vật chất & Giảng đường': {
            'source_doc': 'baocao-quanly-csvc-eaut.docx',
            'department': 'Phòng Quản trị - Cơ sở vật chất',
            'default_topic': 'Co_so_vat_chat',
            'issues': {
                'Vấn đề vệ sinh phòng học / Giảng đường': ('Co_so_vat_chat', 'PROC_CSVC_01'),
                'Điều hòa phòng học hỏng / chảy nước / không mát': ('Co_so_vat_chat', 'PROC_CSVC_01'),
                'Máy chiếu / Màn chiếu không hoạt động / hỏng cáp HDMI': ('Co_so_vat_chat', 'PROC_CSVC_01'),
                'Hệ thống âm thanh / Loa micro giảng đường lỗi rè': ('Co_so_vat_chat', 'PROC_CSVC_01'),
                'Bàn ghế, bóng điện chiếu sáng, ổ cắm phòng học hư hại': ('Co_so_vat_chat', 'PROC_CSVC_01'),
                'Đăng ký mượn phòng học, Hội trường và Thiết bị ngoài giờ': ('Co_so_vat_chat', 'PROC_CSVC_02'),
                'Khai thác Thư viện số và Mượn trả tài liệu Thư viện': ('Co_so_vat_chat', 'PROC_CSVC_03')
            }
        },
        'Công tác sinh viên & Chế độ chính sách': {
            'source_doc': 'bao_cao_quy_trinh_nghiep_vu_sinh_vien_eaut.docx',
            'department': 'Phòng Công tác sinh viên',
            'default_topic': 'Thu_tuc_hanh_chinh',
            'issues': {
                'Xin cấp Giấy xác nhận sinh viên (Tạm hoãn NVQS, Vay vốn, Xe buýt)': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_01'),
                'Đề nghị cấp lại thẻ sinh viên (mất, gãy hỏng chip, sai thông tin)': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_02'),
                'Thủ tục miễn giảm học phí & Hỗ trợ chi phí học tập (Nghị định 81)': ('Hoc_phi', 'PROC_CTSV_03'),
                'Thắc mắc / Khiếu nại kết quả Đánh giá điểm rèn luyện (ĐRL)': ('Diem_khao_thi', 'PROC_CTSV_04'),
                'Tiếp nhận hồ sơ sinh viên nhập học & Cam kết bổ sung giấy tờ': ('Thu_tuc_hanh_chinh', 'PROC_CTSV_05')
            }
        },
        'Quản lý Đào tạo & Khảo thí': {
            'source_doc': 'bao_cao_tong_hop_quy_trinh_dao_tao.docx',
            'department': 'Phòng Quản lý Đào tạo & Khảo thí',
            'default_topic': 'Lich_hoc_lich_thi',
            'issues': {
                'Thủ tục xin chuyển ngành đào tạo (BM_CN01)': ('Thu_tuc_hanh_chinh', 'PROC_DT_01'),
                'Thủ tục xin bảo lưu kết quả học tập & Quay lại học (BM01/BM05)': ('Thu_tuc_hanh_chinh', 'PROC_DT_02'),
                'Đăng ký học lại môn bị trượt (điểm F) & Học cải thiện điểm': ('Lich_hoc_lich_thi', 'PROC_DT_03'),
                'Đơn đề nghị phúc khảo bài thi kết thúc học phần': ('Diem_khao_thi', 'PROC_DT_04'),
                'Đơn xin hoãn thi kết thúc học phần do trùng ca thi hoặc ốm đau': ('Diem_khao_thi', 'PROC_DT_04'),
                'Thủ tục xét công nhận tốt nghiệp & Cấp bản sao văn bằng tốt nghiệp': ('Thu_tuc_hanh_chinh', 'PROC_DT_05')
            }
        }
    }

    # Chọn 1 trong 3 nhóm chuyên môn chính
    st.markdown('##### Chọn nhóm chuyên môn cần hỗ trợ:')
    domain_options = list(three_doc_domains.keys())
    selected_domain = st.radio(
        'Chuyên môn tiếp nhận:',
        options=domain_options,
        horizontal=True,
        key='intake_topic_radio',
        label_visibility='collapsed'
    )
    current_domain_info = three_doc_domains[selected_domain]
    st.caption(f"Tài liệu căn cứ: **{current_domain_info['source_doc']}** &nbsp;|&nbsp; Đơn vị chủ trì: **{current_domain_info['department']}**")

    # Form tiếp nhận chính
    with st.form('intake_form', clear_on_submit=False):
        st.markdown(f"##### Chọn vấn đề cụ thể thuộc [{selected_domain}]:")
        sub_issues_dict = current_domain_info['issues']
        sub_issues = list(sub_issues_dict.keys())
        chk_cols = st.columns(2)
        checked_issues = []
        for idx, issue in enumerate(sub_issues):
            with chk_cols[idx % 2]:
                if st.checkbox(issue, key=f"chk_{selected_domain}_{idx}"):
                    checked_issues.append(issue)

        st.markdown("##### Nội dung phản ánh chi tiết (hoặc tự điền ý kiến cá nhân):")
        user_text = st.text_area(
            'Nội dung yêu cầu',
            key='request_text',
            height=110,
            max_chars=8000,
            placeholder='Mô tả chi tiết sự việc, địa điểm (phòng học, tòa nhà), thời gian xảy ra hoặc đề xuất cụ thể của bạn...',
            label_visibility='collapsed'
        )

        st.markdown("##### Thông tin sinh viên nhận phản hồi:")
        c_mssv, c_phone, c_mail = st.columns(3)
        with c_mssv:
            in_mssv = st.text_input('Mã sinh viên (MSSV):', key='in_mssv', placeholder='Ví dụ: 2022601234')
        with c_phone:
            in_phone = st.text_input('Số điện thoại:', key='in_phone', placeholder='Ví dụ: 0987654321')
        with c_mail:
            in_email = st.text_input('Gmail / Email sinh viên:', key='in_email', placeholder='Ví dụ: sinhvien@eaut.edu.vn')

        st.caption('Thông tin sinh viên (MSSV, SĐT, Email) và nội dung phản ánh được tiếp nhận đầy đủ để phục vụ giải quyết học vụ.')
        submitted = st.form_submit_button('Gửi', type='primary', width='stretch')

    if submitted:
        # Bất cứ phản hồi nào cũng được gửi đi: tổng hợp tickbox + ý kiến chi tiết + thông tin liên hệ
        parts = []
        topic_hint = None
        proc_hint = None

        if checked_issues:
            parts.append(f"Vấn đề ghi nhận: {', '.join(checked_issues)}.")
            first_issue = checked_issues[0]
            issue_meta = current_domain_info['issues'].get(first_issue)
            if issue_meta:
                topic_hint = issue_meta[0]
                proc_hint = issue_meta[1]
        else:
            topic_hint = None
            proc_hint = None

        if user_text.strip():
            parts.append(user_text.strip())

        contacts = []
        if in_mssv.strip():
            contacts.append(f"Mã sinh viên {in_mssv.strip()}")
        if in_phone.strip():
            contacts.append(f"Số điện thoại {in_phone.strip()}")
        if in_email.strip():
            contacts.append(f"Email {in_email.strip()}")

        if contacts:
            parts.append(f"Thông tin liên hệ: {', '.join(contacts)}.")

        combined_input = "\n".join(parts) if parts else user_text

        if not combined_input.strip():
            st.warning('Bạn cần chọn vấn đề hoặc nhập nội dung phản ánh trước khi gửi.')
        else:
            fingerprint = hashlib.sha256(combined_input.strip().encode()).hexdigest()
            old_id = st.session_state.get('last_record_id')
            if fingerprint == st.session_state.get('submission_fingerprint') and old_id and get_request(old_id):
                st.info('Yêu cầu này đã được lưu trong phiên hiện tại; không tạo thêm bản ghi trùng lặp.')
            else:
                try:
                    app_log("INTAKE", "Người dùng nhấn nút [Gửi phản ánh]", f"Chuyên môn: [{selected_domain}], Vấn đề: {len(checked_issues)} mục, MSSV: {in_mssv.strip() or 'N/A'}")
                    result = service.process(combined_input, topic_hint=topic_hint, proc_hint=proc_hint, mask_pii=False)
                    rid = save_request(result, source_type='portal_student', mask_pii=False)
                    st.session_state.update(
                        analysis_result=result,
                        last_record_id=rid,
                        submission_fingerprint=fingerprint,
                        focus_review_id=rid,
                        review_id=rid
                    )

                    target_email = in_email.strip()
                    if not target_email:
                        match_mail = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', combined_input)
                        target_email = match_mail.group(1) if match_mail else DEFAULT_TEST_EMAIL

                    # Kiểm tra điều kiện tự động phê duyệt và lưu trữ:
                    is_auto_approved = (
                        result['confidence_score'] >= AUTO_APPROVE_CONFIDENCE_THRESHOLD
                        and bool(result.get('is_usable'))
                        and (bool(result.get('matched_kb_id')) or bool(result.get('matched_procedure')))
                        and result.get('priority_level') != 'Khẩn cấp'
                    )

                    # Gửi toàn bộ phản hồi giải quyết về email người nhận (kể cả khi không đủ độ tin cậy)
                    subj, body = build_resolution_email(
                        record_id=rid,
                        topic=result['predicted_topic'],
                        department=result['department'],
                        resolution_text=result['draft_response'],
                        confidence_score=result['confidence_score'],
                        is_auto_approved=is_auto_approved
                    )
                    mail_ok, mail_msg = send_resolution_email(
                        recipient_email=target_email,
                        subject=subj,
                        body_text=body,
                        record_id=rid
                    )
                    app_log("EMAIL", "Gọi send_resolution_email()", f"Mã: [{rid}], Gửi tới: [{target_email}], Kết quả: {'Thành công' if mail_ok else 'Thất bại'}")

                    if is_auto_approved:
                        log_review_action(
                            record_id=rid,
                            officer_action='approve',
                            original_topic=result['predicted_topic'],
                            final_topic=result['predicted_topic'],
                            final_response=result['draft_response'],
                            notes=f"AI tự động phê duyệt theo quy trình chuẩn hóa (Độ tự tin: {result['confidence_score']:.1%})"
                        )
                        app_log("DISPATCH", f"Tự động phê duyệt hồ sơ [{rid}]", f"Độ tự tin {result['confidence_score']:.1%} >= 70% chuẩn hóa theo {result['department']}", level="SUCCESS")
                        st.success(
                            f"TIẾP NHẬN & TỰ ĐỘNG XỬ LÝ THÀNH CÔNG: Yêu cầu {rid} đã được hệ thống AI đối soát theo đúng quy trình chuẩn của {result['department']}. "
                            f"Hướng dẫn giải quyết đã được gửi tự động về email: {target_email}!"
                        )
                    elif result.get('priority_level') == 'Khẩn cấp':
                        app_log("DISPATCH", f"Chuyển ưu tiên khẩn cấp hồ sơ [{rid}]", f"Đơn vị thụ lý: [{result['department']}]", level="WARN")
                        st.warning(
                            f"ĐÃ TIẾP NHẬN ƯU TIÊN KHẨN CẤP: Yêu cầu {rid} thuộc diện khẩn cấp. Phản hồi giải quyết đã được gửi về email: {target_email}. "
                            f"Hồ sơ đã được ưu tiên chuyển trực tiếp tới Bàn duyệt cán bộ ({result['department']}) để theo dõi và xử lý ngay."
                        )
                    else:
                        app_log("DISPATCH", f"Chuyển hồ sơ [{rid}] sang Bàn duyệt cán bộ", f"Đơn vị: [{result['department']}]")
                        st.success(
                            f"TIẾP NHẬN & GỬI PHẢN HỒI THÀNH CÔNG: Yêu cầu {rid} đã được hệ thống AI xử lý và gửi phản hồi giải quyết về email: {target_email}. "
                            f"Hồ sơ đã được đồng bộ tới Bàn duyệt cán bộ ({result['department']})."
                        )
                except ValueError as exc:
                    st.error(str(exc))

    result = st.session_state.get('analysis_result')
    rid = st.session_state.get('last_record_id')
    row = get_request(rid) if rid else None

    if result and row:
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        st.subheader('Kết quả phân tích & Phân luồng')

        # Thẻ thông số kết quả nghiệp vụ
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Đơn vị chuyên môn phụ trách</div>
                <div class="metric-val">{row['department']} <span style="font-size: 0.85rem; font-weight: normal; color: #64748b;">({TOPICS.get(row['predicted_topic'], row['predicted_topic'])})</span></div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Độ tự tin phân loại</div>
                <div class="metric-val">{row['confidence_score']:.1%}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            prio = row['priority_level']
            prio_class = {
                "Khẩn cấp": "badge-urgent",
                "Cao": "badge-high",
                "Bình thường": "badge-normal",
                "Thấp": "badge-low"
            }.get(prio, "badge-normal")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Mức độ ưu tiên</div>
                <div class="metric-val"><span class="{prio_class}">{prio}</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.caption(f"Căn cứ phân cấp ưu tiên: {row['priority_reason']}")

        st.text_area(
            'Nội dung phản ánh chi tiết',
            value=row['clean_text'],
            disabled=True,
            key='clean_' + rid,
            height=90
        )
        st.caption('Chất lượng dữ liệu: ' + describe_flags(row['quality_flags']))

        matched_proc = result.get('matched_procedure')
        if matched_proc:
            st.markdown(f"""
            <div class="procedure-box">
                <div style="font-size: 0.74rem; font-weight: 700; color: #047857; text-transform: uppercase;">Quy trình nghiệp vụ giải quyết chuẩn hóa</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-top: 3px;">[{matched_proc.get('proc_id')}] {matched_proc.get('title')}</div>
                <div style="font-size: 0.83rem; color: #475569; margin-top: 5px;">
                    <strong>Căn cứ:</strong> {matched_proc.get('legal_basis')} &nbsp;|&nbsp; 
                    <strong>Thời hạn giải quyết:</strong> {matched_proc.get('processing_time')} &nbsp;|&nbsp; 
                    <strong>Biểu mẫu:</strong> {matched_proc.get('forms_required')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        if result.get('draft_response'):
            with st.expander("Hướng Dẫn Giải Quyết Chuẩn Nghiệp Vụ (Theo Quy Trình EAUT)", expanded=True):
                st.write(result['draft_response'])

        with st.expander('Tài liệu quy chế tham chiếu (FAQ)', expanded=False):
            for article in result['articles']:
                st.markdown(f"**{article['kb_id']} — {article['question_standard']}**")
                if article['verified']:
                    st.caption(f"Nguồn chính thức đã xác minh: {article['source_url']}")
                else:
                    st.caption('Nội dung minh họa; chưa xác minh quy định chính thức của trường.')
                st.write(article['content_extract'])
                st.caption(f"Độ tương đồng ngữ nghĩa: {article['similarity_score']:.3f}")
            if not result['articles']:
                st.write('Đã áp dụng trực tiếp quy trình chuyên sâu chuẩn hóa.')

        # Hộp hiển thị minh bạch toàn bộ quá trình xử lý và suy luận nội tâm của Model
        from app.components.trace_viewer import render_trace_view
        render_trace_view(
            trace_data=result.get('execution_trace', {}),
            terminal_log=result.get('terminal_log', ''),
            title="Nhật Ký Thực Thi & Suy Luận Chi Tiết Của Máy Học (Execution & LLM Trace)",
            expanded=True,
            key_prefix=f"intake_{rid}"
        )

        with st.expander("🖥️ Console Runtime Logs (Tiến trình gọi Web / Server)", expanded=False):
            st.caption("Các sự kiện, API và lời gọi hàm vừa được thực thi tự động:")
            recent_req_logs = get_recent_logs(limit=12)
            st.markdown(render_log_terminal_html(recent_req_logs, height_px=220), unsafe_allow_html=True)

        if row['status'] == 'pending_review':
            st.subheader('Soạn thảo bản nháp hoặc chuyển sang bàn duyệt')
            draft_key = 'intake_draft_' + rid
            if draft_key not in st.session_state:
                st.session_state[draft_key] = row['draft_response']

            with st.form('draft_form_' + rid):
                draft = st.text_area('Bản nháp phản hồi có thể chỉnh sửa', key=draft_key, height=170)
                draft_saved = st.form_submit_button('Lưu bản nháp', width='stretch')

            if draft_saved:
                try:
                    save_draft(rid, draft)
                    st.session_state['notice'] = f'Đã cập nhật bản nháp cho {rid}.'
                    st.session_state.pop('response_' + rid, None)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            is_auto = 'tự động' in (str(row.get('final_response', '')) + str(row.get('reviewed_at', ''))).lower()
            if is_auto or row.get('status') == 'reviewed_approve':
                st.success(f"Yêu cầu đã được phê duyệt và lưu trữ thành công (Độ chắc chắn: {row['confidence_score']:.1%}). Hướng giải quyết đã được gửi về email.")
            else:
                st.success('Yêu cầu đã được cán bộ xử lý và phê duyệt.')
            st.write(row['final_response'])

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    # Tùy chọn gửi file đính kèm đơn lẻ & nạp hàng loạt
    with st.expander('Tùy chọn: Đính kèm tệp văn bản hoặc nạp danh sách từ Excel / CSV', expanded=False):
        t1, t2 = st.tabs(['Đính kèm tệp đơn từ / Ảnh minh chứng', 'Nạp danh sách nhiều Ticket từ tệp'])
        with t1:
            uploaded_doc = st.file_uploader(
                'Tải tệp đơn từ (.txt, .docx, .pdf) hoặc ảnh biên lai (.png, .jpg):',
                type=['txt', 'docx', 'pdf', 'png', 'jpg', 'jpeg'],
                key='ticket_doc_upload'
            )
            if uploaded_doc is not None:
                doc_name = uploaded_doc.name.lower()
                if doc_name.endswith(('.png', '.jpg', '.jpeg')):
                    st.caption(f'Đã đính kèm ảnh minh chứng: **{uploaded_doc.name}**')
                    st.image(uploaded_doc, width=200)
                elif doc_name.endswith(('.txt', '.docx', '.pdf')):
                    content = extract_text_from_upload(uploaded_doc)
                    if content and not content.startswith("Lỗi"):
                        st.caption(f'Đã trích xuất nội dung từ **{uploaded_doc.name}** ({len(content)} ký tự).')
                        if st.button('Điền nội dung tệp vào ô ý kiến cá nhân', key='btn_fill_doc'):
                            st.session_state['request_text'] = content
                            st.rerun()

        with t2:
            batch_file = st.file_uploader(
                'Chọn tệp bảng tính (.xlsx hoặc .csv):',
                type=['csv', 'xlsx'],
                key='batch_file_intake'
            )
            if batch_file is not None:
                try:
                    df_b = pd.read_csv(batch_file) if batch_file.name.lower().endswith('.csv') else pd.read_excel(batch_file)
                    if not df_b.empty:
                        potential = [c for c in df_b.columns if any(k in str(c).lower() for k in ['noi_dung', 'text', 'cau_hoi', 'phan_anh', 'content'])]
                        col_picked = potential[0] if potential else df_b.columns[0]
                        col_target = st.selectbox('Cột nội dung:', options=list(df_b.columns), index=list(df_b.columns).index(col_picked), key='batch_col_target')
                        st.dataframe(df_b[[col_target]].head(3), width='stretch')
                        if st.button(f'Nạp {min(len(df_b), 50)} Ticket vào Bàn duyệt', type='primary', key='btn_do_batch_import'):
                            added = 0
                            for _, r in df_b.head(50).iterrows():
                                val = str(r[col_target]).strip()
                                if val and val != 'nan' and val != 'None':
                                    b_res = service.process(val)
                                    save_request(b_res, source_type='file_batch')
                                    added += 1
                            st.success(f'Đã nạp thành công {added} Ticket vào Bàn duyệt cán bộ!')
                            st.rerun()
                except Exception as err:
                    st.error(f'Lỗi đọc tệp: {err}')

    # Thử nghiệm gửi email giải quyết mẫu tới kennysk114239@gmail.com
    with st.expander('Thử nghiệm gửi email giải quyết mẫu tới kennysk114239@gmail.com', expanded=False):
        st.caption('Kiểm tra trực tiếp tính năng tự động gửi email thông báo giải quyết phản ánh học vụ sinh viên.')
        c_tm1, c_tm2 = st.columns([2, 1])
        with c_tm1:
            t_email_dest = st.text_input(
                'Địa chỉ email người nhận thử nghiệm:',
                value=DEFAULT_TEST_EMAIL,
                key='intake_test_email_dest'
            )
        with c_tm2:
            t_topic_sample = st.selectbox(
                'Chủ đề giải pháp mẫu:',
                options=list(TOPICS.keys()),
                format_func=lambda k: TOPICS.get(k, k),
                key='intake_test_topic_select'
            )

        sample_solutions = {
            'Hoc_phi': 'Phòng Tài chính - Kế toán đã đối soát giao dịch nộp học phí qua ngân hàng. Hệ thống cổng đào tạo đã hoàn tất gạch nợ học kỳ cho sinh viên.',
            'Lich_hoc_lich_thi': 'Phòng Đào tạo đã ghi nhận và xử lý đơn trùng ca thi. Lịch thi bổ sung của sinh viên đã được bố trí vào phòng B302 tuần tới.',
            'Diem_khao_thi': 'Ban Khảo thí & Đảm bảo chất lượng đã hoàn tất chấm phúc khảo bài thi kết thúc học phần. Điểm số chính thức đã được cập nhật trên cổng.',
            'Thu_tuc_hanh_chinh': 'Bộ phận Một cửa đã xác nhận và cấp Giấy xác nhận sinh viên tạm hoãn nghĩa vụ quân sự. Sinh viên có thể đến bàn tiếp nhận nhận bản cứng.',
            'Co_so_vat_chat': 'Phòng Quản trị Cơ sở vật chất đã cử nhân viên kỹ thuật kiểm tra và khắc phục sự cố điều hòa phòng học trong sáng nay.',
            'He_thong_CNTT': 'Trung tâm CNTT đã cấp lại mật khẩu tài khoản cổng đào tạo sinh viên daotao.eaut.edu.vn và hướng dẫn đổi mật khẩu an toàn.',
            'Khac': 'Bộ phận Tiếp nhận chung đã ghi nhận đóng góp ý kiến nâng cao chất lượng dịch vụ của bạn và chuyển đến Ban Giám hiệu xem xét.'
        }
        chosen_sample_sol = sample_solutions.get(t_topic_sample, 'Đã ghi nhận và xử lý phản ánh.')
        st.text_area('Nội dung giải pháp gửi thử nghiệm:', value=chosen_sample_sol, height=85, disabled=True, key='intake_sample_sol_area')

        if st.button('Gửi email giải quyết mẫu tới ' + t_email_dest, type='primary', key='btn_send_sample_email_intake'):
            with st.spinner('Đang tiến hành gửi email thử nghiệm...'):
                from app.components.workbench import DEPT_MAPPING
                t_dept = DEPT_MAPPING.get(t_topic_sample, 'Bộ phận Tiếp nhận')
                subj, body = build_resolution_email(
                    record_id='DEMO_TEST_EMAIL',
                    topic=t_topic_sample,
                    department=t_dept,
                    resolution_text=chosen_sample_sol,
                    confidence_score=0.92,
                    is_auto_approved=True
                )
                ok, send_info = send_resolution_email(
                    recipient_email=t_email_dest,
                    subject=subj,
                    body_text=body,
                    record_id='DEMO_TEST_EMAIL'
                )
                if ok:
                    st.success(send_info)
                    st.markdown(f"""
                    <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-top: 8px;">
                        <div style="font-size: 0.82rem; color: #475569; font-weight: 600;">TIÊU ĐỀ: {subj}</div>
                        <div style="font-size: 0.82rem; color: #475569; margin-top: 4px;">NGƯỜI NHẬN: <strong>{t_email_dest}</strong> | PHƯƠNG THỨC: Tự động phê duyệt bởi AI</div>
                        <pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px; margin-top: 8px; font-size: 0.8rem; white-space: pre-wrap;">{body}</pre>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(send_info)

with tabs[1]:
    render_workbench()

with tabs[2]:
    render_knowledge_center()

with tabs[3]:
    render_dashboard(service=service)
