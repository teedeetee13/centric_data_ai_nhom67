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

import pandas as pd
import streamlit as st
from src.config import KB_PATH, MODEL_PATH, TOPICS, describe_flags
from src.database import init_db, sync_kb_from_csv, save_request, get_request, save_draft, list_requests
from src.service import RequestService
from app.components.workbench import render_workbench
from app.components.dashboard import render_dashboard

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
</style>
""", unsafe_allow_html=True)

init_db()

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

if st.session_state.get('notice'):
    st.success(st.session_state.pop('notice'))

samples = {
    'Học phí': 'Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.',
    'Lỗi đăng nhập': 'Em không đăng nhập được cổng sinh viên, số điện thoại 0912 345 678.',
    'Thiếu thông tin': 'Giúp em với',
}

tabs = st.tabs(['Tiếp nhận yêu cầu', 'Bàn duyệt cán bộ', 'Dữ liệu và lịch sử'])

with tabs[0]:
    st.subheader('Tiếp nhận phản ánh sinh viên')

    # Danh mục chủ đề vấn đề và các tick box chi tiết
    topic_catalog = {
        'Cơ sở vật chất & Vật dụng giảng đường': [
            'Điều hòa phòng học hỏng / chảy nước',
            'Máy chiếu / Màn chiếu không hoạt động',
            'Hệ thống âm thanh / Micro giảng đường lỗi',
            'Bàn ghế, bóng điện, ổ cắm phòng học hư hại',
            'Vấn đề vệ sinh phòng học / Giảng đường'
        ],
        'Học tập & Môn học': [
            'Trùng ca thi kết thúc học phần',
            'Đơn đề nghị phúc khảo bài thi',
            'Thắc mắc điểm chuyên cần / Điểm quá trình',
            'Lịch học bù / Thay đổi phòng học',
            'Đăng ký môn học / Rút bớt học phần'
        ],
        'Học phí & Tài chính sinh viên': [
            'Đã nộp học phí qua ngân hàng nhưng cổng chưa gạch nợ',
            'Thắc mắc về mức thu học phí học kỳ',
            'Đơn xin gia hạn thời gian nộp học phí',
            'Thủ tục miễn giảm học phí / Chế độ chính sách'
        ],
        'Thủ tục hành chính & Giấy tờ': [
            'Xin giấy xác nhận sinh viên tạm hoãn nghĩa vụ quân sự',
            'Xin cấp bảng điểm quá trình học tập',
            'Xin giấy xác nhận vay vốn ngân hàng chính sách',
            'Thủ tục bảo lưu kết quả học tập / Chuyển ngành'
        ],
        'Tài khoản & Hệ thống CNTT': [
            'Quên mật khẩu cổng thông tin daotao.eaut.edu.vn',
            'Không nhận được mã xác thực OTP qua email',
            'Lỗi tài khoản ứng dụng sinh viên / Thư viện số'
        ],
        'Ý kiến đóng góp & Góp ý khác': [
            'Đóng góp ý kiến nâng cao chất lượng dịch vụ đào tạo',
            'Đề xuất nâng cấp tiện ích và không gian tự học',
            'Ý kiến phản ánh hoặc đề xuất khác'
        ]
    }

    # Chọn chủ đề vấn đề đang gặp phải
    st.markdown('##### Chủ đề phản ánh:')
    selected_topic = st.radio(
        'Chủ đề vấn đề:',
        options=list(topic_catalog.keys()),
        horizontal=True,
        key='intake_topic_radio',
        label_visibility='collapsed'
    )

    # Form tiếp nhận chính
    with st.form('intake_form', clear_on_submit=False):
        st.markdown(f"##### Chọn vấn đề cụ thể thuộc [{selected_topic}]:")
        sub_issues = topic_catalog[selected_topic]
        chk_cols = st.columns(2)
        checked_issues = []
        for idx, issue in enumerate(sub_issues):
            with chk_cols[idx % 2]:
                if st.checkbox(issue, key=f"chk_{selected_topic}_{idx}"):
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

        st.caption('Thông tin cá nhân (MSSV, SĐT, Email) sẽ được hệ thống tự động bảo mật và che dấu (PII masking) ngay khi tiếp nhận.')
        submitted = st.form_submit_button('Gửi', type='primary', width='stretch')

    if submitted:
        # Tổng hợp toàn bộ dữ liệu gồm: Tick box đã chọn + Ý kiến chi tiết + Thông tin liên hệ
        parts = []
        if checked_issues:
            parts.append(f"Vấn đề ghi nhận: {', '.join(checked_issues)}.")

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
                    result = service.process(combined_input)
                    rid = save_request(result, source_type='portal_student')
                    st.session_state.update(
                        analysis_result=result,
                        last_record_id=rid,
                        submission_fingerprint=fingerprint,
                        focus_review_id=rid
                    )
                    st.success(f'Đã lưu thành công yêu cầu {rid}. Hệ thống AI đã tự động lọc vấn đề và chuyển đến Bàn duyệt cán bộ.')
                except ValueError as exc:
                    st.error(str(exc))

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

    result = st.session_state.get('analysis_result')
    rid = st.session_state.get('last_record_id')
    row = get_request(rid) if rid else None

    if result and row:
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        st.subheader('2. Kết quả phân tích & Phân luồng')

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
            'Nội dung đã bảo mật thông tin cá nhân (Che PII)',
            value=row['clean_text'],
            disabled=True,
            key='clean_' + rid,
            height=90
        )
        st.caption('Chất lượng dữ liệu: ' + describe_flags(row['quality_flags']))

        for reason in result['review_reasons']:
            st.warning(reason)

        with st.expander('Tài liệu quy chế tham chiếu', expanded=True):
            for article in result['articles']:
                st.markdown(f"**{article['kb_id']} — {article['question_standard']}**")
                if article['verified']:
                    st.caption(f"Nguồn chính thức đã xác minh: {article['source_url']}")
                else:
                    st.caption('Nội dung minh họa; chưa xác minh quy định chính thức của trường.')
                st.write(article['content_extract'])
                st.caption(f"Độ tương đồng ngữ nghĩa: {article['similarity_score']:.3f}")
            if not result['articles']:
                st.write('Chưa tìm thấy điều khoản quy chế đủ liên quan. Cần cán bộ tra cứu trực tiếp.')

        if row['status'] == 'pending_review':
            st.subheader('3. Soạn thảo bản nháp hoặc chuyển sang bàn duyệt')
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
            st.success('Yêu cầu đã được cán bộ xử lý và phê duyệt.')
            st.write(row['final_response'])

with tabs[1]:
    render_workbench()

with tabs[2]:
    render_dashboard(service=service)
