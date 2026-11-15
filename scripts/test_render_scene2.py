# -*- coding: utf-8 -*-
"""
Prototype: Test Scene 2 Student Portal with Viewport Frame and Spotlight Highlight in Light Tech HUD
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 720, 1280
FONT_PATH_REG = "/usr/share/fonts/noto/NotoSans-Regular.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/noto/NotoSans-Bold.ttf"
FONT_DEJAVU = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"

def get_font(size, bold=False):
    p = FONT_PATH_BOLD if bold else FONT_PATH_REG
    try:
        return ImageFont.truetype(p, size)
    except:
        return ImageFont.load_default()

def test_frame_scene2():
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    # Subtle tech grid
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill="#edf2f7", width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill="#edf2f7", width=1)

    # Header capsule
    draw.rounded_rectangle([30, 36, W-30, 106], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    draw.rounded_rectangle([44, 48, 104, 94], radius=8, fill="#1d4ed8")
    draw.text((54, 58), "EAUT", font=get_font(18, True), fill="#ffffff")
    draw.text((116, 50), "EDUSUPPORT.AI", font=get_font(18, True), fill="#0f172a")
    draw.text((116, 76), "DATA-CENTRIC AI // HỆ THỐNG HỌC VỤ", font=get_font(11, True), fill="#64748b")
    draw.ellipse([540, 68, 548, 76], fill="#10b981")
    draw.text((554, 62), "ACTIVE // 60 FPS", font=get_font(11, True), fill="#059669")
    draw.text((554, 80), "00:18 / 01:12", font=get_font(11, False), fill="#64748b")

    # Breadcrumb
    draw.text((36, 136), "■ EAUT // STUDENT RECONNAISSANCE PORTAL", font=get_font(13, True), fill="#0284c7")
    draw.text((W-180, 136), "[LIVE // ONLINE 24/7]", font=get_font(13, True), fill="#64748b")

    # Main Title
    draw.text((36, 168), "CỔNG TIẾP NHẬN ", font=get_font(28, True), fill="#0f172a")
    draw.text((276, 168), "SINH VIÊN 24/7", font=get_font(28, True), fill="#2563eb")
    draw.text((36, 210), "Tiếp nhận trực tuyến, tự động chuẩn hóa dữ liệu và bảo vệ danh tính PII.", font=get_font(14, False), fill="#475569")

    # HUD Box 1: Viewport Frame containing Image 1
    draw.text((36, 252), "[ 01 ] GIAO DIỆN CỔNG TIẾP NHẬN HỌC VỤ TRỰC TUYẾN", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-150, 248, W-36, 274], radius=6, outline="#0284c7", width=1)
    draw.text((W-142, 254), "WEB RESPONSIVE", font=get_font(10, True), fill="#0284c7")

    # Load Image 1
    img1_path = "/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_0_1794750093652.png"
    img1 = Image.open(img1_path).convert("RGB")

    # Viewport rectangle
    vx0, vy0, vx1, vy1 = 34, 284, W-34, 760
    vw, vh = vx1 - vx0, vy1 - vy0

    # Crop and fit with slight zoom
    crop_w, crop_h = img1.width, int(img1.width * (vh / vw))
    crop_box = (0, 0, img1.width, min(crop_h, img1.height))
    cropped = img1.crop(crop_box).resize((vw, vh), Image.Resampling.LANCZOS)
    im.paste(cropped, (vx0, vy0))

    # Viewport monitor border
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=8, outline="#0284c7", width=2)

    # Animated Spotlight Box 1: Around the Form Inputs
    # Coordinates inside viewport
    sf_x0, sf_y0, sf_x1, sf_y1 = vx0 + 20, vy0 + 80, vx0 + 380, vy1 - 50
    draw.rounded_rectangle([sf_x0, sf_y0, sf_x1, sf_y1], radius=8, outline="#2563eb", width=3)
    # Floating Pill Tag
    draw.rounded_rectangle([sf_x0 + 10, sf_y0 - 16, sf_x0 + 220, sf_y0 + 12], radius=6, fill="#2563eb")
    draw.text((sf_x0 + 18, sf_y0 - 12), "TỰ ĐỘNG NFC & MASK PII", font=get_font(11, True), fill="#ffffff")

    # Animated Spotlight Box 2: Around SLA commitment
    sla_x0, sla_y0, sla_x1, sla_y1 = vx0 + 400, vy0 + 80, vx1 - 20, vy0 + 280
    draw.rounded_rectangle([sla_x0, sla_y0, sla_x1, sla_y1], radius=8, outline="#059669", width=3)
    # Floating Pill Tag
    draw.rounded_rectangle([sla_x0 + 10, sla_y0 - 16, sla_x0 + 200, sla_y0 + 12], radius=6, fill="#059669")
    draw.text((sla_x0 + 18, sla_y0 - 12), "SLA MINH BẠCH 4H - 48H", font=get_font(11, True), fill="#ffffff")

    # HUD Box 2: Mechanics (bottom)
    draw.text((36, 780), "[ 02 ] CƠ CHẾ DATA-CENTRIC TIẾP NHẬN", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 776, W-36, 802], radius=6, outline="#059669", width=1)
    draw.text((W-150, 782), "DATA INTEGRITY", font=get_font(10, True), fill="#059669")

    # 2 Feature Cards
    f_cards = [
        ("01", "Chuẩn Hóa Unicode NFC & Bảo Mật PII", "Bộ lọc DCAI tự động làm sạch ký tự gõ lỗi và che giấu thông tin định danh cá nhân.", "#2563eb"),
        ("02", "Cam Kết Thời Hạn Xử Lý SLA Minh Bạch", "Đối soát và giải quyết đúng quy trình từ tức thì đến tối đa 48 giờ làm việc.", "#059669"),
        ("03", "Tiếp Nhận Đa Kênh 24/7 Không Gián Đoạn", "Hỗ trợ tải tệp đính kèm lên tới 200MB, phản ánh trực tuyến mọi lúc mọi nơi.", "#7c3aed")
    ]
    cy = 816
    for num, title, desc, col in f_cards:
        draw.rounded_rectangle([34, cy, W-34, cy + 115], radius=12, fill="#ffffff", outline="#cbd5e1", width=1)
        # Left accent pill
        draw.rounded_rectangle([34, cy, 42, cy + 115], radius=4, fill=col)
        # Number badge
        draw.rounded_rectangle([54, cy + 16, 90, cy + 52], radius=6, fill="#eff6ff" if col=="#2563eb" else ("#f0fdf4" if col=="#059669" else "#f5f3ff"))
        draw.text((62, cy + 22), num, font=get_font(15, True), fill=col)
        # Title & Desc
        draw.text((104, cy + 16), title, font=get_font(16, True), fill="#0f172a")
        draw.text((104, cy + 48), desc, font=get_font(13, False), fill="#475569")
        cy += 130

    im.save("/tmp/test_scene2_frame.png")
    print("Test Scene 2 frame generated successfully!")

if __name__ == "__main__":
    test_frame_scene2()
