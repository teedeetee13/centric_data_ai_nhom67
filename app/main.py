# -*- coding: utf-8 -*-
"""
EduSupportAI - Giao diện tối giản (Không Emoji)
Hệ thống nâng cao chất lượng dữ liệu & Phân luồng phản ánh học vụ
"""

import os
import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc dự án luôn nằm trong sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import sqlite3
import pandas as pd
import streamlit as st

from src.cleaner import clean_text_single, run_cleaning_pipeline
from src.model import EduSupportClassifier
from src.faq_engine import FAQEngine
from src.database import init_db, sync_kb_from_csv, get_connection
from app.components.workbench import render_workbench
from app.components.dashboard import render_dashboard

# Cấu hình giao diện Streamlit gọn gàng, không emoji
st.set_page_config(
    page_title="EduSupportAI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS phong cách tối giản (clean & modern)
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    .app-header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        border-bottom: 1px solid #e9ecef;
        padding-bottom: 0.6rem;
        margin-bottom: 1.2rem;
    }
    .app-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.9rem;
        color: #64748b;
        margin: 0;
    }
    .status-tag {
        font-size: 0.8rem;
        color: #059669;
        background-color: #ecfdf5;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 500;
    }
    .card-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_system():
    init_db()
    sync_kb_from_csv()
    model_path = "models/best_classifier.joblib"
    if not os.path.exists(model_path):
        from src.model import train_and_save_production_model
        clf = train_and_save_production_model()
    else:
        clf = EduSupportClassifier().load(model_path)
    faq_eng = FAQEngine()
    return clf, faq_eng

clf_model, faq_engine = load_system()

# HEADER TỐI GIẢN (KHÔNG EMOJI)
st.markdown("""
<div class="app-header">
    <div>
        <h1 class="app-title">EduSupportAI</h1>
        <p class="app-subtitle">Hệ thống phân luồng phản ánh sinh viên & Chuẩn hóa dữ liệu (Data-Centric AI)</p>
    </div>
    <div class="status-tag">Trực tuyến</div>
</div>
""", unsafe_allow_html=True)

# SIDEBAR GỌN GÀNG
with st.sidebar:
    st.markdown("##### Quản trị hệ thống")
    st.caption("Mô hình: TF-IDF + Logistic Regression\nCSDL: SQLite local")
    
    with st.expander("Tác vụ dữ liệu & Mô hình"):
        if st.button("Tạo lại 424 mẫu kịch bản", use_container_width=True):
            from src.data_generator import generate_synthetic_dataset
            generate_synthetic_dataset()
            st.toast("Đã tạo mới 424 bản ghi!")

        if st.button("Chạy lại Pipeline làm sạch", use_container_width=True):
            run_cleaning_pipeline()
            st.toast("Đã chuẩn hóa và che PII thành công!")

        if st.button("Huấn luyện lại mô hình", use_container_width=True):
            from src.model import train_and_save_production_model
            train_and_save_production_model()
            st.toast("Đã cập nhật trọng số mô hình mới!")

# 3 TABS TẬP TRUNG NGHIỆP VỤ (KHÔNG EMOJI)
tab_process, tab_review, tab_analytics = st.tabs([
    "Xử lý phản ánh",
    "Bàn duyệt cán bộ",
    "Thống kê & Dữ liệu"
])

# -----------------------------------------------------------------------------
# TAB 1: XỬ LÝ PHẢN ÁNH
# -----------------------------------------------------------------------------
with tab_process:
    sample_scenarios = [
        ("-- Chọn kịch bản kiểm thử mẫu thực tế --", ""),
        ("1. [Khẩn cấp + PII] Trùng ca thi kết thúc học phần (Kèm SĐT, MSSV)", 
         "Dạ em chào thầy cô, lịch thi kết thúc học phần môn Mạng máy tính và Hệ điều hành của em bị trùng ca thi lúc 7h30 sáng ngày 20/10 tại nhà B. Sđt em 0987123456, mssv 2022601234, cứu em với gấp ạ!"),
        ("2. [Học phí + PII] Đóng học phí qua ngân hàng cổng vẫn báo nợ (Kèm SĐT, MSSV)", 
         "Em đã đóng học phí 8.500.000đ qua ngân hàng từ hôm qua nhưng cổng vẫn báo chưa nộp, số điện thoại em 0987654321, mssv 2022601234, mong phòng tài chính kiểm tra giúp em."),
        ("3. [Khảo thí] Phúc khảo điểm thi kết thúc học phần bị chấm sai", 
         "Điểm thi môn Trí tuệ nhân tạo của em trên cổng bị sai 2.0, trong khi bài làm của em đạt yêu cầu, em muốn nộp đơn phúc khảo bài thi thì nộp ở đâu ạ?"),
        ("4. [Hành chính] Xin giấy xác nhận sinh viên tạm hoãn nghĩa vụ quân sự", 
         "Em cần xin giấy xác nhận sinh viên đang theo học tại trường để làm thủ tục tạm hoãn nghĩa vụ quân sự ở quê thì làm đơn online hay đến trực tiếp phòng nào ạ?"),
        ("5. [Cơ sở vật chất] Hỏng điều hòa và máy chiếu phòng học giảng đường", 
         "Điều hòa phòng 305 nhà C bị hỏng chảy nước lênh láng, máy chiếu cũng không bật lên được, cả lớp không học được mong nhà trường khắc phục."),
        ("6. [Hệ thống CNTT] Quên mật khẩu cổng thông tin sinh viên", 
         "Em quên mật khẩu đăng nhập cổng daotao.eaut.edu.vn, ấn quên pass nhưng không thấy gửi mã xác thực về email sv.eaut@student.edu.vn."),
        ("7. [Lọc rác Data-Centric] Phản ánh quá ngắn / rác (Dưới 12 ký tự)", 
         "Học phí"),
        ("8. [Độ tự tin thấp] Câu hỏi đa ý học vụ cần Cán bộ duyệt", 
         "Em muốn hỏi vừa xin gia hạn nộp học phí vừa xin đổi lịch thi học kỳ phụ thì làm đơn chung được không ạ?")
    ]

    col_input, col_sample = st.columns([3, 2], gap="medium")
    with col_sample:
        st.caption("Hoặc chọn kịch bản mẫu kiểm thử nhanh:")
        chosen_idx = st.selectbox(
            "Chọn câu mẫu:",
            options=list(range(len(sample_scenarios))),
            format_func=lambda i: sample_scenarios[i][0],
            label_visibility="collapsed"
        )
        selected_text = sample_scenarios[chosen_idx][1]

    with col_input:
        user_text = st.text_area(
            "Nội dung phản ánh:",
            value=selected_text,
            placeholder="Nhập câu hỏi, thắc mắc hoặc phản ánh của sinh viên...",
            height=90,
            label_visibility="collapsed"
        )

    btn_analyze = st.button("Phân tích ngay", type="primary")

    if btn_analyze and user_text.strip():
        # 1. Pipeline Làm sạch & Che PII
        clean_res = clean_text_single(user_text)
        clean_t = clean_res["clean_text"]
        flags = clean_res["quality_flags"]
        is_usable = clean_res["is_usable"]

        # 2. Suy luận AI
        if is_usable:
            pred_res = clf_model.predict_single(clean_t)
            pred_topic = pred_res["predicted_topic"]
            conf = pred_res["confidence_score"]
            prio = pred_res["priority_level"]
            needs_review = pred_res["needs_review"]
            draft_res = faq_engine.generate_draft_response(clean_t, predicted_topic=pred_topic)
        else:
            pred_topic = "Không hợp lệ"
            conf = 0.0
            prio = "Thấp"
            needs_review = True
            draft_res = {
                "matched_kb_id": None,
                "draft_text": "Nội dung quá ngắn (dưới 12 ký tự) hoặc không hợp lệ. Vui lòng cung cấp thêm thông tin.",
                "department": "Bộ phận tiếp nhận"
            }

        st.markdown("---")
        
        # 3 Thẻ chỉ số kết quả
        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric("Chuyên môn điều phối", pred_topic)
        with r2:
            st.metric("Mức độ ưu tiên", prio)
        with r3:
            st.metric("Độ tự tin AI", f"{conf*100:.1f}%")
            st.progress(conf)

        if needs_review:
            st.warning("Độ tự tin dưới 60% hoặc có cờ nhạy cảm — Yêu cầu đã được chuyển vào Bàn duyệt cán bộ.")

        # So sánh dữ liệu sạch và bản nháp
        c_clean, c_draft = st.columns(2, gap="medium")
        with c_clean:
            st.markdown("##### Văn bản đã chuẩn hóa & Che PII:")
            st.info(clean_t)
            if flags:
                st.caption(f"Cờ phát hiện: {', '.join(flags)}")
        
        with c_draft:
            st.markdown(f"##### Bản nháp phản hồi ({draft_res.get('department', 'Bộ phận chức năng')}):")
            st.text_area("Bản nháp", value=draft_res["draft_text"], height=160, label_visibility="collapsed")

    # Tùy chọn nạp hàng loạt gọn gàng trong expander
    st.markdown("---")
    with st.expander("Tùy chọn nạp dữ liệu hàng loạt vào Hàng đợi SQLite"):
        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            st.write("Nạp toàn bộ tập dữ liệu đã làm sạch vào cơ sở dữ liệu để phục vụ kiểm duyệt của cán bộ.")
        with col_b2:
            if st.button("Nạp dữ liệu vào Hàng đợi", use_container_width=True):
                clean_path = "data/processed/dataset_clean.csv"
                if not os.path.exists(clean_path):
                    run_cleaning_pipeline()
                df_clean = pd.read_csv(clean_path)
                conn = get_connection()
                cursor = conn.cursor()
                count = 0
                for _, r in df_clean.iterrows():
                    if r["is_usable"]:
                        p = clf_model.predict_single(r["clean_text"])
                        d = faq_engine.generate_draft_response(r["clean_text"], predicted_topic=p["predicted_topic"])
                        p_top, p_conf, p_prio = p["predicted_topic"], p["confidence_score"], p["priority_level"]
                        d_txt, d_kb = d["draft_text"], d["matched_kb_id"]
                    else:
                        p_top, p_conf, p_prio = "Khac", 0.0, "Thấp"
                        d_txt, d_kb = "Câu hỏi không hợp lệ.", None

                    cursor.execute("""
                    INSERT OR REPLACE INTO processed_requests 
                    (record_id, raw_text, clean_text, quality_flags, is_usable, predicted_topic, confidence_score, priority_level, matched_kb_id, draft_response, status, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', datetime('now'))
                    """, (r["record_id"], r["raw_text"], r["clean_text"], r["quality_flags"], int(r["is_usable"]), p_top, p_conf, p_prio, d_kb, d_txt))
                    count += 1
                conn.commit()
                conn.close()
                st.toast(f"Đã nạp thành công {count} bản ghi!")

# -----------------------------------------------------------------------------
# TAB 2: BÀN DUYỆT CÁN BỘ
# -----------------------------------------------------------------------------
with tab_review:
    render_workbench(faq_engine=faq_engine)

# -----------------------------------------------------------------------------
# TAB 3: THỐNG KÊ & DỮ LIỆU THỰC TẾ
# -----------------------------------------------------------------------------
with tab_analytics:
    render_dashboard(clf_model=clf_model)
