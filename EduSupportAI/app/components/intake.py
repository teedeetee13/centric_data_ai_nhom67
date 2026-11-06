# -*- coding: utf-8 -*-
"""
Module: app.components.intake
Tab Tiếp nhận yêu cầu: form gửi phản ánh, tự động phê duyệt theo ngưỡng, đính kèm / nạp hàng loạt, email thử nghiệm.
"""

import hashlib
import re

import pandas as pd
import streamlit as st

from src.config import AUTO_APPROVE_CONFIDENCE_THRESHOLD, DEFAULT_TEST_EMAIL, TOPICS
from src.database import get_request, log_review_action, save_request
from src.email_service import build_resolution_email, send_resolution_email

# Danh mục chủ đề và vấn đề cụ thể hiển thị dạng ô tích trong form
TOPIC_CATALOG = {
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


def render_intake_form(service):
    # Chọn chủ đề vấn đề đang gặp phải
    st.markdown('##### Chủ đề phản ánh:')
    selected_topic = st.radio(
        'Chủ đề vấn đề:',
        options=list(TOPIC_CATALOG.keys()),
        horizontal=True,
        key='intake_topic_radio',
        label_visibility='collapsed'
    )

    # Form tiếp nhận chính
    with st.form('intake_form', clear_on_submit=False):
        st.markdown(f"##### Chọn vấn đề cụ thể thuộc [{selected_topic}]:")
        sub_issues = TOPIC_CATALOG[selected_topic]
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

                    # Trích xuất địa chỉ email sinh viên để gửi kết quả giải quyết
                    target_email = in_email.strip()
                    if not target_email:
                        match_mail = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', combined_input)
                        target_email = match_mail.group(1) if match_mail else DEFAULT_TEST_EMAIL

                    # Kiểm tra điều kiện tự động phê duyệt và lưu trữ:
                    # 1. Mức độ chắc chắn của AI đạt hoặc vượt ngưỡng (>= 70%)
                    # 2. Dữ liệu chất lượng hợp lệ (is_usable == True)
                    # 3. Đã tìm thấy căn cứ giải pháp quy chế (matched_kb_id)
                    # 4. Không thuộc diện ưu tiên Khẩn cấp (Khẩn cấp bắt buộc cán bộ xem xét)
                    # 5. Bản nháp không do mô hình ngôn ngữ sinh ra (nội dung sinh luôn qua cán bộ duyệt)
                    is_auto_approved = (
                        result['confidence_score'] >= AUTO_APPROVE_CONFIDENCE_THRESHOLD
                        and bool(result.get('is_usable'))
                        and bool(result.get('matched_kb_id'))
                        and result.get('priority_level') != 'Khẩn cấp'
                        and result.get('draft_source') != 'llm'
                    )

                    if is_auto_approved:
                        log_review_action(
                            record_id=rid,
                            officer_action='approve',
                            original_topic=result['predicted_topic'],
                            final_topic=result['predicted_topic'],
                            final_response=result['draft_response'],
                            notes=f"AI tự động phê duyệt và lưu trữ (Độ tự tin: {result['confidence_score']:.1%})"
                        )
                        subj, body = build_resolution_email(
                            record_id=rid,
                            topic=result['predicted_topic'],
                            department=result['department'],
                            resolution_text=result['draft_response'],
                            confidence_score=result['confidence_score'],
                            is_auto_approved=True
                        )
                        mail_ok, mail_msg = send_resolution_email(
                            recipient_email=target_email,
                            subject=subj,
                            body_text=body,
                            record_id=rid
                        )
                        st.success(
                            f"ĐÃ TỰ ĐỘNG PHÊ DUYỆT & LƯU TRỮ THÀNH CÔNG: Mức độ chắc chắn của AI đạt {result['confidence_score']:.1%}, "
                            f"thuộc thẩm quyền {result['department']} và đã có căn cứ quy chế giải pháp. "
                            f"Hướng giải quyết đã được gửi tự động về email: {target_email}!"
                        )
                    elif result['confidence_score'] < 0.50:
                        st.warning(
                            f"CẢNH BÁO QUẢN TRỊ: Mức độ chắc chắn của mô hình AI dưới 50% ({result['confidence_score']:.1%}) hoặc phản ánh vượt quá khả năng tự động hóa. "
                            f"Yêu cầu {rid} đã được lưu và chuyển tiếp tới Bàn duyệt cán bộ ({result['department']}) / Quản trị viên để xem xét thủ công."
                        )
                    elif result.get('priority_level') == 'Khẩn cấp':
                        st.warning(
                            f"ƯU TIÊN KHẨN CẤP: Yêu cầu {rid} thuộc diện khẩn cấp. "
                            f"Đã lưu và chuyển trực tiếp tới Bàn duyệt cán bộ ({result['department']}) để ưu tiên xử lý trực tiếp."
                        )
                    else:
                        st.info(
                            f"Đã lưu thành công yêu cầu {rid} (Độ tự tin: {result['confidence_score']:.1%}). "
                            f"Hệ thống đã tự động lọc vấn đề và chuyển đến Bàn duyệt cán bộ ({result['department']}) để kiểm tra và phê duyệt."
                        )
                except ValueError as exc:
                    st.error(str(exc))


def render_upload_tools(service):
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


def render_test_email():
    # Địa chỉ nhận thử nghiệm lấy từ biến môi trường DEFAULT_TEST_EMAIL (src/config.py)
    with st.expander(f'Thử nghiệm gửi email giải quyết mẫu tới {DEFAULT_TEST_EMAIL}', expanded=False):
        st.caption('Kiểm tra trực tiếp tính năng tự động gửi email thông báo giải quyết phản ánh học vụ sinh viên.')
        c_tm1, c_tm2 = st.columns([2, 1])
        with c_tm1:
            t_email_dest = st.text_input(
                'Địa chỉ email người nhận thử nghiệm:',
                value=DEFAULT_TEST_EMAIL,
                key='intake_test_email_dest'
            )
        with c_tm2:
            t_topic_sample = st.selectbox(
                'Chủ đề giải pháp mẫu:',
                options=list(TOPICS.keys()),
                format_func=lambda k: TOPICS.get(k, k),
                key='intake_test_topic_select'
            )

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
        st.text_area('Nội dung giải pháp gửi thử nghiệm:', value=chosen_sample_sol, height=85, disabled=True, key='intake_sample_sol_area')

        if st.button('Gửi email giải quyết mẫu tới ' + t_email_dest, type='primary', key='btn_send_sample_email_intake'):
            with st.spinner('Đang tiến hành gửi email thử nghiệm...'):
                from app.components.workbench import DEPT_MAPPING
                t_dept = DEPT_MAPPING.get(t_topic_sample, 'Bộ phận Tiếp nhận')
                subj, body = build_resolution_email(
                    record_id='DEMO_TEST_EMAIL',
                    topic=t_topic_sample,
                    department=t_dept,
                    resolution_text=chosen_sample_sol,
                    confidence_score=0.92,
                    is_auto_approved=True
                )
                ok, send_info = send_resolution_email(
                    recipient_email=t_email_dest,
                    subject=subj,
                    body_text=body,
                    record_id='DEMO_TEST_EMAIL'
                )
                if ok:
                    st.success(send_info)
                    st.markdown(f"""
                    <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-top: 8px;">
                        <div style="font-size: 0.82rem; color: #475569; font-weight: 600;">TIÊU ĐỀ: {subj}</div>
                        <div style="font-size: 0.82rem; color: #475569; margin-top: 4px;">NGƯỜI NHẬN: <strong>{t_email_dest}</strong> | PHƯƠNG THỨC: Tự động phê duyệt bởi AI</div>
                        <pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px; margin-top: 8px; font-size: 0.8rem; white-space: pre-wrap;">{body}</pre>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(send_info)
