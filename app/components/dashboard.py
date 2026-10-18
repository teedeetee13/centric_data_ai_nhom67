# -*- coding: utf-8 -*-
"""
Module: app.components.dashboard
Thống kê chất lượng & Phân tích phản ánh học vụ sinh viên.
Thiết kế tối giản, trực quan, tính toán trực tiếp từ dữ liệu thực tế.
Không emoji - Hỗ trợ xuất dữ liệu an toàn chống Formula Injection và bảo mật PII.
"""

import io
import json
import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st

from src.cleaner import clean_dataframe, clean_text_single
from src.config import RAW_DEMO_PATH, TOPICS, describe_flags
from src.database import list_requests, review_history, save_request, get_request

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
    rows = list_requests()
    logs = review_history()

    # Hàng chỉ số cấp cao
    m1, m2, m3 = st.columns(3)
    m1.metric('Yêu cầu đã lưu', len(rows))
    m2.metric('Đang chờ duyệt', sum(r['status'] == 'pending_review' for r in rows))
    m3.metric('Lượt xử lý đã lưu', len(logs))

    # Bảng yêu cầu đã lưu
    if rows:
        st.subheader('Danh sách yêu cầu trong hệ thống')
        view = pd.DataFrame(rows)[['record_id', 'clean_text', 'predicted_topic', 'confidence_score', 'priority_level', 'source_type', 'status', 'processed_at']]
        display = view.copy()
        display['predicted_topic'] = display['predicted_topic'].map(TOPICS)
        display['status'] = display['status'].map({
            'pending_review': 'Chờ duyệt',
            'reviewed_approve': 'Đã duyệt',
            'reviewed_edit_label': 'Đã duyệt và đổi nhãn',
            'reviewed_reject': 'Đã từ chối'
        })
        display['source_type'] = display['source_type'].map({
            'manual_demo': 'Nhập thủ công',
            'controlled_demo': 'Mẫu kiểm thử'
        })
        display = display.rename(columns={
            'record_id': 'Mã yêu cầu',
            'clean_text': 'Nội dung đã che',
            'predicted_topic': 'Nhóm dự đoán',
            'confidence_score': 'Độ tự tin',
            'priority_level': 'Ưu tiên',
            'source_type': 'Nguồn',
            'status': 'Trạng thái',
            'processed_at': 'Thời điểm UTC'
        })
        st.dataframe(display, width='stretch', hide_index=True)
        st.download_button(
            'Tải danh sách đã che thông tin',
            data=export_csv(view),
            file_name='yeu_cau_da_che.csv',
            mime='text/csv'
        )

        # Trực quan hóa phân bổ yêu cầu
        c_pie, c_bar = st.columns(2)
        with c_pie:
            st.markdown('##### Phân bổ theo Đơn vị chuyên môn')
            topic_df = view['predicted_topic'].map(TOPICS).value_counts().reset_index()
            topic_df.columns = ['Chuyên môn', 'Số lượng']
            fig_pie = px.pie(topic_df, names='Chuyên môn', values='Số lượng', hole=0.45,
                             color_discrete_sequence=['#1d4ed8', '#0284c7', '#0f766e', '#6366f1', '#d97706', '#059669', '#64748b'])
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=250,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, width='stretch')

        with c_bar:
            st.markdown('##### Phân bổ theo Mức độ ưu tiên')
            prio_df = view['priority_level'].value_counts().reset_index()
            prio_df.columns = ['Mức ưu tiên', 'Số lượng']
            prio_colors = {'Khẩn cấp': '#dc2626', 'Cao': '#ea580c', 'Bình thường': '#0284c7', 'Thấp': '#94a3b8'}
            fig_bar = px.bar(prio_df, x='Mức ưu tiên', y='Số lượng', color='Mức ưu tiên', color_discrete_map=prio_colors)
            fig_bar.update_layout(xaxis_title='', yaxis_title='', margin=dict(t=10, b=10, l=10, r=10), height=250,
                                  showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, width='stretch')

    # Bảng nhật ký duyệt
    if logs:
        st.subheader('Nhật ký duyệt của cán bộ')
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
            'Tải nhật ký duyệt',
            data=export_csv(history),
            file_name='nhat_ky_duyet.csv',
            mime='text/csv'
        )

    # Nhật ký gửi email thông báo giải quyết
    from src.email_service import list_email_dispatches
    email_logs = list_email_dispatches()
    if email_logs:
        st.subheader('Nhật ký gửi email thông báo giải quyết')
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

    # Phân hệ Kiểm tra chất lượng dữ liệu
    st.subheader('Kiểm tra chất lượng dữ liệu')
    source = st.radio('Nguồn kiểm tra', ['Bộ mô phỏng 424 dòng', 'Tải CSV hoặc XLSX'], horizontal=True)
    target = None
    text_col = 'raw_text'

    if source == 'Bộ mô phỏng 424 dòng':
        target = pd.read_csv(RAW_DEMO_PATH)
        text_col = 'raw_text'
        st.caption('Đây là dữ liệu mô phỏng. Các số liệu được tính toán thời gian thực bằng bộ xử lý thống nhất.')
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

    # Nạp dữ liệu mẫu vào bàn duyệt
    st.subheader('Nạp ba yêu cầu mẫu vào bàn duyệt')
    st.caption('Nạp lại không tạo bản ghi trùng và bảo toàn trạng thái đã duyệt trước đó.')
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
