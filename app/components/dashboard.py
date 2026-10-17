# -*- coding: utf-8 -*-
"""
Module: app.components.dashboard
Thống kê chất lượng & Phân tích phản ánh học vụ sinh viên.
Thiết kế tối giản, trực quan, tính toán trực tiếp từ dữ liệu thực tế.
Không emoji - Loại bỏ các tùy chọn kỹ thuật nội bộ.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import get_connection
from src.cleaner import clean_text_single
from src.model import EduSupportClassifier, determine_priority

TOPIC_VIETNAMESE = {
    "Hoc_phi": "Học phí & Chính sách",
    "Lich_hoc_lich_thi": "Lịch học & Lịch thi",
    "Diem_khao_thi": "Điểm số & Khảo thí",
    "Thu_tuc_hanh_chinh": "Thủ tục hành chính",
    "Co_so_vat_chat": "Cơ sở vật chất",
    "He_thong_CNTT": "Hệ thống CNTT",
    "Khac": "Ý kiến khác"
}

def analyze_dataframe_realtime(df, text_col, clf_model=None):
    """Phân tích các chỉ số chất lượng thực tế từ một DataFrame cụ thể."""
    total = len(df)
    if total == 0:
        return None

    texts = df[text_col].fillna("").astype(str)

    # 1. Rỗng & quá ngắn
    empty_count = int((texts.str.strip() == "").sum() + df[text_col].isna().sum())
    short_count = int((texts.apply(len) < 12).sum())

    # 2. Trùng lặp
    duplicate_count = int(texts.duplicated().sum())

    # 3. Quét thông tin cá nhân (PII) thực tế bằng Regex
    pii_phone_count = int(texts.str.contains(r'0[3|5|7|8|9]\d{8}').sum())
    pii_email_count = int(texts.str.contains(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+').sum())
    pii_mssv_count = int(texts.str.contains(r'20\d{6}').sum())
    pii_total_records = int(((texts.str.contains(r'0[3|5|7|8|9]\d{8}')) | 
                            (texts.str.contains(r'@[a-zA-Z0-9-]+\.')) | 
                            (texts.str.contains(r'20\d{6}'))).sum())

    # 4. Xác định chuyên môn
    if "predicted_topic" in df.columns:
        topic_series = df["predicted_topic"]
    elif "target_label_gold" in df.columns:
        topic_series = df["target_label_gold"]
    elif clf_model is not None:
        topic_series = texts.apply(lambda t: clf_model.predict_single(clean_text_single(t)["clean_text"])["predicted_topic"] if len(t) >= 12 else "Khac")
    else:
        topic_series = pd.Series(["Chưa phân loại"] * total)

    # 5. Mức độ ưu tiên
    if "priority_level" in df.columns:
        prio_series = df["priority_level"]
    elif "priority_gold" in df.columns:
        prio_series = df["priority_gold"]
    else:
        prio_series = texts.apply(determine_priority)

    usable_count = total - duplicate_count - short_count

    return {
        "total": total,
        "empty_count": empty_count,
        "short_count": short_count,
        "usable_count": max(0, usable_count),
        "usable_ratio": float(max(0, usable_count) / total * 100),
        "duplicate_count": duplicate_count,
        "duplicate_ratio": float(duplicate_count / total * 100),
        "pii_total": pii_total_records,
        "pii_phone": pii_phone_count,
        "pii_email": pii_email_count,
        "pii_mssv": pii_mssv_count,
        "topic_counts": topic_series.value_counts(),
        "priority_counts": prio_series.value_counts(),
        "df_processed": df.assign(chuyen_mon=topic_series.map(lambda x: TOPIC_VIETNAMESE.get(x, x)), muc_uu_tien=prio_series)
    }

def render_dashboard(clf_model=None):
    col_mode, col_info = st.columns([2, 1], gap="large")
    
    with col_mode:
        data_source = st.radio(
            "Nguồn dữ liệu:",
            options=[
                "Dữ liệu đang tiếp nhận trong hệ thống",
                "Tải lên tệp phản ánh mới (Excel / CSV)"
            ],
            horizontal=True,
            label_visibility="collapsed"
        )

    df_target = None
    text_column = None

    # NGUỒN 1: DỮ LIỆU ĐANG TIẾP NHẬN TRONG HỆ THỐNG
    if data_source == "Dữ liệu đang tiếp nhận trong hệ thống":
        conn = get_connection()
        try:
            df_target = pd.read_sql_query("SELECT * FROM processed_requests", conn)
        except Exception:
            df_target = pd.DataFrame()
        finally:
            conn.close()

        if df_target.empty:
            fallback_clean = "data/processed/dataset_clean.csv"
            if os.path.exists(fallback_clean):
                df_target = pd.read_csv(fallback_clean)
                text_column = "clean_text"
            else:
                st.info("Hệ thống chưa có phản ánh nào được ghi nhận.")
                return
        else:
            text_column = "clean_text" if "clean_text" in df_target.columns else "raw_text"

        with col_info:
            st.caption(f"Đang hiển thị thống kê từ **{len(df_target):,}** phản ánh sinh viên.")

    # NGUỒN 2: TẢI LÊN TỆP MỚI
    else:
        c_up1, c_up2 = st.columns([3, 2], gap="large")
        with c_up1:
            uploaded_file = st.file_uploader(
                "Chọn tệp bảng tính phản ánh (.xlsx hoặc .csv):",
                type=["csv", "xlsx"]
            )
        with c_up2:
            st.caption("Hoặc nạp nhanh dữ liệu mẫu kiểm thử:")
            sample_real_path = "data/mau_phan_anh_thuc_te_eaut.csv"
            if os.path.exists(sample_real_path):
                if st.button("Nạp tệp mẫu 50 phản ánh thực tế EAUT", use_container_width=True):
                    st.session_state["use_sample_real"] = True

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_target = pd.read_csv(uploaded_file)
                else:
                    df_target = pd.read_excel(uploaded_file)
                
                possible_cols = [c for c in df_target.columns if any(k in str(c).lower() for k in ["text", "noi_dung", "cau_hoi", "phan_anh", "content", "tin_nhan"])]
                text_column = possible_cols[0] if possible_cols else df_target.columns[0]
                st.caption(f"Đã nạp tệp: **{uploaded_file.name}** ({len(df_target):,} dòng).")
            except Exception as e:
                st.error(f"Lỗi khi đọc tệp: {e}")
                return
        elif st.session_state.get("use_sample_real", False) and os.path.exists(sample_real_path):
            df_target = pd.read_csv(sample_real_path)
            text_column = "raw_text"
            st.caption(f"Đang phân tích tệp mẫu thực tế EAUT ({len(df_target)} bản ghi).")
        else:
            st.info("Vui lòng tải lên tệp CSV/Excel từ máy tính hoặc bấm nút 'Nạp tệp mẫu 50 phản ánh thực tế EAUT'.")
            return

    # PHÂN TÍCH CHỈ SỐ
    stats = analyze_dataframe_realtime(df_target, text_column, clf_model=clf_model)
    if stats is None:
        st.warning("Tệp dữ liệu không có dòng nào.")
        return

    st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

    # 4 THẺ TỔNG QUAN
    m1, m2, m3, m4 = st.columns(4, gap="medium")
    with m1:
        st.metric("Tổng phản ánh", f"{stats['total']:,}")
    with m2:
        st.metric("Hợp lệ xử lý", f"{stats['usable_ratio']:.1f}%", f"{stats['usable_count']} phản ánh")
    with m3:
        st.metric("Đã bảo mật PII", f"{stats['pii_total']} ca", f"SĐT: {stats['pii_phone']} | Email: {stats['pii_email']}")
    with m4:
        st.metric("Trùng lặp đã lọc", f"{stats['duplicate_count']} ca", f"{stats['duplicate_ratio']:.1f}%")

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # BIỂU ĐỒ TRỰC QUAN
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("##### Phân bổ theo Đơn vị chuyên môn")
        tc = stats["topic_counts"].reset_index()
        tc.columns = ["Chuyên môn", "Số lượng"]
        tc["Tên"] = tc["Chuyên môn"].map(lambda x: TOPIC_VIETNAMESE.get(x, x))

        topic_color_map = {
            "Học phí & Chính sách": "#1d4ed8",
            "Lịch học & Lịch thi": "#0284c7",
            "Điểm số & Khảo thí": "#0f766e",
            "Thủ tục hành chính": "#6366f1",
            "Cơ sở vật chất": "#d97706",
            "Hệ thống CNTT": "#059669",
            "Ý kiến khác": "#64748b",
            "Nội dung không hợp lệ": "#94a3b8"
        }

        fig_pie = px.pie(
            tc,
            names="Tên",
            values="Số lượng",
            hole=0.48,
            color="Tên",
            color_discrete_map=topic_color_map
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
            height=270,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#0f172a")
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.markdown("##### Phân bổ theo Mức độ ưu tiên")
        pc = stats["priority_counts"].reset_index()
        pc.columns = ["Mức ưu tiên", "Số lượng"]
        
        prio_color_map = {
            "Khẩn cấp": "#dc2626",
            "Cao": "#ea580c",
            "Bình thường": "#0284c7",
            "Thấp": "#94a3b8"
        }

        fig_bar = px.bar(
            pc,
            x="Mức ưu tiên",
            y="Số lượng",
            color="Mức ưu tiên",
            color_discrete_map=prio_color_map
        )
        fig_bar.update_layout(
            xaxis_title="",
            yaxis_title="",
            margin=dict(t=10, b=10, l=10, r=10),
            height=270,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#0f172a")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # NÚT XUẤT DỮ LIỆU SẠCH
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    csv_bytes = stats["df_processed"].to_csv(index=False, encoding="utf-8").encode("utf-8")
    st.download_button(
        "Tải bảng dữ liệu đã xử lý và phân loại (CSV)",
        data=csv_bytes,
        file_name="du_lieu_phan_anh_da_xu_ly.csv",
        mime="text/csv",
        use_container_width=True
    )
