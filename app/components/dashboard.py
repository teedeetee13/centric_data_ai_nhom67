# -*- coding: utf-8 -*-
"""
Module: app.components.dashboard
Thống kê & Phân tích chất lượng dữ liệu thực tế (Không số liệu giả định).
Hỗ trợ:
1. Tải lên tệp dữ liệu thực tế (.xlsx, .csv) để phân tích trực tiếp.
2. Thống kê từ dữ liệu tiếp nhận thực tế trong CSDL SQLite.
3. Xem tập dữ liệu kiểm thử kỹ thuật khi cần.
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
    "Hoc_phi": "Học phí",
    "Lich_hoc_lich_thi": "Lịch thi & Lịch học",
    "Diem_khao_thi": "Khảo thí & Điểm",
    "Thu_tuc_hanh_chinh": "Thủ tục 1 cửa",
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

    # 1. Đo lường rỗng & quá ngắn
    empty_count = int((texts.str.strip() == "").sum() + df[text_col].isna().sum())
    short_count = int((texts.apply(len) < 12).sum())

    # 2. Đo lường trùng lặp thực tế
    duplicate_count = int(texts.duplicated().sum())

    # 3. Quét thông tin cá nhân (PII) thực tế bằng Regex
    pii_phone_count = int(texts.str.contains(r'0[3|5|7|8|9]\d{8}').sum())
    pii_email_count = int(texts.str.contains(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+').sum())
    pii_mssv_count = int(texts.str.contains(r'20\d{6}').sum())
    pii_total_records = int(((texts.str.contains(r'0[3|5|7|8|9]\d{8}')) | 
                            (texts.str.contains(r'@[a-zA-Z0-9-]+\.')) | 
                            (texts.str.contains(r'20\d{6}'))).sum())

    # 4. Dự đoán chuyên môn thực tế nếu chưa có nhãn
    if "predicted_topic" in df.columns:
        topic_series = df["predicted_topic"]
    elif "target_label_gold" in df.columns:
        topic_series = df["target_label_gold"]
    elif clf_model is not None:
        topic_series = texts.apply(lambda t: clf_model.predict_single(clean_text_single(t)["clean_text"])["predicted_topic"] if len(t) >= 12 else "Khac")
    else:
        topic_series = pd.Series(["Chưa phân loại"] * total)

    # 5. Mức độ ưu tiên thực tế
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
        "df_processed": df.assign(phan_loai=topic_series, muc_uu_tien=prio_series)
    }

def render_dashboard(clf_model=None):
    st.markdown("##### Nguồn dữ liệu phân tích thống kê")

    data_source = st.radio(
        "Chọn nguồn dữ liệu:",
        options=[
            "Tải lên tệp dữ liệu thực tế (Excel / CSV)",
            "Dữ liệu tiếp nhận thực tế trong CSDL SQLite",
            "Tập dữ liệu kịch bản kiểm thử (Demo)"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )

    df_target = None
    text_column = None

    # NGUỒN 1: TẢI LÊN TỆP THỰC TẾ
    if data_source == "Tải lên tệp dữ liệu thực tế (Excel / CSV)":
        c_up1, c_up2 = st.columns([3, 2], gap="medium")
        with c_up1:
            uploaded_file = st.file_uploader(
                "Tải lên tệp phản ánh của sinh viên (.xlsx hoặc .csv):",
                type=["csv", "xlsx"]
            )
        with c_up2:
            st.caption("Hoặc thử nghiệm nhanh với dữ liệu thực tế EAUT:")
            sample_real_path = "data/mau_phan_anh_thuc_te_eaut.csv"
            if os.path.exists(sample_real_path):
                with open(sample_real_path, "rb") as f_samp:
                    st.download_button(
                        "Tải tệp 50 phản ánh mẫu thực tế (.csv)",
                        data=f_samp.read(),
                        file_name="mau_phan_anh_thuc_te_eaut.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                if st.button("Nạp trực tiếp 50 phản ánh thực tế EAUT", use_container_width=True):
                    st.session_state["use_sample_real"] = True

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_target = pd.read_csv(uploaded_file)
                else:
                    df_target = pd.read_excel(uploaded_file)
                
                # Tự động tìm cột văn bản phù hợp
                possible_cols = [c for c in df_target.columns if any(k in str(c).lower() for k in ["text", "noi_dung", "cau_hoi", "phan_anh", "content", "tin_nhan"])]
                text_column = possible_cols[0] if possible_cols else df_target.columns[0]

                st.caption(f"Đã nạp tệp **{uploaded_file.name}** gồm **{len(df_target):,}** dòng. Cột văn bản phân tích: `{text_column}`")
            except Exception as e:
                st.error(f"Lỗi khi đọc tệp: {e}")
                return
        elif st.session_state.get("use_sample_real", False) and os.path.exists(sample_real_path):
            df_target = pd.read_csv(sample_real_path)
            text_column = "raw_text"
            st.caption(f"Đang hiển thị phân tích trực tiếp từ tệp mẫu thực tế EAUT: **{sample_real_path}** ({len(df_target)} bản ghi).")
        else:
            st.info("Chưa có tệp dữ liệu nào được tải lên. Vui lòng chọn tệp CSV/Excel từ máy tính hoặc bấm nút 'Nạp trực tiếp 50 phản ánh thực tế EAUT' ở trên.")
            return

    # NGUỒN 2: DỮ LIỆU TIẾP NHẬN TRONG SQLITE
    elif data_source == "Dữ liệu tiếp nhận thực tế trong CSDL SQLite":
        conn = get_connection()
        try:
            df_target = pd.read_sql_query("SELECT * FROM processed_requests", conn)
            reviewed_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM review_logs", conn)["cnt"].iloc[0]
        except Exception:
            df_target = pd.DataFrame()
            reviewed_count = 0
        finally:
            conn.close()

        if df_target.empty:
            st.info("Hiện chưa có phản ánh nào được lưu trong cơ sở dữ liệu SQLite. Bạn có thể gửi phản ánh ở Tab 'Xử lý phản ánh' hoặc tải lên tệp dữ liệu.")
            return
        else:
            text_column = "clean_text" if "clean_text" in df_target.columns else "raw_text"
            st.caption(f"Đang hiển thị thống kê từ **{len(df_target):,}** bản ghi thực tế được lưu trong cơ sở dữ liệu SQLite.")

    # NGUỒN 3: TẬP DỮ LIỆU KỊCH BẢN KIỂM THỬ
    else:
        test_path = "data/processed/dataset_clean.csv"
        if os.path.exists(test_path):
            df_target = pd.read_csv(test_path)
            text_column = "clean_text"
            st.caption(f"Đang hiển thị dữ liệu kiểm thử kỹ thuật nội bộ ({len(df_target):,} mẫu kịch bản).")
        else:
            st.info("Chưa tìm thấy tập dữ liệu kiểm thử nội bộ.")
            return

    # PHÂN TÍCH THỐNG KÊ THỰC TẾ
    stats = analyze_dataframe_realtime(df_target, text_column, clf_model=clf_model)
    if stats is None:
        st.warning("Tệp dữ liệu không có dòng nào.")
        return

    st.markdown("---")

    # 4 THẺ CHỈ SỐ THỰC TẾ (TÍNH TRỰC TIẾP TỪ DỮ LIỆU)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Tổng số dòng tiếp nhận", f"{stats['total']:,}")
    with m2:
        st.metric("Dữ liệu hợp lệ", f"{stats['usable_ratio']:.1f}%", f"{stats['usable_count']} mẫu")
    with m3:
        st.metric("Phát hiện thông tin cá nhân (PII)", f"{stats['pii_total']} ca", f"SĐT: {stats['pii_phone']} | Email: {stats['pii_email']}")
    with m4:
        st.metric("Số bản ghi trùng lặp", f"{stats['duplicate_count']} ca", f"{stats['duplicate_ratio']:.1f}%")

    st.markdown("---")

    # BIỂU ĐỒ THỰC TẾ
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Phân bổ theo Chuyên môn")
        tc = stats["topic_counts"].reset_index()
        tc.columns = ["Chuyên môn", "Số lượng"]
        tc["Tên"] = tc["Chuyên môn"].map(lambda x: TOPIC_VIETNAMESE.get(x, x))

        fig_pie = px.pie(
            tc,
            names="Tên",
            values="Số lượng",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=280)
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.markdown("##### Phân bổ theo Mức độ ưu tiên")
        pc = stats["priority_counts"].reset_index()
        pc.columns = ["Mức ưu tiên", "Số lượng"]
        
        prio_color_map = {
            "Khẩn cấp": "#e63946",
            "Cao": "#f4a261",
            "Bình thường": "#2a9d8f",
            "Thấp": "#adb5bd"
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
            height=280,
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # XUẤT DỮ LIỆU THỰC TẾ
    st.markdown("---")
    csv_bytes = stats["df_processed"].to_csv(index=False, encoding="utf-8").encode("utf-8")
    st.download_button(
        "Tải kết quả phân tích thống kê (CSV)",
        data=csv_bytes,
        file_name="thong_ke_du_lieu_thuc_te.csv",
        mime="text/csv",
        use_container_width=True
    )
