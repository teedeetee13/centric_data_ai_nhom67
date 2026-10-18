# -*- coding: utf-8 -*-
"""
Module: app.components.workbench
Bàn làm việc cán bộ tiếp nhận & kiểm duyệt (Human-in-the-Loop)
Thiết kế tối giản, trực quan, hỗ trợ duyệt nguyên tử và bảo mật PII.
Không emoji - Đồng bộ trạng thái form theo từng bản ghi.
"""

import json
import pandas as pd
import streamlit as st
from src.config import TOPICS, describe_flags
from src.database import list_requests, log_review_action, save_draft

ALL_TOPICS = list(TOPICS.keys())
TOPIC_VIETNAMESE = TOPICS

def load_review_queue():
    return pd.DataFrame(list_requests(pending_only=True))

def render_workbench(faq_engine=None):
    queue = list_requests(pending_only=True)
    st.subheader('Bàn duyệt cán bộ')
    st.caption('Mọi yêu cầu đều cần cán bộ duyệt và kiểm tra quy chế. Lưu nội bộ, không gửi email tự động.')

    if not queue:
        st.success('Hàng đợi hoàn tất — Không có yêu cầu nào đang chờ duyệt.')
        return

    ids = [row['record_id'] for row in queue]
    focus = st.session_state.get('focus_review_id')
    if focus in ids and st.session_state.get('_focused_once') != focus:
        st.session_state['review_id'] = focus
        st.session_state['_focused_once'] = focus

    if st.session_state.get('review_id') not in ids:
        st.session_state['review_id'] = ids[0]

    by_id = {row['record_id']: row for row in queue}
    rid = st.selectbox(
        'Chọn yêu cầu cần xử lý',
        options=ids,
        key='review_id',
        format_func=lambda k: f"{k} · {TOPICS.get(by_id[k]['predicted_topic'], 'Khác')} · {by_id[k]['priority_level']}"
    )
    item = by_id[rid]

    # Khung tóm tắt Sapphire Academic
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 14px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 0.74rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">MÃ YÊU CẦU: <strong style="color: #0f172a;">{rid}</strong></span>
            <span style="font-size: 0.78rem; font-weight: 600; color: #1d4ed8; background: #eff6ff; padding: 2px 8px; border-radius: 4px;">Độ tự tin: {item['confidence_score']:.1%}</span>
        </div>
        <div style="font-size: 0.88rem; color: #334155;">
            Hàng đợi: <strong>{len(queue)}</strong> yêu cầu chờ duyệt | Đơn vị gợi ý: <strong>{item['department']}</strong> | Mức độ: <strong>{item['priority_level']}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_detail1, c_detail2 = st.columns([1, 1], gap="medium")
    with c_detail1:
        st.caption('Nội dung phản ánh đã bảo mật (Che PII):')
        st.text_area('Yêu cầu đã che thông tin', value=item['clean_text'], disabled=True, key='review_clean_' + rid, height=120)
        st.caption('Chất lượng dữ liệu: ' + describe_flags(item['quality_flags']))

    with c_detail2:
        st.caption('Tài liệu quy chế tham chiếu:')
        articles = json.loads(item['articles_json']) if item.get('articles_json') else []
        if articles:
            for article in articles:
                with st.expander(f"{article['kb_id']} — {article['question_standard']}"):
                    st.caption('Nguồn đã xác minh' if article.get('verified') else 'Tài liệu minh họa, chưa xác minh')
                    st.write(article.get('content_extract', ''))
                    if article.get('source_url'):
                        st.write(f"Nguồn: {article['source_url']}")
        else:
            st.info('Không có điều khoản quy chế tương ứng. Cán bộ đối chiếu quy định thủ công.')

    # Form duyệt phản hồi
    topics = list(TOPICS.keys())
    response_key = 'response_' + rid
    if response_key not in st.session_state:
        st.session_state[response_key] = item['draft_response']

    with st.form('review_form_' + rid):
        curr_topic = item['predicted_topic'] if item['predicted_topic'] in topics else 'Khac'
        final_topic = st.selectbox(
            'Nhóm phân loại cuối cùng',
            options=topics,
            index=topics.index(curr_topic),
            format_func=lambda t: TOPICS.get(t, t),
            key='topic_' + rid
        )
        response = st.text_area('Nội dung phản hồi chính thức', key=response_key, height=170)
        notes = st.text_input('Ghi chú xử lý nội bộ', key='notes_' + rid, placeholder='Nhập ghi chú hoặc lý do nếu có...')

        c1, c2, c3 = st.columns(3)
        draft_button = c1.form_submit_button('Lưu nháp', width='stretch')
        approve = c2.form_submit_button('Duyệt và lưu', type='primary', width='stretch')
        reject = c3.form_submit_button('Từ chối', width='stretch')

    if draft_button or approve or reject:
        try:
            if draft_button:
                save_draft(rid, response)
                st.session_state.pop('intake_draft_' + rid, None)
                message = f'Đã lưu bản nháp cho yêu cầu {rid}.'
            else:
                action = 'reject' if reject else ('edit_label' if final_topic != item['predicted_topic'] else 'approve')
                final_resp = 'Yêu cầu bị từ chối.' if reject else response
                log_review_action(rid, action, item['predicted_topic'], final_topic, final_resp, notes)
                message = f'Đã xử lý xong {rid}. Bản ghi đã rời khỏi hàng đợi.'
            st.session_state['notice'] = message
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
