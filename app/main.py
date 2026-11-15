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
os.chdir(ROOT)
import re
import importlib
import pandas as pd
import streamlit as st

import src.config as config_mod
try:
    importlib.reload(config_mod)
except Exception:
    pass

import src.cleaner as cleaner_mod
try:
    importlib.reload(cleaner_mod)
except Exception:
    pass

try:
    from src.cleaner import parse_student_feedback
except ImportError:
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

from src.database import init_db, sync_kb_from_csv, sync_procedures_kb, save_request, get_request, save_draft, log_review_action, format_datetime_vn
import src.email_service as email_mod
try:
    importlib.reload(email_mod)
except Exception:
    pass

try:
    from src.email_service import (
        build_resolution_email,
        build_rich_resolution_email,
        build_rejection_email,
        build_intake_confirmation_email,
        send_resolution_email,
        get_smtp_config,
        save_smtp_credentials,
        test_smtp_connection
    )
except ImportError:
    importlib.reload(email_mod)
    from src.email_service import (
        build_resolution_email,
        build_rich_resolution_email,
        build_rejection_email,
        build_intake_confirmation_email,
        send_resolution_email,
        get_smtp_config,
        save_smtp_credentials,
        test_smtp_connection
    )
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

# Custom CSS phong cách Sapphire Academic & Slate chuyên nghiệp chuẩn SaaS Đích Thực
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        --font-mono: 'JetBrains Mono', Courier, monospace;
        --brand-navy: #1e3a8a;
        --brand-blue: #2563eb;
        --brand-sky: #0284c7;
        --bg-canvas: #f8fafc;
        --bg-card: #ffffff;
        --border-subtle: #e2e8f0;
        --border-medium: #cbd5e1;
        --text-headline: #0f172a;
        --text-body: #334155;
        --text-muted: #64748b;
    }

    /* Ẩn hoàn toàn header mặc định, footer và nút Deploy của Streamlit */
    #MainMenu { visibility: hidden !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    /* Nền tổng thể và font chữ chuẩn SaaS */
    .stApp {
        background-color: var(--bg-canvas) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-body) !important;
    }

    /* Tối ưu hóa padding toàn trang */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1440px !important;
    }

    /* Tùy chỉnh thanh cuộn thanh mảnh */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* App Header & Navigation Bar chuẩn SaaS Đích Thực */
    /* Nút icon bánh răng mở Quản trị ở góc trên bên phải */
    .stButton > button[key="btn_toggle_admin"],
    .stButton > button[key="btn_toggle_workbench"],
    button[key="btn_toggle_admin"],
    button[key="btn_toggle_workbench"] {
        font-size: 1.4rem !important;
        height: 52px !important;
        min-height: 52px !important;
        border-radius: 12px !important;
        border: 1.5px solid #cbd5e1 !important;
        background: #ffffff !important;
        color: #1e3a8a !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    button[key="btn_toggle_admin"]:hover {
        background: #eff6ff !important;
        border-color: #2563eb !important;
        color: #2563eb !important;
        transform: rotate(45deg);
    }
    button[key="btn_toggle_workbench"]:hover {
        background: #eff6ff !important;
        border-color: #2563eb !important;
        color: #2563eb !important;
    }

    .app-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 24px;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .brand-container {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .brand-pill {
        background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%);
        color: #ffffff;
        font-size: 0.8rem;
        font-weight: 800;
        padding: 5px 10px;
        border-radius: 8px;
        letter-spacing: 0.06em;
        box-shadow: 0 2px 4px rgba(30, 58, 138, 0.25);
    }
    .brand-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.025em;
    }
    .brand-sub {
        font-size: 0.82rem;
        color: #64748b;
        border-left: 1px solid #cbd5e1;
        padding-left: 12px;
        font-weight: 500;
    }
    .nav-meta {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .nav-badge-term {
        display: inline-flex;
        align-items: center;
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
    }
    .nav-badge-live {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
    }
    .pulse-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }
    .user-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #eff6ff;
        color: #1e40af;
        border: 1px solid #dbeafe;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 600;
    }

    /* Thanh Tabs chuẩn SaaS (Navigation Pills Bar) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 6px 8px;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-size: 0.88rem;
        font-weight: 600;
        color: #64748b;
        background-color: transparent !important;
        border-radius: 6px !important;
        border: none !important;
        transition: all 0.15s ease-in-out;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0f172a !important;
        background-color: #f8fafc !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: #1e3a8a !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 4px rgba(30, 58, 138, 0.2) !important;
    }

    /* Khung nhập liệu Form Controls */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        transition: all 0.15s ease !important;
    }
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within, div[data-baseweb="textarea"]:focus-within {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }

    /* Nút bấm Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.2rem !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%) !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px);
    }
    .stButton > button:not([kind="primary"]) {
        background-color: #ffffff !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 0.75rem !important;
    }

    /* Metric Cards */
    .metric-card {
        background: #ffffff;
        border: 1px solid #b8cad8;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .metric-val {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1a508b;
        margin-top: 4px;
    }

    /* Terminal Console Box */
    .terminal-box {
        background-color: #0b1120;
        color: #38bdf8;
        font-family: var(--font-mono);
        font-size: 0.81rem;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #1e293b;
        white-space: pre-wrap;
        line-height: 1.5;
        overflow-x: auto;
        max-height: 480px;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
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

is_admin_mode = st.session_state.get("show_admin_view", False)

# Header ứng dụng nghiệp vụ chuẩn SaaS Đích Thực kèm Icon Bánh Răng ở góc trên bên phải
col_nav, col_gear = st.columns([0.94, 0.06], vertical_alignment="center")

with col_nav:
    st.markdown("""
<div class="app-navbar">
    <div class="brand-container">
        <span class="brand-pill">EAUT</span>
        <div>
            <div class="brand-title">EduSupport AI</div>
        </div>
        <span class="brand-sub">Hệ thống Tiếp nhận, Điều phối & Phê duyệt Học vụ Sinh viên</span>
    </div>
</div>
""", unsafe_allow_html=True)

with col_gear:
    if not is_admin_mode:
        if st.button("⚙️", key="btn_toggle_admin", help="Mở Trung tâm Quản trị, Quy chế & Cài đặt hệ thống", width="stretch"):
            st.session_state["show_admin_view"] = True
            st.rerun()
    else:
        if st.button("📥", key="btn_toggle_workbench", help="Quay lại Bàn duyệt hồ sơ cán bộ", width="stretch"):
            st.session_state["show_admin_view"] = False
            st.rerun()

if st.session_state.get('notice'):
    st.success(st.session_state.pop('notice'))

samples = {
    'Học phí': 'Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.',
    'Lỗi đăng nhập': 'Em không đăng nhập được cổng sinh viên, số điện thoại 0912 345 678.',
    'Thiếu thông tin': 'Giúp em với',
}

if not is_admin_mode:
    # -------------------------------------------------------------
    # MÀN HÌNH CHÍNH: BÀN DUYỆT TINH GỌN (CHỈ HIỂN THỊ NỘI DUNG EMAIL ĐÃ GỬI)
    # -------------------------------------------------------------
    render_workbench(show_trace=False, show_review_form=False)
else:
    # -------------------------------------------------------------
    # TRANG QUẢN TRỊ & TIỆN ÍCH: ĐẦY ĐỦ CÁC PHẦN (KÈM BÀN DUYỆT CÓ VẾT THỰC THI)
    # -------------------------------------------------------------
    c_back, c_title = st.columns([0.24, 0.76], vertical_alignment="center")
    with c_back:
        if st.button("⬅️ Quay lại Bàn duyệt hồ sơ", key="btn_back_main_top", type="primary", width="stretch"):
            st.session_state["show_admin_view"] = False
            st.rerun()
    with c_title:
        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 18px; margin-bottom: 8px;">
            <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b;">⚙️ Trung Tâm Quản Trị, Quy Chế & Cài Đặt Hệ Thống</div>
            <div style="font-size: 0.8rem; color: #64748b;">Quản lý kho tri thức quy chế, xem báo cáo phân tích học vụ, kiểm thử tiếp nhận và cấu hình máy chủ SMTP / CSDL</div>
        </div>
        """, unsafe_allow_html=True)

    admin_tabs = st.tabs([
        '📥 Bàn duyệt hồ sơ',
        '📝 Tiếp nhận phản ánh',
        '📚 Quy chế & Tri thức',
        '📊 Thống kê & Báo cáo',
        '⚙️ Cài đặt & Hệ thống'
    ])

    with admin_tabs[0]:
        render_workbench(show_trace=True, show_review_form=True)

    with admin_tabs[1]:
        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size: 1.15rem; font-weight: 800; color: #1a508b; letter-spacing: -0.01em;">📝 Cổng Tiếp Nhận & Hỗ Trợ Học Vụ Sinh Viên EAUT</div>
            <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">Điền thông tin và phản ánh của bạn để được hỗ trợ giải quyết nhanh chóng theo đúng quy trình quy chế Nhà trường</div>
        </div>
        """, unsafe_allow_html=True)

        # Bố cục 2 cột chuẩn Cổng Hỗ trợ Sinh viên mis.eaut.edu.vn/ho-tro
        col_form, col_guide = st.columns([5.5, 4.5], gap="large")

        with col_form:
            st.markdown("""
            <div style="background: #cfdce8; border: 1px solid #b8cad8; border-radius: 12px; padding: 16px 20px 8px 20px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b; letter-spacing: -0.01em;">Phiếu Tiếp Nhận & Hỗ Trợ Học Vụ</div>
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

            with st.form('intake_form', clear_on_submit=False):
                f_c1, f_c2 = st.columns(2)
                with f_c1:
                    in_fullname = st.text_input('Họ và tên sinh viên *', placeholder='Ví dụ: Nguyễn Văn A', key='in_fullname')
                with f_c2:
                    in_mssv = st.text_input('Mã sinh viên *', placeholder='Ví dụ: 2022601234', key='in_mssv')

                f_c3, f_c4 = st.columns(2)
                with f_c3:
                    in_phone = st.text_input('Số điện thoại liên hệ *', placeholder='Ví dụ: 0987654321', key='in_phone')
                with f_c4:
                    in_email = st.text_input('Email nhận kết quả *', placeholder='Ví dụ: sinhvien@eaut.edu.vn', key='in_email')

                in_service = st.selectbox('Nhóm dịch vụ cần hỗ trợ *', options=service_options, key='in_service')
                in_issue = st.text_input('Tóm tắt vấn đề *', placeholder='Ví dụ: Đề nghị phúc khảo điểm thi môn Toán, Mượn phòng học...', key='in_issue')

                user_text = st.text_area(
                    'Mô tả chi tiết nội dung',
                    key='request_text',
                    height=110,
                    max_chars=8000,
                    placeholder='Mô tả cụ thể sự việc, địa điểm (phòng học, tòa nhà), thời gian xảy ra hoặc nguyện vọng cụ thể của bạn...'
                )

                in_file = st.file_uploader('Tệp đính kèm (Biên lai / Đơn từ / Ảnh minh chứng nếu có):', type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'], key='in_file')

                submitted = st.form_submit_button('Gửi phiếu hỗ trợ', type='primary', width='stretch')

        with col_guide:
            st.markdown("""
            <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); margin-bottom: 12px;">
                <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b; margin-bottom: 10px;">
                    ℹ️ Đầu Mối Tiếp Nhận & Cam Kết Phục Vụ
                </div>
                <div style="font-size: 0.85rem; color: #334155; line-height: 1.6;">
                    <p style="margin-bottom: 6px;">🏛️ <strong>Bộ phận Một cửa Sinh viên:</strong> Tầng 1 Tòa nhà Hiệu bộ (Cơ sở Hà Nội & Cơ sở Bắc Ninh)</p>
                    <p style="margin-bottom: 6px;">📞 <strong>Tổng đài hỗ trợ:</strong> <code>024.3768.9999</code> &nbsp;|&nbsp; ✉️ <strong>Email:</strong> <code>hotro@eaut.edu.vn</code></p>
                    <p style="margin-bottom: 6px;">⏱️ <strong>Giờ làm việc:</strong> Thứ 2 - Thứ 6 (08:00 - 17:00), Thứ 7 (08:00 - 12:00)</p>
                    <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 10px 14px; border-radius: 6px; margin: 10px 0;">
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

            with st.expander("📋 Xem phạm vi 10 nhóm dịch vụ sinh viên", expanded=False):
                st.markdown("""
                <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                    <thead>
                        <tr style="background: #1a508b; color: #ffffff; text-align: left;">
                            <th style="padding: 8px 10px; width: 40%;">DỊCH VỤ</th>
                            <th style="padding: 8px 10px; width: 60%;">PHẠM VI NỘI DUNG</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Học tập, học vụ và cảnh báo</td><td style="padding: 6px 10px;">Lịch học, lịch thi, học phần, kết quả học tập</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Hồ sơ và thủ tục sinh viên</td><td style="padding: 6px 10px;">Xác nhận sinh viên, giấy tờ hành chính</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Cơ sở vật chất & Giảng đường</td><td style="padding: 6px 10px;">Báo hỏng thiết bị, mượn phòng học, hội trường</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Học bổng & Chế độ chính sách</td><td style="padding: 6px 10px;">Học phí, miễn giảm, học bổng khuyến khích</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Rèn luyện & Khen thưởng</td><td style="padding: 6px 10px;">Điểm rèn luyện, khen thưởng, kỷ luật</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Dịch vụ phục vụ sinh viên</td><td style="padding: 6px 10px;">Thẻ sinh viên, bảo hiểm y tế, đồng phục</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Ký túc xá & Cư trú</td><td style="padding: 6px 10px;">Đăng ký nội trú, sinh hoạt KTX</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #f8fafc;"><td style="padding: 6px 10px; font-weight: 600;">Khó khăn & Hỗ trợ đặc biệt</td><td style="padding: 6px 10px;">Tư vấn sức khỏe, tâm lý, hoàn cảnh</td></tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #ffffff;"><td style="padding: 6px 10px; font-weight: 600;">Phản ánh, kiến nghị & khiếu nại</td><td style="padding: 6px 10px;">Tiếp nhận và giải quyết khiếu nại học vụ</td></tr>
                    </tbody>
                </table>
                """, unsafe_allow_html=True)



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
                st.warning('Bạn cần chọn vấn đề hoặc nhập nội dung phản ánh trước khi gửi.')
            else:
                fingerprint = hashlib.sha256(combined_input.strip().encode()).hexdigest()
                old_id = st.session_state.get('last_record_id')
                if fingerprint == st.session_state.get('submission_fingerprint') and old_id and get_request(old_id):
                    st.info('Yêu cầu này đã được lưu trong phiên hiện tại; không tạo thêm bản ghi trùng lặp.')
                else:
                    try:
                        app_log("INTAKE", "Người dùng nhấn nút [Gửi phản ánh]", f"Chuyên môn: [{in_service}], Vấn đề: {in_issue.strip() or 'N/A'}, MSSV: {in_mssv.strip() or 'N/A'}")
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

                        # Kiểm tra điều kiện tự động phê duyệt và gửi thẳng email:
                        thresh = float(st.session_state.get('auto_conf_thresh', AUTO_APPROVE_CONFIDENCE_THRESHOLD))
                        is_auto_approved = (
                            result['confidence_score'] >= thresh
                            and bool(result.get('is_usable'))
                            and (bool(result.get('matched_kb_id')) or bool(result.get('matched_procedure')))
                            and result.get('priority_level') != 'Khẩn cấp'
                        )

                        if is_auto_approved:
                            # ĐỦ ĐỘ TIN CẬY: Model gửi thẳng email giải quyết ngay cho người nhận (định dạng HTML + Plain Text)
                            best_response = result.get('procedure_draft_response') or result.get('draft_response', '')
                            subj, body_plain, body_html = build_rich_resolution_email(
                                record_id=rid,
                                topic=result['predicted_topic'],
                                department=result['department'],
                                resolution_text=best_response,
                                confidence_score=result['confidence_score'],
                                is_auto_approved=True,
                                student_id=in_mssv.strip() or None,
                                procedure_info=result.get('matched_procedure'),
                                library_info=result.get('library_lookup')
                            )
                            mail_ok, mail_msg = send_resolution_email(
                                recipient_email=target_email,
                                subject=subj,
                                body_text=body_plain,
                                body_html=body_html,
                                record_id=rid
                            )
                            st.session_state['last_sent_email'] = {
                                "subject": subj,
                                "body_plain": body_plain,
                                "body_html": body_html,
                                "recipient": target_email,
                                "status": f"Tự động gửi thẳng văn bản giải quyết (Độ tin cậy: {result['confidence_score']:.1%} >= {thresh:.0%})"
                            }
                            app_log("EMAIL", "Model gửi thẳng email giải quyết tự động", f"Mã: [{rid}], Gửi tới: [{target_email}], Độ tin cậy: {result['confidence_score']:.1%} >= {thresh:.0%}, Kết quả: {'Thành công' if mail_ok else 'Thất bại'}")

                            log_review_action(
                                record_id=rid,
                                officer_action='approve',
                                original_topic=result['predicted_topic'],
                                final_topic=result['predicted_topic'],
                                final_response=best_response,
                                notes=f"Model AI tự động gửi thẳng email khi đủ độ tin cậy ({result['confidence_score']:.1%} >= {thresh:.0%})"
                            )
                            app_log("DISPATCH", f"Tự động phê duyệt hồ sơ [{rid}]", f"Độ tin cậy {result['confidence_score']:.1%} >= {thresh:.0%} chuẩn hóa theo {result['department']}", level="SUCCESS")
                            st.success(
                                f"🎉 **Tiếp nhận & Giải quyết tự động thành công!** Văn bản giải quyết đã được gửi tới email **{target_email}**."
                            )
                        elif result.get('priority_level') == 'Khẩn cấp':
                            # KHẨN CẤP: Gửi email biên nhận tiếp nhận ưu tiên và chuyển ngay Bàn duyệt cán bộ
                            conf_subj, conf_plain, conf_html = build_intake_confirmation_email(
                                record_id=rid,
                                topic=result['predicted_topic'],
                                department=result['department'],
                                clean_text=combined_input,
                                priority_level='Khẩn cấp',
                                student_id=in_mssv.strip() or None,
                                estimated_sla="Xử lý ưu tiên trong 04 - 12 giờ làm việc"
                            )
                            send_resolution_email(
                                recipient_email=target_email,
                                subject=conf_subj,
                                body_text=conf_plain,
                                body_html=conf_html,
                                record_id=rid
                            )
                            st.session_state['last_sent_email'] = {
                                "subject": conf_subj,
                                "body_plain": conf_plain,
                                "body_html": conf_html,
                                "recipient": target_email,
                                "status": "Đã gửi email biên nhận tiếp nhận hồ sơ ưu tiên khẩn cấp"
                            }
                            app_log("DISPATCH", f"Chuyển ưu tiên khẩn cấp hồ sơ [{rid}] sang Bàn duyệt cán bộ", f"Đơn vị: [{result['department']}]", level="WARN")
                            st.warning(
                                f"🚨 **Đã tiếp nhận ưu tiên khẩn cấp!** Mã hồ sơ **{rid}**. Email xác nhận đã gửi tới **{target_email}** và hồ sơ đã chuyển thẳng tới bàn trực ban để xử lý ngay."
                            )
                        else:
                            # CHƯA ĐỦ ĐỘ TIN CẬY: Gửi email biên nhận tiếp nhận hồ sơ, chuyển sang Bàn duyệt cán bộ
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
                            st.session_state['last_sent_email'] = {
                                "subject": conf_subj,
                                "body_plain": conf_plain,
                                "body_html": conf_html,
                                "recipient": target_email,
                                "status": f"Đã gửi email biên nhận tiếp nhận hồ sơ (Độ tin cậy: {result['confidence_score']:.1%} < {thresh:.0%})"
                            }
                            app_log("DISPATCH", f"Chưa đủ độ tin cậy ({result['confidence_score']:.1%} < {thresh:.0%}), chuyển hồ sơ [{rid}] sang Bàn duyệt cán bộ", f"Đơn vị: [{result['department']}]")
                            st.success(
                                f"✅ **Đã tiếp nhận hồ sơ thành công!** Mã hồ sơ của bạn là **{rid}**. Email xác nhận đã gửi tới **{target_email}**."
                            )
                    except ValueError as exc:
                        st.error(str(exc))

        result = st.session_state.get('analysis_result')
        rid = st.session_state.get('last_record_id')
        row = get_request(rid) if rid else None

        if result and row:
            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

            # 1. Thẻ Biên Nhận Tiếp Nhận Học Vụ Trang Nhã (Student Receipt Card)
            prio = row.get('priority_level', 'Bình thường')
            is_auto = (row.get('status') == 'reviewed_approve' or 'tự động' in (str(row.get('final_response', '')) + str(row.get('reviewed_at', ''))).lower())

            status_label = "🟢 ĐÃ ĐƯỢC PHÊ DUYỆT & GỬI EMAIL" if is_auto else ("🔴 TIẾP NHẬN ƯU TIÊN KHẨN CẤP" if prio == "Khẩn cấp" else "🔵 ĐANG CHỜ PHÒNG BAN THẨM ĐỊNH")
            status_bg = "#f0fdf4" if is_auto else ("#fef2f2" if prio == "Khẩn cấp" else "#eff6ff")
            status_color = "#15803d" if is_auto else ("#dc2626" if prio == "Khẩn cấp" else "#1e40af")
            sla_est = "Trong 04 - 12 giờ làm việc" if prio == "Khẩn cấp" else "Trong 24 - 48 giờ làm việc"

            receipt_html = (
                f'<div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-top: 5px solid {status_color}; border-radius: 12px; padding: 18px 22px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
                f'<div style="display: flex; align-items: center; gap: 8px;">'
                f'<span style="background: {status_bg}; color: {status_color}; font-weight: 800; font-size: 0.76rem; padding: 3px 10px; border-radius: 6px; letter-spacing: 0.03em;">{status_label}</span>'
                f'<span style="font-size: 1.1rem; font-weight: 800; color: #1a508b; font-family: monospace;">{rid}</span>'
                f'</div>'
                f'<span style="font-size: 0.8rem; color: #64748b;">Thời gian: {format_datetime_vn(row.get("processed_at"), fmt="%d/%m/%Y %H:%M")}</span>'
                f'</div>'
                f'<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-top: 10px;">'
                f'<div><div style="font-size: 0.72rem; color: #64748b; font-weight: 600;">ĐƠN VỊ PHỤ TRÁCH</div><div style="font-weight: 700; color: #1a508b; font-size: 0.88rem; margin-top: 2px;">{row["department"]}</div></div>'
                f'<div><div style="font-size: 0.72rem; color: #64748b; font-weight: 600;">CHUYÊN MÔN / THỦ TỤC</div><div style="font-weight: 700; color: #0f172a; font-size: 0.88rem; margin-top: 2px;">{TOPICS.get(row["predicted_topic"], row["predicted_topic"])}</div></div>'
                f'<div><div style="font-size: 0.72rem; color: #64748b; font-weight: 600;">THỜI HẠN XỬ LÝ (SLA)</div><div style="font-weight: 700; color: #15803d; font-size: 0.88rem; margin-top: 2px;">⏱️ {sla_est}</div></div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(receipt_html, unsafe_allow_html=True)

            # 2. Hướng dẫn giải quyết chuẩn hóa & Văn bản phản hồi
            resp_to_show = row.get('final_response') or result.get('procedure_draft_response') or result.get('draft_response')
            if resp_to_show:
                matched_p = result.get('matched_procedure')
                p_title = f"[{matched_p['proc_id']}] {matched_p['title']}" if matched_p else "Hướng dẫn xử lý học vụ EAUT"
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="font-size: 0.95rem; font-weight: 700; color: #1a508b; margin-bottom: 6px;">
                        📋 {p_title}
                    </div>
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; border-radius: 8px; padding: 12px 16px; font-size: 0.9rem; color: #1e293b; line-height: 1.6; white-space: pre-wrap;">
    {resp_to_show}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 3. Tra cứu thư viện (nếu có dữ liệu)
            lib_data = result.get('library_lookup')
            if lib_data and lib_data.get('has_live_data'):
                b_list = lib_data.get('books_found', [])
                br_list = lib_data.get('student_borrows', [])
                if b_list or br_list:
                    with st.expander("📚 Dữ liệu tra cứu Thư viện EAUT thời gian thực", expanded=True):
                        if b_list:
                            b_cols = st.columns(min(len(b_list), 3))
                            for b_idx, book in enumerate(b_list[:3]):
                                with b_cols[b_idx % 3]:
                                    avail_badge = "<span style='color:#16a34a; font-weight:700;'>🟢 Còn sách</span>" if book['available_copies'] > 0 else "<span style='color:#dc2626; font-weight:700;'>🔴 Hết</span>"
                                    st.markdown(f"""
                                    <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; font-size: 0.82rem;">
                                        <strong>{book['title']}</strong><br/>
                                        <span style="color:#64748b;">Vị trí: {book['location']}</span> · {avail_badge}
                                    </div>
                                    """, unsafe_allow_html=True)
                        if br_list:
                            for br in br_list:
                                st.caption(f"📘 **{br['book_title']}** · Hạn trả: **{br['due_date']}** · Trạng thái: **{br['status']}**")

            # 4. Xác nhận gửi email thông báo
            last_mail = st.session_state.get('last_sent_email')
            if last_mail:
                st.info(f"📧 **Thông báo:** Đã gửi email xác nhận và hướng dẫn tới hộp thư **{last_mail['recipient']}**.")
                with st.expander("Xem trước email đã gửi", expanded=False):
                    st.caption(f"Tiêu đề: {last_mail['subject']}")
                    st.text_area("Nội dung thư:", value=last_mail['body_plain'], height=160, disabled=True, key=f"preview_plain_{rid}")

            # 5. Dành cho cán bộ: Bản nháp & Tra cứu quy chế tham chiếu (Tương thích kiểm thử & Xử lý nhanh)
            with st.expander("🛠️ Dành cho cán bộ tiếp nhận: Chỉnh sửa bản nháp & Tham chiếu quy chế", expanded=(row['status'] == 'pending_review')):
                draft_key = 'intake_draft_' + rid
                if draft_key not in st.session_state:
                    st.session_state[draft_key] = row.get('draft_response', '')

                with st.form('draft_form_' + rid):
                    draft = st.text_area('Bản nháp phản hồi có thể chỉnh sửa', key=draft_key, height=120)
                    draft_saved = st.form_submit_button('Lưu bản nháp', width='stretch')

                if draft_saved:
                    try:
                        save_draft(rid, draft)
                        st.session_state['notice'] = f'Đã cập nhật bản nháp cho {rid}.'
                        st.session_state.pop('response_' + rid, None)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

                if result.get('articles'):
                    st.caption("Các điều khoản FAQ tham chiếu:")
                    for article in result['articles'][:2]:
                        st.markdown(f"- **{article['kb_id']}**: {article['question_standard']}")

    with admin_tabs[2]:
        render_knowledge_center()

    with admin_tabs[3]:
        render_dashboard(service=service)

    with admin_tabs[4]:
        st.markdown("""
        <div style="background: #cfdce8; border: 1px solid #b8cad8; border-radius: 12px; padding: 16px 20px 8px 20px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
            <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b;">Cài Đặt Hệ Thống & Quản Trị Hạ Tầng EAUT</div>
            <div style="font-size: 0.8rem; color: #475569; margin-top: 2px;">Cấu hình máy chủ SMTP Gmail gửi thư thực tế, huấn luyện mô hình Active Learning và giám sát Server Console thời gian thực</div>
        </div>
        """, unsafe_allow_html=True)

        c_cfg1, c_cfg2 = st.columns([1, 1], gap="large")

        with c_cfg1:
            st.markdown("##### 📬 Máy chủ Gửi Email (SMTP Gmail)")
            smtp_cfg = get_smtp_config()
            is_smtp_active = bool(smtp_cfg.get("user") and smtp_cfg.get("password"))
            if is_smtp_active:
                st.success(f"🟢 **Máy chủ SMTP đã kích hoạt:** Gửi thực tế qua `{smtp_cfg.get('user')}` (Cổng {smtp_cfg.get('port', 587)})")
            else:
                st.warning("⚠️ **Chế độ hiện tại: Mô phỏng (Mock).** Chưa thiết lập Mật khẩu ứng dụng Gmail 16 ký tự.")

            with st.expander("⚙️ Cấu hình thông tin tài khoản SMTP", expanded=not is_smtp_active):
                st.caption("Nhập tài khoản Gmail và Mật khẩu ứng dụng 16 ký tự để kích hoạt gửi thư thực tế:")
                sb_u = st.text_input("Gmail gửi:", value=smtp_cfg.get("user", ""), key="cfg_smtp_user", placeholder="hotro@gmail.com")
                sb_p = st.text_input("Mật khẩu ứng dụng (16 ký tự):", value=smtp_cfg.get("password", ""), type="password", key="cfg_smtp_pass", placeholder="xxxx yyyy zzzz wwww", help="Google App Password 16 chữ cái tạo tại myaccount.google.com/apppasswords")
                if st.button("💾 Lưu cấu hình & Kiểm tra kết nối SMTP", key="cfg_btn_save_smtp", type="primary", width="stretch"):
                    if not sb_u.strip() or not sb_p.strip():
                        st.error("Cần nhập cả Gmail và Mật khẩu ứng dụng.")
                    else:
                        with st.spinner("Đang kết nối thử tới máy chủ Gmail..."):
                            ok_sb, msg_sb = test_smtp_connection(sb_u, sb_p)
                            if ok_sb:
                                save_smtp_credentials(sb_u, sb_p)
                                st.success(f"Kết nối thành công! {msg_sb}")
                                st.rerun()
                            else:
                                st.error(msg_sb)

            st.markdown("##### 🧪 Thử nghiệm gửi email giải quyết mẫu")
            c_tm1, c_tm2 = st.columns([2, 1])
            with c_tm1:
                t_email_dest = st.text_input("Email người nhận thử nghiệm:", value=DEFAULT_TEST_EMAIL, key="cfg_test_email_dest")
            with c_tm2:
                t_topic_sample = st.selectbox("Chuyên môn mẫu:", options=list(TOPICS.keys()), format_func=lambda k: TOPICS.get(k, k), key="cfg_topic_sample")

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
            if st.button('Gửi email giải quyết mẫu tới ' + t_email_dest, type="primary", key="cfg_btn_send_sample"):
                with st.spinner("Đang tiến hành gửi email..."):
                    from app.components.workbench import DEPT_DOCX_MAPPING
                    t_dept = DEPT_DOCX_MAPPING.get(t_topic_sample, "Bộ phận Tiếp nhận")
                    subj, body_plain, body_html = build_rich_resolution_email(
                        record_id="DEMO_TEST_EMAIL",
                        topic=t_topic_sample,
                        department=t_dept,
                        resolution_text=chosen_sample_sol,
                        confidence_score=0.92,
                        is_auto_approved=True,
                        student_name="Sinh viên Thử nghiệm",
                        student_id="2024609999"
                    )
                    ok, send_info = send_resolution_email(
                        recipient_email=t_email_dest,
                        subject=subj,
                        body_text=body_plain,
                        body_html=body_html,
                        record_id="DEMO_TEST_EMAIL"
                    )
                    if ok:
                        if is_smtp_active:
                            st.success(f"🎉 **Đã gửi thư thực tế thành công!** {send_info} Vui lòng kiểm tra hộp thư đến của **{t_email_dest}**.")
                        else:
                            st.warning(f"{send_info}\n\n👉 Lưu ý: Để thư thực sự đến hộp thư đến, hãy lưu Mật khẩu ứng dụng ở trên.")
                    else:
                        st.error(send_info)

            st.markdown("---")
            st.markdown("##### 🤖 Tự động hóa & Huấn luyện lại AI (Active Learning)")
            auto_conf_thresh = st.slider(
                "Ngưỡng tin cậy tự động duyệt & gửi thẳng mail:",
                min_value=0.50,
                max_value=0.95,
                value=float(st.session_state.get('auto_conf_thresh', AUTO_APPROVE_CONFIDENCE_THRESHOLD)),
                step=0.05,
                format="%.0f%%",
                key="cfg_slider_thresh",
                help="Khi độ tin cậy AI >= ngưỡng này, hệ thống sẽ tự động duyệt và gửi thẳng email giải quyết cho sinh viên mà không cần chờ cán bộ duyệt thủ công."
            )
            st.session_state['auto_conf_thresh'] = auto_conf_thresh
            st.caption(f"Trạng thái: Khi AI đạt ≥ **{auto_conf_thresh:.0%}**, Model sẽ tự động gửi thẳng email ngay.")

            if st.button("🔄 Huấn luyện lại mô hình AI từ nhật ký duyệt", key="cfg_btn_retrain_model", width="stretch"):
                with st.spinner("Đang huấn luyện lại mô hình Logistic Regression + TF-IDF..."):
                    from src.model import train_and_save_production_model
                    clf = train_and_save_production_model()
                    st.success("Đã huấn luyện lại mô hình thành công! Khả năng tự động hóa đã được nâng cấp.")

            st.markdown("---")
            with st.expander("📥 Nạp danh sách nhiều Ticket từ tệp (.xlsx / .csv)", expanded=False):
                batch_file = st.file_uploader(
                    'Chọn tệp bảng tính (.xlsx hoặc .csv):',
                    type=['csv', 'xlsx'],
                    key='batch_file_settings'
                )
                if batch_file is not None:
                    try:
                        df_b = pd.read_csv(batch_file) if batch_file.name.lower().endswith('.csv') else pd.read_excel(batch_file)
                        if not df_b.empty:
                            potential = [c for c in df_b.columns if any(k in str(c).lower() for k in ['noi_dung', 'text', 'cau_hoi', 'phan_anh', 'content'])]
                            col_picked = potential[0] if potential else df_b.columns[0]
                            col_target = st.selectbox('Cột nội dung:', options=list(df_b.columns), index=list(df_b.columns).index(col_picked), key='batch_col_target_settings')
                            st.dataframe(df_b[[col_target]].head(3), width='stretch')
                            if st.button(f'Nạp {min(len(df_b), 50)} Ticket vào Bàn duyệt', type='primary', key='btn_do_batch_import_settings'):
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

        with c_cfg2:
            st.markdown("##### 🖥️ Console Nhật ký Web & Server")
            st.caption("Ghi nhận thời gian thực: gọi hàm gì, xử lý gì, kết quả ra sao.")
            comp_options = ["TẤT CẢ", "INTAKE", "CLEANER", "AI-MODEL", "RAG-DOCX", "SYNTHESIS", "GUARDRAILS", "DATABASE", "EMAIL", "WORKBENCH"]
            selected_comp = st.selectbox("Lọc thành phần:", options=comp_options, key="cfg_filter_comp")

            recent_logs = get_recent_logs(limit=35, component_filter=selected_comp)
            st.markdown(render_log_terminal_html(recent_logs, height_px=380), unsafe_allow_html=True)

            c_sb1, c_sb2, c_sb3 = st.columns([1, 1, 1])
            with c_sb1:
                if st.button("🔄 Làm mới", key="cfg_btn_refresh_log", width="stretch"):
                    st.rerun()
            with c_sb2:
                if st.button("🗑️ Xóa log", key="cfg_btn_clear_log", width="stretch"):
                    clear_logs()
                    st.rerun()
            with c_sb3:
                st.download_button(
                    "📥 Tải log (.txt)",
                    data=export_logs_text(),
                    file_name="app_server_logs.txt",
                    mime="text/plain",
                    key="cfg_btn_dl_logs",
                    width="stretch"
                )


