# -*- coding: utf-8 -*-
"""
EduSupportAI - Cổng tiếp nhận & Xử lý phản ánh học vụ sinh viên.
Tệp này chỉ ghép các thành phần; giao diện từng tab nằm trong app/components, kiểu dáng trong app/styles.css.
"""

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.components.auth import is_officer, render_officer_gate
from app.components.dashboard import render_dashboard
from app.components.intake import render_intake_form
from app.components.result_view import render_result
from app.components.workbench import render_workbench
from src.config import KB_PATH, MODEL_PATH, PROCEDURE_KB_PATH, database_path, is_production
from src.database import init_db, sync_kb_from_csv
from src.service import RequestService

st.set_page_config(page_title='EduSupportAI - Cổng xử lý phản ánh sinh viên', layout='wide',
                   initial_sidebar_state='collapsed')
st.markdown(f"<style>{(Path(__file__).parent / 'styles.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)



@st.cache_resource
def prepare_database(db_path, kb_stamp):
    """Khởi tạo CSDL và đồng bộ FAQ một lần cho mỗi CSDL / phiên bản FAQ, không lặp lại ở mỗi lần vẽ lại."""
    init_db()
    sync_kb_from_csv()
    return True


@st.cache_resource
def load_service(model_stamp, kb_stamp, procedure_stamp):
    """Nạp lại khi mô hình hoặc kho tri thức thay đổi (tham số là thời điểm sửa tệp)."""
    svc = RequestService()
    # Nạp sẵn mô hình ngôn ngữ ở nền để yêu cầu đầu tiên không phải chờ nạp model
    threading.Thread(target=svc.llm.warm_up, daemon=True).start()
    return svc


try:
    service = load_service(MODEL_PATH.stat().st_mtime_ns, KB_PATH.stat().st_mtime_ns,
                           PROCEDURE_KB_PATH.stat().st_mtime_ns)
    prepare_database(str(database_path()), KB_PATH.stat().st_mtime_ns)
except Exception as exc:
    st.error('Không nạp được mô hình phân loại hoặc kho tài liệu quy chế.')
    if not is_production():
        st.code(str(exc))
    st.stop()

llm_on = service.llm.is_available(refresh=True)
st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">EduSupportAI</div>
        <div class="app-subtitle">Hỗ trợ cố vấn học tập và Phòng Công tác sinh viên xử lý thắc mắc của sinh viên</div>
    </div>
    <div class="status-badge {'' if llm_on else 'status-muted'}">{'Mô hình ngôn ngữ cục bộ: bật' if llm_on else 'Bản nháp theo mẫu'}</div>
</div>
""", unsafe_allow_html=True)

if st.session_state.get('notice'):
    st.success(st.session_state.pop('notice'))

tab_intake, tab_review, tab_data = st.tabs(['Gửi yêu cầu', 'Bàn duyệt', 'Thống kê'])

officer = is_officer()

with tab_intake:
    render_intake_form(service, demo=not is_production())
    render_result(service, officer=officer)

with tab_review:
    if render_officer_gate():
        render_workbench()

with tab_data:
    if officer:
        render_dashboard(service=service)
    else:
        st.info('Khu vực này dành cho cán bộ. Đăng nhập ở tab Bàn duyệt.')
