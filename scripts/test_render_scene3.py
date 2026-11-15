# -*- coding: utf-8 -*-
"""
Prototype: Test Scene 3 DCAI 5-Stage Animation Frame in Light Tech HUD
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 720, 1280

FONT_PATH_REG = "/usr/share/fonts/noto/NotoSans-Regular.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/noto/NotoSans-Bold.ttf"

def get_font(size, bold=False):
    p = FONT_PATH_BOLD if bold else FONT_PATH_REG
    try:
        return ImageFont.truetype(p, size)
    except:
        return ImageFont.load_default()

def test_frame():
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    # Subtle tech grid
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill="#edf2f7", width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill="#edf2f7", width=1)

    # Ambient soft glow orbs (pastel blue & emerald)
    # Header capsule
    draw.rounded_rectangle([30, 36, W-30, 106], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    
    # EAUT badge
    draw.rounded_rectangle([44, 48, 104, 94], radius=8, fill="#1d4ed8")
    draw.text((54, 58), "EAUT", font=get_font(18, True), fill="#ffffff")

    # Brand Title & Subtext
    draw.text((116, 50), "EDUSUPPORT.AI", font=get_font(18, True), fill="#0f172a")
    draw.text((116, 76), "DATA-CENTRIC AI // HỆ THỐNG HỌC VỤ", font=get_font(11, True), fill="#64748b")

    # Right Badge
    draw.ellipse([540, 68, 548, 76], fill="#10b981")
    draw.text((554, 62), "ACTIVE // 60 FPS", font=get_font(11, True), fill="#059669")
    draw.text((554, 80), "00:28 / 01:12", font=get_font(11, False), fill="#64748b")

    # Breadcrumb
    draw.text((36, 136), "■ EAUT // DATA-CENTRIC AI ARCHITECTURE", font=get_font(13, True), fill="#0284c7")
    draw.text((W-180, 136), "[PIPELINE // 5-STAGE]", font=get_font(13, True), fill="#64748b")

    # Main Title
    draw.text((36, 168), "KIẾN TRÚC ", font=get_font(28, True), fill="#0f172a")
    draw.text((188, 168), "DCAI 5 BƯỚC KHÉP KÍN", font=get_font(28, True), fill="#2563eb")
    draw.text((36, 210), "Tự động hóa luồng tiếp nhận, phân loại và tra cứu quy chế EAUT.", font=get_font(14, False), fill="#475569")

    # HUD Box Header
    draw.text((36, 252), "┌ 01 ┘ QUY TRÌNH TIỀN XỬ LÝ & PHÂN LUỒNG HỌC VỤ", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-170, 248, W-36, 274], radius=6, outline="#0284c7", width=1)
    draw.text((W-162, 254), "OFFLINE // RAG SECURE", font=get_font(10, True), fill="#0284c7")

    # Box frame with corner brackets
    bx0, by0, bx1, by1 = 34, 284, W-34, 1220
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=14, fill="#ffffff", outline="#cbd5e1", width=1)
    
    # Corner brackets accents
    c_len = 16
    draw.line([(bx0, by0), (bx0 + c_len, by0)], fill="#0284c7", width=3)
    draw.line([(bx0, by0), (bx0, by0 + c_len)], fill="#0284c7", width=3)
    draw.line([(bx1, by0), (bx1 - c_len, by0)], fill="#0284c7", width=3)
    draw.line([(bx1, by0), (bx1, by0 + c_len)], fill="#0284c7", width=3)
    draw.line([(bx0, by1), (bx0 + c_len, by1)], fill="#0284c7", width=3)
    draw.line([(bx0, by1), (bx0, by1 - c_len)], fill="#0284c7", width=3)
    draw.line([(bx1, by1), (bx1 - c_len, by1)], fill="#0284c7", width=3)
    draw.line([(bx1, by1), (bx1, by1 - c_len)], fill="#0284c7", width=3)

    # 5 Stages
    stages = [
        ("01", "Cổng Tiếp Nhận Sinh Viên", "Chuẩn hóa bảng mã Unicode NFC, sửa lỗi gõ tiếng Việt tự động.", "#2563eb", False),
        ("02", "Bảo Vệ Quyền Riêng Tư (PII Masking)", "Che giấu CCCD, số điện thoại, email bằng token ẩn danh an toàn.", "#7c3aed", False),
        ("03", "Phân Luồng AI & Định Tuyến Phòng Ban", "Độ chính xác >94.2%, phân loại đúng 10 nhóm thủ tục học vụ.", "#0284c7", True),
        ("04", "Tra Cứu Quy Chế RAG & Kiểm Soát SLA", "Tự động trích dẫn PROC_TC_01 và thời hạn đối soát giao dịch ngân hàng.", "#059669", False),
        ("05", "Bàn Duyệt Human-in-the-Loop", "Cán bộ chuyên môn kiểm tra, ký duyệt văn bản trước khi gửi sinh viên.", "#d97706", False)
    ]

    sy = by0 + 24
    for idx, (num, name, desc, col, is_active) in enumerate(stages):
        sh = 140
        # Connecting line to next stage
        if idx < len(stages) - 1:
            draw.line([(bx0 + 52, sy + sh), (bx0 + 52, sy + sh + 28)], fill="#cbd5e1" if not is_active else col, width=3)
            # small arrow / dot
            draw.ellipse([bx0 + 49, sy + sh + 12, bx0 + 55, sy + sh + 18], fill=col if is_active else "#94a3b8")

        # Stage card
        card_fill = "#f0fdf4" if (is_active and col == "#059669") else ("#eff6ff" if is_active else "#f8fafc")
        card_border = col if is_active else "#e2e8f0"
        card_width = 2 if is_active else 1

        draw.rounded_rectangle([bx0 + 20, sy, bx1 - 20, sy + sh], radius=12, fill=card_fill, outline=card_border, width=card_width)

        # Number badge
        badge_fill = col if is_active else "#e2e8f0"
        badge_text_col = "#ffffff" if is_active else "#64748b"
        draw.rounded_rectangle([bx0 + 36, sy + 20, bx0 + 76, sy + 60], radius=8, fill=badge_fill)
        draw.text((bx0 + 44, sy + 28), num, font=get_font(16, True), fill=badge_text_col)

        # Stage Name & Status tag
        draw.text((bx0 + 90, sy + 20), name, font=get_font(17, True), fill="#0f172a" if is_active else "#334155")
        if is_active:
            draw.rounded_rectangle([bx1 - 150, sy + 18, bx1 - 36, sy + 44], radius=6, fill=col)
            draw.text((bx1 - 140, sy + 23), "CURRENT STEP", font=get_font(10, True), fill="#ffffff")

        # Description
        draw.text((bx0 + 90, sy + 54), desc, font=get_font(13, False), fill="#475569")

        # Extra interactive metric bar inside active stage 3
        if num == "03":
            # Confidence bar
            draw.text((bx0 + 90, sy + 94), "Độ tin cậy phân loại AI:", font=get_font(12, True), fill="#0284c7")
            draw.rounded_rectangle([bx0 + 250, sy + 96, bx1 - 110, sy + 112], radius=8, fill="#e2e8f0")
            draw.rounded_rectangle([bx0 + 250, sy + 96, bx0 + 250 + int((bx1 - 110 - bx0 - 250)*0.942), sy + 112], radius=8, fill="#0284c7")
            draw.text((bx1 - 100, sy + 94), "94.2%", font=get_font(13, True), fill="#0284c7")
        elif num == "04":
            draw.text((bx0 + 90, sy + 94), "Căn cứ:", font=get_font(12, True), fill="#059669")
            draw.rounded_rectangle([bx0 + 140, sy + 92, bx0 + 240, sy + 116], radius=4, fill="#dcfce7", outline="#86efac", width=1)
            draw.text((bx0 + 150, sy + 96), "PROC_TC_01", font=get_font(11, True), fill="#15803d")
            draw.text((bx0 + 250, sy + 94), "SLA: 24 - 48 giờ làm việc", font=get_font(12, False), fill="#475569")
        elif num == "01":
            draw.text((bx0 + 90, sy + 94), "Bảo vệ đầu vào: Unicode NFC Normalized ✓", font=get_font(12, False), fill="#2563eb")

        sy += sh + 30

    im.save("/tmp/test_scene3_frame.png")
    print("Test Scene 3 frame generated successfully!")

if __name__ == "__main__":
    test_frame()
