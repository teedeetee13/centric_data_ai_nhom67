# -*- coding: utf-8 -*-
"""
Module: app.components.workbench
Giao diện Bàn làm việc cán bộ tối giản (Không Emoji):
- Lọc các ca cần rà soát (Độ tự tin < 0.60 hoặc có cờ cảnh báo PII/trùng lặp).
- So sánh trực quan dữ liệu gốc và dữ liệu sau che PII.
- Thao tác phê duyệt 1 chạm lưu vết kiểm toán vào SQLite.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from src.database import get_connection, log_review_action

ALL_TOPICS = [
    "Hoc_phi", "Lich_hoc_lich_thi", "Diem_khao_thi", 
    "Thu_tuc_hanh_chinh", "Co_so_vat_chat", "He_thong_CNTT", "Khac"
]

TOPIC_VIETNAMESE = {
    "Hoc_phi": "Học phí & Chính sách",
    "Lich_hoc_lich_thi": "Lịch học & Lịch thi",
    "Diem_khao_thi": "Điểm số & Khảo thí",
    "Thu_tuc_hanh_chinh": "Thủ tục hành chính",
    "Co_so_vat_chat": "Cơ sở vật chất",
    "He_thong_CNTT": "Hệ thống CNTT",
    "Khac": "Ý kiến khác"
}

def load_review_queue():
    """Tải các yêu cầu cần duyệt từ SQLite."""
    conn = get_connection()
    query = """
    SELECT * FROM processed_requests 
    WHERE status = 'pending_review' 
       OR confidence_score < 0.60 
       OR quality_flags LIKE '%near_duplicate%'
       OR quality_flags LIKE '%has_%'
    ORDER BY 
        CASE priority_level 
            WHEN 'Khẩn cấp' THEN 1 
            WHEN 'Cao' THEN 2 
            WHEN 'Bình thường' THEN 3 
            ELSE 4 
        END,
        id DESC
    LIMIT 80
    """
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def render_workbench(faq_engine=None):
    df_queue = load_review_queue()

    if df_queue.empty:
        st.success("Hàng đợi rỗng — Hiện không có phản ánh nào cần rà soát.")
        return

    st.markdown(f"##### Danh sách phản ánh cần rà soát ({len(df_queue)} mục)")

    col_nav, col_detail = st.columns([1, 2], gap="medium")

    with col_nav:
        options = []
        for _, row in df_queue.iterrows():
            label = f"[{row['priority_level']}] [{row['record_id']}] {TOPIC_VIETNAMESE.get(row['predicted_topic'], row['predicted_topic'])}"
            options.append((row["record_id"], label))

        selected_id = st.selectbox(
            "Chọn phản ánh:",
            options=[opt[0] for opt in options],
            format_func=lambda x: next(opt[1] for opt in options if opt[0] == x),
            label_visibility="collapsed"
        )

        item = df_queue[df_queue["record_id"] == selected_id].iloc[0]

        # Thông tin tóm tắt tối giản
        conf = float(item["confidence_score"])
        st.markdown(f"**Mã:** `{item['record_id']}` | **Ưu tiên:** `{item['priority_level']}`")
        st.markdown(f"**Độ tự tin AI:** `{conf*100:.1f}%`")
        st.progress(conf)
        if item["quality_flags"] and item["quality_flags"] != "CLEAN":
            st.caption(f"Cờ cảnh báo: `{item['quality_flags']}`")

    with col_detail:
        # So sánh nội dung trước và sau làm sạch
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Văn bản gốc:")
            st.text_area("Gốc", value=item["raw_text"], height=90, disabled=True, label_visibility="collapsed")
        with c2:
            st.caption("Đã chuẩn hóa & Che PII:")
            st.text_area("Sạch", value=item["clean_text"], height=90, disabled=True, label_visibility="collapsed")

        # Căn cứ quy chế nếu có
        if item.get("matched_kb_id") and pd.notna(item["matched_kb_id"]):
            st.caption(f"Căn cứ quy chế trích xuất: **{item['matched_kb_id']}**")

        # Điều chỉnh phân loại & soạn thảo phản hồi
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            curr_idx = ALL_TOPICS.index(item["predicted_topic"]) if item["predicted_topic"] in ALL_TOPICS else 0
            final_topic = st.selectbox(
                "Phân loại chính thức:",
                options=ALL_TOPICS,
                index=curr_idx,
                format_func=lambda x: f"{x} - {TOPIC_VIETNAMESE.get(x, '')}"
            )
        with f_col2:
            notes = st.text_input("Ghi chú cán bộ:", placeholder="Ví dụ: Đã kiểm tra...")

        draft_val = item["draft_response"] if pd.notna(item["draft_response"]) and item["draft_response"] != "" else (
            f"Chào bạn,\nBộ phận hỗ trợ đã tiếp nhận phản ánh của bạn về vấn đề {TOPIC_VIETNAMESE.get(final_topic, final_topic)}.\nTrân trọng."
        )

        response_text = st.text_area("Nội dung phản hồi sinh viên:", value=draft_val, height=130)

        # 3 nút hành động tối giản không emoji
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Duyệt & Gửi", use_container_width=True, type="primary"):
                log_review_action(selected_id, "approve", item["predicted_topic"], final_topic, response_text, notes)
                st.toast(f"Đã duyệt {selected_id} thành công!")
                st.rerun()
        with b2:
            if st.button("Đổi nhãn & Duyệt", use_container_width=True):
                log_review_action(selected_id, "edit_label", item["predicted_topic"], final_topic, response_text, notes)
                st.toast(f"Đã cập nhật nhãn cho {selected_id}!")
                st.rerun()
        with b3:
            if st.button("Từ chối / Spam", use_container_width=True):
                log_review_action(selected_id, "reject", item["predicted_topic"], final_topic, "Từ chối do spam.", notes)
                st.toast(f"Đã từ chối {selected_id}!")
                st.rerun()
