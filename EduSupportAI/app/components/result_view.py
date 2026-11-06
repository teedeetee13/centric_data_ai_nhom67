# -*- coding: utf-8 -*-
"""
Module: app.components.result_view
Hiển thị kết quả phân tích một yêu cầu: thẻ chỉ số, phiếu ticket theo quy trình, tài liệu tham chiếu, bản nháp.
"""

import streamlit as st

from src.config import TOPICS, describe_flags
from src.database import get_request, save_draft

PRIORITY_BADGES = {'Khẩn cấp': 'badge-urgent', 'Cao': 'badge-high', 'Bình thường': 'badge-normal', 'Thấp': 'badge-low'}

METRIC_NOTE = (
    'Chú thích: Đơn vị phụ trách lấy theo quy trình nghiệp vụ nếu ghép được, ngược lại theo nhóm chủ đề. '
    'Độ tự tin là xác suất mô hình gán cho nhóm đã chọn, chưa phải độ chính xác thực tế; dưới 60% thì cán bộ xác nhận lại. '
    'Mức ưu tiên do luật từ khóa quyết định (ví dụ "nhập viện" là Khẩn cấp), không do mô hình.'
)


def _metric_card(label, value_html):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-val">{value_html}</div></div>', unsafe_allow_html=True)


def render_metrics(row, result):
    topic = TOPICS.get(row['predicted_topic'], row['predicted_topic'])
    badge = PRIORITY_BADGES.get(row['priority_level'], 'badge-normal')
    c1, c2, c3 = st.columns(3)
    with c1:
        _metric_card('Đơn vị chuyên môn phụ trách', f"{row['department']} <span class=\"metric-sub\">({topic})</span>")
    with c2:
        _metric_card('Độ tự tin phân loại', f"{row['confidence_score']:.1%}")
    with c3:
        _metric_card('Mức độ ưu tiên', f"<span class=\"{badge}\">{row['priority_level']}</span>")

    st.caption(f"Căn cứ phân cấp ưu tiên: {row['priority_reason']}")
    st.caption(METRIC_NOTE)
    if result.get('model_topic') and result['model_topic'] != row['predicted_topic']:
        st.caption(f"Mô hình phân loại gợi ý nhóm {TOPICS.get(result['model_topic'], result['model_topic'])}; "
                   f"hệ thống dùng nhóm của quy trình đã khớp.")


def render_ticket_plan(plan, key_prefix):
    """Phiếu xử lý ticket theo quy trình (dùng chung cho tab Tiếp nhận và các màn hình khác)."""
    with st.expander(f"Phiếu xử lý ticket theo quy trình {plan['procedure_id']} — {plan['procedure_name']}", expanded=True):
        p1, p2, p3 = st.columns(3)
        p1.markdown(f"**Đơn vị đầu mối**  \n{plan['receiving_unit']}")
        p2.markdown(f"**Trạng thái**  \n{plan['status']}")
        p3.markdown(f"**Hạn xử lý dự kiến**  \n{plan['sla_due_date'] or plan['result_time']}")
        st.caption(f"Căn cứ: {plan['legal_basis']} · Nguồn: {plan['source_doc']} · Độ khớp quy trình: {plan['match_score']:.3f}")
        st.markdown(f"**Việc tiếp theo:** {plan['next_action']}")
        if plan['documents']:
            st.markdown('**Hồ sơ sinh viên cần chuẩn bị**')
            for doc in plan['documents']:
                st.checkbox(doc, key=f"doc_{key_prefix}_{doc}")
        if plan['submit_window']:
            st.caption(f"Thời hạn nộp: {plan['submit_window']}")
        st.dataframe(
            [{'Bước': i, 'Đơn vị': s['unit'], 'Nội dung': s['action'], 'Thời gian': s['time']}
             for i, s in enumerate(plan['steps'], 1)],
            hide_index=True, width='stretch'
        )


def render_articles(articles):
    with st.expander('Tài liệu quy chế tham chiếu', expanded=True):
        for article in articles:
            st.markdown(f"**{article['kb_id']} — {article['question_standard']}**")
            if article['verified']:
                st.caption(f"Nguồn chính thức đã xác minh: {article['source_url']}")
            else:
                st.caption('Nội dung minh họa; chưa xác minh quy định chính thức của trường.')
            st.write(article['content_extract'].replace('\n', '  \n'))
            st.caption(f"Độ tương đồng ngữ nghĩa: {article['similarity_score']:.3f}")
        if not articles:
            st.write('Chưa tìm thấy điều khoản quy chế đủ liên quan. Cần cán bộ tra cứu trực tiếp.')


def render_draft(row, rid):
    if row['status'] != 'pending_review':
        is_auto = 'tự động' in (str(row.get('final_response', '')) + str(row.get('reviewed_at', ''))).lower()
        if is_auto or row.get('status') == 'reviewed_approve':
            st.success(f"Yêu cầu đã được phê duyệt và lưu trữ thành công (Độ chắc chắn: {row['confidence_score']:.1%}). "
                       "Hướng giải quyết đã được gửi về email.")
        else:
            st.success('Yêu cầu đã được cán bộ xử lý và phê duyệt.')
        st.write(row['final_response'])
        return

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


def render_result(service):
    result = st.session_state.get('analysis_result')
    rid = st.session_state.get('last_record_id')
    row = get_request(rid) if rid else None
    if not (result and row):
        return

    st.subheader('Kết quả phân tích & Phân luồng')
    render_metrics(row, result)

    st.text_area('Nội dung đã bảo mật thông tin cá nhân (Che PII)', value=row['clean_text'],
                 disabled=True, key='clean_' + rid, height=90)
    st.caption('Chất lượng dữ liệu: ' + describe_flags(row['quality_flags']))

    for reason in result['review_reasons']:
        st.warning(reason)

    if result.get('ticket_plan'):
        render_ticket_plan(result['ticket_plan'], rid)

    draft_labels = {
        'llm': f"Bản nháp do mô hình ngôn ngữ cục bộ {result.get('llm_model')} soạn, đã qua kiểm tra bám nguồn.",
        'template_fallback': 'Bản nháp theo mẫu (bản của mô hình ngôn ngữ bị loại vì không bám nguồn).',
        'template': 'Bản nháp theo mẫu từ quy trình / quy chế. ' + service.llm.status(),
    }
    st.caption(draft_labels.get(result.get('draft_source'), ''))

    render_articles(result['articles'])
    render_draft(row, rid)
