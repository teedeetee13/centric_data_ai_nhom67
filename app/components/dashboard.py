# -*- coding: utf-8 -*-
"""
Module: app.components.dashboard
Thống kê chất lượng & Phân tích phản ánh học vụ sinh viên.
Thiết kế tối giản, trực quan, tính toán trực tiếp từ dữ liệu thực tế.
Không emoji - Hỗ trợ xuất dữ liệu an toàn chống Formula Injection và bảo mật PII.
"""

import json
import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st

from src.cleaner import clean_dataframe, clean_text_single

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
from src.config import RAW_DEMO_PATH, TOPICS, describe_flags
from src.database import list_requests, review_history, save_request, get_request
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

def analyze_dataframe_realtime(df, text_col='raw_text', clf_model=None):
    """
    Phân tích các chỉ số chất lượng thực tế từ một DataFrame.
    Đầu ra chuẩn hóa phục vụ đồng thời cho giao diện kiểm tra chất lượng và kiểm thử tự động.
    """
    cleaned = clean_dataframe(df, text_col)
    if cleaned.empty:
        return None
    flags = cleaned['quality_flags']
    total = len(cleaned)
    return {
        'total': total,
        'empty_count': int(flags.str.contains('empty').sum()),
        'short_count': int(flags.str.contains('too_short').sum()),
        'usable_count': int(cleaned['is_usable'].sum()),
        'usable_ratio': float(cleaned['is_usable'].mean() * 100) if total > 0 else 0.0,
        'duplicate_count': int(flags.str.contains('exact_duplicate').sum()),
        'near_duplicate_count': int(flags.str.contains('near_duplicate').sum()),
        'pii_total': int(flags.str.contains('has_').sum()),
        'pii_phone': int(flags.str.contains('has_phone').sum()),
        'pii_email': int(flags.str.contains('has_email').sum()),
        'pii_mssv': int(flags.str.contains('has_student_id').sum()),
        'df_processed': cleaned
    }

def export_csv(df):
    """
    Xuất dữ liệu an toàn ra định dạng CSV (UTF-8 with BOM):
    - Khử triệt để PII còn sót lại trong các chuỗi văn bản tự do.
    - Trung hòa các ký tự khởi đầu công thức (=, +, -, @) chống Spreadsheet Formula Injection.
    """
    safe = df.copy()
    def sanitize_cell(value):
        if isinstance(value, str):
            value = clean_text_single(value)['clean_text']
            if value.lstrip().startswith(('=', '+', '-', '@')):
                value = "'" + value
        return value

    for col in safe.columns:
        safe[col] = safe[col].map(sanitize_cell)
    return safe.to_csv(index=False).encode('utf-8-sig')

def hashlib_bytes(frame, text_col):
    return hashlib.sha256(frame[text_col].fillna('').astype(str).str.cat(sep='\n').encode()).hexdigest()

def render_dashboard(service=None, clf_model=None):
    st.markdown("""
    <div style="background: #cfdce8; border: 1px solid #b8cad8; border-radius: 12px; padding: 16px 20px 8px 20px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
        <div style="font-size: 1.05rem; font-weight: 800; color: #1a508b;">Báo Cáo & Thống Kê Chỉ Số Vận Hành Học Vụ</div>
        <div style="font-size: 0.8rem; color: #475569; margin-top: 2px;">Giám sát lưu lượng hồ sơ tiếp nhận, tỷ lệ xử lý tự động và nhật ký phê duyệt của cán bộ EAUT</div>
    </div>
    """, unsafe_allow_html=True)
    rows = list_requests()
    logs = review_history()

    # Hàng chỉ số cấp cao
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Tổng số yêu cầu tiếp nhận</div>
            <div class="metric-val">{len(rows)} hồ sơ</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        pending_cnt = sum(r['status'] == 'pending_review' for r in rows)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Hồ sơ đang chờ xử lý</div>
            <div class="metric-val" style="color: {'#dc2626' if pending_cnt > 0 else '#166534'};">{pending_cnt} hồ sơ</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Lượt phê duyệt đã lưu</div>
            <div class="metric-val">{len(logs)} lượt</div>
        </div>
        """, unsafe_allow_html=True)

    d_tabs = st.tabs([
        "📊 Chỉ số Vận hành & Phân bổ",
        "📑 Danh sách Hồ sơ & Lịch sử Duyệt",
        "🔍 Kiểm toán Chất lượng & Thử nghiệm"
    ])

    with d_tabs[0]:
        if rows:
            # Trực quan hóa phân bổ yêu cầu
            view = pd.DataFrame(rows)[['record_id', 'processed_at', 'clean_text', 'predicted_topic', 'confidence_score', 'priority_level', 'source_type', 'status']]
            c_pie, c_bar = st.columns(2)
            with c_pie:
                st.markdown('##### Phân bổ theo Đơn vị chuyên môn')
                topic_df = view['predicted_topic'].map(TOPICS).value_counts().reset_index()
                topic_df.columns = ['Chuyên môn', 'Số lượng']
                fig_pie = px.pie(topic_df, names='Chuyên môn', values='Số lượng', hole=0.45,
                                 color_discrete_sequence=['#1d4ed8', '#0284c7', '#0f766e', '#6366f1', '#d97706', '#059669', '#64748b'])
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=260,
                                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_pie, width='stretch')

            with c_bar:
                st.markdown('##### Phân bổ theo Mức độ ưu tiên')
                prio_df = view['priority_level'].value_counts().reset_index()
                prio_df.columns = ['Mức ưu tiên', 'Số lượng']
                prio_colors = {'Khẩn cấp': '#dc2626', 'Cao': '#ea580c', 'Bình thường': '#0284c7', 'Thấp': '#94a3b8'}
                fig_bar = px.bar(prio_df, x='Mức ưu tiên', y='Số lượng', color='Mức ưu tiên', color_discrete_map=prio_colors)
                fig_bar.update_layout(xaxis_title='', yaxis_title='', margin=dict(t=10, b=10, l=10, r=10), height=260,
                                      showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, width='stretch')
        else:
            st.info("Chưa có dữ liệu hồ sơ để hiển thị biểu đồ thống kê.")

    with d_tabs[1]:
        # Bảng yêu cầu đã lưu
        if rows:
            st.markdown('##### Danh sách yêu cầu trong hệ thống')
            c_ds1, c_ds2 = st.columns([3, 1])
            with c_ds2:
                dash_sort = st.selectbox(
                    "Sắp xếp ngày đăng:",
                    options=["Mới nhất trước", "Cũ nhất trước"],
                    key="dash_sort_date"
                )

            sorted_rows = sorted(
                rows,
                key=lambda x: (x.get('processed_at') or '', x.get('id', 0)),
                reverse=(dash_sort == "Mới nhất trước")
            )

            view = pd.DataFrame(sorted_rows)[['record_id', 'processed_at', 'clean_text', 'predicted_topic', 'confidence_score', 'priority_level', 'source_type', 'status']]
            display = view.copy()
            display['clean_text'] = display['clean_text'].apply(lambda s: parse_student_feedback(str(s))['student_message'] if pd.notna(s) else '')
            display['predicted_topic'] = display['predicted_topic'].map(TOPICS)
            display['status'] = display['status'].map({
                'pending_review': 'Chờ duyệt',
                'reviewed_approve': 'Đã duyệt',
                'reviewed_edit_label': 'Đã duyệt và đổi nhãn',
                'reviewed_reject': 'Đã từ chối'
            })
            display['source_type'] = display['source_type'].map({
                'manual_demo': 'Nhập thủ công',
                'controlled_demo': 'Mẫu kiểm thử',
                'portal_student': 'Cổng sinh viên'
            }).fillna('Cổng sinh viên')
            display['processed_at'] = display['processed_at'].apply(lambda t: format_datetime_vn(t) if pd.notna(t) else '')
            display = display.rename(columns={
                'record_id': 'Mã yêu cầu',
                'processed_at': 'Ngày đăng',
                'clean_text': 'Nội dung phản ánh',
                'predicted_topic': 'Nhóm dự đoán',
                'confidence_score': 'Độ tự tin',
                'priority_level': 'Ưu tiên',
                'source_type': 'Nguồn',
                'status': 'Trạng thái'
            })
            st.dataframe(
                display,
                width='stretch',
                hide_index=True,
                key="dash_table_select"
            )

            st.download_button(
                'Tải danh sách yêu cầu (CSV)',
                data=export_csv(view),
                file_name='danh_sach_yeu_cau.csv',
                mime='text/csv'
            )

        # Bảng nhật ký duyệt
        if logs:
            st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
            st.markdown('##### Nhật ký phê duyệt của cán bộ')
            history = pd.DataFrame(logs)
            visible = history.drop(columns=['id']).copy()
            visible['original_predicted_topic'] = visible['original_predicted_topic'].map(TOPICS)
            visible['final_topic'] = visible['final_topic'].map(TOPICS)
            visible['officer_action'] = visible['officer_action'].map({
                'approve': 'Duyệt',
                'edit_label': 'Đổi nhãn và duyệt',
                'reject': 'Từ chối'
            })
            visible = visible.rename(columns={
                'record_id': 'Mã yêu cầu',
                'officer_action': 'Thao tác',
                'original_predicted_topic': 'Nhãn dự đoán',
                'final_topic': 'Nhãn cuối',
                'final_response': 'Trả lời đã lưu',
                'officer_notes': 'Ghi chú',
                'reviewed_at': 'Thời điểm UTC'
            })
            st.dataframe(visible, width='stretch', hide_index=True)
            st.download_button(
                'Tải nhật ký duyệt (CSV)',
                data=export_csv(history),
                file_name='nhat_ky_duyet.csv',
                mime='text/csv'
            )

        # Nhật ký gửi email thông báo giải quyết
        from src.email_service import list_email_dispatches
        email_logs = list_email_dispatches()
        if email_logs:
            st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
            st.markdown('##### Nhật ký gửi email giải quyết')
            df_emails = pd.DataFrame(email_logs)[['sent_at', 'record_id', 'recipient_email', 'dispatch_mode', 'status', 'subject']]
            df_emails['dispatch_mode'] = df_emails['dispatch_mode'].map({
                'smtp_real': 'Máy chủ SMTP',
                'simulated': 'Mô phỏng (Mock)'
            }).fillna(df_emails['dispatch_mode'])
            df_emails['status'] = df_emails['status'].map({
                'success': 'Thành công',
                'failed': 'Thất bại'
            }).fillna(df_emails['status'])
            df_emails = df_emails.rename(columns={
                'sent_at': 'Thời điểm gửi (UTC)',
                'record_id': 'Mã yêu cầu',
                'recipient_email': 'Email người nhận',
                'dispatch_mode': 'Kênh gửi',
                'status': 'Trạng thái',
                'subject': 'Tiêu đề thông báo'
            })
            st.dataframe(df_emails, width='stretch', hide_index=True)

    with d_tabs[2]:
        # Nạp dữ liệu mẫu vào bàn duyệt (Dành cho kiểm thử)
        st.markdown('##### 🧪 Nạp dữ liệu mẫu thử nghiệm')
        st.caption('Nạp 3 yêu cầu mẫu vào Bàn duyệt cán bộ (bảo toàn trạng thái đã duyệt trước đó).')
        if st.button('Nạp 3 yêu cầu demo', width='stretch') and service:
            for index, text in enumerate([
                'Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.',
                'Em không đăng nhập được cổng sinh viên, số điện thoại 0912 345 678.',
                'Hai môn của em bị trùng lịch thi sáng thứ Hai.',
            ], start=1):
                rid = 'DEMO_' + str(index).zfill(3)
                if not get_request(rid):
                    save_request(service.process(text), record_id=rid, source_type='controlled_demo')
            st.session_state['notice'] = 'Đã nạp các mẫu còn thiếu. Kết quả duyệt trước đó được giữ nguyên.'
            st.rerun()

        st.markdown("---")
        # Phân hệ Kiểm tra chất lượng dữ liệu
        st.markdown('##### 🛡️ Kiểm tra chất lượng & Che giấu PII dữ liệu hàng loạt')
        source = st.radio('Nguồn kiểm tra', ['Bộ mô phỏng 424 dòng', 'Tải CSV hoặc XLSX'], horizontal=True)
        target = None
        text_col = 'raw_text'

        if source == 'Bộ mô phỏng 424 dòng':
            target = pd.read_csv(RAW_DEMO_PATH)
            text_col = 'raw_text'
            st.caption('Dữ liệu mô phỏng 424 dòng thực tế, chuẩn hóa NFC và che giấu PII tự động.')
        else:
            uploaded = st.file_uploader('Chọn tệp dữ liệu', type=['csv', 'xlsx'])
            if uploaded is not None:
                if uploaded.size > 5_000_000:
                    st.warning('Hệ thống nhận tệp tối đa 5 MB.')
                    return
                try:
                    target = pd.read_csv(uploaded) if uploaded.name.lower().endswith('.csv') else pd.read_excel(uploaded)
                except Exception as exc:
                    st.error('Không đọc được tệp. Kiểm tra định dạng và mã hóa UTF-8. ' + str(exc))
                    return
                if not len(target.columns):
                    st.warning('Tệp chưa có cột.')
                    return
                if len(target) > 500:
                    st.warning('Giới hạn kiểm tra tối đa 500 dòng mỗi tệp.')
                    return
                preferred = next((c for c in ('raw_text', 'clean_text', 'noi_dung', 'content') if c in target.columns), target.columns[0])
                text_col = st.selectbox('Cột chứa nội dung', list(target.columns), index=list(target.columns).index(preferred))

        if target is not None:
            if target.empty:
                st.info('Tệp không có dòng dữ liệu.')
                return

            signature = (source, hashlib_bytes(target, text_col))
            if st.session_state.get('_profile_signature') != signature:
                st.session_state.pop('profile_result', None)
                st.session_state['_profile_signature'] = signature

            if st.button('Kiểm tra và che thông tin', key='profile_data', width='stretch'):
                st.session_state['profile_result'] = analyze_dataframe_realtime(target, text_col)

            stats = st.session_state.get('profile_result')
            if stats:
                x, y, z = st.columns(3)
                x.metric('Dòng hợp lệ để dùng', f"{stats['usable_count']}/{stats['total']}")
                y.metric('Dòng rỗng', stats['empty_count'])
                z.metric('Dòng có thông tin cá nhân', stats['pii_total'])
                st.caption(f"Trùng hoàn toàn: {stats['duplicate_count']} | Gần trùng: {stats['near_duplicate_count']} | Ngắn: {stats['short_count']}.")
                display = stats['df_processed'].copy()
                display['quality_flags'] = display['quality_flags'].map(describe_flags)
                display = display.rename(columns={
                    'row_number': 'Dòng',
                    'clean_text': 'Nội dung đã che',
                    'quality_flags': 'Chất lượng',
                    'is_usable': 'Dùng được',
                    'char_length': 'Số ký tự'
                })
                st.dataframe(display, width='stretch', hide_index=True)
                st.download_button(
                    'Tải dữ liệu đã che',
                    data=export_csv(stats['df_processed']),
                    file_name='du_lieu_da_che.csv',
                    mime='text/csv'
                )

        st.markdown("---")
        # Phân hệ Tra cứu Vết Thực Thi & Nhật Ký Suy Luận của Model
        if rows:
            st.markdown('##### 🔎 Tra cứu Vết thực thi & Nhật ký suy luận của Model')
            st.caption('Kiểm toán toàn bộ quá trình xử lý, phân phối xác suất và chuỗi suy luận của Local Learning Machine cho từng yêu cầu.')
            from src.database import get_execution_trace
            from app.components.trace_viewer import render_trace_view
            from src.local_machine import get_local_machine

            trace_rids = [r['record_id'] for r in rows]
            if st.session_state.get('dash_select_trace_rid') not in trace_rids and trace_rids:
                st.session_state['dash_select_trace_rid'] = trace_rids[0]

            curr_t_rid = st.session_state.get('dash_select_trace_rid')
            curr_t_idx = trace_rids.index(curr_t_rid) if curr_t_rid in trace_rids else 0

            selected_trace_rid = st.selectbox(
                "Chọn mã yêu cầu cần kiểm toán chi tiết:",
                options=trace_rids,
                index=curr_t_idx,
                format_func=lambda k: f"{k} — [{next((r['predicted_topic'] for r in rows if r['record_id'] == k), '')}] {next((r['clean_text'][:50] for r in rows if r['record_id'] == k), '')}...",
                key="dash_select_trace_rid"
            )
            if selected_trace_rid:
                t_row = get_execution_trace(selected_trace_rid)
                t_data = None
                t_log = ""
                if t_row and t_row.get('steps_json'):
                    try:
                        t_data = json.loads(t_row['steps_json']) if isinstance(t_row['steps_json'], str) else t_row['steps_json']
                        t_log = t_row.get('terminal_log', '')
                    except Exception:
                        t_data = None
                if not t_data:
                    target_r = next((r for r in rows if r['record_id'] == selected_trace_rid), None)
                    if target_r:
                        lm = get_local_machine()
                        res_lm = lm.process_request_with_trace(target_r['clean_text'], record_id=selected_trace_rid)
                        t_data = res_lm.get('execution_trace', {})
                        t_log = res_lm.get('terminal_log', '')

                render_trace_view(
                    trace_data=t_data,
                    terminal_log=t_log,
                    title=f"Vết Thực Thi Của Model Cho Yêu Cầu [{selected_trace_rid}]",
                    expanded=False,
                    key_prefix=f"dash_trace_{selected_trace_rid}"
                )



