# -*- coding: utf-8 -*-
"""
Module: app.components.demo_guide
Khung hướng dẫn nhanh và câu hỏi mẫu cho buổi demo.
Thêm câu mẫu mới: thêm một dòng vào SAMPLES (nhãn nút -> (nội dung, tính năng được minh họa)).
"""

import streamlit as st

# Dữ liệu mô phỏng, không phải sinh viên thật
SAMPLES = {
    'NVQS (thiếu MSSV)': (
        'Em vừa có lệnh gọi nhập ngũ, em muốn xin giấy tạm hoãn nghĩa vụ quân sự thì làm thế nào ạ?',
        'Ghép quy trình QT19 từ tài liệu CTSV; phiếu ticket báo thiếu Mã sinh viên; bản nháp do mô hình cục bộ soạn.'),
    'Bảo lưu (có MSSV)': (
        'Em muốn xin bảo lưu kết quả học tập kỳ này vì gia đình khó khăn, mã sinh viên 20991234.',
        'Mã sinh viên bị che thành [STUDENT_ID]; quy trình QT04 có hạn nộp 04 tuần và các bước Khoa - P.HCNS - P.CTSV.'),
    'Đối soát học phí': (
        'Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234, sđt 0912 345 678.',
        'Che cả SĐT và MSSV; quy trình QT16: nộp tại Một cửa, Phòng Tài chính - Kế toán đối soát trong 03 ngày làm việc.'),
    'Gõ không dấu': (
        'em xin giay xac nhan sinh vien de lam ve xe buyt a',
        'Câu gõ không dấu vẫn ghép đúng quy trình QT11 (cấp giấy xác nhận sinh viên).'),
    'Sự cố phòng học': (
        'Máy chiếu phòng 302 nhà A không lên hình, lớp em đang học.',
        'Quy trình CSVC (QT28): báo cán bộ quản lý phòng học của Khoa, sự cố phức tạp lập biên bản.'),
    'Ngoài quy trình': (
        'Điểm thi môn Trí tuệ nhân tạo của em bị sai, em muốn phúc khảo.',
        'Không có quy trình trong tài liệu nên hệ thống không ép ghép; chỉ dùng FAQ minh họa và yêu cầu cán bộ xác minh.'),
    'Thiếu thông tin': (
        'Giúp em với',
        'Câu quá ngắn bị gắn cờ, hệ thống đề nghị sinh viên bổ sung thay vì đoán.'),
}

PIPELINE_STEPS = (
    "**Một yêu cầu đi qua 6 bước:**\n"
    "1. **Làm sạch & che thông tin cá nhân:** chuẩn hóa Unicode, che SĐT / Email / MSSV thành [PHONE], [EMAIL], [STUDENT_ID].\n"
    "2. **Phân loại 7 nhóm** bằng TF-IDF + Logistic Regression; *độ tự tin* là xác suất của mô hình, không phải độ chính xác.\n"
    "3. **Ghép quy trình nghiệp vụ** (33 quy trình biên tập từ tài liệu CTSV, Đào tạo, CSVC của trường) để định tuyến đơn vị đầu mối.\n"
    "4. **Lập phiếu ticket:** hồ sơ cần chuẩn bị, các bước - đơn vị - thời gian, hạn xử lý theo ngày làm việc, thông tin còn thiếu.\n"
    "5. **Soạn bản nháp:** mô hình ngôn ngữ chạy trên máy (Ollama) chỉ dựa vào quy trình; con số / mã biểu mẫu lạ bị loại. "
    "Không có Ollama thì dùng mẫu câu. Mỗi bản nháp mất vài giây; lần đầu sau khi bật máy có thể lâu hơn do nạp model.\n"
    "6. **Cán bộ duyệt** ở tab Bàn duyệt cán bộ; mọi thao tác được lưu nhật ký."
)


def _fill_sample(label):
    st.session_state['request_text'] = SAMPLES[label][0]
    st.session_state['sample_note'] = f"Câu mẫu “{label}” minh họa: {SAMPLES[label][1]}"


def render_demo_guide(service):
    with st.expander('Hướng dẫn nhanh và câu hỏi mẫu để demo', expanded=False):
        st.markdown(PIPELINE_STEPS)
        st.caption('Bấm một câu mẫu để điền sẵn vào ô nội dung, rồi bấm Gửi. Toàn bộ là dữ liệu mô phỏng.')
        cols = st.columns(4)
        for i, label in enumerate(SAMPLES):
            cols[i % 4].button(label, key=f'sample_{i}', on_click=_fill_sample, args=(label,), width='stretch')
        st.caption(service.llm.status())

    if st.session_state.get('sample_note'):
        st.info(st.session_state['sample_note'])
