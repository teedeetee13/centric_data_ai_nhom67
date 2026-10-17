# -*- coding: utf-8 -*-
"""
EduSupportAI - Cổng tiếp nhận & Xử lý phản ánh học vụ sinh viên
Giao diện tối giản, trực quan, phục vụ trực tiếp mục đích nghiệp vụ sản phẩm.
Không emoji - Loại bỏ hoàn toàn các cấu phần kỹ thuật nội bộ không cần thiết.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import sqlite3
import pandas as pd
import streamlit as st

from src.cleaner import clean_text_single
from src.model import EduSupportClassifier
from src.faq_engine import FAQEngine
from src.database import init_db, sync_kb_from_csv, get_connection
from app.components.workbench import render_workbench, TOPIC_VIETNAMESE
from app.components.dashboard import render_dashboard

# Cấu hình giao diện Streamlit tập trung nghiệp vụ
st.set_page_config(
    page_title="EduSupportAI - Cổng xử lý phản ánh sinh viên",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS phong cách tối giản, trang nhã, chuyên nghiệp
st.markdown("""
<style>
    /* Font và khoảng cách khung chứa */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1220px;
    }
    
    /* Header chính */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0.9rem;
        margin-bottom: 1.4rem;
    }
    .app-title {
        font-size: 1.55rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .app-subtitle {
        font-size: 0.88rem;
        color: #475569;
        margin-top: 2px;
    }
    .status-badge {
        font-size: 0.78rem;
        font-weight: 600;
        color: #047857;
        background-color: #ecfdf5;
        border: 1px solid #a7f3d0;
        padding: 4px 10px;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
    }

    /* Thẻ tóm tắt kết quả */
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
    }

    /* Badge mức độ ưu tiên */
    .badge-urgent {
        color: #b91c1c;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-high {
        color: #c2410c;
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-normal {
        color: #0369a1;
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-low {
        color: #475569;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Ẩn bớt sidebar mặc định không cần thiết */
    section[data-testid="stSidebar"] {
        display: none;
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

# HEADER ỨNG DỤNG NGHIỆP VỤ
st.markdown("""
<div class="app-header">
    <div>
        <div class="app-title">EduSupportAI</div>
        <div class="app-subtitle">Cổng tiếp nhận, phân loại và xử lý phản ánh học vụ sinh viên</div>
    </div>
    <div class="status-badge">Hệ thống sẵn sàng</div>
</div>
""", unsafe_allow_html=True)

# 3 PHÂN HỆ LÀM VIỆC RÕ RÀNG
tab_process, tab_review, tab_analytics = st.tabs([
    "Tiếp nhận & Xử lý",
    "Bàn duyệt cán bộ",
    "Thống kê phản ánh"
])

# -----------------------------------------------------------------------------
# PHÂN HỆ 1: TIẾP NHẬN & XỬ LÝ PHẢN ÁNH
# -----------------------------------------------------------------------------
with tab_process:
    sample_scenarios = [
        ("-- Chọn kịch bản mẫu kiểm thử nhanh --", ""),
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
        ("7. [Lọc tin rác] Phản ánh quá ngắn / không rõ nội dung", 
         "Học phí"),
        ("8. [Cần cán bộ duyệt] Yêu cầu xin gia hạn và đổi lịch thi chung", 
         "Em muốn hỏi vừa xin gia hạn nộp học phí vừa xin đổi lịch thi học kỳ phụ thì làm đơn chung được không ạ?")
    ]

    col_input, col_sample = st.columns([3, 2], gap="large")
    with col_sample:
        st.caption("Hoặc chọn kịch bản mẫu thử nghiệm:")
        chosen_idx = st.selectbox(
            "Chọn câu mẫu:",
            options=list(range(len(sample_scenarios))),
            format_func=lambda i: sample_scenarios[i][0],
            label_visibility="collapsed"
        )
        selected_text = sample_scenarios[chosen_idx][1]

    with col_input:
        user_text = st.text_area(
            "Nội dung phản ánh từ sinh viên:",
            value=selected_text,
            placeholder="Nhập nội dung phản ánh, thắc mắc hoặc câu hỏi của sinh viên...",
            height=95,
            label_visibility="collapsed"
        )

    btn_analyze = st.button("Xử lý phản ánh", type="primary")

    if btn_analyze and user_text.strip():
        # 1. Pipeline Làm sạch & Che PII
        clean_res = clean_text_single(user_text)
        clean_t = clean_res["clean_text"]
        flags = clean_res["quality_flags"]
        is_usable = clean_res["is_usable"]

        # 2. Xử lý nghiệp vụ & Dự đoán
        if is_usable:
            pred_res = clf_model.predict_single(clean_t)
            raw_topic = pred_res["predicted_topic"]
            topic_vn = TOPIC_VIETNAMESE.get(raw_topic, raw_topic)
            conf = pred_res["confidence_score"]
            prio = pred_res["priority_level"]
            needs_review = pred_res["needs_review"]
            draft_res = faq_engine.generate_draft_response(clean_t, predicted_topic=raw_topic)
            dept_name = draft_res.get("department", "Phòng ban chức năng")
        else:
            raw_topic = "Khac"
            topic_vn = "Nội dung không hợp lệ"
            dept_name = "Bộ phận tiếp nhận"
            conf = 0.0
            prio = "Thấp"
            needs_review = True
            draft_res = {
                "matched_kb_id": None,
                "draft_text": "Nội dung phản ánh quá ngắn (dưới 12 ký tự) hoặc không rõ ràng. Vui lòng cung cấp thêm thông tin cụ thể để nhà trường hỗ trợ.",
                "department": dept_name
            }

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        
        # Hàng 3 chỉ số nghiệp vụ trực quan
        m_col1, m_col2, m_col3 = st.columns([2, 1, 1], gap="medium")
        
        with m_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Đơn vị chuyên môn tiếp nhận</div>
                <div class="metric-val">{dept_name} <span style="font-size: 0.85rem; font-weight: normal; color: #64748b;">({topic_vn})</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col2:
            prio_badge_class = {
                "Khẩn cấp": "badge-urgent",
                "Cao": "badge-high",
                "Bình thường": "badge-normal",
                "Thấp": "badge-low"
            }.get(prio, "badge-normal")
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Mức độ ưu tiên</div>
                <div class="metric-val"><span class="{prio_badge_class}">{prio}</span></div>
            </div>
            """, unsafe_allow_html=True)

        with m_col3:
            status_text = "Cần rà soát" if needs_review else "Tự động đạt chuẩn"
            status_style = "color: #c2410c;" if needs_review else "color: #047857;"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Trạng thái phân luồng</div>
                <div class="metric-val" style="{status_style} font-size: 1rem;">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)

        if needs_review and is_usable:
            st.info("Lưu ý: Phản ánh này có độ tự tin thấp hoặc chứa yếu tố phức tạp, đã được đưa vào danh sách rà soát tại Bàn duyệt cán bộ.")

        # Khu vực làm việc: Bản nháp & Dữ liệu an toàn
        c_draft, c_clean = st.columns([3, 2], gap="large")
        
        with c_draft:
            st.markdown("##### Bản nháp phản hồi đề xuất:")
            st.text_area("Bản nháp", value=draft_res["draft_text"], height=190, label_visibility="collapsed")
            if draft_res.get("matched_kb_id"):
                st.caption(f"Căn cứ điều khoản: **{draft_res['matched_kb_id']}**")
        
        with c_clean:
            st.markdown("##### Nội dung phản ánh đã bảo mật (Che PII):")
            st.text_area("Nội dung sạch", value=clean_t, height=190, disabled=True, label_visibility="collapsed")
            if flags:
                flag_labels = {
                    "has_phone": "Số điện thoại",
                    "has_email": "Email cá nhân",
                    "has_student_id": "Mã sinh viên",
                    "too_short": "Quá ngắn"
                }
                detected_names = [flag_labels.get(f, f) for f in flags]
                st.caption(f"Đã tự động bảo mật: {', '.join(detected_names)}")

# -----------------------------------------------------------------------------
# PHÂN HỆ 2: BÀN DUYỆT CÁN BỘ (HUMAN-IN-THE-LOOP)
# -----------------------------------------------------------------------------
with tab_review:
    render_workbench(faq_engine=faq_engine)

# -----------------------------------------------------------------------------
# PHÂN HỆ 3: THỐNG KÊ PHẢN ÁNH THỰC TẾ
# -----------------------------------------------------------------------------
with tab_analytics:
    render_dashboard(clf_model=clf_model)
