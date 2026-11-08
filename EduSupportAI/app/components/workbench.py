# -*- coding: utf-8 -*-
"""
Module: app.components.workbench
Bàn làm việc cán bộ tiếp nhận & kiểm duyệt (Human-in-the-Loop)
Hỗ trợ:
- Bảng danh sách trực quan hàng đợi yêu cầu
- Phân luồng thẩm quyền duyệt theo Đơn vị / Phòng ban chuyên môn
- Tự động hóa giải quyết yêu cầu và gửi email phản hồi về cho người gửi
- Cảnh báo chuyển Quản trị viên khi độ chắc chắn AI dưới 50% hoặc vượt quá khả năng
- Huấn luyện lại mô hình AI (Active Learning) từ nhật ký duyệt
Không emoji - Thiết kế chuẩn Sapphire Academic & Slate.
"""

import html
import json
import pandas as pd
import streamlit as st
from src.config import DEFAULT_TEST_EMAIL, TOPICS, describe_flags, is_production
from src.database import count_pending, delete_contact, get_contact, list_requests, log_review_action, save_draft
from src.email_service import build_resolution_email, send_resolution_email

ALL_TOPICS = list(TOPICS.keys())
TOPIC_VIETNAMESE = TOPICS

# Hàng chờ dài làm chậm trình duyệt; xử lý theo thứ tự ưu tiên nên chỉ cần phần đầu
QUEUE_DISPLAY_LIMIT = 200

DEPT_MAPPING = {
    "Hoc_phi": "Phòng Tài chính - Kế toán",
    "Lich_hoc_lich_thi": "Phòng Đào tạo",
    "Diem_khao_thi": "Phòng Khảo thí & Đảm bảo chất lượng",
    "Thu_tuc_hanh_chinh": "Phòng Công tác sinh viên (Bộ phận Một cửa)",
    "Co_so_vat_chat": "Phòng Hành chính - Nhân sự",
    "He_thong_CNTT": "Trung tâm Công nghệ thông tin",
    "Khac": "Bộ phận Tiếp nhận chung"
}

def load_review_queue():
    return pd.DataFrame(list_requests(pending_only=True))

def render_workbench(faq_engine=None):
    queue = list_requests(pending_only=True, limit=QUEUE_DISPLAY_LIMIT)
    st.subheader('Bàn duyệt cán bộ & Quản lý phân luồng')
    st.caption('Phân quyền duyệt theo đơn vị chuyên môn. Tự động hóa gửi email giải quyết và cảnh báo khi độ tự tin dưới 50%.')
    st.caption(
        'Chú thích: hàng chờ gồm các yêu cầu chưa được tự động duyệt (độ tự tin thấp, khẩn cấp, thiếu thông tin, '
        'hoặc bản nháp do mô hình ngôn ngữ soạn). Cán bộ đọc tài liệu tham chiếu bên phải (mục QTxx là quy trình '
        'từ tài liệu của trường, KBxx là FAQ), sửa bản nháp rồi Duyệt, Đổi nhãn hoặc Từ chối. Mọi thao tác ghi vào nhật ký review_logs.'
    )

    if not queue:
        st.success('Hàng đợi hoàn tất — Không có yêu cầu nào đang chờ duyệt.')
        return

    total_pending = count_pending()
    if total_pending > len(queue):
        st.info(f'Đang hiển thị {len(queue)} yêu cầu ưu tiên cao nhất trong tổng số {total_pending} yêu cầu chờ duyệt.')

    # 1. Bộ lọc thẩm quyền duyệt theo Đơn vị, Mức độ ưu tiên và Ngưỡng tự tin AI
    c_f1, c_f2, c_f3 = st.columns([2, 1, 1], gap="medium")
    with c_f1:
        # Lấy từ chính hàng chờ vì ticket theo quy trình có tên đơn vị riêng, không nằm trong DEPT_MAPPING
        queue_depts = {r.get('department') or DEPT_MAPPING.get(r['predicted_topic'], 'Bộ phận Tiếp nhận chung') for r in queue}
        dept_options = ["Tất cả đơn vị / phòng ban"] + sorted(queue_depts)
        selected_dept = st.selectbox(
            "Đơn vị chuyên môn phụ trách duyệt:",
            options=dept_options,
            key="wb_filter_dept"
        )
    with c_f2:
        prio_options = ["Tất cả mức độ", "Khẩn cấp", "Cao", "Bình thường", "Thấp"]
        selected_prio = st.selectbox(
            "Mức độ ưu tiên:",
            options=prio_options,
            key="wb_filter_prio"
        )
    with c_f3:
        conf_options = ["Tất cả ngưỡng", "Dưới 50% (Cần quản trị xem xét)", "Từ 50% trở lên (Tự động đạt chuẩn)"]
        selected_conf = st.selectbox(
            "Độ tin cậy AI:",
            options=conf_options,
            key="wb_filter_conf"
        )

    # Lọc danh sách hàng đợi theo tiêu chí chọn
    filtered_queue = []
    for r in queue:
        r_dept = r.get('department') or DEPT_MAPPING.get(r['predicted_topic'], 'Bộ phận Tiếp nhận chung')
        if selected_dept != "Tất cả đơn vị / phòng ban" and r_dept != selected_dept:
            continue
        if selected_prio != "Tất cả mức độ" and r['priority_level'] != selected_prio:
            continue
        if selected_conf == "Dưới 50% (Cần quản trị xem xét)" and r['confidence_score'] >= 0.50:
            continue
        if selected_conf == "Từ 50% trở lên (Tự động đạt chuẩn)" and r['confidence_score'] < 0.50:
            continue
        filtered_queue.append(r)

    # Nếu bộ lọc không có phần tử, fallback về toàn bộ queue để đảm bảo tính sẵn sàng
    active_queue = filtered_queue if filtered_queue else queue
    if not filtered_queue and queue:
        st.info("Không có yêu cầu nào khớp chính xác với bộ lọc. Đang hiển thị toàn bộ hàng đợi.")

    # 2. Bảng tổng quan danh sách yêu cầu chờ xử lý
    st.markdown(f"##### Danh sách yêu cầu chờ xử lý ({len(active_queue)} yêu cầu)")
    df_rows = []
    for r in active_queue:
        dept_name = r.get('department') or DEPT_MAPPING.get(r['predicted_topic'], 'Bộ phận Tiếp nhận chung')
        conf_score = r['confidence_score']
        status_label = "Cần quản trị duyệt (< 50%)" if conf_score < 0.50 else ("Khẩn cấp (Ưu tiên)" if r['priority_level'] == 'Khẩn cấp' else "Tự động đạt chuẩn")
        preview_text = (r['clean_text'][:60] + "...") if len(r['clean_text']) > 60 else r['clean_text']
        df_rows.append({
            'Mã yêu cầu': r['record_id'],
            'Đơn vị phụ trách': dept_name,
            'Chuyên môn': TOPICS.get(r['predicted_topic'], r['predicted_topic']),
            'Mức ưu tiên': r['priority_level'],
            'Độ tự tin AI': f"{conf_score:.1%}",
            'Thẩm quyền xử lý': status_label,
            'Nội dung tóm tắt': preview_text
        })
    st.dataframe(pd.DataFrame(df_rows), width='stretch', hide_index=True)

    # 3. Chọn yêu cầu chi tiết để xử lý
    ids = [row['record_id'] for row in active_queue]
    focus = st.session_state.get('focus_review_id')
    if focus in ids and st.session_state.get('_focused_once') != focus:
        st.session_state['review_id'] = focus
        st.session_state['_focused_once'] = focus

    if st.session_state.get('review_id') not in ids:
        st.session_state['review_id'] = ids[0]

    by_id = {row['record_id']: row for row in active_queue}
    rid = st.selectbox(
        'Chọn yêu cầu cần duyệt chi tiết:',
        options=ids,
        key='review_id',
        format_func=lambda k: f"{k} · {by_id[k].get('department') or DEPT_MAPPING.get(by_id[k]['predicted_topic'], 'Bộ phận')} · {TOPICS.get(by_id[k]['predicted_topic'], 'Khác')} · {by_id[k]['priority_level']}"
    )
    item = by_id[rid]
    item_dept = item.get('department') or DEPT_MAPPING.get(item['predicted_topic'], 'Bộ phận Tiếp nhận chung')
    conf = item['confidence_score']

    # 4. Banner phân luồng & Cảnh báo theo ngưỡng chắc chắn 50%
    if conf < 0.50:
        st.warning(
            f"CẢNH BÁO QUẢN TRỊ: Mức độ chắc chắn của mô hình AI dưới 50% ({conf:.1%}) hoặc phản ánh vượt quá khả năng tự động hóa. "
            f"Đã chuyển đến {item_dept} để Cán bộ / Quản trị viên xem xét đối chiếu kỹ lưỡng trước khi phê duyệt!"
        )
    elif item['priority_level'] == 'Khẩn cấp':
        st.warning(
            f"ƯU TIÊN KHẨN CẤP: Phản ánh thuộc diện cấp bách. Yêu cầu Cán bộ {item_dept} xử lý ưu tiên hàng đầu!"
        )
    else:
        st.success(
            f"ĐẠT CHUẨN TỰ ĐỘNG HÓA: Mô hình AI phân loại với độ tin cậy {conf:.1%}, phù hợp quy chế của {item_dept}. "
            "Sẵn sàng gửi hướng giải quyết về email người gửi."
        )

    # Khung tóm tắt Sapphire Academic
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 14px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 0.74rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">MÃ YÊU CẦU: <strong style="color: #0f172a;">{html.escape(rid)}</strong></span>
            <span style="font-size: 0.78rem; font-weight: 600; color: #1d4ed8; background: #eff6ff; padding: 2px 8px; border-radius: 4px;">Độ tự tin: {conf:.1%}</span>
        </div>
        <div style="font-size: 0.88rem; color: #334155;">
            Đơn vị giải quyết: <strong>{html.escape(item_dept)}</strong> | Nhóm chuyên môn: <strong>{html.escape(TOPICS.get(item['predicted_topic'], item['predicted_topic']))}</strong> | Mức độ ưu tiên: <strong>{html.escape(item['priority_level'])}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_detail1, c_detail2 = st.columns([1, 1], gap="medium")
    with c_detail1:
        st.caption('Nội dung phản ánh đã bảo mật (Che PII):')
        st.text_area('Yêu cầu đã che thông tin', value=item['clean_text'], disabled=True, key='review_clean_' + rid, height=120)
        st.caption('Chất lượng dữ liệu: ' + describe_flags(item['quality_flags']))

    with c_detail2:
        st.caption('Tài liệu quy chế tham chiếu đối chiếu:')
        articles = json.loads(item['articles_json']) if item.get('articles_json') else []
        if articles:
            for article in articles:
                with st.expander(f"{article['kb_id']} — {article['question_standard']}"):
                    st.caption('Nguồn đã xác minh' if article.get('verified') else 'Tài liệu minh họa, chưa xác minh')
                    st.write(article.get('content_extract', '').replace('\n', '  \n'))
                    if article.get('source_url'):
                        st.write(f"Nguồn: {article['source_url']}")
        else:
            st.info('Chưa tìm thấy điều khoản quy chế tương ứng. Cán bộ đối chiếu quy định thủ công.')

    # 5. Form phê duyệt và gửi email giải quyết
    topics = list(TOPICS.keys())
    response_key = 'response_' + rid
    if response_key not in st.session_state:
        st.session_state[response_key] = item['draft_response']

    # Nội dung đã che nên email thật nằm ở bảng liên hệ riêng; không có thì không gửi cho ai cả
    recipient_email = get_contact(rid)

    with st.form('review_form_' + rid):
        curr_topic = item['predicted_topic'] if item['predicted_topic'] in topics else 'Khac'
        final_topic = st.selectbox(
            'Nhóm phân loại cuối cùng (Điều chỉnh nếu cần)',
            options=topics,
            index=topics.index(curr_topic),
            format_func=lambda t: f"{TOPICS.get(t, t)} — [{DEPT_MAPPING.get(t, 'Bộ phận Tiếp nhận')}]",
            key='topic_' + rid
        )
        response = st.text_area('Nội dung giải quyết gửi về email người gửi:', key=response_key, height=170)
        notes = st.text_input('Ghi chú xử lý nội bộ:', key='notes_' + rid, placeholder='Nhập ghi chú xử lý hoặc căn cứ giải quyết...')

        st.caption(f"Khi bấm duyệt, kết quả sẽ gửi về email: **{recipient_email}**." if recipient_email
                   else 'Sinh viên không để lại email: kết quả chỉ lưu trên hệ thống, không gửi thư.')
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
                if not recipient_email:
                    message = f'Đã xử lý yêu cầu {rid}. Không có email liên hệ nên kết quả chỉ lưu trên hệ thống.'
                elif reject:
                    send_resolution_email(
                        recipient_email=recipient_email,
                        subject=f"[EduSupportAI] Thông báo kết quả rà soát yêu cầu - {rid}",
                        body_text=f"Kính gửi Sinh viên,\n\nYêu cầu {rid} của bạn đã bị từ chối với lý do: {notes or 'Không phù hợp quy định đào tạo'}.\n\nTrân trọng,\n{item_dept}",
                        record_id=rid
                    )
                    message = f'Đã từ chối yêu cầu {rid}. Thông báo từ chối đã gửi về email: {recipient_email}.'
                else:
                    subj, body = build_resolution_email(
                        record_id=rid,
                        topic=final_topic,
                        department=item_dept,
                        resolution_text=final_resp,
                        confidence_score=conf,
                        is_auto_approved=False
                    )
                    send_resolution_email(
                        recipient_email=recipient_email,
                        subject=subj,
                        body_text=body,
                        record_id=rid
                    )
                    message = f'Đã phê duyệt và gửi giải pháp thành công về email: {recipient_email}. Bản ghi đã rời khỏi hàng đợi.'
            if not draft_button:
                delete_contact(rid)
            st.session_state['notice'] = message
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    if is_production():
        return

    # Công cụ thử nghiệm và huấn luyện lại chỉ có ở chế độ demo
    with st.expander('Thử nghiệm: Gửi bản sao hướng giải quyết', expanded=False):
        st.caption('Gửi bản sao nội dung giải quyết của yêu cầu này tới email thử nghiệm.')
        c_wb_m1, c_wb_m2 = st.columns([3, 1])
        with c_wb_m1:
            wb_test_mail = st.text_input('Email nhận bản sao kiểm thử:', value=DEFAULT_TEST_EMAIL, key='wb_test_mail_input')
        with c_wb_m2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button('Gửi email test', type='secondary', key='btn_wb_send_test', width='stretch'):
                t_subj, t_body = build_resolution_email(
                    record_id=rid,
                    topic=item['predicted_topic'],
                    department=item_dept,
                    resolution_text=st.session_state.get(response_key, item['draft_response']),
                    confidence_score=conf,
                    is_auto_approved=False
                )
                t_ok, t_msg = send_resolution_email(
                    recipient_email=wb_test_mail,
                    subject=t_subj,
                    body_text=t_body,
                    record_id=rid
                )
                if t_ok:
                    st.success(t_msg)
                else:
                    st.error(t_msg)

    # Phân hệ Huấn luyện AI từ dữ liệu cán bộ đã duyệt (Active Learning & Automation)
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    with st.expander('Huấn luyện lại mô hình phân loại', expanded=False):
        st.caption(
            'Huấn luyện lại từ tập train và câu mẫu của kho quy trình. Nhật ký duyệt hiện mới được lưu lại, '
            'chưa được đưa vào dữ liệu huấn luyện; đây là việc của giai đoạn sau.'
        )
        c_tr1, c_tr2 = st.columns([3, 1], gap="medium")
        with c_tr1:
            st.write('Mô hình học máy: **Logistic Regression + TF-IDF (Word & Char n-grams)**.')
            st.caption('Cơ chế cảnh báo: Tự động chuyển quản trị viên khi độ tự tin dưới 50% hoặc không tìm thấy quy chế phù hợp.')
        with c_tr2:
            if st.button('Huấn luyện lại AI ngay', type='primary', key='btn_retrain_ai_workbench', width='stretch'):
                with st.spinner('Đang huấn luyện lại mô hình AI...'):
                    from src.model import train_and_save_production_model
                    train_and_save_production_model()
                    st.success('Đã huấn luyện lại mô hình phân loại.')
