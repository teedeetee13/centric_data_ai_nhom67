# -*- coding: utf-8 -*-
"""
Module: app.components.trace_viewer
Thành phần giao diện trực quan hóa toàn bộ quá trình xử lý, suy luận nội tâm
và kiểm định rào chắn của Local Learning Machine / LLM cho mọi tính năng:
- Trang Tiếp nhận phản ánh sinh viên (Tab 0)
- Bàn duyệt cán bộ (Tab 1)
- Trung tâm tri thức data-doc (Tab 2)
- Lịch sử kiểm toán & Vết thực thi (Tab 3)
"""

import pandas as pd
import streamlit as st
from src.config import TOPICS
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

DEPT_NAMES = {
    "Co_so_vat_chat": "Phòng Quản trị Cơ sở vật chất",
    "Thu_tuc_hanh_chinh": "Phòng Công tác sinh viên",
    "Lich_hoc_lich_thi": "Phòng Quản lý Đào tạo & Khảo thí",
    "Diem_khao_thi": "Phòng Quản lý Đào tạo & Khảo thí",
    "Hoc_phi": "Phòng Tài chính - Kế toán",
    "He_thong_CNTT": "Trung tâm Công nghệ thông tin",
    "Khac": "Bộ phận Tiếp nhận chung"
}

def render_trace_view(trace_data: dict, terminal_log: str = "", title: str = "Nhật Ký Thực Thi & Suy Luận Chi Tiết Của Máy Học (Execution & LLM Trace)", expanded: bool = True, key_prefix: str = "trace"):
    """
    Hiển thị toàn bộ thông số xử lý, chuỗi suy luận nội tâm và rào chắn của Model
    một cách rõ ràng, chi tiết, chuyên nghiệp trên giao diện Streamlit.
    """
    if not trace_data:
        st.info("Chưa có dữ liệu vết thực thi (Execution Trace) cho yêu cầu này.")
        return

    trace_id = trace_data.get("trace_id", "TRACE-LOCAL")
    record_id = trace_data.get("record_id", "")
    total_ms = trace_data.get("total_duration_ms", 0.0)
    start_time = trace_data.get("start_time", "")
    steps = trace_data.get("steps", [])

    steps_by_num = {s.get("step_number"): s for s in steps}

    with st.expander(f"🔬 {title} (`{trace_id}`)", expanded=expanded):
        # 1. Khung tổng quan trạng thái sapphire
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <span style="font-size: 0.82rem; font-weight: 700; color: #0f172a;">
                    TRACE ID: <code style="color: #1d4ed8; background: #eff6ff; padding: 2px 6px; border-radius: 4px;">{trace_id}</code>
                    {f" | MÃ YÊU CẦU: <strong>{record_id}</strong>" if record_id else ""}
                </span>
                <span style="font-size: 0.80rem; color: #475569;">
                    ⏱️ Tổng độ trễ toàn trình: <strong style="color: #047857;">{total_ms:.2f} ms</strong> | Thời điểm: <code>{format_datetime_vn(start_time)}</code>
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_analysis, tab_terminal, tab_json = st.tabs([
            "📊 Phân Tích Chuyên Sâu 5 Bước Của Model",
            "🖥️ Console Terminal Trace (Chi Tiết Toàn Bộ Log)",
            "📦 Cấu Trúc Dữ Liệu JSON"
        ])

        # =====================================================================
        # TAB 1: PHÂN TÍCH CHUYÊN SÂU TỪNG BƯỚC XỬ LÝ NỘI TÂM
        # =====================================================================
        with tab_analysis:
            # -------------------------------------------------------------
            # BƯỚC 1: TIỀN XỬ LÝ & BẢO MẬT PII
            # -------------------------------------------------------------
            s1 = steps_by_num.get(1, {})
            s1_details = s1.get("details", {})
            st.markdown(f"##### 1. Tiếp nhận, Chuẩn hóa Unicode NFC & Lọc thông tin định danh (PII)")
            c_s1_a, c_s1_b, c_s1_c = st.columns(3)
            with c_s1_a:
                st.metric("Thời gian xử lý Bước 1", f"{s1.get('duration_ms', 0.0):.2f} ms")
            with c_s1_b:
                flags = s1_details.get("quality_flags", [])
                st.metric("Cờ kiểm soát chất lượng", ", ".join(flags) if flags else "CLEAN (Đạt chuẩn)")
            with c_s1_c:
                st.metric("Tính khả dụng dữ liệu", "HỢP LỆ (Sẵn sàng)" if s1_details.get("is_usable", True) else "KHÔNG HỢP LỆ")

            if s1.get("logs"):
                with st.expander("Chi tiết nhật ký Bước 1", expanded=False):
                    for l in s1.get("logs", []):
                        st.caption(f"• {l}")

            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #e2e8f0;'/>", unsafe_allow_html=True)

            # -------------------------------------------------------------
            # BƯỚC 2: QUÁ TRÌNH SUY LUẬN PHÂN LOẠI & XÁC SUẤT TỪNG LỚP
            # -------------------------------------------------------------
            s2 = steps_by_num.get(2, {})
            s2_details = s2.get("details", {})
            pred_topic = s2_details.get("predicted_topic", "Khac")
            conf = s2_details.get("confidence_score", 0.0)
            prio = s2_details.get("priority_level", "Bình thường")
            prio_reason = s2_details.get("priority_reason", "Rà soát thường quy")
            all_probs = s2_details.get("all_probabilities") or s2_details.get("top_3_probabilities") or {}

            st.markdown(f"##### 2. Quá trình Máy học Phân loại & Phân phối Xác suất (Classifier Internals)")
            c_s2_a, c_s2_b, c_s2_c = st.columns(3)
            with c_s2_a:
                st.metric("Chủ đề quyết định (Top-1)", f"{TOPICS.get(pred_topic, pred_topic)}")
            with c_s2_b:
                st.metric("Độ tự tin (Confidence)", f"{conf:.1%}")
            with c_s2_c:
                st.metric("Mức ưu tiên nghiệp vụ", f"{prio}")

            st.caption(f"**Lý do xếp mức ưu tiên:** *{prio_reason}*")

            # Hiển thị bảng và thanh xác suất phân loại
            if all_probs:
                st.markdown("**Bảng phân phối xác suất mô hình cho từng nhóm chuyên môn:**")
                prob_rows = []
                for t_name, p_val in sorted(all_probs.items(), key=lambda x: x[1], reverse=True):
                    prob_rows.append({
                        "Mã chủ đề": t_name,
                        "Tên chuyên môn": TOPICS.get(t_name, t_name),
                        "Đơn vị phụ trách": DEPT_NAMES.get(t_name, "Bộ phận Tiếp nhận"),
                        "Xác suất dự đoán": f"{p_val:.2%}",
                        "Tỷ lệ": p_val
                    })
                df_prob = pd.DataFrame(prob_rows)
                st.dataframe(
                    df_prob[["Tên chuyên môn", "Đơn vị phụ trách", "Xác suất dự đoán"]],
                    width="stretch",
                    hide_index=True
                )

            if s2.get("logs"):
                with st.expander("Chi tiết nhật ký Bước 2", expanded=False):
                    for l in s2.get("logs", []):
                        st.caption(f"• {l}")

            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #e2e8f0;'/>", unsafe_allow_html=True)

            # -------------------------------------------------------------
            # BƯỚC 3: TÍNH TOÁN KHÔNG GIAN VECTOR & TRA CỨU QUY TRÌNH DOCX
            # -------------------------------------------------------------
            s3 = steps_by_num.get(3, {})
            s3_details = s3.get("details", {})
            st.markdown(f"##### 3. Tính toán Vector & Đối chiếu Quy trình từ 3 File DOCX (Vector Search)")
            c_s3_a, c_s3_b = st.columns([1, 1])
            with c_s3_a:
                st.markdown(f"**Quy trình khớp tối ưu:** `{s3_details.get('proc_id', 'N/A')} — {s3_details.get('title', 'N/A')}`")
                st.markdown(f"**Căn cứ văn bản pháp lý:** `{s3_details.get('legal_basis', 'Quy định Nhà trường')}`")
            with c_s3_b:
                st.markdown(f"**Đơn vị giải quyết:** `{s3_details.get('department', 'Bộ phận Tiếp nhận')}`")
                st.markdown(f"**Thời hạn xử lý (SLA):** `{s3_details.get('processing_time', 'Theo quy định')}`")

            candidates = s3_details.get("candidate_procedures", [])
            if candidates:
                st.markdown("**Bảng điểm số đối sánh Cosine Similarity các quy trình ứng viên:**")
                cand_rows = []
                for c in candidates:
                    cand_rows.append({
                        "Mã quy trình": c.get("proc_id"),
                        "Tên quy trình nghiệp vụ": c.get("title"),
                        "Tệp Word nguồn": c.get("doc_source", "").split("/")[-1],
                        "Độ tương đồng Cosine": f"{c.get('similarity_score', 0):.2%}",
                        "Tổng điểm xếp hạng": f"{c.get('rank_score', 0):.2%}"
                    })
                st.dataframe(pd.DataFrame(cand_rows), width="stretch", hide_index=True)

            if s3.get("logs"):
                with st.expander("Chi tiết nhật ký Bước 3", expanded=False):
                    for l in s3.get("logs", []):
                        st.caption(f"• {l}")

            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #e2e8f0;'/>", unsafe_allow_html=True)

            # -------------------------------------------------------------
            # BƯỚC 4: CHUỖI SUY LUẬN NỘI TÂM CHAIN-OF-THOUGHT
            # -------------------------------------------------------------
            s4 = steps_by_num.get(4, {})
            s4_details = s4.get("details", {})
            st.markdown(f"##### 4. Chuỗi Suy luận Nội tâm Chain-of-Thought & Tổng hợp Lời giải (CoT)")
            cot_logs = [l for l in s4.get("logs", []) if "Suy luận" in l] or s4_details.get("reasoning_steps", [])
            if cot_logs:
                for c_log in cot_logs:
                    clean_msg = c_log.split("] ", 1)[-1] if "] " in c_log else c_log
                    st.markdown(f"""
                    <div style="background: #f8fafc; border-left: 3px solid #3b82f6; border-radius: 4px; padding: 6px 12px; margin-bottom: 6px; font-size: 0.86rem; color: #1e293b;">
                        {clean_msg}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Chưa có chuỗi suy luận chi tiết.")

            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #e2e8f0;'/>", unsafe_allow_html=True)

            # -------------------------------------------------------------
            # BƯỚC 5: RÀO CHẮN AN TOÀN & RA QUYẾT ĐỊNH
            # -------------------------------------------------------------
            s5 = steps_by_num.get(5, {})
            s5_details = s5.get("details", {})
            st.markdown(f"##### 5. Rào chắn An toàn & Quyết định Phân luồng (Guardrails & Dispatch)")
            
            checks = s5_details.get("guardrail_checks", {})
            if checks:
                check_rows = []
                for k, c_info in checks.items():
                    passed = c_info.get("passed", False)
                    check_rows.append({
                        "Tiêu chí kiểm định an toàn": c_info.get("rule", k),
                        "Trạng thái": "✅ ĐẠT YÊU CẦU" if passed else "⚠️ CẦN XÁC MINH",
                        "Ghi chú kiểm tra": str(c_info.get("score") or c_info.get("procedure") or c_info.get("level") or "Hợp lệ")
                    })
                st.dataframe(pd.DataFrame(check_rows), width="stretch", hide_index=True)

            reasons = s5_details.get("review_reasons", [])
            dispatch_status = s5_details.get("final_dispatch") or ("TỰ ĐỘNG PHÊ DUYỆT" if s5.get("status") == "AUTO_APPROVED" else "CHUYỂN BÀN DUYỆT CÁN BỘ")
            
            if reasons:
                st.warning(f"**Lý do cần cán bộ rà soát:** {' | '.join(reasons)}")
            else:
                st.success(f"**Quyết định phân luồng cuối cùng:** `{dispatch_status}`")

        # =====================================================================
        # TAB 2: CONSOLE TERMINAL EXECUTION TRACE
        # =====================================================================
        with tab_terminal:
            log_content = terminal_log or trace_data.get("terminal_log") or ""
            if not log_content and steps:
                # Tạo log terminal từ steps nếu chưa có sẵn
                lines = [
                    "=" * 80,
                    "EDUSUPPORT-AI :: LOCAL LEARNING MACHINE EXECUTION TRACE LOG",
                    f"Trace ID  : {trace_id} | Record ID: {record_id or 'N/A'}",
                    f"Timestamp : {start_time} | Total Latency: {total_ms:.2f} ms",
                    "=" * 80
                ]
                for s in steps:
                    status_tag = "[OK]" if s.get("status") in ("SUCCESS", "AUTO_APPROVED") else "[WAIT]"
                    lines.append(f"{status_tag} BƯỚC {s.get('step_number')}: {s.get('name')} ({s.get('duration_ms', 0):.2f} ms)")
                    lines.append(f"     Mục tiêu: {s.get('description')}")
                    for lg in s.get("logs", []):
                        lines.append(f"     > {lg}")
                    for dk, dv in s.get("details", {}).items():
                        lines.append(f"     * {dk}: {dv}")
                    lines.append("-" * 80)
                lines.append(f"HOÀN TẤT CHUỖI XỬ LÝ (5 BƯỚC) TRONG {total_ms:.2f} MS")
                lines.append("=" * 80)
                log_content = "\n".join(lines)

            st.text_area("Toàn bộ nhật ký thực thi dòng lệnh (Console Output):", value=log_content, height=360, disabled=True, key=f"{key_prefix}_term_out")

        # =====================================================================
        # TAB 3: DỮ LIỆU CẤU TRÚC JSON
        # =====================================================================
        with tab_json:
            st.json(trace_data)
