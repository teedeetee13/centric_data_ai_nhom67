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
import importlib
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
        import importlib
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

# 3 Nhóm chuyên môn chính thức của 3 tài liệu trong thư mục data-doc/
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
    st.subheader('Bàn duyệt cán bộ & Quản lý phân luồng')
    st.caption('Phân quyền duyệt theo đơn vị chuyên môn. Tự động hóa gửi email giải quyết và cảnh báo khi độ tự tin dưới 50%.')

    recent_rid = st.session_state.get('last_record_id') or st.session_state.get('focus_review_id')

    # 1. Bộ lọc thẩm quyền duyệt theo Đơn vị, Trạng thái, Mức độ ưu tiên, Ngưỡng tự tin AI và Thứ tự ngày đăng
    c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns([1.4, 1.1, 1, 1, 1.1], gap="small")
    with c_f1:
        dept_options = [
            "Tất cả đơn vị / phòng ban",
            "Phòng Đào tạo",
            "Phòng Quản lý Đào tạo & Khảo thí",
            "Phòng Tài chính - Kế toán",
            "Phòng Công tác sinh viên",
            "Phòng Quản trị Cơ sở vật chất",
            "Trung tâm Công nghệ thông tin"
        ]
        selected_dept = st.selectbox(
            "Đơn vị chuyên môn phụ trách duyệt:",
            options=dept_options,
            key="wb_filter_dept"
        )
    with c_f2:
        view_options = ["Tất cả yêu cầu", "Chờ cán bộ duyệt", "Đã tự động duyệt (AI)"]
        selected_view = st.selectbox(
            "Trạng thái xử lý:",
            options=view_options,
            key="wb_filter_view"
        )
    with c_f3:
        prio_options = ["Tất cả mức độ", "Khẩn cấp", "Cao", "Bình thường", "Thấp"]
        selected_prio = st.selectbox(
            "Mức độ ưu tiên:",
            options=prio_options,
            key="wb_filter_prio"
        )
    with c_f4:
        conf_options = ["Tất cả ngưỡng", "Dưới 50% (Cần quản trị xem xét)", "Từ 50% trở lên (Tự động đạt chuẩn)"]
        selected_conf = st.selectbox(
            "Độ tin cậy AI:",
            options=conf_options,
            key="wb_filter_conf"
        )
    with c_f5:
        sort_options = ["Ngày đăng mới nhất", "Ngày đăng cũ nhất", "Theo mức ưu tiên"]
        selected_sort = st.selectbox(
            "Thứ tự sắp xếp:",
            options=sort_options,
            key="wb_filter_sort"
        )

    # Nạp danh sách yêu cầu: Mặc định nạp toàn bộ để bảo đảm mọi yêu cầu vừa nạp (kể cả tự động duyệt) đều hiển thị
    all_requests = list_requests(pending_only=False)
    if selected_view == "Chờ cán bộ duyệt":
        queue = [r for r in all_requests if r.get('status') == 'pending_review']
    elif selected_view == "Đã tự động duyệt (AI)":
        queue = [r for r in all_requests if r.get('status') == 'reviewed_approve']
    else:
        queue = all_requests

    # Luôn bảo toàn yêu cầu vừa nạp trong phiên xuất hiện ngay trên bảng
    if recent_rid and not any(r['record_id'] == recent_rid for r in queue):
        recent_req = get_request(recent_rid)
        if recent_req:
            queue.insert(0, recent_req)

    if not queue:
        st.success('Hàng đợi hoàn tất — Không có yêu cầu nào phù hợp tiêu chí.')
        return

    filtered_queue = []
    for r in queue:
        # Luôn bảo toàn yêu cầu vừa gửi để hiển thị ngay trên bảng cho người dùng
        if recent_rid and r['record_id'] == recent_rid:
            filtered_queue.append(r)
            continue

        if selected_dept not in ["Tất cả đơn vị / phòng ban", "Tất cả đơn vị chuyên môn", "Toàn bộ đơn vị"]:
            r_actual = (r.get('department') or '').lower()
            r_norm = get_dept_name(r['predicted_topic'], r.get('department')).lower()
            sel_lower = selected_dept.lower()
            if sel_lower not in r_actual and sel_lower not in r_norm and r_actual not in sel_lower:
                continue

        if selected_prio != "Tất cả mức độ" and r['priority_level'] != selected_prio:
            continue
        if selected_conf == "Dưới 50% (Cần quản trị xem xét)" and r['confidence_score'] >= 0.50:
            continue
        if selected_conf == "Từ 50% trở lên (Tự động đạt chuẩn)" and r['confidence_score'] < 0.50:
            continue
        filtered_queue.append(r)

    # Nếu bộ lọc không có phần tử, fallback về queue để đảm bảo tính sẵn sàng
    active_queue = filtered_queue if filtered_queue else queue
    if not filtered_queue and queue:
        st.info("Không có yêu cầu nào khớp chính xác với bộ lọc. Đang hiển thị toàn bộ hàng đợi chuyên môn.")

    # Sắp xếp danh sách hàng đợi theo tiêu chí (mặc định: Ngày đăng mới nhất)
    if selected_sort == "Ngày đăng cũ nhất":
        active_queue = sorted(active_queue, key=lambda x: (x.get('processed_at') or '', x.get('id', 0)))
    elif selected_sort == "Theo mức ưu tiên":
        prio_rank = {'Khẩn cấp': 1, 'Cao': 2, 'Bình thường': 3, 'Thấp': 4}
        active_queue = sorted(active_queue, key=lambda x: (prio_rank.get(x.get('priority_level'), 5), x.get('processed_at') or ''), reverse=False)
    else:  # "Ngày đăng mới nhất" (mặc định)
        active_queue = sorted(active_queue, key=lambda x: (x.get('processed_at') or '', x.get('id', 0)), reverse=True)

    # 2. Bảng tổng quan danh sách yêu cầu
    st.markdown(f"##### Danh sách yêu cầu học vụ ({len(active_queue)} yêu cầu)")
    st.caption("👆 **Bấm chọn trực tiếp một dòng trong bảng** để mở hồ sơ duyệt chi tiết bên dưới.")

    ids = [row['record_id'] for row in active_queue]
    focus = st.session_state.get('focus_review_id')
    if focus in ids and st.session_state.get('_focused_once') != focus:
        st.session_state['review_id'] = focus
        st.session_state['_focused_once'] = focus

    if st.session_state.get('review_id') not in ids:
        st.session_state['review_id'] = ids[0]

    by_id = {row['record_id']: row for row in active_queue}

    df_rows = []
    for r in active_queue:
        dept_name = get_dept_name(r['predicted_topic'], r.get('department'))
        conf_score = r['confidence_score']
        if r.get('status') == 'reviewed_approve':
            status_label = "Đã tự động duyệt (AI)"
        elif r.get('status') == 'reviewed_reject':
            status_label = "Đã từ chối"
        elif conf_score < 0.50:
            status_label = "Cần quản trị duyệt (< 50%)"
        elif r['priority_level'] == 'Khẩn cấp':
            status_label = "Khẩn cấp (Ưu tiên)"
        else:
            status_label = "Chờ cán bộ duyệt"
        parsed_preview = parse_student_feedback(r['clean_text'])['student_message']
        preview_text = (parsed_preview[:60] + "...") if len(parsed_preview) > 60 else parsed_preview
        date_str = format_datetime_vn(r.get('processed_at'))
        df_rows.append({
            'Mã yêu cầu': r['record_id'],
            'Ngày đăng': date_str,
            'Đơn vị phụ trách': dept_name,
            'Chuyên môn': TOPICS.get(r['predicted_topic'], r['predicted_topic']),
            'Mức ưu tiên': r['priority_level'],
            'Độ tự tin AI': f"{conf_score:.1%}",
            'Thẩm quyền xử lý': status_label,
            'Nội dung tóm tắt': preview_text
        })

    tbl_event = st.dataframe(
        pd.DataFrame(df_rows),
        width='stretch',
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
                    app_log("WORKBENCH", "Cán bộ chọn dòng trên bảng để xem chi tiết", f"Vị trí: [{clicked_idx}], Mã: [{clicked_rid}]")
                    st.session_state['review_id'] = clicked_rid
                    st.rerun()

    # 3. Chọn yêu cầu chi tiết để xử lý
    current_rid = st.session_state.get('review_id')
    current_idx = ids.index(current_rid) if current_rid in ids else 0
    rid = st.selectbox(
        'Yêu cầu đang chọn duyệt chi tiết (Bấm trực tiếp trên bảng hoặc chọn tại đây):',
        options=ids,
        index=current_idx,
        key='review_id',
        format_func=lambda k: f"{k} · {format_datetime_vn(by_id[k].get('processed_at'), fmt='%Y-%m-%d %H:%M')} · {get_dept_name(by_id[k]['predicted_topic'], by_id[k].get('department'))} · {TOPICS.get(by_id[k]['predicted_topic'], 'Khác')} · {by_id[k]['priority_level']}"
    )
    st.session_state['_last_wb_tbl_row'] = ids.index(rid) if rid in ids else None
    item = by_id[rid]
    item_dept = get_dept_name(item['predicted_topic'], item.get('department'))
    conf = item['confidence_score']

    # 4. Banner phân luồng & Cảnh báo theo ngưỡng chắc chắn 50%
    if item.get('status') == 'reviewed_approve':
        st.success(
            f"ĐÃ TỰ ĐỘNG PHÊ DUYỆT (AI): Yêu cầu {rid} đã được mô hình AI đối soát chuẩn quy chế và tự động hoàn tất (Độ tin cậy: {conf:.1%}). "
            f"Đơn vị chủ trì: {item_dept}. Cán bộ có thể đối chiếu hồ sơ hoặc hiệu chỉnh lại văn bản giải quyết bên dưới nếu cần."
        )
    elif conf < 0.50:
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
            <span style="font-size: 0.74rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">MÃ YÊU CẦU: <strong style="color: #0f172a;">{rid}</strong></span>
            <span style="font-size: 0.78rem; font-weight: 600; color: #1d4ed8; background: #eff6ff; padding: 2px 8px; border-radius: 4px;">Độ tự tin: {conf:.1%}</span>
        </div>
        <div style="font-size: 0.88rem; color: #334155;">
            Đơn vị giải quyết: <strong>{item_dept}</strong> | Nhóm chuyên môn: <strong>{TOPICS.get(item['predicted_topic'], item['predicted_topic'])}</strong> | Mức độ ưu tiên: <strong>{item['priority_level']}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_detail1, c_detail2 = st.columns([1, 1], gap="medium")
    with c_detail1:
        st.caption('Nội dung phản ánh chi tiết từ sinh viên:')
        parsed_f = parse_student_feedback(item['clean_text'])
        student_msg = parsed_f['student_message']
        issue_recorded = parsed_f['issue']
        contacts_recorded = parsed_f['contacts']

        st.text_area('Nội dung phản ánh', value=student_msg, disabled=True, key='review_clean_' + rid, height=110)

        meta_badges = []
        if issue_recorded and issue_recorded != student_msg:
            meta_badges.append(f"<span style='background:#f1f5f9; color:#0f172a; padding:3px 8px; border-radius:4px; font-size:0.78rem; font-weight:600;'>📌 Vấn đề: {issue_recorded}</span>")
        if contacts_recorded:
            meta_badges.append(f"<span style='background:#eff6ff; color:#1e40af; padding:3px 8px; border-radius:4px; font-size:0.78rem;'>👤 {contacts_recorded}</span>")
        if meta_badges:
            st.markdown(f"<div style='margin-top: -4px; margin-bottom: 6px; display:flex; flex-wrap:wrap; gap:6px;'>{''.join(meta_badges)}</div>", unsafe_allow_html=True)

        st.caption('Chất lượng dữ liệu: ' + describe_flags(item['quality_flags']))

    with c_detail2:
        st.caption('Tài liệu quy chế & Quy trình tham chiếu đối chiếu:')
        from src.local_machine import get_local_machine
        lm = get_local_machine()
        matched_procs = lm.retrieve_procedure(item['clean_text'], predicted_topic=item['predicted_topic'], top_k=1)
        if matched_procs:
            proc = matched_procs[0]
            doc_file = "baocao-quanly-csvc-eaut.docx" if "CSVC" in proc['proc_id'] else ("bao_cao_quy_trinh_nghiep_vu_sinh_vien_eaut.docx" if "CTSV" in proc['proc_id'] else "bao_cao_tong_hop_quy_trinh_dao_tao.docx")
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #15803d; text-transform: uppercase;">Căn cứ quy trình chính thức (Nguồn: {doc_file})</div>
                <div style="font-size: 0.88rem; font-weight: 700; color: #0f172a; margin-top: 2px;">[{proc['proc_id']}] {proc['title']}</div>
                <div style="font-size: 0.80rem; color: #334155; margin-top: 4px;">
                    <strong>Căn cứ:</strong> {proc.get('legal_basis')} &nbsp;|&nbsp; 
                    <strong>Thời hạn:</strong> {proc.get('processing_time')} <br/>
                    <strong>Biểu mẫu:</strong> {proc.get('forms_required')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander(f"Xem chi tiết các bước trong quy trình [{proc['proc_id']}]", expanded=False):
                st.write(proc.get('content_extract', ''))
                for s in proc.get('steps', []):
                    st.write(f"• **Bước {s.get('step')} ({s.get('actor')}):** {s.get('action')}")

            with st.expander("🔄 Tra cứu / Đổi quy trình khác từ Trung tâm tri thức", expanded=False):
                all_procs = lm.procedures or []
                if all_procs:
                    proc_map = {p['proc_id']: p for p in all_procs}
                    current_pid = proc['proc_id'] if matched_procs else all_procs[0]['proc_id']
                    override_pid = st.selectbox(
                        "Chọn quy trình chuẩn hóa để đối chiếu thay thế:",
                        options=list(proc_map.keys()),
                        index=list(proc_map.keys()).index(current_pid) if current_pid in proc_map else 0,
                        format_func=lambda k: f"[{k}] {proc_map[k]['title']} ({proc_map[k].get('department', '')})",
                        key=f"wb_change_proc_{rid}"
                    )
                    if st.button("Áp dụng quy trình này vào văn bản giải quyết", key=f"wb_btn_apply_proc_{rid}"):
                        chosen_p = proc_map[override_pid]
                        _, new_draft = lm.reason_and_synthesize(item['clean_text'], chosen_p['topic'], chosen_p)
                        st.session_state['response_' + rid] = new_draft
                        st.success(f"Đã cập nhật văn bản giải quyết theo quy trình [{override_pid}] {chosen_p['title']}!")
                        st.rerun()

        if not matched_procs:
            articles = json.loads(item['articles_json']) if item.get('articles_json') else []
            if articles:
                for article in articles:
                    with st.expander(f"Căn cứ quy chế: {article.get('kb_id', '')} — {article.get('title', '')}", expanded=True):
                        st.write(article.get('content_extract', ''))
                        if article.get('source_url'):
                            st.caption(f"Nguồn tài liệu: {article['source_url']}")
            else:
                st.info('Chưa tìm thấy điều khoản quy trình cụ thể tương ứng. Cán bộ có thể chọn quy trình chuẩn hóa từ danh sách bên dưới:')
                all_procs = lm.procedures or []
                if all_procs:
                    proc_map = {p['proc_id']: p for p in all_procs}
                    override_pid = st.selectbox(
                        "Chọn quy trình áp dụng từ Trung tâm tri thức:",
                        options=list(proc_map.keys()),
                        format_func=lambda k: f"[{k}] {proc_map[k]['title']}",
                        key=f"wb_fallback_proc_{rid}"
                    )
                    if st.button("Áp dụng quy trình này vào phản hồi", key=f"wb_btn_fallback_apply_{rid}"):
                        chosen_p = proc_map[override_pid]
                        _, new_draft = lm.reason_and_synthesize(item['clean_text'], chosen_p['topic'], chosen_p)
                        st.session_state['response_' + rid] = new_draft
                        st.rerun()

    # 4b. Khung xem chi tiết quá trình xử lý & suy luận nội tâm của Model
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

    render_trace_view(
        trace_data=t_data,
        terminal_log=t_log,
        title=f"Nhật Ký Suy Luận & Vết Thực Thi Chi Tiết Của Model Cho Yêu Cầu [{rid}]",
        expanded=False,
        key_prefix=f"wb_trace_{rid}"
    )

    # 5. Form phê duyệt và gửi email giải quyết
    docx_topics = [t for t in CORE_DOCX_TOPICS if t in TOPICS]
    all_known_topics = list(TOPICS.keys())
    topics = docx_topics if item['predicted_topic'] in docx_topics else all_known_topics
    response_key = 'response_' + rid
    saved_draft = item.get('procedure_draft_response') or item.get('draft_response', '')
    if (
        response_key not in st.session_state
        or "[CHẨN ĐOÁN VẤN ĐỀ" in str(st.session_state.get(response_key, ''))
        or "Trình tự các bước thực hiện:" in str(st.session_state.get(response_key, ''))
    ):
        if not saved_draft or "[CHẨN ĐOÁN VẤN ĐỀ" in saved_draft or "Trình tự các bước thực hiện:" in saved_draft:
            matched_p = matched_procs[0] if matched_procs else None
            _, fresh_draft = lm.reason_and_synthesize(item['clean_text'], item['predicted_topic'], matched_p)
            st.session_state[response_key] = fresh_draft
        else:
            st.session_state[response_key] = saved_draft

    # Trích xuất hoặc định danh email người gửi để phản hồi
    email_match = re.search(r'email[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', item['clean_text'], re.IGNORECASE)
    recipient_email = email_match.group(1) if email_match else ("sinhvien.eaut@student.edu.vn" if "[EMAIL]" in item['clean_text'] else "sinhvien@eaut.edu.vn")

    with st.form('review_form_' + rid):
        curr_topic = item['predicted_topic'] if item['predicted_topic'] in topics else topics[0]
        final_topic = st.selectbox(
            'Nhóm phân loại cuối cùng (Điều chỉnh nếu cần)',
            options=topics,
            index=topics.index(curr_topic),
            format_func=lambda t: f"{TOPICS.get(t, t)} — [{get_dept_name(t)}]",
            key='topic_' + rid
        )
        response = st.text_area('Nội dung giải quyết gửi về email người gửi:', key=response_key, height=170)
        notes = st.text_input('Ghi chú xử lý nội bộ:', key='notes_' + rid, placeholder='Nhập ghi chú xử lý hoặc căn cứ giải quyết...')

        # Trường cấu hình email nhận kết quả linh hoạt
        c_rf_m1, c_rf_m2 = st.columns([3, 2])
        with c_rf_m1:
            send_to_email = st.text_input(
                'Email nhận kết quả giải quyết:',
                value=recipient_email,
                key='send_to_email_' + rid,
                help='Có thể sửa trực tiếp sang email của bạn (ví dụ: kennysk114239@gmail.com) để nhận thư thực tế khi bấm Duyệt.'
            )
        with c_rf_m2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            cc_test_mail = st.checkbox(
                f'Gửi kèm bản sao tới {DEFAULT_TEST_EMAIL}',
                value=True,
                key='cc_test_' + rid,
                help=f'Tự động gửi thêm 1 bản sao tới {DEFAULT_TEST_EMAIL} khi duyệt.'
            )

        st.caption(f"Khi bấm duyệt, kết quả giải quyết sẽ tự động gửi thông báo về email: **{send_to_email}**.")
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

    # Xem trước giao diện Email sẽ gửi cho sinh viên (Live Preview)
    with st.expander('👁️ Xem trước giao diện Email sẽ gửi tới sinh viên (HTML & Plain Text)', expanded=False):
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
        st.caption(f"Tiêu đề email: **{pv_subj}** &nbsp;|&nbsp; Người nhận: **{recipient_email}**")
        wb_pv_tabs = st.tabs(["📱 Giao diện Email HTML (Trực quan)", "📄 Định dạng Văn bản thuần (Plain Text)"])
        with wb_pv_tabs[0]:
            st.components.v1.html(pv_html, height=520, scrolling=True)
        with wb_pv_tabs[1]:
            st.text_area("Bản text gửi dự phòng:", value=pv_plain, height=260, disabled=True, key=f"wb_pv_text_{rid}")

    # Phân hệ Thử nghiệm gửi email thực tế & Cấu hình SMTP Gmail
    smtp_cfg = get_smtp_config()
    is_smtp_active = bool(smtp_cfg.get("user") and smtp_cfg.get("password"))

    expander_title = (
        f"📧 Thử nghiệm gửi email thực tế tới {DEFAULT_TEST_EMAIL} "
        + ("(🟢 Máy chủ SMTP sẵn sàng)" if is_smtp_active else "(🟡 Cần cấu hình SMTP để gửi thật)")
    )
    with st.expander(expander_title, expanded=not is_smtp_active):
        if is_smtp_active:
            st.success(
                f"🟢 **Máy chủ SMTP Gmail đã kích hoạt:** Sẵn sàng gửi thư thực tế qua tài khoản "
                f"**{smtp_cfg.get('user')}** (Cổng {smtp_cfg.get('port', 587)})."
            )
        else:
            st.warning(
                "⚠️ **Hệ thống đang ở Chế độ mô phỏng (Mock Dispatch).** "
                "Để thư thực sự chuyển đến hộp thư đến của bạn, vui lòng nhập thông tin tài khoản Gmail gửi bên dưới."
            )

        with st.expander("⚙️ Thiết lập / Thay đổi tài khoản Gmail gửi (SMTP Config)", expanded=not is_smtp_active):
            st.markdown(
                "Hệ thống EduSupportAI sử dụng giao thức bảo mật Google SMTP (TLS cổng 587) để gửi thư giải quyết phản ánh học vụ. "
                "Để gửi thật, Google yêu cầu sử dụng **Mật khẩu ứng dụng (16 ký tự)** thay vì mật khẩu thông thường."
            )
            c_u1, c_u2 = st.columns(2)
            with c_u1:
                smtp_user_in = st.text_input(
                    "Tài khoản Gmail gửi (Sender Gmail):",
                    value=smtp_cfg.get("user", ""),
                    placeholder="ví dụ: hotro.eaut@gmail.com",
                    key=f"smtp_user_in_{rid}"
                )
            with c_u2:
                smtp_pass_in = st.text_input(
                    "Mật khẩu ứng dụng (16 ký tự Google App Password):",
                    value=smtp_cfg.get("password", ""),
                    type="password",
                    placeholder="xxxx yyyy zzzz wwww",
                    key=f"smtp_pass_in_{rid}",
                    help="Chuỗi 16 chữ cái do Google cấp tại trang myaccount.google.com/apppasswords"
                )

            st.info(
                "📌 **Cách lấy Mật khẩu ứng dụng 16 ký tự từ Google (1 phút):**\n\n"
                "1. Bật **Xác minh 2 bước** cho tài khoản Google tại: [myaccount.google.com/security](https://myaccount.google.com/security)\n"
                "2. Truy cập: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)\n"
                "3. Đặt tên ứng dụng là `EduSupportAI` và bấm **Tạo (Create)**.\n"
                "4. Sao chép chuỗi 16 ký tự (ví dụ: `abcd efgh ijkl mnop`), dán vào ô trên rồi bấm nút **Lưu cấu hình & Kiểm tra kết nối SMTP**."
            )

            c_btn_save, _ = st.columns([2, 1])
            with c_btn_save:
                if st.button("💾 Lưu cấu hình & Kiểm tra kết nối SMTP", key=f"btn_save_smtp_{rid}", type="primary", width="stretch"):
                    if not smtp_user_in.strip() or not smtp_pass_in.strip():
                        st.error("Vui lòng nhập đầy đủ cả Tài khoản Gmail gửi và Mật khẩu ứng dụng.")
                    else:
                        with st.spinner("Đang xác thực với máy chủ smtp.gmail.com:587..."):
                            ok_smtp, msg_smtp = test_smtp_connection(smtp_user_in, smtp_pass_in)
                            if ok_smtp:
                                save_smtp_credentials(smtp_user_in, smtp_pass_in)
                                st.session_state['notice'] = f"Đã lưu và xác thực SMTP thành công: {msg_smtp}"
                                st.rerun()
                            else:
                                st.error(f"Xác thực không thành công: {msg_smtp}")

        st.markdown("##### 🚀 Gửi thử nghiệm nội dung giải quyết hồ sơ này:")
        c_wb_m1, c_wb_m2 = st.columns([3, 1])
        with c_wb_m1:
            wb_test_mail = st.text_input(
                'Email nhận thư kiểm thử:',
                value=DEFAULT_TEST_EMAIL,
                key='wb_test_mail_input',
                placeholder="kennysk114239@gmail.com"
            )
        with c_wb_m2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            send_btn_label = "🚀 Gửi email thực tế ngay" if is_smtp_active else "🧪 Gửi thử nghiệm (Mô phỏng)"
            if st.button(send_btn_label, type='primary' if is_smtp_active else 'secondary', key='btn_wb_send_test', width='stretch'):
                with st.spinner(f"Đang tiến hành gửi email tới {wb_test_mail}..."):
                    t_subj, t_plain, t_html = build_rich_resolution_email(
                        record_id=rid,
                        topic=st.session_state.get('topic_' + rid, item['predicted_topic']),
                        department=item_dept,
                        resolution_text=st.session_state.get(response_key, item['draft_response']),
                        confidence_score=conf,
                        is_auto_approved=False,
                        student_id=extract_student_id_from_text(item['clean_text']),
                        officer_notes=st.session_state.get('notes_' + rid, '')
                    )
                    t_ok, t_msg = send_resolution_email(
                        recipient_email=wb_test_mail,
                        subject=t_subj,
                        body_text=t_plain,
                        body_html=t_html,
                        record_id=rid
                    )
                    if t_ok:
                        if is_smtp_active:
                            st.success(f"🎉 **Đã gửi thư thực tế thành công!** {t_msg} Vui lòng kiểm tra hộp thư đến (hoặc hòm thư Rác/Quảng cáo) của **{wb_test_mail}**.")
                        else:
                            st.warning(
                                f"{t_msg}\n\n"
                                "👉 **Lưu ý:** Thư vừa được ghi nhận ở chế độ mô phỏng. "
                                "Để thư thực sự bay về hộp thư Gmail của bạn, vui lòng mở mục **Thiết lập / Thay đổi tài khoản Gmail gửi (SMTP Config)** phía trên để nhập Mật khẩu ứng dụng 16 ký tự."
                            )
                    else:
                        st.error(t_msg)

    # Phân hệ Huấn luyện AI từ dữ liệu cán bộ đã duyệt (Active Learning & Automation)
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    with st.expander('Huấn luyện AI để tự động hóa giải quyết yêu cầu (Active Learning)', expanded=False):
        st.caption(
            'Hệ thống tự động lưu các phản hồi và nhãn chuẩn mà cán bộ đã duyệt vào nhật ký kiểm toán. '
            'Bấm nút bên dưới để huấn luyện lại mô hình AI, giúp tăng tỷ lệ tự động hóa và nâng độ chắc chắn cho các yêu cầu tiếp theo.'
        )
        c_tr1, c_tr2 = st.columns([3, 1], gap="medium")
        with c_tr1:
            st.write('Mô hình học máy: **Logistic Regression + TF-IDF (Word & Char n-grams)**.')
            st.caption('Cơ chế cảnh báo: Tự động chuyển quản trị viên khi độ tự tin dưới 50% hoặc không tìm thấy quy chế phù hợp.')
        with c_tr2:
            if st.button('Huấn luyện lại AI ngay', type='primary', key='btn_retrain_ai_workbench', width='stretch'):
                with st.spinner('Đang huấn luyện lại mô hình AI...'):
                    from src.model import train_and_save_production_model
                    clf = train_and_save_production_model()
                    st.success('Đã huấn luyện lại mô hình thành công! Khả năng tự động hóa đã được nâng cấp.')
