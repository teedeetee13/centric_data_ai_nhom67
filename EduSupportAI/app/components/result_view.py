# -*- coding: utf-8 -*-
"""
Module: app.components.result_view
Kết quả xử lý một yêu cầu: tóm tắt, phiếu xử lý theo quy trình, bản nháp, tài liệu tham chiếu.
"""

import html

import streamlit as st

from src.config import TOPICS
from src.database import get_request, save_draft

PRIORITY_BADGES = {'Khẩn cấp': 'badge-urgent', 'Cao': 'badge-high', 'Bình thường': 'badge-normal', 'Thấp': 'badge-low'}
DRAFT_SOURCES = {
    'llm': 'Soạn bởi mô hình ngôn ngữ cục bộ, đã kiểm tra bám nguồn.',
    'template_fallback': 'Theo mẫu (bản của mô hình ngôn ngữ bị loại vì có dữ kiện ngoài quy trình).',
    'template': 'Theo mẫu từ quy trình / quy chế.',
}


def _field(label, value_html):
    st.markdown(f'<div class="field-label">{label}</div><div class="field-value">{value_html}</div>', unsafe_allow_html=True)


def render_summary(row, result):
    topic = TOPICS.get(row['predicted_topic'], row['predicted_topic'])
    badge = PRIORITY_BADGES.get(row['priority_level'], 'badge-normal')
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 1.4, 1.4])
        with c1:
            _field('Đơn vị đầu mối', html.escape(row['department']))
        with c2:
            _field('Nhóm', html.escape(topic))
        with c3:
            _field('Ưu tiên', f"<span class='{badge}'>{html.escape(row['priority_level'])}</span>")
        with c4:
            _field('Độ tự tin', f"{row['confidence_score']:.0%}")
        st.text_area('Nội dung đã lưu (đã che thông tin cá nhân)', value=row['clean_text'], disabled=True,
                     key='clean_' + row['record_id'], height=80)
    if result['review_reasons']:
        st.warning('Cần cán bộ lưu ý:\n' + '\n'.join(f'- {reason}' for reason in result['review_reasons']))


def render_ticket_plan(plan, key_prefix):
    """Phiếu xử lý ticket theo quy trình (dùng chung cho sinh viên và cán bộ)."""
    with st.expander(f"Phiếu xử lý ticket theo quy trình {plan['procedure_id']} — {plan['procedure_name']}", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            _field('Nơi tiếp nhận', html.escape(plan['receiving_unit']))
        with c2:
            _field('Trạng thái', html.escape(plan['status']))
        with c3:
            _field('Hạn xử lý dự kiến', html.escape(plan['sla_due_date'] or plan['result_time']))
        if plan['documents']:
            st.markdown('**Hồ sơ cần chuẩn bị**')
            for doc in plan['documents']:
                st.checkbox(doc, key=f"doc_{key_prefix}_{doc}")
        st.dataframe([{'Bước': i, 'Đơn vị': s['unit'], 'Nội dung': s['action'], 'Thời gian': s['time']}
                      for i, s in enumerate(plan['steps'], 1)], hide_index=True, width='stretch')
        st.caption(f"Thời hạn nộp: {plan['submit_window']} · Căn cứ: {plan['legal_basis']}")


def render_articles(articles):
    with st.expander(f'Tài liệu tham chiếu ({len(articles)})'):
        if not articles:
            st.write('Chưa tìm thấy tài liệu đủ liên quan. Cán bộ tra cứu trực tiếp.')
        for article in articles:
            st.markdown(f"**{article['kb_id']} — {article['question_standard']}**")
            st.caption(f"Nguồn đã xác minh: {article['source_url']}" if article['verified']
                       else 'Nội dung minh họa, chưa xác minh.')
            st.write(article['content_extract'].replace('\n', '  \n'))


def render_draft(row, rid, source):
    st.markdown('#### Bản nháp trả lời')
    if row['status'] != 'pending_review':
        st.success('Yêu cầu đã được xử lý.')
        st.write(row['final_response'])
        return
    st.caption(DRAFT_SOURCES.get(source, ''))
    draft_key = 'intake_draft_' + rid
    if draft_key not in st.session_state:
        st.session_state[draft_key] = row['draft_response']
    with st.form('draft_form_' + rid, border=False):
        draft = st.text_area('Bản nháp', key=draft_key, height=200, label_visibility='collapsed')
        saved = st.form_submit_button('Lưu bản nháp')
    if saved:
        try:
            save_draft(rid, draft)
            st.session_state['notice'] = f'Đã lưu bản nháp cho {rid}.'
            st.session_state.pop('response_' + rid, None)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def render_student_receipt(result, row, rid):
    """Sinh viên chỉ thấy biên nhận và hướng dẫn đã xác minh, không thấy bản nháp hay nhãn nội bộ."""
    st.success(f"Mã yêu cầu của bạn: {rid}. Đơn vị tiếp nhận: {row['department']}. Cán bộ sẽ phản hồi sau khi xem xét.")
    if result.get('ticket_plan'):
        render_ticket_plan(result['ticket_plan'], rid)


def render_result(service, officer=True):
    result = st.session_state.get('analysis_result')
    rid = st.session_state.get('last_record_id')
    row = get_request(rid) if rid else None
    if not (result and row):
        return
    st.divider()
    if not officer:
        render_student_receipt(result, row, rid)
        return
    st.markdown(f'#### Kết quả xử lý · {rid}')
    render_summary(row, result)
    if result.get('ticket_plan'):
        render_ticket_plan(result['ticket_plan'], rid)
    render_draft(row, rid, result.get('draft_source'))
    render_articles(result['articles'])
