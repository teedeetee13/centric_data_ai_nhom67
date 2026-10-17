# -*- coding: utf-8 -*-
"""
Module: app.components.workbench
Bàn làm việc cán bộ tiếp nhận & kiểm duyệt (Human-in-the-Loop)
Thiết kế tối giản, trực quan, hỗ trợ xử lý nhanh các phản ánh cần rà soát.
Không emoji - Loại bỏ các thông số kỹ thuật dư thừa.
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
    """Tải các yêu cầu đang chờ xử lý từ SQLite."""
    conn = get_connection()
    query = """
    SELECT * FROM processed_requests 
    WHERE status = 'pending_review'
       AND (confidence_score < 0.60 
           OR quality_flags LIKE '%near_duplicate%'
           OR quality_flags LIKE '%has_%'
           OR priority_level = 'Khẩn cấp')
    ORDER BY 
        CASE priority_level 
            WHEN 'Khẩn cấp' THEN 1 
            WHEN 'Cao' THEN 2 
            WHEN 'Bình thường' THEN 3 
            ELSE 4 
        END,
        id DESC
    LIMIT 60
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
        st.success("Hàng đợi hoàn tất — Hiện không có phản ánh nào cần rà soát thêm.")
        return

    st.markdown(f"##### Hàng đợi cần rà soát ({len(df_queue)} phản ánh đang chờ)")

    col_nav, col_detail = st.columns([1, 2], gap="large")

    with col_nav:
        st.caption("Chọn phản ánh cần xử lý:")
        options = []
        for _, row in df_queue.iterrows():
            label = f"[{row['priority_level']}] {row['record_id']} - {TOPIC_VIETNAMESE.get(row['predicted_topic'], row['predicted_topic'])}"
            options.append((row["record_id"], label))

        selected_id = st.selectbox(
            "Danh sách:",
            options=[opt[0] for opt in options],
            format_func=lambda x: next(opt[1] for opt in options if opt[0] == x),
            label_visibility="collapsed"
        )

        item = df_queue[df_queue["record_id"] == selected_id].iloc[0]

        # Thẻ thông tin nhanh về lý do chuyển rà soát
        reasons = []
        if item["priority_level"] == "Khẩn cấp":
            reasons.append("Ưu tiên Khẩn cấp")
        if item["quality_flags"] and "has_" in str(item["quality_flags"]):
            reasons.append("Chứa thông tin cá nhân (PII)")
        if item["confidence_score"] < 0.60:
            reasons.append("Yêu cầu cần xác minh nghiệp vụ")

        reason_str = " | ".join(reasons) if reasons else "Rà soát thường quy"
        
        st.markdown(f"""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 8px;">
            <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">MÃ PHẢN ÁNH</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">{item['record_id']}</div>
            <div style="font-size: 0.78rem; color: #64748b; font-weight: 600;">LÝ DO CẦN DUYỆT</div>
            <div style="font-size: 0.88rem; color: #b45309; font-weight: 500;">{reason_str}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_detail:
        # So sánh nội dung gốc và nội dung đã che PII
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.caption("Nội dung gửi ban đầu của sinh viên:")
            st.text_area("Gốc", value=item["raw_text"], height=95, disabled=True, label_visibility="collapsed")
        with c2:
            st.caption("Nội dung đã bảo mật thông tin cá nhân:")
            st.text_area("Sạch", value=item["clean_text"], height=95, disabled=True, label_visibility="collapsed")

        # Căn cứ quy chế nếu có
        if item.get("matched_kb_id") and pd.notna(item["matched_kb_id"]):
            st.caption(f"Căn cứ điều khoản trích xuất: **{item['matched_kb_id']}**")

        # Điều chỉnh phân loại & soạn thảo phản hồi
        f_col1, f_col2 = st.columns([1, 1], gap="medium")
        with f_col1:
            curr_idx = ALL_TOPICS.index(item["predicted_topic"]) if item["predicted_topic"] in ALL_TOPICS else 0
            final_topic = st.selectbox(
                "Đơn vị chuyên môn phụ trách:",
                options=ALL_TOPICS,
                index=curr_idx,
                format_func=lambda x: f"{TOPIC_VIETNAMESE.get(x, x)}"
            )
        with f_col2:
            notes = st.text_input("Ghi chú xử lý:", placeholder="Nhập ghi chú nếu có...")

        draft_val = item["draft_response"] if pd.notna(item["draft_response"]) and item["draft_response"] != "" else (
            f"Chào bạn,\nBộ phận hỗ trợ đã tiếp nhận phản ánh của bạn về vấn đề {TOPIC_VIETNAMESE.get(final_topic, final_topic)}.\nTrân trọng."
        )

        st.caption("Nội dung phản hồi chính thức gửi sinh viên:")
        response_text = st.text_area("Nội dung phản hồi", value=draft_val, height=135, label_visibility="collapsed")

        # 3 nút hành động nghiệp vụ dứt khoát
        b1, b2, b3 = st.columns(3, gap="medium")
        with b1:
            if st.button("Duyệt & Gửi phản hồi", use_container_width=True, type="primary"):
                log_review_action(selected_id, "approve", item["predicted_topic"], final_topic, response_text, notes)
                st.toast(f"Đã duyệt và gửi phản hồi cho {selected_id}!")
                st.rerun()
        with b2:
            if st.button("Chuyển đơn vị khác", use_container_width=True):
                log_review_action(selected_id, "edit_label", item["predicted_topic"], final_topic, response_text, notes)
                st.toast(f"Đã chuyển đơn vị xử lý cho {selected_id}!")
                st.rerun()
        with b3:
            if st.button("Từ chối / Tin rác", use_container_width=True):
                log_review_action(selected_id, "reject", item["predicted_topic"], final_topic, "Từ chối do nội dung không hợp lệ.", notes)
                st.toast(f"Đã từ chối {selected_id}!")
                st.rerun()

    # Nhật ký kiểm duyệt gần nhất
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    with st.expander("Lịch sử kiểm duyệt gần đây"):
        conn = get_connection()
        try:
            df_logs = pd.read_sql_query(
                "SELECT id, record_id, officer_action, original_predicted_topic, final_topic, officer_notes, reviewed_at FROM review_logs ORDER BY id DESC LIMIT 15",
                conn
            )
        except Exception:
            df_logs = pd.DataFrame()
        finally:
            conn.close()

        if not df_logs.empty:
            action_map = {
                "approve": "Đã duyệt gửi",
                "edit_label": "Đã đổi đơn vị",
                "reject": "Đã từ chối"
            }
            df_logs["officer_action"] = df_logs["officer_action"].map(lambda a: action_map.get(a, a))
            df_logs["original_predicted_topic"] = df_logs["original_predicted_topic"].map(lambda t: TOPIC_VIETNAMESE.get(t, t))
            df_logs["final_topic"] = df_logs["final_topic"].map(lambda t: TOPIC_VIETNAMESE.get(t, t))
            df_logs.columns = ["STT", "Mã phản ánh", "Hành động", "Đơn vị ban đầu", "Đơn vị chốt", "Ghi chú", "Thời điểm"]
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.caption("Chưa có phản ánh nào được xử lý trong ca làm việc hiện tại.")
