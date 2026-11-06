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

from app.components.dashboard import render_dashboard
from app.components.demo_guide import render_demo_guide
from app.components.intake import render_intake_form, render_test_email, render_upload_tools
from app.components.result_view import render_result
from app.components.workbench import render_workbench
from src.config import KB_PATH, MODEL_PATH, PROCEDURE_KB_PATH
from src.database import init_db, sync_kb_from_csv
from src.service import RequestService

st.set_page_config(page_title='EduSupportAI - Cổng xử lý phản ánh sinh viên', layout='wide',
                   initial_sidebar_state='collapsed')
st.markdown(f"<style>{(Path(__file__).parent / 'styles.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)

init_db()


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
    sync_kb_from_csv()
except Exception as exc:
    st.error('Không nạp được mô hình phân loại hoặc kho tài liệu quy chế.')
    st.code(str(exc))
    st.stop()

llm_badge = 'Mô hình ngôn ngữ cục bộ: bật' if service.llm.is_available(refresh=True) else 'Bản nháp theo mẫu'
st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">EduSupportAI</div>
        <div class="app-subtitle">Cổng tiếp nhận, phân loại và xử lý phản ánh học vụ sinh viên</div>
    </div>
    <div class="status-badge">Hệ thống sẵn sàng · {llm_badge}</div>
</div>
""", unsafe_allow_html=True)

if st.session_state.get('notice'):
    st.success(st.session_state.pop('notice'))

tab_intake, tab_review, tab_data = st.tabs(['Tiếp nhận yêu cầu', 'Bàn duyệt cán bộ', 'Dữ liệu và lịch sử'])

with tab_intake:
    st.subheader('Tiếp nhận phản ánh sinh viên')
    render_demo_guide(service)
    render_intake_form(service)
    render_upload_tools(service)
    render_test_email()
    render_result(service)

with tab_review:
    render_workbench()

with tab_data:
    render_dashboard(service=service)
