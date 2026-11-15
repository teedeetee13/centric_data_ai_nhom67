# -*- coding: utf-8 -*-
"""
Script: scripts/render_new_video.py
Dựng video demo sản phẩm EduSupportAI thế hệ mới (Full HD 1080p, 30fps)
Tích hợp 3 ảnh chụp thực tế từ người dùng, tạo các slide giải thích đồ họa trực quan
và áp dụng hiệu ứng chuyển cảnh mượt mà (Crossfade Transitions qua FFmpeg xfade).
"""

import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio_new"
FRAMES_DIR = OUTPUT_DIR / "frames_new"
CLIPS_DIR = OUTPUT_DIR / "clips_new"

FRAMES_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

IMG1_PATH = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_0_1794750093652.png")
IMG2_PATH = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_1_1794750093652.png")
IMG3_PATH = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_2_1794750093652.png")

FONT_REG = "/usr/share/fonts/noto/NotoSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/noto/NotoSans-Bold.ttf"
FONT_MED = "/usr/share/fonts/noto/NotoSans-Medium.ttf"

def get_font(size, bold=False, medium=False):
    if bold:
        return ImageFont.truetype(FONT_BOLD, size)
    elif medium:
        return ImageFont.truetype(FONT_MED, size)
    return ImageFont.truetype(FONT_REG, size)

def create_base_canvas(brand_tag="EDUSUPPORT-AI :: HỆ THỐNG TRỢ LÝ HỌC VỤ THÔNG MINH"):
    """Tạo khung nền Full HD 1920x1080 phong cách Sapphire Academic & Slate sang trọng."""
    img = Image.new("RGB", (1920, 1080), color="#090d16")
    draw = ImageDraw.Draw(img)

    # Gradient nền tinh tế
    for y in range(1080):
        ratio = y / 1080.0
        r = int(9 + ratio * (15 - 9))
        g = int(13 + ratio * (23 - 13))
        b = int(22 + ratio * (38 - 22))
        draw.line([(0, y), (1920, y)], fill=(r, g, b))

    # Thanh header trên cùng
    draw.rectangle([(0, 0), (1920, 76)], fill="#0f172a")
    draw.line([(0, 76), (1920, 76)], fill="#2563eb", width=3)
    draw.text((60, 24), "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ ĐÔNG Á (EAUT)", font=get_font(19, bold=True), fill="#93c5fd")
    draw.text((1440, 26), "CENTRIC DATA AI - NHÓM 67", font=get_font(16, bold=True), fill="#94a3b8")

    # Thanh footer dưới cùng
    draw.rectangle([(0, 1024), (1920, 1080)], fill="#0a0f1d")
    draw.line([(0, 1024), (1920, 1024)], fill="#1e293b", width=2)
    draw.text((60, 1042), brand_tag, font=get_font(14, medium=True), fill="#64748b")
    draw.text((1580, 1042), "Báo cáo Đồ án Học phần 2024 - 2025", font=get_font(14), fill="#475569")

    return img, draw

# ==============================================================================
# SCENE 1: Mở đầu & Giới thiệu tổng quan hệ thống EduSupportAI
# ==============================================================================
def render_scene1():
    img, draw = create_base_canvas()

    # Badge phân loại
    draw.rounded_rectangle([(60, 120), (480, 165)], radius=8, fill="#1e3a8a", outline="#3b82f6", width=1)
    draw.text((80, 132), "[GIẢI PHÁP CHUYỂN ĐỔI SỐ HỌC VỤ]", font=get_font(16, bold=True), fill="#bfdbfe")

    draw.text((60, 190), "EduSupportAI", font=get_font(52, bold=True), fill="#ffffff")
    draw.text((60, 270), "Hệ thống Tiếp nhận, Phân loại & Giải quyết Phản ánh Học vụ Sinh viên", font=get_font(26, bold=True), fill="#60a5fa")
    draw.text((60, 325), "Ứng dụng tiếp cận Data-Centric AI (DCAI) kết hợp Bàn làm việc Phê duyệt Human-in-the-Loop", font=get_font(18), fill="#94a3b8")

    # 3 Thẻ giá trị cốt lõi
    pillars = [
        ("THỰC TRẠNG & BÀI TOÁN", "Hàng nghìn thắc mắc mỗi kỳ thi cử, học phí gửi phân tán qua nhiều kênh không đồng nhất, cán bộ xử lý thủ công gây chậm trễ.", "#ef4444", "#7f1d1d"),
        ("ĐỘ CHÍNH XÁC CAO (> 94%)", "Mô hình máy học cục bộ TF-IDF kép + Logistic Regression phân luồng chuẩn xác 7 chuyên môn nghiệp vụ EAUT.", "#10b981", "#064e3b"),
        ("XỬ LÝ SIÊU TỐC (< 10 MS)", "Rút ngắn thời gian từ 3 - 5 ngày làm việc xuống dưới 10 mili-giây, gửi email giải đáp chuẩn mực tới sinh viên.", "#3b82f6", "#1e3a8a"),
    ]

    for i, (title, desc, cborder, cbg) in enumerate(pillars):
        x = 60 + i * 590
        y = 390
        w = 560
        h = 240
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=12, fill="#111827", outline=cborder, width=2)
        draw.rounded_rectangle([(x + 20, y + 20), (x + 360, y + 60)], radius=6, fill=cbg)
        draw.text((x + 32, y + 28), title, font=get_font(16, bold=True), fill="#ffffff")

        words = desc.split()
        lines, cur = [], []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 42:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:5]):
            draw.text((x + 24, y + 80 + li * 28), line, font=get_font(16), fill="#cbd5e1")

    # Khung tính năng kỹ thuật nổi bật
    draw.rounded_rectangle([(60, 680), (1860, 960)], radius=12, fill="#0f172a", outline="#334155", width=1)
    draw.text((90, 710), "ĐẶC TRƯNG KỸ THUẬT NỔI BẬT", font=get_font(20, bold=True), fill="#38bdf8")

    features = [
        "1. Data-Centric AI Pipeline: Chuẩn hóa Unicode NFC, tự động che giấu thông tin cá nhân (PII) an toàn.",
        "2. Tra cứu RAG Quy chế EAUT: Trích xuất điều khoản và quy trình chuẩn (PROC_...) từ 3 tệp DOCX chính thức.",
        "3. Độc lập 100% Offline: Máy học nhẹ, vận hành hoàn toàn nội bộ, bảo mật thông tin sinh viên tuyệt đối.",
        "4. Phê duyệt & Gửi Email Thực tế: Bàn duyệt phân luồng 2 trạng thái, gửi email học thuật Sapphire Academic trực tiếp."
    ]
    for fi, feat in enumerate(features):
        draw.text((90, 765 + fi * 44), feat, font=get_font(17), fill="#e2e8f0")

    path = FRAMES_DIR / "frame_scene1.png"
    img.save(path)
    return path

# ==============================================================================
# SCENE 2: Cổng tiếp nhận Sinh viên trực tuyến (Sử dụng Ảnh 1)
# ==============================================================================
def render_scene2():
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 105), (460, 150)], radius=8, fill="#065f46", outline="#10b981", width=1)
    draw.text((80, 117), "[CỔNG DỊCH VỤ SINH VIÊN 24/7]", font=get_font(15, bold=True), fill="#a7f3d0")

    draw.text((60, 165), "Cổng Tiếp Nhận & Hỗ Trợ Học Vụ Trực Tuyến", font=get_font(38, bold=True), fill="#ffffff")
    draw.text((60, 220), "Thiết kế trực quan, tiếp nhận đa dịch vụ, tự động bảo vệ thông tin PII và cam kết thời hạn SLA minh bạch", font=get_font(18), fill="#94a3b8")

    # Cột trái: 4 Điểm nhấn thiết kế
    left_x = 60
    cards = [
        ("1. THUẬN TIỆN & TRỰC QUAN 24/7", "Sinh viên điền biểu mẫu nhanh chóng với MSSV, SĐT, Email và lựa chọn trong 10 nhóm thủ tục nghiệp vụ."),
        ("2. DATA-CENTRIC & BẢO VỆ PII", "Bộ lọc tự động phát hiện và che giấu dữ liệu nhạy cảm (SĐT, CCCD, tài khoản) trước khi lưu vào CSDL."),
        ("3. CAM KẾT THỜI HẠN (SLA) CÔNG KHAI", "Minh bạch thời gian xử lý: Tiếp nhận & đối soát tức thì; Giải quyết từ 24 - 48h; Khẩn cấp trong 4 - 12h."),
        ("4. ĐÍNH KÈM MINH CHỨNG LINH HOẠT", "Hỗ trợ đính kèm hình ảnh giao dịch, biên lai hoặc đơn từ (PDF, DOCX, PNG) để đối soát tự động.")
    ]

    for ci, (title, desc) in enumerate(cards):
        y = 275 + ci * 175
        draw.rounded_rectangle([(left_x, y), (left_x + 680, y + 155)], radius=10, fill="#111827", outline="#1e3a8a", width=1)
        draw.text((left_x + 20, y + 18), title, font=get_font(17, bold=True), fill="#60a5fa")

        words = desc.split()
        lines, cur = [], []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 48:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:4]):
            draw.text((left_x + 20, y + 54 + li * 24), line, font=get_font(15), fill="#cbd5e1")

    # Cột phải: Chèn Ảnh 1 (Cổng sinh viên)
    if IMG1_PATH.exists():
        ss = Image.open(IMG1_PATH).convert("RGB")
        # Resize tỷ lệ phù hợp (width 1060, height ~690)
        ss_resized = ss.resize((1060, 690), Image.Resampling.LANCZOS)
        draw.rounded_rectangle([(770, 275), (1850, 985)], radius=12, fill="#0f172a", outline="#2563eb", width=2)
        img.paste(ss_resized, (780, 285))
        draw.text((780, 992), "Ảnh thực tế: Giao diện Cổng Tiếp nhận & Hỗ trợ Học vụ Sinh viên EAUT", font=get_font(14), fill="#94a3b8")

    path = FRAMES_DIR / "frame_scene2.png"
    img.save(path)
    return path

# ==============================================================================
# SCENE 3: Kiến trúc DCAI 5 bước & Tra cứu Quy chế RAG (Slide đồ họa tự tạo)
# ==============================================================================
def render_scene3():
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 105), (480, 150)], radius=8, fill="#581c87", outline="#a855f7", width=1)
    draw.text((80, 117), "[KIẾN TRÚC CÔNG NGHỆ LÕI (DCAI)]", font=get_font(15, bold=True), fill="#e9d5ff")

    draw.text((60, 165), "Đường Ống 5 Bước Xử Lý Thông Minh & Tra Cứu Quy Chế RAG", font=get_font(38, bold=True), fill="#ffffff")
    draw.text((60, 220), "Chuỗi suy luận Chain-of-Thought minh bạch, trích xuất căn cứ pháp lý từ tài liệu DOCX chính thức của EAUT", font=get_font(18), fill="#94a3b8")

    # 5 Khối Pipeline nằm ngang (Flowchart 5 bước)
    steps = [
        ("BƯỚC 1", "DATA CLEANING & PII MASKING", "Chuẩn hóa Unicode NFC\nLọc ký tự lạ & rà soát PII\nKiểm định độ dài văn bản", "#3b82f6", "#1e3a8a"),
        ("BƯỚC 2", "MACHINE LEARNING CLASSIFICATION", "TF-IDF Kép (Char + Word)\nHồi quy Logistic Regression\nĐộ chính xác > 94%", "#8b5cf6", "#4c1d95"),
        ("BƯỚC 3", "RAG REGULATORY RETRIEVAL", "Truy vấn 3 file DOCX EAUT\nKhớp mã [PROC_TC_01...]\nTrích xuất điều khoản & SLA", "#06b6d4", "#164e63"),
        ("BƯỚC 4", "CHAIN-OF-THOUGHT SYNTHESIS", "Lập luận CoT nghiệp vụ\nTổng hợp giải pháp học vụ\nNgôn từ chuẩn mực đại học", "#10b981", "#064e3b"),
        ("BƯỚC 5", "GUARDRAILS & ROUTING", "Kiểm định ngưỡng an toàn\nTự động duyệt (Tin cậy cao)\nChuyển Bàn duyệt Cán bộ", "#f59e0b", "#78350f"),
    ]

    for si, (step_no, title, desc, cborder, cbg) in enumerate(steps):
        x = 60 + si * 365
        y = 280
        w = 335
        h = 290

        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=12, fill="#111827", outline=cborder, width=2)
        draw.rounded_rectangle([(x + 16, y + 16), (x + 140, y + 46)], radius=6, fill=cbg)
        draw.text((x + 26, y + 22), step_no, font=get_font(14, bold=True), fill="#ffffff")
        draw.text((x + 16, y + 60), title, font=get_font(14, bold=True), fill=cborder)

        for li, line in enumerate(desc.split("\n")):
            draw.text((x + 16, y + 120 + li * 28), f"• {line}", font=get_font(14), fill="#cbd5e1")

        # Vẽ mũi tên liên kết giữa các bước (nếu chưa phải bước cuối)
        if si < 4:
            arrow_x = x + w + 8
            arrow_y = y + h // 2
            draw.polygon([(arrow_x, arrow_y - 12), (arrow_x + 16, arrow_y), (arrow_x, arrow_y + 12)], fill="#64748b")

    # Bảng phân tích ưu điểm giải pháp
    draw.rounded_rectangle([(60, 620), (1860, 970)], radius=12, fill="#0f172a", outline="#334155", width=1)
    draw.text((90, 645), "VÌ SAO TIẾP CẬN DATA-CENTRIC AI LẠI HIỆU QUẢ VƯỢT TRỘI?", font=get_font(20, bold=True), fill="#38bdf8")

    advs = [
        ("TỐC ĐỘ XỬ LÝ SIÊU TỐC:", "Toàn bộ chuỗi 5 bước thực thi trung bình chỉ mất 5 - 10 mili-giây, nhanh hơn hàng nghìn lần so với gọi API đám mây."),
        ("AN TOÀN BẢO MẬT TUYỆT ĐỐI:", "Chạy 100% Offline trên hạ tầng máy chủ của Nhà trường, không gửi dữ liệu sinh viên ra bên ngoài, tuân thủ an toàn thông tin."),
        ("MINH BẠCH & DỄ KIỂM ĐỊNH:", "Mỗi quyết định đều có căn cứ từ điều khoản quy chế cụ thể, cán bộ quản lý có thể truy vết toàn bộ nhật ký suy luận.")
    ]
    for ai, (atitle, adesc) in enumerate(advs):
        y_adv = 705 + ai * 82
        draw.text((90, y_adv), atitle, font=get_font(17, bold=True), fill="#60a5fa")
        draw.text((90, y_adv + 30), adesc, font=get_font(16), fill="#cbd5e1")

    path = FRAMES_DIR / "frame_scene3.png"
    img.save(path)
    return path

# ==============================================================================
# SCENE 4: Bàn duyệt Cán bộ & Quản lý Phân luồng Học vụ (Sử dụng Ảnh 2)
# ==============================================================================
def render_scene4():
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 105), (510, 150)], radius=8, fill="#1e3a8a", outline="#3b82f6", width=1)
    draw.text((80, 117), "[BÀN DUYỆT CÁN BỘ & QUẢN LÝ PHÂN LUỒNG]", font=get_font(15, bold=True), fill="#93c5fd")

    draw.text((60, 165), "Bàn Phê Duyệt Cán Bộ & Đối Chiếu Quy Chế Chính Thức", font=get_font(38, bold=True), fill="#ffffff")
    draw.text((60, 220), "Tối ưu hóa quy trình với 2 phân luồng rõ ràng, loại bỏ mức độ ưu tiên cho hồ sơ đã xử lý và liên kết quy chế [PROC_TC_01]", font=get_font(18), fill="#94a3b8")

    # Cột trái: 4 Điểm nâng cấp đột phá
    left_x = 60
    features = [
        ("1. BỘ LỌC 2 TRẠNG THÁI RÕ RÀNG", "Phân loại trực quan: 'Phản ánh cần đưa về đơn vị xem xét' (chờ giải quyết) và 'Phản ánh đã gửi' (đã hoàn tất)."),
        ("2. BỎ ƯU TIÊN CHO HỒ SƠ ĐÃ DUYỆT", "Đối với phản ánh đã xử lý, loại bỏ huy hiệu ưu tiên (Khẩn cấp/Cao), hiển thị trạng thái '✅ Đã xử lý & gửi email' trang nhã."),
        ("3. ĐỐI CHIẾU CĂN CỨ QUY CHẾ EAUT", "Tự động trích dẫn quy trình chuẩn hóa [PROC_TC_01] Đối soát học phí kèm cam kết thời hạn SLA 24 - 48 giờ làm việc."),
        ("4. SOẠN THẢO & GỬI EMAIL CHÍNH THỨC", "Cán bộ có thể tinh chỉnh văn bản hướng dẫn và nhấn 'Duyệt & gửi email' tức thì tới tài khoản hòm thư sinh viên.")
    ]

    for fi, (title, desc) in enumerate(features):
        y = 275 + fi * 175
        draw.rounded_rectangle([(left_x, y), (left_x + 680, y + 155)], radius=10, fill="#111827", outline="#1e3a8a", width=1)
        draw.text((left_x + 20, y + 18), title, font=get_font(17, bold=True), fill="#38bdf8")

        words = desc.split()
        lines, cur = [], []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 48:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:4]):
            draw.text((left_x + 20, y + 54 + li * 24), line, font=get_font(15), fill="#cbd5e1")

    # Cột phải: Chèn Ảnh 2 (Bàn duyệt Full HD)
    if IMG2_PATH.exists():
        ss = Image.open(IMG2_PATH).convert("RGB")
        ss_resized = ss.resize((1060, 690), Image.Resampling.LANCZOS)
        draw.rounded_rectangle([(770, 275), (1850, 985)], radius=12, fill="#0f172a", outline="#0284c7", width=2)
        img.paste(ss_resized, (780, 285))
        draw.text((780, 992), "Ảnh thực tế: Bàn duyệt cán bộ EAUT hồ sơ REQ_E7378453DA56 (Đã xử lý & gửi email)", font=get_font(14), fill="#94a3b8")

    path = FRAMES_DIR / "frame_scene4.png"
    img.save(path)
    return path

# ==============================================================================
# SCENE 5: Nội dung Email Giải quyết gửi tới Sinh viên (Sử dụng Ảnh 3)
# ==============================================================================
def render_scene5():
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 105), (510, 150)], radius=8, fill="#065f46", outline="#10b981", width=1)
    draw.text((80, 117), "[KẾT QUẢ GIẢI QUYẾT & GỬI EMAIL CHÍNH THỨC]", font=get_font(15, bold=True), fill="#a7f3d0")

    draw.text((60, 165), "Văn Bản Hướng Dẫn & Thông Báo Kết Quả Giải Quyết", font=get_font(38, bold=True), fill="#ffffff")
    draw.text((60, 220), "Định dạng email học thuật Sapphire Academic trang trọng, thông tin giải pháp rõ ràng, hiển thị trọn vẹn đầy đủ", font=get_font(18), fill="#94a3b8")

    # Cột trái: 4 Thành phần chuẩn mực của bức thư
    left_x = 60
    email_elements = [
        ("1. NHẬN DIỆN THƯƠNG HIỆU EAUT", "Header xanh than trang trọng, nhận diện thương hiệu Trường Đại học Công nghệ Đông Á và Cổng EduSupportAI."),
        ("2. BẢNG TÓM TẮT HỒ SƠ TIẾP NHẬN", "Đầy đủ Mã hồ sơ REQ_E7378453DA56, Chuyên môn Học phí, Đơn vị thụ lý Phòng CTSV và phương thức phê duyệt."),
        ("3. HƯỚNG DẪN NGHIỆP VỤ TRỰC DIỆN", "Hướng dẫn cụ thể về thời gian đối soát liên ngân hàng (24 - 48h), địa điểm nộp ảnh chụp biên lai giao dịch."),
        ("4. ĐỊA ĐIỂM & KÊNH HỖ TRỢ TRỰC TIẾP", "Địa chỉ Bộ phận Một cửa Tòa A, thời gian làm việc hành chính, số điện thoại hotline và email liên hệ trực tiếp.")
    ]

    for ei, (title, desc) in enumerate(email_elements):
        y = 275 + ei * 175
        draw.rounded_rectangle([(left_x, y), (left_x + 980, y + 155)], radius=10, fill="#111827", outline="#166534", width=1)
        draw.text((left_x + 24, y + 18), title, font=get_font(18, bold=True), fill="#4ade80")

        words = desc.split()
        lines, cur = [], []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 70:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:4]):
            draw.text((left_x + 24, y + 54 + li * 24), line, font=get_font(15), fill="#cbd5e1")

    # Cột phải: Chèn Ảnh 3 (Ảnh email chụp thực tế)
    if IMG3_PATH.exists():
        ss = Image.open(IMG3_PATH).convert("RGB")
        # Resize tỷ lệ phù hợp (width 700, height 700)
        ss_resized = ss.resize((700, 700), Image.Resampling.LANCZOS)
        draw.rounded_rectangle([(1080, 275), (1850, 985)], radius=12, fill="#0f172a", outline="#22c55e", width=2)
        img.paste(ss_resized, (1115, 280))
        draw.text((1115, 992), "Ảnh thực tế: Email kết quả giải quyết phản ánh học vụ gửi sinh viên", font=get_font(14), fill="#94a3b8")

    path = FRAMES_DIR / "frame_scene5.png"
    img.save(path)
    return path

# ==============================================================================
# SCENE 6: Tổng kết & Sẵn sàng Triển khai (Slide đồ họa kết luận)
# ==============================================================================
def render_scene6():
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 105), (460, 150)], radius=8, fill="#065f46", outline="#10b981", width=1)
    draw.text((80, 117), "[TỔNG KẾT & HIỆU QUẢ THỰC TIỄN]", font=get_font(15, bold=True), fill="#a7f3d0")

    draw.text((60, 165), "EduSupportAI — Sẵn Sàng Triển Khai Thực Tế Tại EAUT", font=get_font(38, bold=True), fill="#ffffff")
    draw.text((60, 220), "Giải pháp toàn diện thúc đẩy chuyển đổi số quản lý học vụ và nâng cao chất lượng phục vụ người học", font=get_font(18), fill="#94a3b8")

    # 4 Khối số liệu ấn tượng
    stats = [
        ("43 / 43", "BÀI KIỂM THỬ PASS (100%)", "Toàn bộ bài test Pipeline, CSDL, Machine Learning và Giao diện đều vượt qua kiểm định tự động.", "#10b981", "#064e3b"),
        ("< 10 MS", "TỐC ĐỘ SUY LUẬN SIÊU TỐC", "Thời gian xử lý máy học cục bộ cực nhanh, đảm bảo phản hồi tức thì mà không phụ thuộc Internet.", "#3b82f6", "#1e3a8a"),
        ("100% OFFLINE", "BẢO MẬT DỮ LIỆU TUYỆT ĐỐI", "Mô hình và cơ sở dữ liệu vận hành hoàn toàn nội bộ, an toàn thông tin theo chuẩn Bộ GD&ĐT.", "#8b5cf6", "#4c1d95"),
        ("DOCKER READY", "ĐỒNG BỘ DỮ LIỆU ĐA NỀN TẢNG", "Sẵn sàng khởi chạy môi trường Docker, đồng bộ song song SQLite và MySQL thời gian thực.", "#f59e0b", "#78350f"),
    ]

    for i, (metric, title, desc, cborder, cbg) in enumerate(stats):
        x = 60 + i * 445
        y = 280
        w = 425
        h = 320
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=12, fill="#111827", outline=cborder, width=2)
        draw.text((x + 24, y + 24), metric, font=get_font(44, bold=True), fill=cborder)
        draw.text((x + 24, y + 84), title, font=get_font(16, bold=True), fill="#ffffff")

        words = desc.split()
        lines, cur = [], []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 32:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:4]):
            draw.text((x + 24, y + 130 + li * 26), line, font=get_font(15), fill="#cbd5e1")

    # Băng chuyền giá trị xã hội & ứng dụng
    draw.rounded_rectangle([(60, 640), (1860, 960)], radius=12, fill="#0f172a", outline="#2563eb", width=2)
    draw.text((100, 680), "GIÁ TRỊ XÃ HỘI & Ý NGHĨA THỰC TIỄN", font=get_font(22, bold=True), fill="#60a5fa")

    conclusions = [
        "• Đối với Sinh viên: Phản ánh được tiếp nhận 24/7, có mã hồ sơ theo dõi, giải đáp có căn cứ và minh bạch tiến độ.",
        "• Đối với Cán bộ: Giảm hơn 80% áp lực thủ công, tập trung xử lý các trường hợp đặc thù cần thẩm định chuyên sâu.",
        "• Đối với Nhà trường: Tối ưu hóa quy trình hành chính Một cửa, nâng cao chỉ số hài lòng của người học hướng tới Đại học số."
    ]
    for ci, ctext in enumerate(conclusions):
        draw.text((100, 740 + ci * 56), ctext, font=get_font(18), fill="#e2e8f0")

    path = FRAMES_DIR / "frame_scene6.png"
    img.save(path)
    return path

# ==============================================================================
# DỰNG CÁC CLIP & GHÉP NỐI VỚI TRANSITION (XFADE)
# ==============================================================================
def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(audio_path)
    ]
    return float(subprocess.check_output(cmd).decode().strip())

def build_individual_clips():
    scenes = [
        ("scene1", render_scene1()),
        ("scene2", render_scene2()),
        ("scene3", render_scene3()),
        ("scene4", render_scene4()),
        ("scene5", render_scene5()),
        ("scene6", render_scene6()),
    ]

    durations = []
    clip_paths = []

    for sc_id, frame_path in scenes:
        audio_path = AUDIO_DIR / f"{sc_id}.mp3"
        clip_path = CLIPS_DIR / f"{sc_id}.mp4"
        duration = get_audio_duration(audio_path)
        durations.append(duration)
        clip_paths.append(clip_path)

        print(f"-> Phân cảnh [{sc_id}]: Thời lượng audio {duration:.2f}s...")

        # Dựng clip mp4 chuẩn 1080p 30fps
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(frame_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-shortest",
            str(clip_path)
        ]
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   + Đã dựng thành công: {clip_path}")

    return clip_paths, durations

def compose_video_with_transitions(clip_paths, durations):
    """
    Ghép 6 phân cảnh bằng FFmpeg xfade (transition=fade, duration=0.75s) và acrossfade.
    Tạo hiệu ứng chuyển cảnh mềm mại giữa các màn hình và slide giải thích.
    """
    final_video = OUTPUT_DIR / "edusupport_ai_demo_v2.mp4"
    transition_dur = 0.75

    print("-> Đang tính toán chuỗi xfade transitions cho 6 phân cảnh...")

    # Xây dựng filter_complex cho xfade
    # Ví dụ: v0 + v1 -> xfade tại offset0, sau đó kết quả + v2 tại offset1, ...
    v_filters = []
    a_filters = []

    # Tính toán offset cho từng điểm giao thoa
    # offset[0] = d0 - transition_dur
    # offset[1] = offset[0] + d1 - transition_dur
    # ...
    offsets = []
    cur_offset = durations[0] - transition_dur
    offsets.append(cur_offset)
    for i in range(1, len(durations) - 1):
        cur_offset += durations[i] - transition_dur
        offsets.append(cur_offset)

    inputs = []
    for p in clip_paths:
        inputs.extend(["-i", str(p)])

    # Video chain
    # [0:v][1:v]xfade=transition=fade:duration=0.75:offset=...[v01];
    # [v01][2:v]xfade=transition=fade:duration=0.75:offset=...[v02];
    # ...
    prev_v = "0:v"
    for i in range(1, len(clip_paths)):
        next_v = f"{i}:v"
        out_v = f"v_trans_{i}" if i < len(clip_paths) - 1 else "v_final"
        offset = offsets[i - 1]
        v_filters.append(f"[{prev_v}][{next_v}]xfade=transition=fade:duration={transition_dur}:offset={offset:.2f}[{out_v}]")
        prev_v = out_v

    # Audio chain
    prev_a = "0:a"
    for i in range(1, len(clip_paths)):
        next_a = f"{i}:a"
        out_a = f"a_trans_{i}" if i < len(clip_paths) - 1 else "a_final"
        a_filters.append(f"[{prev_a}][{next_a}]acrossfade=d={transition_dur}[{out_a}]")
        prev_a = out_a

    full_filter = ";".join(v_filters + a_filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", full_filter,
        "-map", "[v_final]",
        "-map", "[a_final]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(final_video)
    ]

    print(f"-> Đang thực thi lệnh FFmpeg xfade ghép nối toàn bộ video...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"🎉 HOÀN TẤT XUẤT VIDEO REVIEW SẢN PHẨM MỚI: {final_video}")
    return final_video

if __name__ == "__main__":
    print("=== BẮT ĐẦU DỰNG VIDEO DEMO SẢN PHẨM MỚI VỚI 3 ẢNH & TRANSITIONS ===")
    clips, durs = build_individual_clips()
    final_vid = compose_video_with_transitions(clips, durs)
    print("XONG!")
