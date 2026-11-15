# -*- coding: utf-8 -*-
"""
Module: app.components.workbench
Bàn làm việc cán bộ tiếp nhận & kiểm duyệt (Human-in-the-Loop)
Thiết kế theo chuẩn SaaS Split-View (Linear / Zendesk / Front):
- Cột trái: Hàng đợi tiếp nhận (Ticket Inbox Feed) + Tìm kiếm & Lọc nhanh
- Cột phải: Bàn làm việc tập trung (Focus Workspace) - Xem hồ sơ, AI Copilot, Soạn & Duyệt giải pháp
Loại bỏ hoàn toàn các yếu tố thừa và cuộn trang không cần thiết.
"""

import html
import importlib
import json
import re
import pandas as pd
import streamlit as st

from src.config import TOPICS, describe_flags
try:
    from src.config import DEFAULT_TEST_EMAIL
except ImportError:
    import os
    DEFAULT_TEST_EMAIL = os.environ.get("DEFAULT_TEST_EMAIL", "kennysk114239@gmail.com")

from src.database import list_requests, log_review_action, save_draft, get_request
try:
    from src.database import format_datetime_vn
except ImportError:
    def format_datetime_vn(val, fmt='%Y-%m-%d %H:%M:%S'):
        if not val:
            return "-"
        val = str(val).strip()
        try:
            from datetime import datetime
            if 'T' in val or '+' in val or val.endswith('Z'):
                clean_iso = val.replace('Z', '+00:00')
                dt = datetime.fromisoformat(clean_iso)
                if dt.tzinfo is not None:
                    dt = dt.astimezone()
                return dt.strftime(fmt)
            else:
                return val[:19]
        except Exception:
            return val.replace('T', ' ')[:19]

import src.email_service as email_mod
try:
    importlib.reload(email_mod)
except Exception:
    pass

try:
    from src.email_service import (
        build_resolution_email,
        build_rich_resolution_email,
        build_rejection_email,
        send_resolution_email,
        get_smtp_config,
        save_smtp_credentials,
        test_smtp_connection
    )
except ImportError:
    importlib.reload(email_mod)
    from src.email_service import (
        build_resolution_email,
        build_rich_resolution_email,
        build_rejection_email,
        send_resolution_email,
        get_smtp_config,
        save_smtp_credentials,
        test_smtp_connection
    )

from src.library_service import extract_student_id_from_text

try:
    from src.cleaner import parse_student_feedback
except ImportError:
    try:
        import src.cleaner
        importlib.reload(src.cleaner)
        from src.cleaner import parse_student_feedback
    except Exception:
        def parse_student_feedback(raw_text: str) -> dict:
            import re
            if not isinstance(raw_text, str) or not raw_text.strip():
                return {"issue": "", "contacts": "", "student_message": ""}
            content = raw_text.strip()
            issue = ""
            contacts = ""
            m_contact = re.search(r'Thông tin liên hệ:\s*(.+)$', content, re.IGNORECASE | re.DOTALL)
            if m_contact:
                contacts = m_contact.group(1).strip()
                content = content[:m_contact.start()].strip()
            m_issue = re.search(r'Vấn đề ghi nhận:\s*([^.\n]+(?:\.[^.\n]+)*?)(?:\.\s*|\n|$)', content, re.IGNORECASE)
            if m_issue:
                issue = m_issue.group(1).strip()
                content = content[m_issue.end():].strip()
            student_msg = content.strip(' .;\n')
            if not student_msg and issue:
                student_msg = issue
            elif not student_msg:
                student_msg = raw_text.strip()
            return {"issue": issue, "contacts": contacts, "student_message": student_msg}

try:
    from src.app_logger import app_log
except ImportError:
    def app_log(*args, **kwargs):
        pass

ALL_TOPICS = list(TOPICS.keys())
TOPIC_VIETNAMESE = TOPICS

CORE_DOCX_TOPICS = ["Co_so_vat_chat", "Thu_tuc_hanh_chinh", "Lich_hoc_lich_thi", "Diem_khao_thi", "Hoc_phi", "He_thong_CNTT", "Khac"]

DEPT_DOCX_MAPPING = {
    "Co_so_vat_chat": "Phòng Quản trị Cơ sở vật chất",
    "Thu_tuc_hanh_chinh": "Phòng Công tác sinh viên",
    "Lich_hoc_lich_thi": "Phòng Quản lý Đào tạo & Khảo thí",
    "Diem_khao_thi": "Phòng Quản lý Đào tạo & Khảo thí",
    "Hoc_phi": "Phòng Công tác sinh viên",
    "He_thong_CNTT": "Phòng Quản trị Cơ sở vật chất",
    "Khac": "Phòng Công tác sinh viên"
}
DEPT_MAPPING = DEPT_DOCX_MAPPING

def get_dept_name(topic: str, explicit_dept: str = None) -> str:
    """Chuẩn hóa tên đơn vị thụ lý theo 3 chuyên môn của 3 file DOCX."""
    if explicit_dept and explicit_dept not in ["", "Bộ phận Tiếp nhận chung", "Bộ phận Tiếp nhận"]:
        ed_lower = explicit_dept.lower()
        if any(k in ed_lower for k in ["cơ sở vật chất", "csvc", "thư viện", "ký túc xá", "giảng đường", "hội trường", "máy chiếu", "điều hòa"]):
            return "Phòng Quản trị Cơ sở vật chất"
        if any(k in ed_lower for k in ["sinh viên", "một cửa", "ctsv", "chính sách", "học phí", "tài chính", "kế toán"]):
            return "Phòng Công tác sinh viên"
        if any(k in ed_lower for k in ["đào tạo", "khảo thí", "học phần", "lịch thi", "tốt nghiệp", "điểm thi", "phúc khảo"]):
            return "Phòng Quản lý Đào tạo & Khảo thí"
        return explicit_dept
    return DEPT_DOCX_MAPPING.get(topic, "Phòng Quản lý Đào tạo & Khảo thí")

def render_workbench(faq_engine=None):
    recent_rid = st.session_state.get('last_record_id') or st.session_state.get('focus_review_id')

    # Nạp danh sách yêu cầu
    all_requests = list_requests(pending_only=False)
    if not all_requests:
        st.success('Hàng đợi hoàn tất — Hiện không có yêu cầu nào trong hệ thống.')
        return

    # Khung bố cục Master - Detail (Split-View 2 cột chuẩn SaaS)
    col_queue, col_detail = st.columns([4.2, 7.8], gap="large")

    # =========================================================================
    # CỘT TRÁI: HÀNG ĐỢI TIẾP NHẬN (TICKET INBOX)
    # =========================================================================
    with col_queue:
        st.markdown("##### 📋 Hàng đợi tiếp nhận")

        # 1. Bộ lọc trạng thái nhanh
        filter_status = st.radio(
            "Lọc trạng thái:",
            options=["Chờ duyệt", "Khẩn cấp", "Đã duyệt (AI)", "Tất cả"],
            horizontal=True,
            key="wb_quick_status",
            label_visibility="collapsed"
        )

        # 2. Bộ lọc đơn vị & Tìm kiếm nhanh
        c_qf1, c_qf2 = st.columns([1, 1], gap="small")
        with c_qf1:
            dept_opts = [
                "Tất cả phòng ban",
                "Phòng Đào tạo",
                "Phòng Quản lý Đào tạo & Khảo thí",
                "Phòng Tài chính - Kế toán",
                "Phòng Công tác sinh viên",
                "Phòng Quản trị Cơ sở vật chất",
                "Trung tâm Công nghệ thông tin"
            ]
            selected_dept = st.selectbox("Lọc phòng ban:", options=dept_opts, key="wb_filter_dept", label_visibility="collapsed")
        with c_qf2:
            search_query = st.text_input("Tìm kiếm:", placeholder="Mã phiếu, từ khóa...", key="wb_search_query", label_visibility="collapsed")

        # Áp dụng bộ lọc
        queue = all_requests
        if filter_status == "Chờ duyệt":
            queue = [r for r in queue if r.get('status') == 'pending_review']
        elif filter_status == "Khẩn cấp":
            queue = [r for r in queue if r.get('priority_level') == 'Khẩn cấp']
        elif filter_status == "Đã duyệt (AI)":
            queue = [r for r in queue if r.get('status') == 'reviewed_approve']

        if selected_dept != "Tất cả phòng ban":
            sel_lower = selected_dept.lower()
            queue = [r for r in queue if sel_lower in (r.get('department') or '').lower() or sel_lower in get_dept_name(r['predicted_topic'], r.get('department')).lower()]

        if search_query.strip():
            sq = search_query.strip().lower()
            queue = [r for r in queue if sq in r['record_id'].lower() or sq in r['clean_text'].lower()]

        # Luôn bảo toàn yêu cầu vừa nạp trong phiên xuất hiện ngay trên bảng
        if recent_rid and not any(r['record_id'] == recent_rid for r in queue):
            recent_req = get_request(recent_rid)
            if recent_req:
                queue.insert(0, recent_req)

        if not queue:
            st.info("Không có yêu cầu nào phù hợp với bộ lọc đã chọn.")
            return

        ids = [row['record_id'] for row in queue]
        by_id = {row['record_id']: row for row in queue}

        # Quản lý ID đang chọn duyệt
        focus = st.session_state.get('focus_review_id')
        if focus in ids and st.session_state.get('_focused_once') != focus:
            st.session_state['review_id'] = focus
            st.session_state['_focused_once'] = focus

        if st.session_state.get('review_id') not in ids:
            st.session_state['review_id'] = ids[0]

        curr_id = st.session_state['review_id']
        st.caption(f"Tổng cộng: **{len(queue)}** yêu cầu &nbsp;|&nbsp; Đang xem: **{curr_id}**")

        # Bảng tóm tắt danh sách yêu cầu
        df_rows = []
        for r in queue:
            prio = r['priority_level']
            prio_badge = "🔴 Khẩn cấp" if prio == "Khẩn cấp" else ("🟠 Cao" if prio == "Cao" else "🔵 Bình thường")
            parsed_txt = parse_student_feedback(r['clean_text'])['student_message']
            snip = (parsed_txt[:36] + "...") if len(parsed_txt) > 36 else parsed_txt
            df_rows.append({
                'Mã phiếu': r['record_id'],
                'Ưu tiên': prio_badge,
                'Chuyên môn': TOPICS.get(r['predicted_topic'], r['predicted_topic']),
                'Tóm tắt phản ánh': snip
            })

        tbl_event = st.dataframe(
            pd.DataFrame(df_rows),
            height=540,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="wb_queue_table"
        )

        selected_rows = []
        if tbl_event and hasattr(tbl_event, 'selection') and tbl_event.selection:
            selected_rows = tbl_event.selection.get('rows', []) if isinstance(tbl_event.selection, dict) else getattr(tbl_event.selection, 'rows', [])

        last_tbl_row = st.session_state.get('_last_wb_tbl_row')
        if selected_rows:
            clicked_idx = selected_rows[0]
            if clicked_idx != last_tbl_row:
                st.session_state['_last_wb_tbl_row'] = clicked_idx
                if 0 <= clicked_idx < len(ids):
                    clicked_rid = ids[clicked_idx]
                    if clicked_rid != st.session_state.get('review_id'):
                        st.session_state['review_id'] = clicked_rid
                        st.rerun()

        # Cho phép đổi phiếu nhanh bằng menu nếu không click bảng
        rid = st.selectbox(
            "Chọn mã hồ sơ cần xem:",
            options=ids,
            index=ids.index(st.session_state['review_id']) if st.session_state.get('review_id') in ids else 0,
            key="review_id",
            label_visibility="collapsed"
        )

    # =========================================================================
    # CỘT PHẢI: BÀN LÀM VIỆC TẬP TRUNG (FOCUS WORKSPACE)
    # =========================================================================
    with col_detail:
        rid = st.session_state['review_id']
        item = by_id[rid]
        item_dept = get_dept_name(item['predicted_topic'], item.get('department'))
        conf = item['confidence_score']
        prio = item['priority_level']
        topics = ALL_TOPICS

        # 1. Header Card hồ sơ chi tiết
        prio_color = "#dc2626" if prio == "Khẩn cấp" else ("#ea580c" if prio == "Cao" else "#2563eb")
        prio_bg = "#fef2f2" if prio == "Khẩn cấp" else ("#fff7ed" if prio == "Cao" else "#eff6ff")

        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 0.82rem; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.04em;">HỒ SƠ HỌC VỤ: <strong>{rid}</strong></span>
                <div style="display: flex; gap: 6px;">
                    <span style="background: {prio_bg}; color: {prio_color}; border: 1px solid {prio_color}33; font-size: 0.74rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">{prio}</span>
                    <span style="background: #f1f5f9; color: #334155; font-size: 0.74rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px;">Độ tin cậy: {conf:.1%}</span>
                </div>
            </div>
            <div style="font-size: 0.84rem; color: #475569;">
                Đơn vị phụ trách: <strong style="color:#0f172a;">{item_dept}</strong> &nbsp;|&nbsp; 
                Chuyên môn: <strong style="color:#0f172a;">{TOPICS.get(item['predicted_topic'], item['predicted_topic'])}</strong> &nbsp;|&nbsp; 
                Ngày gửi: {format_datetime_vn(item.get('processed_at'), fmt='%d/%m/%Y %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Nội dung phản ánh từ sinh viên
        parsed_f = parse_student_feedback(item['clean_text'])
        student_msg = parsed_f['student_message']
        issue_recorded = parsed_f['issue']
        contacts_recorded = parsed_f['contacts']

        st.markdown(f"""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px;">
            <div style="font-size: 0.74rem; font-weight: 700; color: #1e40af; text-transform: uppercase; margin-bottom: 4px;">Nội dung phản ánh từ sinh viên:</div>
            <div style="font-size: 0.92rem; color: #1e293b; line-height: 1.55; white-space: pre-wrap; font-weight: 500;">{html.escape(student_msg)}</div>
            <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; font-size: 0.78rem;">
                {f'<span style="background:#ffffff; border:1px solid #cbd5e1; padding:2px 8px; border-radius:4px; color:#334155;">👤 {contacts_recorded}</span>' if contacts_recorded else ''}
                {f'<span style="background:#ffffff; border:1px solid #cbd5e1; padding:2px 8px; border-radius:4px; color:#334155;">📌 {issue_recorded}</span>' if issue_recorded and issue_recorded != student_msg else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. AI Copilot: Căn cứ quy chế & Thời hạn cam kết (SLA)
        from src.local_machine import get_local_machine
        lm = get_local_machine()
        matched_procs = lm.retrieve_procedure(item['clean_text'], predicted_topic=item['predicted_topic'], top_k=1)
        if matched_procs:
            proc = matched_procs[0]
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.72rem; font-weight: 700; color: #15803d; text-transform: uppercase;">Căn cứ quy chế EAUT:</span>
                    <span style="font-size: 0.74rem; color: #166534; font-weight: 600;">SLA: {proc.get('processing_time', '24 - 48 giờ')}</span>
                </div>
                <div style="font-size: 0.88rem; font-weight: 700; color: #0f172a; margin-top: 2px;">[{proc['proc_id']}] {proc['title']}</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander(f"Chi tiết quy trình & Biểu mẫu [{proc['proc_id']}]", expanded=False):
                st.caption(f"Căn cứ pháp lý: {proc.get('legal_basis')} | Biểu mẫu: {proc.get('forms_required')}")
                for s in proc.get('steps', []):
                    st.write(f"• **Bước {s.get('step')} ({s.get('actor')}):** {s.get('action')}")

        # 4. Soạn thảo văn bản phản hồi & Duyệt
        response_key = 'response_' + rid
        saved_draft = item.get('draft_response', '').strip()
        if (
            response_key not in st.session_state
            or not st.session_state[response_key]
            or "[CHẨN ĐOÁN VẤN ĐỀ" in str(st.session_state.get(response_key, ''))
            or "Trình tự các bước thực hiện:" in str(st.session_state.get(response_key, ''))
        ):
            if not saved_draft or "[CHẨN ĐOÁN VẤN ĐỀ" in saved_draft or "Trình tự các bước thực hiện:" in saved_draft:
                matched_p = matched_procs[0] if matched_procs else None
                _, fresh_draft = lm.reason_and_synthesize(item['clean_text'], item['predicted_topic'], matched_p)
                st.session_state[response_key] = fresh_draft
            else:
                st.session_state[response_key] = saved_draft

        email_match = re.search(r'email[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', item['clean_text'], re.IGNORECASE)
        recipient_email = email_match.group(1) if email_match else ("sinhvien.eaut@student.edu.vn" if "[EMAIL]" in item['clean_text'] else "sinhvien@eaut.edu.vn")

        with st.form('review_form_' + rid):
            curr_topic = item['predicted_topic'] if item['predicted_topic'] in topics else topics[0]
            final_topic = st.selectbox(
                'Nhóm phân loại cuối cùng:',
                options=topics,
                index=topics.index(curr_topic),
                format_func=lambda t: f"{TOPICS.get(t, t)} — [{get_dept_name(t)}]",
                key='topic_' + rid
            )
            response = st.text_area('Văn bản giải quyết gửi sinh viên:', key=response_key, height=140)
            notes = st.text_input('Ghi chú nội bộ:', key='notes_' + rid, placeholder='Nhập ghi chú xử lý nội bộ (nếu có)...')

            c_rf_m1, c_rf_m2 = st.columns([3, 2])
            with c_rf_m1:
                send_to_email = st.text_input('Email người nhận:', value=recipient_email, key='send_to_email_' + rid)
            with c_rf_m2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                cc_test_mail = st.checkbox(f'Bản sao CC tới {DEFAULT_TEST_EMAIL}', value=True, key='cc_test_' + rid)

            c1, c2, c3 = st.columns([2, 1, 1])
            approve = c1.form_submit_button('Duyệt và lưu', type='primary', width='stretch')
            draft_button = c2.form_submit_button('Lưu nháp', width='stretch')
            reject = c3.form_submit_button('Từ chối', width='stretch')

        if draft_button or approve or reject:
            try:
                if draft_button:
                    save_draft(rid, response)
                    st.session_state.pop('intake_draft_' + rid, None)
                    message = f'Đã lưu nháp cho hồ sơ {rid}.'
                else:
                    action = 'reject' if reject else ('edit_label' if final_topic != item['predicted_topic'] else 'approve')
                    final_resp = 'Yêu cầu bị từ chối.' if reject else response
                    log_review_action(rid, action, item['predicted_topic'], final_topic, final_resp, notes)
                    target_dest = send_to_email.strip() if send_to_email and send_to_email.strip() else recipient_email

                    if reject:
                        r_subj, r_plain, r_html = build_rejection_email(
                            record_id=rid,
                            topic=item['predicted_topic'],
                            department=item_dept,
                            reason_notes=notes or 'Chưa đủ điều kiện thụ lý hoặc không phù hợp quy định đào tạo.',
                            student_id=extract_student_id_from_text(item['clean_text'])
                        )
                        ok_send, send_msg = send_resolution_email(
                            recipient_email=target_dest,
                            subject=r_subj,
                            body_text=r_plain,
                            body_html=r_html,
                            record_id=rid
                        )
                        if cc_test_mail and target_dest != DEFAULT_TEST_EMAIL:
                            send_resolution_email(
                                recipient_email=DEFAULT_TEST_EMAIL,
                                subject=f"[Bản sao kiểm thử] {r_subj}",
                                body_text=r_plain,
                                body_html=r_html,
                                record_id=rid
                            )
                        message = f'Đã từ chối yêu cầu {rid}. {send_msg}'
                    else:
                        s_subj, s_plain, s_html = build_rich_resolution_email(
                            record_id=rid,
                            topic=final_topic,
                            department=item_dept,
                            resolution_text=final_resp,
                            confidence_score=conf,
                            is_auto_approved=False,
                            student_id=extract_student_id_from_text(item['clean_text']),
                            officer_notes=notes or None
                        )
                        ok_send, send_msg = send_resolution_email(
                            recipient_email=target_dest,
                            subject=s_subj,
                            body_text=s_plain,
                            body_html=s_html,
                            record_id=rid
                        )
                        if cc_test_mail and target_dest != DEFAULT_TEST_EMAIL:
                            send_resolution_email(
                                recipient_email=DEFAULT_TEST_EMAIL,
                                subject=f"[Bản sao kiểm thử] {s_subj}",
                                body_text=s_plain,
                                body_html=s_html,
                                record_id=rid
                            )
                        message = f'Đã phê duyệt và lưu hồ sơ {rid}. {send_msg}'

                st.session_state['notice'] = message
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        # 5. Tiện ích bổ trợ (gọn gàng, ẩn mặc định)
        with st.expander("👁️ Xem trước giao diện Email sẽ gửi (HTML)", expanded=False):
            pv_subj, pv_plain, pv_html = build_rich_resolution_email(
                record_id=rid,
                topic=st.session_state.get('topic_' + rid, item['predicted_topic']),
                department=item_dept,
                resolution_text=st.session_state.get(response_key, item['draft_response']),
                confidence_score=conf,
                is_auto_approved=False,
                student_id=extract_student_id_from_text(item['clean_text']),
                officer_notes=st.session_state.get('notes_' + rid, '')
            )
            st.caption(f"Tiêu đề: **{pv_subj}** | Người nhận: **{send_to_email}**")
            st.components.v1.html(pv_html, height=420, scrolling=True)

        with st.expander("🔬 Vết thực thi & Nhật ký suy luận AI", expanded=False):
            from src.database import get_execution_trace
            from app.components.trace_viewer import render_trace_view
            trace_rec = get_execution_trace(rid)
            t_data = None
            t_log = ""
            if trace_rec and trace_rec.get('steps_json'):
                try:
                    t_data = json.loads(trace_rec['steps_json']) if isinstance(trace_rec['steps_json'], str) else trace_rec['steps_json']
                    t_log = trace_rec.get('terminal_log', '')
                except Exception:
                    t_data = None
            if not t_data:
                res_t = lm.process_request_with_trace(item['clean_text'], record_id=rid)
                t_data = res_t.get('execution_trace', {})
                t_log = res_t.get('terminal_log', '')
            render_trace_view(t_data, t_log, rid)
