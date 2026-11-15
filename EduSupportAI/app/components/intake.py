# -*- coding: utf-8 -*-
"""
Module: app.components.intake
Tab Gửi yêu cầu (form của sinh viên) và các công cụ nhập liệu dùng ở tab Thống kê:
nạp danh sách từ tệp, gửi email thử.
"""

import hashlib
import html
import time

import pandas as pd
import streamlit as st

from app.components.demo_guide import render_sample_picker
from src.config import DEFAULT_TEST_EMAIL, TOPICS, is_production
from src.database import delete_contact, get_request, log_review_action, save_contact, save_request
from src.email_service import VALID_EMAIL, build_resolution_email, send_resolution_email
from src.service import can_auto_approve

# Khoảng cách tối thiểu giữa hai lần gửi của một phiên khi vận hành thật
MIN_SUBMIT_INTERVAL_S = 5
MAX_PDF_PAGES = 20
MAX_BATCH_ROWS = 200


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
            texts = [page.extract_text() or '' for page in reader.pages[:MAX_PDF_PAGES]]
            return '\n'.join(t.strip() for t in texts if t.strip())
    except Exception as e:
        return f"Lỗi trích xuất tệp: {e}"
    return ""


def _render_attachment():
    with st.expander('Đính kèm tệp (không bắt buộc)'):
        uploaded_doc = st.file_uploader('Đơn từ (.txt, .docx, .pdf) hoặc ảnh minh chứng (.png, .jpg)',
                                        type=['txt', 'docx', 'pdf', 'png', 'jpg', 'jpeg'], key='ticket_doc_upload')
        if uploaded_doc is None:
            return
        if uploaded_doc.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            st.image(uploaded_doc, width=200)
            return
        content = extract_text_from_upload(uploaded_doc)
        if content and not content.startswith('Lỗi'):
            st.caption(f'Đọc được {len(content)} ký tự từ {uploaded_doc.name}.')
            if st.button('Điền nội dung tệp vào ô nội dung', key='btn_fill_doc'):
                st.session_state['request_text'] = content
                st.rerun()


def _submit(service, text, mssv, email):
    parts = [text.strip()] if text.strip() else []
    if mssv.strip():
        parts.append(f"Mã sinh viên {mssv.strip()}.")
    if email.strip():
        parts.append(f"Email {email.strip()}.")
    combined = "\n".join(parts)

    waited = time.monotonic() - st.session_state.get('last_submit_at', 0.0)
    if not combined:
        st.warning('Bạn cần nhập nội dung trước khi gửi.')
        return
    if is_production() and waited < MIN_SUBMIT_INTERVAL_S:
        st.warning('Bạn vừa gửi một yêu cầu. Vui lòng đợi vài giây rồi gửi lại.')
        return
    st.session_state['last_submit_at'] = time.monotonic()

    fingerprint = hashlib.sha256(combined.encode()).hexdigest()
    old_id = st.session_state.get('last_record_id')
    if fingerprint == st.session_state.get('submission_fingerprint') and old_id and get_request(old_id):
        st.info('Yêu cầu này đã được gửi trong phiên hiện tại.')
        return

    try:
        with st.spinner('Đang xử lý...'):
            result = service.process(combined)
    except ValueError as exc:
        st.error(str(exc))
        return
    rid = save_request(result, source_type='portal_student')
    st.session_state.update(analysis_result=result, last_record_id=rid,
                            submission_fingerprint=fingerprint, focus_review_id=rid)

    # Email chỉ đến đúng địa chỉ sinh viên cung cấp, lưu tách khỏi nội dung đã che
    match_mail = VALID_EMAIL.search(email.strip() or combined)
    target_email = match_mail.group(0) if match_mail else None
    if target_email:
        save_contact(rid, target_email)

    if can_auto_approve(result) and target_email:
        log_review_action(rid, 'approve', result['predicted_topic'], result['predicted_topic'], result['draft_response'],
                          notes=f"AI tự động phê duyệt (độ tự tin {result['confidence_score']:.1%})")
        subject, body = build_resolution_email(rid, result['predicted_topic'], result['department'],
                                               result['draft_response'], result['confidence_score'], is_auto_approved=True)
        send_resolution_email(target_email, subject, body, record_id=rid)
        delete_contact(rid)
        st.success(f'Đã tiếp nhận {rid} và tự động gửi hướng dẫn về {target_email}.')
    elif result.get('priority_level') == 'Khẩn cấp':
        st.warning(f'Đã tiếp nhận {rid}. Yêu cầu khẩn cấp, chuyển ngay tới {result["department"]}.')
    else:
        st.success(f'Đã tiếp nhận {rid}, chuyển tới {result["department"]}.')


def render_intake_form(service, demo=True):
    form_col, side_col = st.columns([3, 2], gap='large') if demo else (st.container(), None)
    with form_col:
        with st.form('intake_form', clear_on_submit=False, border=True):
            text = st.text_area('Nội dung cần hỗ trợ', key='request_text', height=150, max_chars=8000,
                                placeholder='Mô tả việc cần hỗ trợ: việc gì, ở đâu, khi nào...')
            c_mssv, c_mail = st.columns(2)
            mssv = c_mssv.text_input('Mã sinh viên', key='in_mssv', placeholder='VD: 2022601234')
            email = c_mail.text_input('Email nhận kết quả (không bắt buộc)', key='in_email', placeholder='VD: sinhvien@eaut.edu.vn')
            st.caption('Thông tin cá nhân được tự động che trước khi lưu.')
            submitted = st.form_submit_button('Gửi', type='primary', width='stretch')
        if submitted:
            _submit(service, text, mssv, email)
        _render_attachment()
    if side_col is not None:
        with side_col:
            render_sample_picker()


def render_batch_import(service):
    """Nạp danh sách câu hỏi từ CSV/XLSX (ví dụ tệp xuất từ cổng hỗ trợ MIS) vào hàng chờ."""
    batch_file = st.file_uploader('Tệp bảng tính (.xlsx hoặc .csv)', type=['csv', 'xlsx'], key='batch_file_intake')
    if batch_file is None:
        return
    try:
        frame = pd.read_csv(batch_file) if batch_file.name.lower().endswith('.csv') else pd.read_excel(batch_file)
    except Exception as err:
        st.error(f'Không đọc được tệp: {err}')
        return
    if frame.empty:
        st.info('Tệp không có dòng dữ liệu.')
        return
    guess = [c for c in frame.columns if any(k in str(c).lower() for k in ('noi_dung', 'text', 'cau_hoi', 'phan_anh', 'content', 'vấn đề', 'mô tả'))]
    columns = list(frame.columns)
    col = st.selectbox('Cột nội dung', columns, index=columns.index(guess[0]) if guess else 0, key='batch_col_target')
    count = min(len(frame), MAX_BATCH_ROWS)
    if st.button(f'Nạp {count} yêu cầu vào hàng chờ', type='primary', key='btn_do_batch_import'):
        added = 0
        for value in frame[col].head(MAX_BATCH_ROWS):
            value = str(value).strip()
            if value and value not in ('nan', 'None'):
                # Không gọi mô hình ngôn ngữ cho từng dòng để không khóa giao diện
                save_request(service.process(value, use_llm=False), source_type='file_batch')
                added += 1
        st.session_state['notice'] = f'Đã nạp {added} yêu cầu vào hàng chờ.'
        st.rerun()


SAMPLE_SOLUTIONS = {
    'Hoc_phi': 'Phòng Tài chính - Kế toán đã đối soát giao dịch và cập nhật công nợ học phí của bạn.',
    'Lich_hoc_lich_thi': 'Phòng Đào tạo đã ghi nhận yêu cầu và sẽ thông báo lịch thi bổ sung.',
    'Diem_khao_thi': 'Phòng Khảo thí đã kiểm tra và cập nhật điểm trên cổng thông tin.',
    'Thu_tuc_hanh_chinh': 'Bộ phận Một cửa đã cấp giấy xác nhận; bạn có thể đến nhận bản cứng.',
    'Co_so_vat_chat': 'Cán bộ quản lý phòng học đã khắc phục sự cố.',
    'He_thong_CNTT': 'Tài khoản của bạn đã được cấp lại mật khẩu.',
    'Khac': 'Nhà trường đã ghi nhận ý kiến của bạn.',
}


def render_test_email():
    c_mail, c_topic = st.columns([2, 1])
    dest = c_mail.text_input('Email nhận thử', value=DEFAULT_TEST_EMAIL, key='intake_test_email_dest')
    topic = c_topic.selectbox('Chủ đề', list(TOPICS), format_func=lambda k: TOPICS[k], key='intake_test_topic_select')
    if st.button('Gửi email giải quyết mẫu', key='btn_send_sample_email_intake'):
        subject, body = build_resolution_email('DEMO_TEST_EMAIL', topic, 'Bộ phận tiếp nhận', SAMPLE_SOLUTIONS[topic],
                                               confidence_score=0.92, is_auto_approved=True)
        ok, info = send_resolution_email(dest, subject, body, record_id='DEMO_TEST_EMAIL')
        (st.success if ok else st.error)(info)
        if ok:
            st.markdown(f"<pre style='white-space:pre-wrap;font-size:0.8rem'>{html.escape(body)}</pre>", unsafe_allow_html=True)
