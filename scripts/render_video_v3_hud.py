# -*- coding: utf-8 -*-
"""
Script: scripts/render_video_v3_hud.py
Dựng toàn bộ video Demo Tech HUD 60s (chuẩn tỷ lệ 9:16 - 720x1280)
Phong cách: HUD Cyber/Tech Dashboard nhưng dùng Color Scheme SÁNG NHẸ (Light Theme),
có animation từng bước, animated pipeline, animated metric counters, Ken Burns pan/zoom,
glowing spotlight bounding boxes, và ghép thuyết minh trôi chảy, dứt khoát.
"""

from pathlib import Path
import subprocess
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 720, 1280
FPS = 30

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio_v3"
CLIPS_DIR = OUTPUT_DIR / "clips_v3"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_VIDEO = OUTPUT_DIR / "edusupport_ai_hud_v3.mp4"

FONT_PATH_REG = "/usr/share/fonts/noto/NotoSans-Regular.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/noto/NotoSans-Bold.ttf"

# Cache fonts
_fonts = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        p = FONT_PATH_BOLD if bold else FONT_PATH_REG
        try:
            _fonts[key] = ImageFont.truetype(p, size)
        except:
            _fonts[key] = ImageFont.load_default()
    return _fonts[key]

# Load user images
IMG1_PATH = "/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_0_1794750093652.png"
IMG2_PATH = "/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_1_1794750093652.png"
IMG3_PATH = "/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_2_1794750093652.png"

img1 = Image.open(IMG1_PATH).convert("RGB") if Path(IMG1_PATH).exists() else Image.new("RGB", (100, 100), "#fff")
img2 = Image.open(IMG2_PATH).convert("RGB") if Path(IMG2_PATH).exists() else Image.new("RGB", (100, 100), "#fff")
img3 = Image.open(IMG3_PATH).convert("RGB") if Path(IMG3_PATH).exists() else Image.new("RGB", (100, 100), "#fff")

TOTAL_VIDEO_SEC = 72

def draw_hud_base(draw, current_sec, breadcrumb_left, breadcrumb_right, title_pre, title_acc, subtitle):
    # Delicate tech grid
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill="#edf2f7", width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill="#edf2f7", width=1)

    # Top Header Capsule Pill
    draw.rounded_rectangle([30, 36, W-30, 106], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    
    # EAUT badge
    draw.rounded_rectangle([44, 48, 104, 94], radius=8, fill="#1d4ed8")
    draw.text((54, 58), "EAUT", font=get_font(18, True), fill="#ffffff")

    # Brand Title & Subtext
    draw.text((116, 50), "EDUSUPPORT.AI", font=get_font(18, True), fill="#0f172a")
    draw.text((116, 76), "DATA-CENTRIC AI // HỆ THỐNG HỌC VỤ", font=get_font(11, True), fill="#64748b")

    # Right Live Status
    pulse = (math.sin(current_sec * 6.0) + 1.0) / 2.0
    dot_col = "#10b981" if pulse > 0.3 else "#34d399"
    draw.ellipse([540, 68, 548, 76], fill=dot_col)
    draw.text((554, 62), "ACTIVE // 60 FPS", font=get_font(11, True), fill="#059669")
    
    # Running timecode
    mins = int(current_sec) // 60
    secs = int(current_sec) % 60
    tmins = TOTAL_VIDEO_SEC // 60
    tsecs = TOTAL_VIDEO_SEC % 60
    draw.text((554, 80), f"{mins:02d}:{secs:02d} / {tmins:02d}:{tsecs:02d}", font=get_font(11, False), fill="#64748b")

    # Breadcrumb
    draw.text((36, 136), f"■ EAUT // {breadcrumb_left}", font=get_font(13, True), fill="#0284c7")
    draw.text((W - 190, 136), f"[{breadcrumb_right}]", font=get_font(13, True), fill="#64748b")

    # Main Title
    draw.text((36, 168), title_pre, font=get_font(27, True), fill="#0f172a")
    pre_len = int(get_font(27, True).getlength(title_pre))
    draw.text((36 + pre_len + 8, 168), title_acc, font=get_font(27, True), fill="#2563eb")
    draw.text((36, 210), subtitle, font=get_font(14, False), fill="#475569")

def draw_corner_brackets(draw, x0, y0, x1, y1, col="#0284c7", c_len=16):
    draw.line([(x0, y0), (x0 + c_len, y0)], fill=col, width=3)
    draw.line([(x0, y0), (x0, y0 + c_len)], fill=col, width=3)
    draw.line([(x1, y0), (x1 - c_len, y0)], fill=col, width=3)
    draw.line([(x1, y0), (x1, y0 + c_len)], fill=col, width=3)
    draw.line([(x0, y1), (x0 + c_len, y1)], fill=col, width=3)
    draw.line([(x0, y1), (x0, y1 - c_len)], fill=col, width=3)
    draw.line([(x1, y1), (x1 - c_len, y1)], fill=col, width=3)
    draw.line([(x1, y1), (x1, y1 - c_len)], fill=col, width=3)

# ==================== RENDER SCENE 1 ====================
def render_frame_scene1(t, dur):
    cur_sec = t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base(
        draw, cur_sec,
        "SYSTEM ARCHITECTURE OVERVIEW", "SYS // LIVE",
        "HỆ THỐNG", "EDUSUPPORT AI",
        "Tiếp nhận, đối soát quy chế và giải quyết phản ánh học vụ thông minh."
    )

    # Box 1 Header
    draw.text((36, 252), "[ 01 ] 2 TRỤ CỘT CÔNG NGHỆ CỐT LÕI", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 248, W-36, 274], radius=6, outline="#2563eb", width=1)
    draw.text((W-150, 254), "CORE PILLARS", font=get_font(10, True), fill="#2563eb")

    bx0, by0, bx1, by1 = 34, 284, W-34, 690
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=14, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, bx0, by0, bx1, by1)

    # Pillar 1: DCAI (animates in from t=0.5)
    p1_prog = min(1.0, max(0.0, (t - 0.5) / 0.7))
    if p1_prog > 0:
        p1_x = bx0 + 20 - int((1.0 - p1_prog) * 40)
        draw.rounded_rectangle([p1_x, by0 + 24, bx1 - 20, by0 + 190], radius=12, fill="#eff6ff", outline="#93c5fd", width=1)
        draw.rounded_rectangle([p1_x + 16, by0 + 40, p1_x + 80, by0 + 80], radius=8, fill="#2563eb")
        draw.text((p1_x + 24, by0 + 48), "DCAI", font=get_font(15, True), fill="#ffffff")
        draw.text((p1_x + 94, by0 + 38), "Data-Centric AI (Chuẩn hóa Dữ liệu)", font=get_font(16, True), fill="#0f172a")
        draw.text((p1_x + 94, by0 + 66), "Bộ lọc tự động chuẩn hóa bảng mã Unicode NFC, sửa lỗi gõ tiếng Việt", font=get_font(13, False), fill="#334155")
        draw.text((p1_x + 94, by0 + 90), "và che giấu thông tin định danh cá nhân (PII Masking) tuyệt đối an toàn.", font=get_font(13, False), fill="#334155")
        draw.rounded_rectangle([p1_x + 94, by0 + 124, p1_x + 360, by0 + 154], radius=6, fill="#dbeafe")
        draw.text((p1_x + 104, by0 + 130), "Tự động hóa 100% đầu vào không lỗi", font=get_font(12, True), fill="#1d4ed8")

    # Pillar 2: HITL (animates in from t=2.5)
    p2_prog = min(1.0, max(0.0, (t - 2.5) / 0.7))
    if p2_prog > 0:
        p2_x = bx0 + 20 - int((1.0 - p2_prog) * 40)
        draw.rounded_rectangle([p2_x, by0 + 210, bx1 - 20, by0 + 376], radius=12, fill="#f0fdf4", outline="#86efac", width=1)
        draw.rounded_rectangle([p2_x + 16, by0 + 226, p2_x + 80, by0 + 266], radius=8, fill="#059669")
        draw.text((p2_x + 24, by0 + 234), "HITL", font=get_font(15, True), fill="#ffffff")
        draw.text((p2_x + 94, by0 + 224), "Human-in-the-Loop (Bàn duyệt Cán bộ)", font=get_font(16, True), fill="#0f172a")
        draw.text((p2_x + 94, by0 + 252), "Cán bộ chuyên môn luôn giữ quyền kiểm chứng cuối cùng,", font=get_font(13, False), fill="#334155")
        draw.text((p2_x + 94, by0 + 276), "đối chiếu căn cứ quy chế và phê duyệt văn bản trước khi gửi sinh viên.", font=get_font(13, False), fill="#334155")
        draw.rounded_rectangle([p2_x + 94, by0 + 310, p2_x + 340, by0 + 340], radius=6, fill="#dcfce7")
        draw.text((p2_x + 104, by0 + 316), "Bảo đảm tính pháp lý & chuẩn mực", font=get_font(12, True), fill="#15803d")

    # Box 2 Header (animates in from t=5.0)
    b2_prog = min(1.0, max(0.0, (t - 5.0) / 0.7))
    if b2_prog > 0:
        draw.text((36, 720), "[ 02 ] NĂNG LỰC VẬN HÀNH & ĐỘ TIN CẬY", font=get_font(15, True), fill="#1e293b")
        draw.rounded_rectangle([W-160, 716, W-36, 742], radius=6, outline="#059669", width=1)
        draw.text((W-150, 722), "PERFORMANCE", font=get_font(10, True), fill="#059669")

        m_y0 = 754
        draw.rounded_rectangle([34, m_y0, W-34, m_y0 + 460], radius=14, fill="#ffffff", outline="#cbd5e1", width=1)
        draw_corner_brackets(draw, 34, m_y0, W-34, m_y0 + 460)

        # 3 Metrics with counting animations
        cnt_prog = min(1.0, max(0.0, (t - 6.0) / 2.5))
        
        # Metric 1: 100% Offline
        val1 = int(cnt_prog * 100)
        draw.rounded_rectangle([54, m_y0 + 24, W-54, m_y0 + 150], radius=12, fill="#f8fafc", outline="#e2e8f0", width=1)
        draw.text((80, m_y0 + 44), f"{val1}%", font=get_font(38, True), fill="#0284c7")
        draw.text((210, m_y0 + 48), "VẬN HÀNH HOÀN TOÀN OFFLINE", font=get_font(16, True), fill="#0f172a")
        draw.text((210, m_y0 + 78), "Bảo mật nội bộ tuyệt đối, không gửi dữ liệu ra bên ngoài.", font=get_font(13, False), fill="#475569")

        # Metric 2: <10ms
        val2 = max(10, int(150 - cnt_prog * 140))
        draw.rounded_rectangle([54, m_y0 + 168, W-54, m_y0 + 294], radius=12, fill="#f8fafc", outline="#e2e8f0", width=1)
        draw.text((80, m_y0 + 188), f"<{val2}ms", font=get_font(38, True), fill="#2563eb")
        draw.text((210, m_y0 + 192), "TỐC ĐỘ PHẢN HỒI SUY LUẬN", font=get_font(16, True), fill="#0f172a")
        draw.text((210, m_y0 + 222), "Rút ngắn thời gian xử lý từ nhiều ngày xuống dưới 10 mili-giây.", font=get_font(13, False), fill="#475569")

        # Metric 3: >94%
        val3 = min(94.2, cnt_prog * 94.2)
        draw.rounded_rectangle([54, m_y0 + 312, W-54, m_y0 + 438], radius=12, fill="#f8fafc", outline="#e2e8f0", width=1)
        draw.text((80, m_y0 + 332), f"{val3:.1f}%", font=get_font(38, True), fill="#059669")
        draw.text((210, m_y0 + 336), "ĐỘ CHÍNH XÁC PHÂN LOẠI AI", font=get_font(16, True), fill="#0f172a")
        draw.text((210, m_y0 + 366), "Định luồng chuẩn xác theo 10 phân nhóm học vụ tại Trường.", font=get_font(13, False), fill="#475569")

    return im

# ==================== RENDER SCENE 2 ====================
def render_frame_scene2(t, dur):
    cur_sec = 14.10 + t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base(
        draw, cur_sec,
        "STUDENT RECONNAISSANCE PORTAL", "LIVE // 24/7",
        "CỔNG TIẾP NHẬN", "SINH VIÊN 24/7",
        "Tiếp nhận trực tuyến, tự động chuẩn hóa dữ liệu và bảo vệ danh tính PII."
    )

    # Box 1: Viewport Frame
    draw.text((36, 252), "[ 01 ] GIAO DIỆN CỔNG TIẾP NHẬN HỌC VỤ TRỰC TUYẾN", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-150, 248, W-36, 274], radius=6, outline="#0284c7", width=1)
    draw.text((W-142, 254), "WEB RESPONSIVE", font=get_font(10, True), fill="#0284c7")

    vx0, vy0, vx1, vy1 = 34, 284, W-34, 750
    vw, vh = vx1 - vx0, vy1 - vy0

    # Ken burns zoom
    zoom = 1.0 + (t / dur) * 0.12
    crop_w = int(img1.width / zoom)
    crop_h = int(crop_w * (vh / vw))
    crop_x = int((img1.width - crop_w) * 0.3)
    crop_y = int((img1.height - crop_h) * 0.2)
    cropped = img1.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)).resize((vw, vh), Image.Resampling.LANCZOS)
    im.paste(cropped, (vx0, vy0))
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=8, outline="#0284c7", width=2)

    # Spotlight 1: Form (t >= 2.0)
    if t >= 2.0:
        sp1_alpha = min(1.0, (t - 2.0) / 0.5)
        sf_x0, sf_y0, sf_x1, sf_y1 = vx0 + 15, vy0 + 60, vx0 + 380, vy1 - 30
        draw.rounded_rectangle([sf_x0, sf_y0, sf_x1, sf_y1], radius=8, outline="#2563eb", width=3)
        draw.rounded_rectangle([sf_x0 + 10, sf_y0 - 16, sf_x0 + 220, sf_y0 + 12], radius=6, fill="#2563eb")
        draw.text((sf_x0 + 18, sf_y0 - 12), "TỰ ĐỘNG NFC & MASK PII", font=get_font(11, True), fill="#ffffff")

    # Spotlight 2: SLA (t >= 6.0)
    if t >= 6.0:
        sla_x0, sla_y0, sla_x1, sla_y1 = vx0 + 390, vy0 + 60, vx1 - 15, vy0 + 270
        draw.rounded_rectangle([sla_x0, sla_y0, sla_x1, sla_y1], radius=8, outline="#059669", width=3)
        draw.rounded_rectangle([sla_x0 + 10, sla_y0 - 16, sla_x0 + 200, sla_y0 + 12], radius=6, fill="#059669")
        draw.text((sla_x0 + 18, sla_y0 - 12), "SLA MINH BẠCH 4H - 48H", font=get_font(11, True), fill="#ffffff")

    # Box 2: Mechanics
    draw.text((36, 776), "[ 02 ] CƠ CHẾ DATA-CENTRIC TIẾP NHẬN", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 772, W-36, 798], radius=6, outline="#059669", width=1)
    draw.text((W-150, 778), "DATA INTEGRITY", font=get_font(10, True), fill="#059669")

    f_cards = [
        ("01", "Chuẩn Hóa Unicode NFC & Bảo Mật PII", "Bộ lọc DCAI tự động làm sạch ký tự gõ lỗi và che giấu thông tin định danh cá nhân.", "#2563eb", 1.0),
        ("02", "Cam Kết Thời Hạn Xử Lý SLA Minh Bạch", "Đối soát và giải quyết đúng quy trình từ tức thì đến tối đa 48 giờ làm việc.", "#059669", 5.0),
        ("03", "Tiếp Nhận Đa Kênh 24/7 Không Gián Đoạn", "Hỗ trợ tải tệp đính kèm lên tới 200MB, phản ánh trực tuyến mọi lúc mọi nơi.", "#7c3aed", 9.0)
    ]
    cy = 812
    for num, title, desc, col, t_trigger in f_cards:
        if t >= t_trigger:
            draw.rounded_rectangle([34, cy, W-34, cy + 115], radius=12, fill="#ffffff", outline="#cbd5e1", width=1)
            draw.rounded_rectangle([34, cy, 42, cy + 115], radius=4, fill=col)
            draw.rounded_rectangle([54, cy + 16, 90, cy + 52], radius=6, fill="#eff6ff" if col=="#2563eb" else ("#f0fdf4" if col=="#059669" else "#f5f3ff"))
            draw.text((62, cy + 22), num, font=get_font(15, True), fill=col)
            draw.text((104, cy + 16), title, font=get_font(16, True), fill="#0f172a")
            draw.text((104, cy + 48), desc, font=get_font(13, False), fill="#475569")
        cy += 130

    return im

# ==================== RENDER SCENE 3 ====================
def render_frame_scene3(t, dur):
    cur_sec = 29.24 + t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base(
        draw, cur_sec,
        "DATA-CENTRIC AI ARCHITECTURE", "PIPELINE // 5-STAGE",
        "KIẾN TRÚC", "DCAI 5 BƯỚC KHÉP KÍN",
        "Tự động hóa luồng tiếp nhận, phân loại và tra cứu quy chế EAUT."
    )

    draw.text((36, 252), "[ 01 ] QUY TRÌNH TIỀN XỬ LÝ & PHÂN LUỒNG HỌC VỤ", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-170, 248, W-36, 274], radius=6, outline="#0284c7", width=1)
    draw.text((W-162, 254), "OFFLINE // RAG SECURE", font=get_font(10, True), fill="#0284c7")

    bx0, by0, bx1, by1 = 34, 284, W-34, 1220
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=14, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, bx0, by0, bx1, by1)

    # 5 Stages timing:
    # Stage 0: 0.0 - 2.5
    # Stage 1: 2.5 - 5.0
    # Stage 2: 5.0 - 8.5
    # Stage 3: 8.5 - 11.5
    # Stage 4: 11.5 - dur
    active_idx = 0
    if t >= 11.5: active_idx = 4
    elif t >= 8.5: active_idx = 3
    elif t >= 5.0: active_idx = 2
    elif t >= 2.5: active_idx = 1

    stages = [
        ("01", "Cổng Tiếp Nhận Sinh Viên", "Chuẩn hóa bảng mã Unicode NFC, sửa lỗi gõ tiếng Việt tự động.", "#2563eb"),
        ("02", "Bảo Vệ Quyền Riêng Tư (PII Masking)", "Che giấu CCCD, số điện thoại, email bằng token ẩn danh an toàn.", "#7c3aed"),
        ("03", "Phân Luồng AI & Định Tuyến Phòng Ban", "Độ chính xác >94.2%, phân loại đúng 10 nhóm thủ tục học vụ.", "#0284c7"),
        ("04", "Tra Cứu Quy Chế RAG & Kiểm Soát SLA", "Tự động trích dẫn PROC_TC_01 và thời hạn đối soát giao dịch ngân hàng.", "#059669"),
        ("05", "Bàn Duyệt Human-in-the-Loop", "Cán bộ chuyên môn kiểm tra, ký duyệt văn bản trước khi gửi sinh viên.", "#d97706")
    ]

    sy = by0 + 24
    for idx, (num, name, desc, col) in enumerate(stages):
        sh = 140
        is_active = (idx == active_idx)

        # Connecting line
        if idx < len(stages) - 1:
            line_col = col if (idx <= active_idx) else "#cbd5e1"
            draw.line([(bx0 + 52, sy + sh), (bx0 + 52, sy + sh + 28)], fill=line_col, width=3)
            # Animated pulse traveling down
            pulse_y = sy + sh + int((math.sin(t * 8.0) * 0.5 + 0.5) * 28)
            draw.ellipse([bx0 + 49, pulse_y - 3, bx0 + 55, pulse_y + 3], fill=col if idx <= active_idx else "#94a3b8")

        card_fill = "#f0fdf4" if (is_active and col == "#059669") else ("#eff6ff" if is_active else "#f8fafc")
        card_border = col if is_active else "#e2e8f0"
        card_width = 2 if is_active else 1

        draw.rounded_rectangle([bx0 + 20, sy, bx1 - 20, sy + sh], radius=12, fill=card_fill, outline=card_border, width=card_width)

        badge_fill = col if is_active else "#e2e8f0"
        badge_text_col = "#ffffff" if is_active else "#64748b"
        draw.rounded_rectangle([bx0 + 36, sy + 20, bx0 + 76, sy + 60], radius=8, fill=badge_fill)
        draw.text((bx0 + 44, sy + 28), num, font=get_font(16, True), fill=badge_text_col)

        draw.text((bx0 + 90, sy + 20), name, font=get_font(17, True), fill="#0f172a" if is_active else "#334155")
        if is_active:
            draw.rounded_rectangle([bx1 - 150, sy + 18, bx1 - 36, sy + 44], radius=6, fill=col)
            draw.text((bx1 - 140, sy + 23), "CURRENT STEP", font=get_font(10, True), fill="#ffffff")

        draw.text((bx0 + 90, sy + 54), desc, font=get_font(13, False), fill="#475569")

        # Interactive sub-elements
        if num == "03":
            draw.text((bx0 + 90, sy + 94), "Độ tin cậy phân loại AI:", font=get_font(12, True), fill="#0284c7")
            # animated gauge
            p_fill = min(1.0, max(0.0, (t - 5.0) / 2.0)) if active_idx >= 2 else 0.0
            cur_acc = p_fill * 94.2
            draw.rounded_rectangle([bx0 + 250, sy + 96, bx1 - 110, sy + 112], radius=8, fill="#e2e8f0")
            draw.rounded_rectangle([bx0 + 250, sy + 96, bx0 + 250 + int((bx1 - 110 - bx0 - 250) * (cur_acc / 100.0)), sy + 112], radius=8, fill="#0284c7")
            draw.text((bx1 - 100, sy + 94), f"{cur_acc:.1f}%", font=get_font(13, True), fill="#0284c7")
        elif num == "04":
            draw.text((bx0 + 90, sy + 94), "Căn cứ:", font=get_font(12, True), fill="#059669")
            draw.rounded_rectangle([bx0 + 140, sy + 92, bx0 + 240, sy + 116], radius=4, fill="#dcfce7", outline="#86efac", width=1)
            draw.text((bx0 + 150, sy + 96), "PROC_TC_01", font=get_font(11, True), fill="#15803d")
            draw.text((bx0 + 250, sy + 94), "SLA: 24 - 48 giờ làm việc", font=get_font(12, False), fill="#475569")
        elif num == "01":
            draw.text((bx0 + 90, sy + 94), "Bảo vệ đầu vào: Unicode NFC Normalized [OK]", font=get_font(12, False), fill="#2563eb")
        elif num == "02":
            draw.text((bx0 + 90, sy + 94), "Định danh: [CCCD_MASKED] - [PHONE_MASKED]", font=get_font(12, False), fill="#7c3aed")
        elif num == "05":
            draw.text((bx0 + 90, sy + 94), "Trạng thái: Sẵn sàng ký duyệt văn bản điện tử [OK]", font=get_font(12, False), fill="#d97706")

        sy += sh + 30

    return im

# ==================== RENDER SCENE 4 ====================
def render_frame_scene4(t, dur):
    cur_sec = 43.61 + t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base(
        draw, cur_sec,
        "OFFICER WORKBENCH & TRIAGE", "TRIAGE // LIVE",
        "BÀN DUYỆT CÁN BỘ", "& PHÂN LUỒNG EAUT",
        "Tối giản trường dữ liệu, phân luồng 2 nhóm và đối soát quy chế tức thì."
    )

    # Box 1: Viewport Frame containing Image 2
    draw.text((36, 252), "[ 01 ] GIAO DIỆN BÀN DUYỆT CÁN BỘ PHÂN QUYỀN", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 248, W-36, 274], radius=6, outline="#2563eb", width=1)
    draw.text((W-150, 254), "HUMAN REVIEW", font=get_font(10, True), fill="#2563eb")

    vx0, vy0, vx1, vy1 = 34, 284, W-34, 750
    vw, vh = vx1 - vx0, vy1 - vy0

    zoom = 1.0 + (t / dur) * 0.12
    crop_w = int(img2.width / zoom)
    crop_h = int(crop_w * (vh / vw))
    crop_x = int((img2.width - crop_w) * 0.4)
    crop_y = int((img2.height - crop_h) * 0.3)
    cropped = img2.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)).resize((vw, vh), Image.Resampling.LANCZOS)
    im.paste(cropped, (vx0, vy0))
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=8, outline="#2563eb", width=2)

    # Spotlight 1: 2 radio groups (t >= 1.5)
    if t >= 1.5:
        r_x0, r_y0, r_x1, r_y1 = vx0 + 10, vy0 + 60, vx0 + 320, vy0 + 140
        draw.rounded_rectangle([r_x0, r_y0, r_x1, r_y1], radius=8, outline="#2563eb", width=3)
        draw.rounded_rectangle([r_x0 + 8, r_y0 - 16, r_x0 + 230, r_y0 + 12], radius=6, fill="#2563eb")
        draw.text((r_x0 + 14, r_y0 - 12), "2 NHÓM PHÂN LUỒNG MỚI", font=get_font(11, True), fill="#ffffff")

    # Spotlight 2: Table no priority (t >= 5.0)
    if t >= 5.0:
        tb_x0, tb_y0, tb_x1, tb_y1 = vx0 + 10, vy0 + 160, vx0 + 340, vy1 - 20
        draw.rounded_rectangle([tb_x0, tb_y0, tb_x1, tb_y1], radius=8, outline="#059669", width=3)
        draw.rounded_rectangle([tb_x0 + 8, tb_y0 - 16, tb_x0 + 260, tb_y0 + 12], radius=6, fill="#059669")
        draw.text((tb_x0 + 14, tb_y0 - 12), "BỎ ƯU TIÊN Ở HỒ SƠ ĐÃ GỬI", font=get_font(11, True), fill="#ffffff")

    # Spotlight 3: Procedure & SLA card (t >= 8.5)
    if t >= 8.5:
        pr_x0, pr_y0, pr_x1, pr_y1 = vx0 + 360, vy0 + 240, vx1 - 10, vy1 - 40
        draw.rounded_rectangle([pr_x0, pr_y0, pr_x1, pr_y1], radius=8, outline="#d97706", width=3)
        draw.rounded_rectangle([pr_x0 + 8, pr_y0 - 16, pr_x0 + 240, pr_y0 + 12], radius=6, fill="#d97706")
        draw.text((pr_x0 + 14, pr_y0 - 12), "SLA ĐỐI SOÁT GẠCH NỢ 24-48H", font=get_font(11, True), fill="#ffffff")

    # Box 2: Officer UX Enhancements
    draw.text((36, 776), "[ 02 ] CẢI TIẾN TRẢI NGHIỆM CÁN BỘ", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 772, W-36, 798], radius=6, outline="#059669", width=1)
    draw.text((W-150, 778), "OPTIMIZATION", font=get_font(10, True), fill="#059669")

    cards = [
        ("01", "Tinh Gọn 2 Nhóm: Cần Đơn Vị Xem Xét & Đã Gửi", "Loại bỏ hoàn toàn trường ưu tiên thừa ở hồ sơ đã gửi, tránh nhiễu thông tin.", "#2563eb", 1.0),
        ("02", "Tự Động Tra Cứu Quy Chế Học Phí PROC_TC_01", "Căn cứ quy chế và biểu mẫu chuẩn được tự động đính kèm ngay trên màn hình.", "#059669", 5.0),
        ("03", "Kiểm Soát Thời Hạn SLA Trực Quan", "Cảnh báo hạn đối soát ngân hàng và gia hạn học phí, bảo đảm quyền lợi sinh viên.", "#d97706", 8.5)
    ]
    cy = 812
    for num, title, desc, col, t_trig in cards:
        if t >= t_trig:
            draw.rounded_rectangle([34, cy, W-34, cy + 115], radius=12, fill="#ffffff", outline="#cbd5e1", width=1)
            draw.rounded_rectangle([34, cy, 42, cy + 115], radius=4, fill=col)
            draw.rounded_rectangle([54, cy + 16, 90, cy + 52], radius=6, fill="#eff6ff" if col=="#2563eb" else ("#f0fdf4" if col=="#059669" else "#fffbeb"))
            draw.text((62, cy + 22), num, font=get_font(15, True), fill=col)
            draw.text((104, cy + 16), title, font=get_font(16, True), fill="#0f172a")
            draw.text((104, cy + 48), desc, font=get_font(13, False), fill="#475569")
        cy += 130

    return im

# ==================== RENDER SCENE 5 ====================
def render_frame_scene5(t, dur):
    cur_sec = 57.36 + t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base(
        draw, cur_sec,
        "EMAIL DISPATCH & SYSTEM BENCHMARK", "PRODUCTION // READY",
        "EMAIL GIẢI QUYẾT", "& HIỆU NĂNG ĐỘT PHÁ",
        "Văn bản chuẩn nhận diện EAUT, tốc độ phản hồi dưới 10 mili-giây."
    )

    # Box 1: Viewport Frame containing Image 3
    draw.text((36, 252), "[ 01 ] VĂN BẢN EMAIL GIẢI QUYẾT GỬI SINH VIÊN", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 248, W-36, 274], radius=6, outline="#059669", width=1)
    draw.text((W-150, 254), "HTML DISPATCH", font=get_font(10, True), fill="#059669")

    vx0, vy0, vx1, vy1 = 34, 284, W-34, 730
    vw, vh = vx1 - vx0, vy1 - vy0

    # Gentle scroll pan down the email
    scroll_factor = (t / dur) * 0.25
    crop_w = img3.width
    crop_h = int(crop_w * (vh / vw))
    crop_y = int((img3.height - crop_h) * scroll_factor)
    cropped = img3.crop((0, crop_y, crop_w, crop_y + crop_h)).resize((vw, vh), Image.Resampling.LANCZOS)
    im.paste(cropped, (vx0, vy0))
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=8, outline="#059669", width=2)

    # Email badge
    draw.rounded_rectangle([vx0 + 16, vy0 + 16, vx0 + 260, vy0 + 44], radius=6, fill="#059669")
    draw.text((vx0 + 24, vy0 + 20), "EMAIL HTML CHUẨN EAUT [OK]", font=get_font(11, True), fill="#ffffff")

    # Box 2: Benchmark & Impact
    draw.text((36, 756), "[ 02 ] THỰC CHỨNG HIỆU NĂNG & ĐỘ TIN CẬY", font=get_font(15, True), fill="#1e293b")
    draw.rounded_rectangle([W-160, 752, W-36, 778], radius=6, outline="#2563eb", width=1)
    draw.text((W-150, 758), "BENCHMARK", font=get_font(10, True), fill="#2563eb")

    bx0, by0, bx1, by1 = 34, 788, W-34, 1220
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=14, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, bx0, by0, bx1, by1)

    cnt_prog = min(1.0, max(0.0, t / 3.0))

    # Metric 1: 43 / 43 Tests
    n_tests = int(cnt_prog * 43)
    draw.rounded_rectangle([54, by0 + 20, W-54, by0 + 110], radius=10, fill="#f0fdf4", outline="#86efac", width=1)
    draw.text((74, by0 + 32), f"{n_tests} / 43", font=get_font(32, True), fill="#15803d")
    draw.text((220, by0 + 36), "KỊCH BẢN KIỂM THỬ VƯỢT QUA", font=get_font(15, True), fill="#0f172a")
    draw.text((220, by0 + 64), "Bảo đảm tính toàn vẹn 100% chức năng học vụ.", font=get_font(12, False), fill="#475569")

    # Metric 2: <10ms
    ms_val = max(10, int(180 - cnt_prog * 170))
    draw.rounded_rectangle([54, by0 + 126, W-54, by0 + 216], radius=10, fill="#eff6ff", outline="#93c5fd", width=1)
    draw.text((74, by0 + 138), f"<{ms_val}ms", font=get_font(32, True), fill="#1d4ed8")
    draw.text((220, by0 + 142), "TỐC ĐỘ XỬ LÝ PHẢN HỒI", font=get_font(15, True), fill="#0f172a")
    draw.text((220, by0 + 170), "Tự động hóa hoàn toàn quy trình đối soát hồ sơ.", font=get_font(12, False), fill="#475569")

    # Metric 3: 100% Offline
    off_val = int(cnt_prog * 100)
    draw.rounded_rectangle([54, by0 + 232, W-54, by0 + 322], radius=10, fill="#faf5ff", outline="#d8b4fe", width=1)
    draw.text((74, by0 + 244), f"{off_val}%", font=get_font(32, True), fill="#7e22ce")
    draw.text((220, by0 + 248), "BẢO MẬT DỮ LIỆU OFFLINE", font=get_font(15, True), fill="#0f172a")
    draw.text((220, by0 + 276), "An toàn dữ liệu sinh viên tuyệt đối tại chỗ.", font=get_font(12, False), fill="#475569")

    # Final Banner Card
    draw.rounded_rectangle([54, by0 + 342, W-54, by0 + 410], radius=10, fill="#1d4ed8")
    draw.text((80, by0 + 360), "EDUSUPPORT AI — CHUYỂN ĐỔI SỐ HỌC VỤ EAUT", font=get_font(14, True), fill="#ffffff")

    return im

SCENE_CONFIGS = [
    {"id": "scene1", "render_func": render_frame_scene1},
    {"id": "scene2", "render_func": render_frame_scene2},
    {"id": "scene3", "render_func": render_frame_scene3},
    {"id": "scene4", "render_func": render_frame_scene4},
    {"id": "scene5", "render_func": render_frame_scene5},
]

def render_scene_clip(scene_cfg):
    scene_id = scene_cfg["id"]
    render_func = scene_cfg["render_func"]
    audio_path = AUDIO_DIR / f"{scene_id}.mp3"
    clip_path = CLIPS_DIR / f"{scene_id}.mp4"

    # Get exact duration of audio
    dur_str = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]).decode().strip()
    dur = float(dur_str)
    total_frames = int(dur * FPS)

    print(f"\n-> Rendering {scene_id}: duration={dur:.2f}s ({total_frames} frames @ {FPS}fps)...")

    # Launch ffmpeg process taking raw rgb24 frames from stdin
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(clip_path)
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f_idx in range(total_frames):
        t = f_idx / FPS
        frame_im = render_func(t, dur)
        frame_bytes = frame_im.tobytes()
        proc.stdin.write(frame_bytes)

    proc.stdin.close()
    proc.wait()
    print(f"   + Finished: {clip_path.name} (exit code: {proc.returncode})")
    return clip_path, dur

def assemble_final_video(clips_info):
    print("\n-> Assembling final video with crossfade transitions and ambient BGM...")
    # Generate concat / xfade filter
    # 5 clips: c0, c1, c2, c3, c4
    # Crossfade duration: 0.5s
    xfade_dur = 0.5
    
    # We will build ffmpeg filter_complex
    # Inputs: 0 to 4 are clips, input 5 is bgm
    cmd = ["ffmpeg", "-y"]
    for c_path, _ in clips_info:
        cmd.extend(["-i", str(c_path)])
    
    bgm_path = Path("/tmp/bgm_tech.wav")
    has_bgm = bgm_path.exists()
    if has_bgm:
        cmd.extend(["-i", str(bgm_path)])

    filter_lines = []
    
    # Video crossfades
    # [0:v][1:v]xfade=transition=fade:duration=0.5:offset=X[v01]; ...
    cur_offset = clips_info[0][1] - xfade_dur
    prev_v = "0:v"
    for i in range(1, len(clips_info)):
        out_v = f"v{i}"
        filter_lines.append(f"[{prev_v}][{i}:v]xfade=transition=fade:duration={xfade_dur}:offset={cur_offset:.2f}[{out_v}]")
        prev_v = out_v
        if i < len(clips_info) - 1:
            cur_offset += clips_info[i][1] - xfade_dur

    # Audio crossfades
    prev_a = "0:a"
    for i in range(1, len(clips_info)):
        out_a = f"a{i}"
        filter_lines.append(f"[{prev_a}][{i}:a]acrossfade=d={xfade_dur}[{out_a}]")
        prev_a = out_a

    # BGM mixing if available
    final_a = prev_a
    if has_bgm:
        # Duck BGM to volume 0.12 and mix with speech
        filter_lines.append(f"[5:a]volume=0.12[bgm]")
        filter_lines.append(f"[{prev_a}][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_final]")
        final_a = "a_final"

    filter_complex = ";".join(filter_lines)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{prev_v}]",
        "-map", f"[{final_a}]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(FINAL_VIDEO)
    ])

    print("-> Executing FFmpeg final concatenation command...")
    subprocess.run(cmd, check=True)
    print(f"\n🎉 HOÀN TẤT XUẤT VIDEO TECH HUD V3: {FINAL_VIDEO}")

def main():
    print("=== BẮT ĐẦU DỰNG VIDEO TECH HUD REEL (LIGHT THEME - 60s) ===")
    clips_info = []
    for cfg in SCENE_CONFIGS:
        clip_path, dur = render_scene_clip(cfg)
        clips_info.append((clip_path, dur))

    assemble_final_video(clips_info)

if __name__ == "__main__":
    main()
