# -*- coding: utf-8 -*-
"""
Module: app.components.workbench
Bàn duyệt cán bộ: số liệu hàng chờ, danh sách yêu cầu, xử lý từng yêu cầu (Human-in-the-Loop).
"""

import html
import json
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.config import TOPICS, describe_flags
from src.database import count_pending, delete_contact, get_contact, list_requests, log_review_action, save_draft
from src.email_service import build_resolution_email, send_resolution_email

# Hàng chờ dài làm chậm trình duyệt; xử lý theo thứ tự ưu tiên nên chỉ cần phần đầu
QUEUE_DISPLAY_LIMIT = 200
PRIORITY_BADGES = {'Khẩn cấp': 'badge-urgent', 'Cao': 'badge-high', 'Bình thường': 'badge-normal', 'Thấp': 'badge-low'}


def _department(r):
    return r.get('department') or 'Bộ phận tiếp nhận chung'


def _age_days(stamp):
    try:
        start = datetime.fromisoformat(str(stamp))
        start = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - start).total_seconds() / 86400
    except ValueError:
        return 0.0


def _render_queue_metrics(queue, total):
    oldest = max((_age_days(r['processed_at']) for r in queue), default=0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Chờ duyệt', total, border=True)
    c2.metric('Khẩn cấp', sum(r['priority_level'] == 'Khẩn cấp' for r in queue), border=True)
    c3.metric('Độ tự tin dưới 60%', sum(r['confidence_score'] < 0.60 for r in queue), border=True)
    c4.metric('Chờ lâu nhất', f'{oldest:.0f} ngày' if oldest >= 1 else f'{oldest * 24:.0f} giờ', border=True)


def _send_result(rid, recipient, reject, notes, final_topic, final_resp, dept, conf):
    if not recipient:
        return f'Đã xử lý {rid}. Sinh viên không để lại email nên kết quả chỉ lưu trên hệ thống.'
    if reject:
        send_resolution_email(recipient, f"[EduSupportAI] Kết quả rà soát yêu cầu {rid}",
                              f"Kính gửi Sinh viên,\n\nYêu cầu {rid} chưa được chấp nhận. Lý do: {notes or 'không phù hợp quy định'}.\n\nTrân trọng,\n{dept}",
                              record_id=rid)
        return f'Đã từ chối {rid} và báo lý do về {recipient}.'
    subject, body = build_resolution_email(rid, final_topic, dept, final_resp, conf, is_auto_approved=False)
    send_resolution_email(recipient, subject, body, record_id=rid)
    return f'Đã duyệt {rid} và gửi kết quả về {recipient}.'


def render_workbench():
    queue = list_requests(pending_only=True, limit=QUEUE_DISPLAY_LIMIT)
    if not queue:
        st.success('Không có yêu cầu nào đang chờ duyệt.')
        return
    _render_queue_metrics(queue, count_pending())

    c_dept, c_prio = st.columns(2)
    dept = c_dept.selectbox('Đơn vị', ['Tất cả'] + sorted({_department(r) for r in queue}), key='wb_filter_dept')
    prio = c_prio.selectbox('Mức ưu tiên', ['Tất cả', 'Khẩn cấp', 'Cao', 'Bình thường', 'Thấp'], key='wb_filter_prio')
    shown = [r for r in queue if (dept == 'Tất cả' or _department(r) == dept) and (prio == 'Tất cả' or r['priority_level'] == prio)]
    if not shown:
        st.info('Không có yêu cầu khớp bộ lọc.')
        return

    st.dataframe(pd.DataFrame([{
        'Mã': r['record_id'], 'Ưu tiên': r['priority_level'], 'Đơn vị': _department(r),
        'Nội dung': r['clean_text'][:90] + ('...' if len(r['clean_text']) > 90 else ''),
    } for r in shown]), hide_index=True, width='stretch', height=min(38 * len(shown) + 38, 280))

    ids = [r['record_id'] for r in shown]
    focus = st.session_state.get('focus_review_id')
    if focus in ids and st.session_state.get('_focused_once') != focus:
        st.session_state['review_id'] = focus
        st.session_state['_focused_once'] = focus
    if st.session_state.get('review_id') not in ids:
        st.session_state['review_id'] = ids[0]
    by_id = {r['record_id']: r for r in shown}
    rid = st.selectbox('Yêu cầu đang xử lý', ids, key='review_id',
                       format_func=lambda k: f"{k} · {by_id[k]['priority_level']} · {by_id[k]['clean_text'][:60]}")
    _render_review(by_id[rid])


def _render_review(item):
    rid = item['record_id']
    item_dept = _department(item)
    badge = PRIORITY_BADGES.get(item['priority_level'], 'badge-normal')
    articles = json.loads(item['articles_json']) if item.get('articles_json') else []
    recipient = get_contact(rid)

    with st.container(border=True):
        st.markdown(f"<span class='{badge}'>{html.escape(item['priority_level'])}</span> &nbsp; "
                    f"<b>{html.escape(item_dept)}</b> &nbsp;·&nbsp; {html.escape(TOPICS.get(item['predicted_topic'], item['predicted_topic']))}"
                    f" &nbsp;·&nbsp; độ tự tin {item['confidence_score']:.0%}", unsafe_allow_html=True)
        st.text_area('Nội dung (đã che thông tin cá nhân)', value=item['clean_text'], disabled=True, key='review_clean_' + rid, height=90)
        st.caption('Chất lượng dữ liệu: ' + describe_flags(item['quality_flags']))
        with st.expander(f'Tài liệu tham chiếu ({len(articles)})'):
            if not articles:
                st.write('Chưa có tài liệu phù hợp; cán bộ đối chiếu quy định thủ công.')
            for article in articles:
                st.markdown(f"**{article['kb_id']} — {article['question_standard']}**")
                st.caption('Nguồn đã xác minh' if article.get('verified') else 'Minh họa, chưa xác minh')
                st.write(article.get('content_extract', '').replace('\n', '  \n'))

        response_key = 'response_' + rid
        if response_key not in st.session_state:
            st.session_state[response_key] = item['draft_response']
        topics = list(TOPICS)
        with st.form('review_form_' + rid, border=False):
            c_topic, c_notes = st.columns([1, 2])
            final_topic = c_topic.selectbox('Nhóm', topics, format_func=lambda t: TOPICS[t], key='topic_' + rid,
                                            index=topics.index(item['predicted_topic']) if item['predicted_topic'] in topics else topics.index('Khac'))
            notes = c_notes.text_input('Ghi chú / lý do từ chối', key='notes_' + rid)
            response = st.text_area('Nội dung trả lời', key=response_key, height=180)
            st.caption(f'Kết quả sẽ gửi về {recipient}.' if recipient else 'Sinh viên không để lại email: kết quả chỉ lưu trên hệ thống.')
            c1, c2, c3 = st.columns(3)
            draft_button = c1.form_submit_button('Lưu nháp', width='stretch')
            approve = c2.form_submit_button('Duyệt và lưu', type='primary', width='stretch')
            reject = c3.form_submit_button('Từ chối', width='stretch')

    if not (draft_button or approve or reject):
        return
    try:
        if draft_button:
            save_draft(rid, response)
            st.session_state.pop('intake_draft_' + rid, None)
            message = f'Đã lưu nháp {rid}.'
        else:
            action = 'reject' if reject else ('edit_label' if final_topic != item['predicted_topic'] else 'approve')
            final_resp = 'Yêu cầu bị từ chối.' if reject else response
            log_review_action(rid, action, item['predicted_topic'], final_topic, final_resp, notes)
            message = _send_result(rid, recipient, reject, notes, final_topic, final_resp, item_dept, item['confidence_score'])
            delete_contact(rid)
        st.session_state['notice'] = message
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
