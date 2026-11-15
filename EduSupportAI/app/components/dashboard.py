# -*- coding: utf-8 -*-
"""
Module: app.components.dashboard
Tab Thống kê: chỉ số tổng quan, biểu đồ, kết quả thực nghiệm và công cụ cán bộ
(nạp dữ liệu mẫu, nạp từ tệp, kiểm tra chất lượng tệp, tải xuống, email thử, huấn luyện lại).
"""

import hashlib
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.intake import render_batch_import, render_test_email
from src.cleaner import clean_dataframe, clean_text_single
from src.config import RAW_DEMO_PATH, ROOT, describe_flags, is_production
from src.database import list_requests, review_history
from src.sample_data import import_samples
from src.stats import compute_statistics

PRIMARY = '#1d4ed8'
PRIORITY_COLORS = {'Khẩn cấp': '#dc2626', 'Cao': '#ea580c', 'Bình thường': '#2563eb', 'Thấp': '#94a3b8'}
STATUS_COLORS = {'Chờ duyệt': '#f59e0b', 'Đã duyệt': '#16a34a', 'Duyệt, đổi nhãn': '#0d9488', 'Từ chối': '#94a3b8'}


def analyze_dataframe_realtime(df, text_col='raw_text', clf_model=None):
    """Chỉ số chất lượng của một bảng dữ liệu (dùng cho công cụ kiểm tra tệp và kiểm thử)."""
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
    """CSV UTF-8 có BOM: che PII còn sót và vô hiệu ký tự mở đầu công thức (chống Formula Injection)."""
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


def _bar(counts, color_map=None, horizontal=False, height=260):
    frame = pd.DataFrame({'Nhãn': list(counts), 'Số lượng': list(counts.values())})
    if horizontal:
        frame = frame.iloc[::-1]
    fig = px.bar(frame, x='Số lượng' if horizontal else 'Nhãn', y='Nhãn' if horizontal else 'Số lượng',
                 orientation='h' if horizontal else 'v', color='Nhãn' if color_map else None,
                 color_discrete_map=color_map, color_discrete_sequence=[PRIMARY], text='Số lượng')
    fig.update_traces(textposition='outside', cliponaxis=False)
    fig.update_layout(height=height, margin=dict(t=8, b=8, l=8, r=24), showlegend=False, xaxis_title='', yaxis_title='',
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


def _chart(title, fig):
    with st.container(border=True):
        st.markdown(f'**{title}**')
        st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})


def render_overview(stats):
    hours = stats['avg_handle_hours']
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Tổng yêu cầu', stats['total'], border=True)
    c2.metric('Chờ duyệt', stats['pending'], f"{stats['urgent_pending']} khẩn cấp" if stats['urgent_pending'] else None,
              delta_color='inverse', border=True)
    c3.metric('Đã xử lý', stats['reviewed'] + stats['rejected'], f"{stats['auto_approved']} tự động" if stats['auto_approved'] else None,
              delta_color='off', border=True)
    c4.metric('Thời gian xử lý TB', '—' if hours is None else (f'{hours:.1f} giờ' if hours < 48 else f'{hours / 24:.1f} ngày'), border=True)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric('Khớp quy trình', f"{stats['procedure_match_rate']:.0%}", border=True,
              help='Tỷ lệ câu hỏi hợp lệ được ghép vào một trong 33 quy trình của trường')
    c6.metric('Có thông tin cá nhân đã che', f"{stats['pii_rate']:.0%}", border=True)
    c7.metric('Độ tự tin trung bình', f"{stats['mean_confidence']:.0%}", border=True,
              help='Xác suất trung bình của mô hình phân loại, không phải độ chính xác')
    c8.metric('Cán bộ đổi nhãn', f"{stats['label_change_rate']:.0%}", border=True,
              help='Tỷ lệ yêu cầu đã duyệt mà cán bộ phải sửa nhóm phân loại')

    left, right = st.columns(2)
    with left:
        _chart('Theo nhóm chủ đề', _bar(stats['by_topic'], horizontal=True))
        _chart('Theo mức ưu tiên', _bar(stats['by_priority'], PRIORITY_COLORS))
    with right:
        top = {f"{pid} · {name[:38]}": n for pid, name, n in stats['top_procedures']}
        if top:
            _chart('Quy trình được hỏi nhiều nhất', _bar(top, horizontal=True))
        else:
            with st.container(border=True):
                st.markdown('**Quy trình được hỏi nhiều nhất**')
                st.caption('Chưa có yêu cầu nào khớp quy trình.')
        status = {k: v for k, v in stats['by_status'].items() if v}
        fig = px.pie(names=list(status), values=list(status.values()), hole=0.55, color=list(status),
                     color_discrete_map=STATUS_COLORS)
        fig.update_traces(textinfo='value', textposition='inside', sort=False)
        fig.update_layout(height=260, margin=dict(t=8, b=8, l=8, r=8), paper_bgcolor='rgba(0,0,0,0)',
                          legend=dict(orientation='h', y=-0.08, x=0.5, xanchor='center'))
        _chart('Trạng thái xử lý', fig)


def render_experiment_reports():
    """Kết quả thực nghiệm đã chạy (đọc từ experiments/*.json, không tính lại trong app)."""
    routing_path = ROOT / 'experiments' / 'procedure_routing_report.json'
    augment_path = ROOT / 'experiments' / 'procedure_augmentation_report.json'
    if not routing_path.exists() and not augment_path.exists():
        return
    with st.expander('Kết quả thực nghiệm của mô hình'):
        if routing_path.exists():
            rep = json.loads(routing_path.read_text(encoding='utf-8'))
            c1, c2, c3 = st.columns(3)
            c1.metric('Ghép đúng quy trình', f"{rep['routing_accuracy_in_scope']:.1%}", border=True,
                      help=f"{rep['n_in_scope']} câu diễn đạt khác câu mẫu")
            c2.metric('Từ chối đúng câu ngoài phạm vi', f"{rep['rejection_accuracy_out_of_scope']:.1%}", border=True,
                      help=f"{rep['n_out_of_scope']} câu không thuộc quy trình nào")
            extended = rep.get('extended')
            if extended:
                c3.metric('Bộ mẫu mở rộng (72 câu)', f"{extended['overall_accuracy']:.1%}", border=True,
                          help='Tỷ lệ định tuyến đúng (kể cả từ chối đúng) trên data/mau_mo_rong.csv')
        if augment_path.exists():
            rep = json.loads(augment_path.read_text(encoding='utf-8'))
            names = {'A_base': 'A. Dữ liệu gốc', 'B_base_plus_procedures': 'B. Gốc + câu mẫu quy trình (đang dùng)'}
            sets = {'test_sealed': 'Test niêm phong', 'mau_thuc_te': 'Văn phong thực tế', 'procedure_eval': 'Câu thuộc quy trình'}
            st.markdown('**Giữ nguyên thuật toán, chỉ bổ sung dữ liệu**')
            st.dataframe([{'Dữ liệu huấn luyện': names.get(k, k), 'Tập đánh giá': sets.get(s, s),
                           'Độ chính xác': f"{v['accuracy']:.1%}", 'Macro F1': f"{v['macro_f1']:.3f}"}
                          for k, res in rep['results'].items() for s, v in res.items()], hide_index=True, width='stretch')
            st.caption('Test niêm phong đạt 100% vì sinh từ cùng mẫu câu với dữ liệu huấn luyện. Tập đánh giá do nhóm viết, chưa phải dữ liệu thật.')


def _tool_samples(service):
    st.caption('72 câu hỏi mô phỏng phủ 33 quy trình và 10 loại dịch vụ của cổng hỗ trợ MIS. Nạp lại không tạo trùng.')
    if st.button('Nạp dữ liệu mẫu', type='primary') and service:
        added = import_samples(service)
        st.session_state['notice'] = f'Đã nạp {added} câu mẫu mới vào hàng chờ.'
        st.rerun()


def _tool_quality():
    source = st.radio('Nguồn', ['Bộ mô phỏng 424 dòng', 'Tải CSV hoặc XLSX'], horizontal=True, key='quality_source')
    target, text_col = None, 'raw_text'
    if source == 'Bộ mô phỏng 424 dòng':
        target = pd.read_csv(RAW_DEMO_PATH)
    else:
        uploaded = st.file_uploader('Tệp dữ liệu (tối đa 500 dòng)', type=['csv', 'xlsx'], key='quality_upload')
        if uploaded is None:
            return
        try:
            target = pd.read_csv(uploaded) if uploaded.name.lower().endswith('.csv') else pd.read_excel(uploaded)
        except Exception as exc:
            st.error('Không đọc được tệp. ' + str(exc))
            return
        if target.empty or len(target) > 500:
            st.warning('Tệp rỗng hoặc vượt 500 dòng.')
            return
        preferred = next((c for c in ('raw_text', 'clean_text', 'noi_dung', 'content') if c in target.columns), target.columns[0])
        text_col = st.selectbox('Cột nội dung', list(target.columns), index=list(target.columns).index(preferred))

    signature = (source, hashlib_bytes(target, text_col))
    if st.session_state.get('_profile_signature') != signature:
        st.session_state.pop('profile_result', None)
        st.session_state['_profile_signature'] = signature
    if st.button('Kiểm tra và che thông tin', key='profile_data'):
        st.session_state['profile_result'] = analyze_dataframe_realtime(target, text_col)
    stats = st.session_state.get('profile_result')
    if not stats:
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Dùng được', f"{stats['usable_count']}/{stats['total']}", border=True)
    c2.metric('Có thông tin cá nhân', stats['pii_total'], border=True)
    c3.metric('Trùng / gần trùng', f"{stats['duplicate_count']} / {stats['near_duplicate_count']}", border=True)
    c4.metric('Rỗng / quá ngắn', f"{stats['empty_count']} / {stats['short_count']}", border=True)
    preview = stats['df_processed'].head(50).copy()
    preview['quality_flags'] = preview['quality_flags'].map(describe_flags)
    st.dataframe(preview.rename(columns={'row_number': 'Dòng', 'clean_text': 'Nội dung đã che', 'quality_flags': 'Chất lượng',
                                         'is_usable': 'Dùng được', 'char_length': 'Số ký tự'}), hide_index=True, width='stretch', height=240)
    st.download_button('Tải dữ liệu đã che', data=export_csv(stats['df_processed']), file_name='du_lieu_da_che.csv', mime='text/csv')


def _tool_downloads(rows, logs):
    st.caption('Dữ liệu tải về đã che thông tin cá nhân và chống chèn công thức bảng tính.')
    columns = ['record_id', 'clean_text', 'predicted_topic', 'confidence_score', 'priority_level', 'department',
               'matched_kb_id', 'source_type', 'status', 'processed_at', 'reviewed_at']
    c1, c2 = st.columns(2)
    if rows:
        c1.download_button('Danh sách yêu cầu (CSV)', data=export_csv(pd.DataFrame(rows)[columns]),
                           file_name='yeu_cau_da_che.csv', mime='text/csv', width='stretch')
    if logs:
        c2.download_button('Nhật ký duyệt (CSV)', data=export_csv(pd.DataFrame(logs)),
                           file_name='nhat_ky_duyet.csv', mime='text/csv', width='stretch')
    if not rows and not logs:
        st.info('Chưa có dữ liệu để tải.')


def _tool_retrain():
    st.caption('Huấn luyện lại từ tập train và câu mẫu của kho quy trình. Nhật ký duyệt chưa được dùng để huấn luyện.')
    if st.button('Huấn luyện lại mô hình phân loại', key='btn_retrain_ai_workbench'):
        with st.spinner('Đang huấn luyện...'):
            from src.model import train_and_save_production_model
            train_and_save_production_model()
        st.success('Đã huấn luyện lại; ứng dụng tự nạp mô hình mới ở lần tải trang kế tiếp.')


def render_tools(service, rows, logs):
    with st.expander('Công cụ cán bộ'):
        names = ['Dữ liệu mẫu', 'Nạp từ tệp', 'Kiểm tra chất lượng tệp', 'Tải xuống']
        if not is_production():
            names += ['Email thử', 'Huấn luyện lại']
        tabs = st.tabs(names)
        with tabs[0]:
            _tool_samples(service)
        with tabs[1]:
            st.caption('Ví dụ tệp phiếu xuất từ cổng hỗ trợ MIS. Tối đa 200 dòng mỗi lần.')
            render_batch_import(service)
        with tabs[2]:
            _tool_quality()
        with tabs[3]:
            _tool_downloads(rows, logs)
        if not is_production():
            with tabs[4]:
                render_test_email()
            with tabs[5]:
                _tool_retrain()


def render_dashboard(service=None, clf_model=None):
    rows = list_requests()
    logs = review_history()
    if rows:
        render_overview(compute_statistics(rows, logs))
    else:
        st.info('Chưa có yêu cầu nào. Mở "Công cụ cán bộ" bên dưới và bấm "Nạp dữ liệu mẫu" để xem thống kê.')
    render_experiment_reports()
    render_tools(service, rows, logs)
