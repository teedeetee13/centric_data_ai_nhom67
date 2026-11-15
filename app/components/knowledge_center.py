# -*- coding: utf-8 -*-
"""
Module: app.components.knowledge_center
Phân hệ Trung tâm Tri thức & Huấn luyện Máy học Cục bộ (data-doc):
- Hiển thị danh mục tài liệu quy trình trong data-doc/ (3 file docx chuẩn hóa)
- Quản lý và tra cứu toàn bộ 15 quy trình nghiệp vụ chính thức EAUT
- TÍCH HỢP TÍNH NĂNG ĐỐI CHIẾU THAM CHIẾU QUY CHẾ:
  + Tra cứu ngữ nghĩa (Semantic search) đối chiếu câu hỏi sinh viên với 3 file DOCX
  + Hiển thị văn bản căn cứ, điều khoản, thời hạn xử lý (SLA), biểu mẫu và trình tự từng bước
  + Cho phép kiểm tra với cả phản ánh thực tế đang chờ duyệt hoặc tình huống mẫu
- Huấn luyện lại Local Learning Machine trực tiếp từ data-doc
"""

import json
import pandas as pd
import streamlit as st

from src.doc_parser import build_procedure_catalog, KB_OUTPUT_JSON, DATA_DOC_DIR
from src.local_machine import get_local_machine
from src.database import sync_procedures_kb, list_requests
try:
    from src.app_logger import app_log
except ImportError:
    def app_log(*args, **kwargs):
        pass

DOCX_MAPPING = {
    "CSVC": "baocao-quanly-csvc-eaut.docx",
    "CTSV": "bao_cao_quy_trinh_nghiep_vu_sinh_vien_eaut.docx",
    "TC": "bao_cao_quy_trinh_nghiep_vu_sinh_vien_eaut.docx",
    "DT": "bao_cao_tong_hop_quy_trinh_dao_tao.docx",
    "IT": "bao_cao_tong_hop_quy_trinh_dao_tao.docx"
}

def get_docx_filename(proc_id: str) -> str:
    for prefix, fname in DOCX_MAPPING.items():
        if prefix in proc_id:
            return fname
    return "bao_cao_tong_hop_quy_trinh_dao_tao.docx"

SAMPLE_SCENARIOS = {
    "🏢 [CSVC] Điều hòa phòng 304 nhà B hỏng chảy nước": "Phòng học 304 nhà B điều hòa bị hỏng chảy nước liên tục làm ướt sàn nhà, nhờ kỹ thuật viên trường kiểm tra sửa chữa gấp.",
    "🏢 [CSVC] Báo hỏng bóng đèn và mượn giảng đường ngoài giờ": "Đèn trần phòng 202 bị chập chập chờn, đồng thời CLB sinh viên muốn mượn phòng này sinh hoạt vào tối thứ 6.",
    "🎓 [CTSV] Xin cấp giấy xác nhận sinh viên làm thẻ xe buýt": "Em là sinh viên K14 muốn xin giấy xác nhận sinh viên tạm thời để nộp làm vé tháng xe buýt học sinh sinh viên.",
    "🎓 [CTSV] Hướng dẫn thủ tục miễn giảm học phí theo Nghị định 81": "Em thuộc diện hộ cận nghèo ở quê, em muốn hỏi hồ sơ và thời hạn nộp giấy tờ để được miễn giảm học phí kỳ này.",
    "📚 [Đào tạo] Xin phúc khảo điểm thi kết thúc học phần": "Em muốn làm đơn xin phúc khảo điểm thi hết môn Lập trình Python vì kết quả thấp hơn nhiều so với bài làm thực tế.",
    "📚 [Đào tạo] Xin bảo lưu kết quả học tập để điều trị y tế": "Em bị ốm phải nằm viện điều trị dài ngày nên muốn xin làm thủ tục bảo lưu kết quả học tập trong học kỳ 1 năm nay."
}

def render_knowledge_center():
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="font-size: 1.15rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">📚 Trung tâm Tri thức Quy chế & Kho Tài liệu Nghiệp vụ</div>
        <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">Quản trị tài liệu quy trình đại học chính thức (data-doc), đối soát căn cứ pháp lý và tra cứu thư viện OPAC</div>
    </div>
    """, unsafe_allow_html=True)

    machine = get_local_machine()
    procedures = machine.procedures or build_procedure_catalog()

    # 1. Thẻ thông số tổng quan
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Tài liệu quy trình gốc</div>
            <div class="metric-val">{len(list(DATA_DOC_DIR.glob('*.docx')))} tệp văn bản</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Quy trình đã chuẩn hóa</div>
            <div class="metric-val">{len(procedures)} quy trình</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Cơ chế đối chiếu tham chiếu</div>
            <div class="metric-val">Semantic Hybrid TF-IDF</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Độ sẵn sàng tham chiếu</div>
            <div class="metric-val" style="color: #047857;">Sẵn sàng 100%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # 2. KHU VỰC ĐỐI CHIẾU & THAM CHIẾU QUY CHẾ TỰ ĐỘNG (MERGED FEATURE)
    st.markdown("### 🔍 Công cụ Đối Chiếu & Tham Chiếu Quy Chế Theo Phản Ánh Thực Tế")
    st.info("Công cụ này cho phép Cán bộ / Giảng viên kiểm tra cách AI đối chiếu nội dung phản ánh của sinh viên với căn cứ pháp lý, tự động trích xuất điều khoản, thời hạn xử lý (SLA), biểu mẫu và tạo dự thảo giải quyết chuẩn.")

    # Lựa chọn nguồn phản ánh: từ hệ thống hoặc nhập tùy ý
    pending_list = list_requests(pending_only=True)
    mode_options = ["Chọn một tình huống mẫu tiêu biểu", "Nhập nội dung phản ánh tùy ý"]
    if pending_list:
        mode_options.insert(0, f"Lấy từ phản ánh thực tế đang chờ duyệt ({len(pending_list)} yêu cầu)")

    selected_mode = st.radio("Chọn nguồn dữ liệu phản ánh để đối chiếu:", options=mode_options, horizontal=True, key="kc_ref_mode")

    query_input = ""
    selected_topic_hint = None

    if "chờ duyệt" in selected_mode and pending_list:
        pending_dict = {f"{r['record_id']} · {r.get('processed_at', '').replace('T', ' ')[:16]} - [{r['predicted_topic']}] {r['clean_text'][:50]}...": r for r in pending_list}
        chosen_label = st.selectbox("Chọn yêu cầu sinh viên đang chờ xử lý:", options=list(pending_dict.keys()), key="kc_pending_sel")
        chosen_req = pending_dict[chosen_label]
        query_input = chosen_req['clean_text']
        selected_topic_hint = chosen_req.get('predicted_topic')
        st.caption(f"Đang đối chiếu cho Mã yêu cầu: **{chosen_req['record_id']}** (Đơn vị: {chosen_req.get('department')})")
    elif "tình huống mẫu" in selected_mode:
        sample_key = st.selectbox("Chọn một tình huống mẫu:", options=list(SAMPLE_SCENARIOS.keys()), key="kc_sample_sel")
        query_input = SAMPLE_SCENARIOS[sample_key]
        st.text_area("Nội dung phản ánh tình huống:", value=query_input, height=75, disabled=True, key="kc_sample_txt")
    else:
        query_input = st.text_area("Nhập nội dung phản ánh hoặc câu hỏi cần đối chiếu quy chế:", 
                                   value="Em muốn làm đơn xin phúc khảo điểm thi học phần Tiếng Anh chuyên ngành vì điểm thấp hơn dự kiến.", 
                                   height=80, key="kc_custom_txt")

    if query_input.strip():
        # Thực hiện đối chiếu ngữ nghĩa với kho 15 quy trình DOCX
        matched_procs = machine.retrieve_procedure(query_input, predicted_topic=selected_topic_hint, top_k=2)

        if matched_procs:
            top_proc = matched_procs[0]
            doc_file = top_proc.get('doc_source') or get_docx_filename(top_proc['proc_id'])
            
            # Sinh dự thảo và chuỗi suy luận bằng Local Machine
            steps_log, synthesized_draft = machine.reason_and_synthesize(
                clean_text=query_input,
                topic=top_proc['topic'],
                matched_procedure=top_proc
            )
            app_log("KNOWLEDGE", "Thực thi đối chiếu tham chiếu quy chế data-doc", f"Khớp: [{top_proc['proc_id']}] {top_proc['title']} ({top_proc.get('similarity_score', 0):.1%})")

            st.markdown("#### Kết quả Đối Chiếu Căn Cứ Quy Chế & Trình Tự Giải Quyết:")
            
            # Khung thẻ kết quả Sapphire & Emerald
            st.markdown(f"""
            <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-left: 6px solid #16a34a; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 0.76rem; font-weight: 700; color: #166534; text-transform: uppercase; letter-spacing: 0.05em;">
                        📄 Căn cứ quy chế chính thức (Nguồn tệp Word: <strong>{doc_file}</strong>)
                    </span>
                    <span style="font-size: 0.78rem; font-weight: 600; color: #15803d; background: #dcfce7; padding: 2px 8px; border-radius: 4px;">
                        Độ tương đồng: {top_proc.get('similarity_score', 0.85):.1%}
                    </span>
                </div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-top: 2px;">
                    [{top_proc['proc_id']}] {top_proc['title']}
                </div>
                <div style="font-size: 0.86rem; color: #334155; margin-top: 6px; line-height: 1.6;">
                    • <strong>Căn cứ văn bản pháp lý:</strong> <code>{top_proc.get('legal_basis', 'Quy định Nhà trường')}</code><br/>
                    • <strong>Đơn vị thụ lý:</strong> <strong>{top_proc.get('department', 'Bộ phận Tiếp nhận')}</strong> &nbsp;|&nbsp; 
                    • <strong>Thời hạn giải quyết (SLA):</strong> <strong>{top_proc.get('processing_time', 'Theo quy định')}</strong><br/>
                    • <strong>Biểu mẫu bắt buộc:</strong> <code>{top_proc.get('forms_required', 'Không yêu cầu')}</code><br/>
                    • <strong>Đối tượng áp dụng:</strong> {top_proc.get('target_users', 'Toàn thể sinh viên')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            c_match1, c_match2 = st.columns([1, 1], gap="medium")
            with c_match1:
                st.markdown("**Trình tự các bước giải quyết theo quy chế:**")
                steps = top_proc.get('steps', [])
                if steps:
                    for s in steps:
                        st.markdown(f"- **Bước {s.get('step')} ({s.get('actor')}):** {s.get('action')}")
                else:
                    st.write(top_proc.get('content_extract', ''))

            with c_match2:
                st.markdown("**Nội dung giải quyết chuẩn hóa tự động gửi sinh viên:**")
                st.text_area("Văn bản phản hồi tự động tổng hợp:", value=synthesized_draft, height=180, disabled=True, key="kc_synth_preview")

            # Nếu còn quy trình tương đồng thứ 2, hiện expander tham khảo phụ
            if len(matched_procs) > 1:
                sub_proc = matched_procs[1]
                sub_file = sub_proc.get('doc_source') or get_docx_filename(sub_proc['proc_id'])
                with st.expander(f"📌 Quy trình liên quan khác: [{sub_proc['proc_id']}] {sub_proc['title']} (Nguồn: {sub_file})", expanded=False):
                    st.write(f"- **Căn cứ:** {sub_proc.get('legal_basis')}")
                    st.write(f"- **Thời hạn:** {sub_proc.get('processing_time')}")
                    st.write(f"- **Biểu mẫu:** {sub_proc.get('forms_required')}")
                    st.write(sub_proc.get('content_extract', ''))

            # Hiển thị vết thực thi và suy luận chi tiết của Model cho câu hỏi này
            from app.components.trace_viewer import render_trace_view
            kc_trace_res = machine.process_request_with_trace(query_input, record_id="KC-INTERACTIVE")
            render_trace_view(
                trace_data=kc_trace_res.get('execution_trace', {}),
                terminal_log=kc_trace_res.get('terminal_log', ''),
                title="Nhật Ký Suy Luận & Vết Thực Thi Chi Tiết Của Model Cho Tình Huống Này",
                expanded=False,
                key_prefix="kc_trace_view"
            )
        else:
            st.warning("Chưa tìm thấy quy trình DOCX tương đồng vượt ngưỡng. Cán bộ đối chiếu quy chế thủ công.")

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # 3. DANH SÁCH TỆP VĂN BẢN
    st.markdown("### 📁 1. Danh sách tệp văn bản nghiệp vụ & quy chế")
    doc_files = list(DATA_DOC_DIR.glob("*.docx"))
    doc_info = []
    for d in doc_files:
        size_kb = round(d.stat().st_size / 1024, 1)
        dept_name = "Quản trị Cơ sở vật chất" if "csvc" in d.name else ("Công tác sinh viên" if "sinh_vien" in d.name else "Quản lý Đào tạo & Khảo thí")
        doc_info.append({
            "Tên tệp Word": d.name,
            "Kích thước": f"{size_kb} KB",
            "Định dạng": "Microsoft Word (.docx)",
            "Chuyên môn phụ trách": dept_name,
            "Tình trạng nạp": "Đã trích xuất & lập chỉ mục tham chiếu"
        })
    st.dataframe(pd.DataFrame(doc_info), width="stretch", hide_index=True)

    # 4. KHU VỰC HUẤN LUYỆN LẠI LOCAL MACHINE
    with st.expander("⚡ Vận hành Máy học: Huấn luyện & Lập chỉ mục lại", expanded=False):
        st.write("Khi có văn bản quy định hoặc tài liệu mới, bấm nút dưới đây để hệ thống tự động đọc lại, lập chỉ mục vector và tái huấn luyện mô hình học máy cục bộ.")
        c_tr1, c_tr2 = st.columns([1, 2])
        with c_tr1:
            if st.button("Huấn luyện lại Local Machine", type="primary", key="btn_retrain_local_machine", width="stretch"):
                with st.spinner("Đang trích xuất tài liệu và huấn luyện lại Local Machine..."):
                    try:
                        new_catalog = build_procedure_catalog()
                        with open(KB_OUTPUT_JSON, "w", encoding="utf-8") as f:
                            json.dump(new_catalog, f, ensure_ascii=False, indent=2)
                        
                        machine.reload_procedures()
                        train_res = machine.train_local_model()
                        sync_procedures_kb(new_catalog)
                        app_log("KNOWLEDGE", "Huấn luyện lại mô hình Local Machine", f"Đã nạp {train_res['total_samples']} mẫu dữ liệu và {train_res['procedures_count']} quy trình", level="SUCCESS")
                        
                        st.success(f"Huấn luyện thành công! Đã nạp {train_res['total_samples']} mẫu dữ liệu và {train_res['procedures_count']} quy trình nghiệp vụ.")
                        st.json(train_res)
                    except Exception as err:
                        st.error(f"Lỗi khi huấn luyện lại: {err}")
        with c_tr2:
            st.caption("Mô hình được huấn luyện hoàn toàn cục bộ trên máy chủ (Local Offline), sử dụng trích xuất đặc trưng kết hợp cấp từ (Word 1-2 n-grams) và cấp ký tự (Character 3-5 n-grams) để chống lỗi chính tả và teencode.")

    # 5. CẨM NANG TOÀN BỘ 15 QUY TRÌNH CHUẨN HÓA VÀ NGUỒN DOCX
    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 📚 2. Cẩm nang tra cứu chi tiết 15 quy trình nghiệp vụ EAUT")

    # Bộ lọc tra cứu
    c_s1, c_s2 = st.columns([1, 2])
    with c_s1:
        topics_list = ["Tất cả lĩnh vực"] + list(dict.fromkeys(p["topic"] for p in procedures))
        filter_topic = st.selectbox("Lọc theo lĩnh vực:", options=topics_list, key="kc_filter_topic")
    with c_s2:
        search_kw = st.text_input("Tìm kiếm theo từ khóa hoặc tên thủ tục:", placeholder="Ví dụ: chuyển ngành, bảo lưu, thẻ sinh viên, điều hòa, học phí...", key="kc_search_kw")

    # Lọc danh sách quy trình
    displayed_procs = []
    for p in procedures:
        if filter_topic != "Tất cả lĩnh vực" and p["topic"] != filter_topic:
            continue
        if search_kw.strip():
            kw = search_kw.strip().lower()
            text_search = f"{p['title']} {p.get('legal_basis','')} {p.get('content_extract','')} {' '.join(p.get('sample_queries',[]))}".lower()
            if kw not in text_search:
                continue
        displayed_procs.append(p)

    st.caption(f"Tìm thấy {len(displayed_procs)} quy trình nghiệp vụ phù hợp:")

    for p in displayed_procs:
        src_file = p.get('doc_source') or get_docx_filename(p['proc_id'])
        with st.expander(f"[{p['proc_id']}] {p['title']} — {p.get('department', 'Bộ phận Tiếp nhận')} (Nguồn: {src_file})", expanded=False):
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                st.markdown(f"**Tài liệu văn bản:** `{src_file}`")
                st.markdown(f"**Căn cứ pháp lý:** `{p.get('legal_basis', 'Quy định Nhà trường')}`")
                st.markdown(f"**Đơn vị giải quyết:** `{p.get('department', '')}`")
                st.markdown(f"**Thời hạn giải quyết:** `{p.get('processing_time', 'Theo quy định')}`")
            with c_p2:
                st.markdown(f"**Biểu mẫu yêu cầu:** `{p.get('forms_required', 'Theo hướng dẫn')}`")
                st.markdown(f"**Đối tượng áp dụng:** `{p.get('target_users', 'Sinh viên EAUT')}`")

            st.markdown("**Nội dung tóm tắt quy định:**")
            st.info(p.get("content_extract", ""))

            # Bảng các bước tuần tự
            steps = p.get("steps", [])
            if steps:
                st.markdown("**Trình tự các bước thực hiện:**")
                step_rows = []
                for s in steps:
                    step_rows.append({
                        "Bước": f"Bước {s.get('step', '')}",
                        "Chủ thể thực hiện": s.get("actor", ""),
                        "Nội dung công việc chi tiết": s.get("action", "")
                    })
                st.dataframe(pd.DataFrame(step_rows), width="stretch", hide_index=True)

            # Câu hỏi sinh viên thường hỏi
            queries = p.get("sample_queries", [])
            if queries:
                st.markdown("**Mẫu câu hỏi sinh viên thường thắc mắc:**")
                for q in queries:
                    st.markdown(f"- *\"{q}\"*")

    # 6. PHÂN HỆ CSDL THƯ VIỆN EAUT (KHO SÁCH & SỔ MƯỢN TRẢ THỜI GIAN THỰC)
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 📚 3. Phân hệ Tra cứu CSDL Thư viện EAUT (Kho Sách & Sổ Mượn Trả)")
    st.caption("Dữ liệu được truy vấn trực tiếp từ bảng `library_books` và `library_borrows` trong CSDL SQLite cục bộ.")

    from src.database import search_library_books, get_student_library_borrows, list_library_categories

    lib_tabs = st.tabs(["🔍 Tra cứu kho sách (OPAC)", "👤 Tra cứu sổ mượn trả sinh viên"])

    with lib_tabs[0]:
        c_lb1, c_lb2 = st.columns([1, 2])
        with c_lb1:
            cats = ["Tất cả"] + list_library_categories()
            sel_cat = st.selectbox("Lọc theo chuyên ngành:", options=cats, key="lib_cat_filter")
        with c_lb2:
            lib_kw = st.text_input("Từ khóa tên sách, tác giả hoặc mã xếp giá:", placeholder="Ví dụ: Kỹ thuật phần mềm, Python, Kế toán, Cơ sở dữ liệu...", key="lib_kw_search")

        found_books = search_library_books(query=lib_kw, category=sel_cat if sel_cat != "Tất cả" else None, limit=20)
        st.caption(f"Tìm thấy **{len(found_books)}** đầu sách trong kho thư viện:")

        if found_books:
            b_display = []
            for b in found_books:
                b_display.append({
                    "Mã sách": b["book_id"],
                    "Tên tài liệu / Giáo trình": b["title"],
                    "Tác giả": b["author"],
                    "Chuyên ngành": b["category"],
                    "Năm XB": b["publish_year"],
                    "Vị trí giá sách": b["location"],
                    "Mã xếp giá": b["call_number"],
                    "Còn sẵn / Tổng": f"{b['available_copies']} / {b['total_copies']}",
                    "Tình trạng": "🟢 Sẵn sàng" if b["available_copies"] > 0 else "🔴 Hết sách",
                    "Số hóa": "Có" if b.get("is_digital") else "Chưa"
                })
            st.dataframe(pd.DataFrame(b_display), width="stretch", hide_index=True)
        else:
            st.info("Không tìm thấy đầu sách nào phù hợp với từ khóa tra cứu.")

    with lib_tabs[1]:
        c_sid1, c_sid2 = st.columns([1, 2])
        with c_sid1:
            check_sid = st.text_input("Nhập Mã sinh viên (MSSV):", value="2021600123", key="lib_check_sid_input", placeholder="Ví dụ: 2022601234, 2021600123...")
        with c_sid2:
            st.caption("Các MSSV mẫu thử nghiệm trong hệ thống:")
            st.markdown("- `2022601234`: Mượn đúng hạn (2 cuốn: *Kỹ thuật phần mềm*, *Python AI*)\n- `2021600123`: Quá hạn (1 cuốn: *Nguyên lý Kế toán*, phạt 90.000đ)\n- `2023602111`: Đã hoàn trả đầy đủ (*Toán Giải tích 1 & 2*)")

        if check_sid.strip():
            borrows = get_student_library_borrows(check_sid.strip())
            if borrows:
                st.markdown(f"**Kết quả mượn trả của sinh viên: {borrows[0]['student_name']} (MSSV: {check_sid.strip()}):**")
                br_display = []
                for br in borrows:
                    fine_str = f"{br.get('fine_amount', 0):,} VNĐ" if br.get('fine_amount', 0) > 0 else "0 VNĐ"
                    br_display.append({
                        "Mã mượn": br["borrow_id"],
                        "Tên sách": br["book_title"],
                        "Ngày mượn": br["borrow_date"],
                        "Hạn trả": br["due_date"],
                        "Ngày trả": br.get("return_date") or "-",
                        "Trạng thái": br["status"],
                        "Số lần gia hạn": f"{br.get('renew_count', 0)} / 2",
                        "Phí phạt quá hạn (5k/ngày)": fine_str,
                        "Ghi chú thủ thư": br.get("notes", "")
                    })
                st.dataframe(pd.DataFrame(br_display), width="stretch", hide_index=True)
            else:
                st.info(f"Sinh viên MSSV {check_sid.strip()} hiện không có lịch sử mượn trả tài liệu nào trong CSDL Thư viện.")
