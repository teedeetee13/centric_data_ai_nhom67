# -*- coding: utf-8 -*-
"""
Script: scripts/render_master_combined_video.py
Dựng Video Master Tổng Hợp Kết Hợp Cả 3 Thành Phần:
1. Giới thiệu (Intro & Định vị 2 trụ cột DCAI + HITL)
2. Giải thích (Kiến trúc DCAI 5 bước hoạt họa động, tự động tra cứu RAG)
3. Demo thực tế (Trực tiếp quay từ trình duyệt điều khiển web live, chuyển 2 nhóm, quy chế, email, bánh răng)
4. Tổng kết & Hiệu năng đột phá

Định dạng: Full HD 1080p (1920 x 1080), 30 FPS.
Color Scheme: Sáng nhẹ (Light Tech Theme), hiệu ứng chuyển động mượt mà, thuyết minh dứt khoát.
"""

from pathlib import Path
import subprocess
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 1920, 1080
FPS = 30

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio_master"
CLIPS_DIR = OUTPUT_DIR / "clips_master"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
MASTER_VIDEO = OUTPUT_DIR / "edusupport_ai_master_combined.mp4"

FONT_PATH_REG = "/usr/share/fonts/noto/NotoSans-Regular.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/noto/NotoSans-Bold.ttf"

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

TOTAL_VIDEO_SEC = 67

def draw_hud_base_16_9(draw, current_sec, breadcrumb_left, breadcrumb_right, title_pre, title_acc, subtitle):
    # Delicate tech grid
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill="#edf2f7", width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill="#edf2f7", width=1)

    # Top Header Capsule Pill
    draw.rounded_rectangle([60, 36, W-60, 116], radius=18, fill="#ffffff", outline="#cbd5e1", width=1)
    
    # EAUT badge
    draw.rounded_rectangle([80, 50, 160, 102], radius=10, fill="#1d4ed8")
    draw.text((95, 62), "EAUT", font=get_font(22, True), fill="#ffffff")

    # Brand Title & Subtext
    draw.text((180, 52), "EDUSUPPORT.AI", font=get_font(24, True), fill="#0f172a")
    draw.text((180, 84), "DATA-CENTRIC AI // HỆ THỐNG TIẾP NHẬN & PHÂN LUỒNG HỌC VỤ", font=get_font(13, True), fill="#64748b")

    # Right Live Status
    pulse = (math.sin(current_sec * 6.0) + 1.0) / 2.0
    dot_col = "#10b981" if pulse > 0.3 else "#34d399"
    draw.ellipse([W - 320, 72, W - 308, 84], fill=dot_col)
    draw.text((W - 296, 64), "ACTIVE // 60 FPS", font=get_font(14, True), fill="#059669")
    
    mins = int(current_sec) // 60
    secs = int(current_sec) % 60
    tmins = TOTAL_VIDEO_SEC // 60
    tsecs = TOTAL_VIDEO_SEC % 60
    draw.text((W - 296, 86), f"{mins:02d}:{secs:02d} / {tmins:02d}:{tsecs:02d}", font=get_font(13, False), fill="#64748b")

    # Breadcrumb
    draw.text((68, 142), f"■ EAUT // {breadcrumb_left}", font=get_font(16, True), fill="#0284c7")
    draw.text((W - 280, 142), f"[{breadcrumb_right}]", font=get_font(15, True), fill="#64748b")

    # Main Title
    draw.text((68, 176), title_pre, font=get_font(34, True), fill="#0f172a")
    pre_len = int(get_font(34, True).getlength(title_pre))
    draw.text((68 + pre_len + 12, 176), title_acc, font=get_font(34, True), fill="#2563eb")
    draw.text((68, 226), subtitle, font=get_font(18, False), fill="#475569")

def draw_corner_brackets(draw, x0, y0, x1, y1, col="#0284c7", c_len=20):
    draw.line([(x0, y0), (x0 + c_len, y0)], fill=col, width=3)
    draw.line([(x0, y0), (x0, y0 + c_len)], fill=col, width=3)
    draw.line([(x1, y0), (x1 - c_len, y0)], fill=col, width=3)
    draw.line([(x1, y0), (x1, y0 + c_len)], fill=col, width=3)
    draw.line([(x0, y1), (x0 + c_len, y1)], fill=col, width=3)
    draw.line([(x0, y1), (x0, y1 - c_len)], fill=col, width=3)
    draw.line([(x1, y1), (x1 - c_len, y1)], fill=col, width=3)
    draw.line([(x1, y1), (x1, y1 - c_len)], fill=col, width=3)

# ==================== PHẦN 1: GIỚI THIỆU ====================
def render_frame_part1(t, dur):
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base_16_9(
        draw, t,
        "SYSTEM ARCHITECTURE OVERVIEW", "SYS // LIVE",
        "HỆ THỐNG", "EDUSUPPORT AI",
        "Tiếp nhận, đối soát quy chế và giải quyết phản ánh học vụ thông minh tại Trường Đại học Công nghệ Đông Á."
    )

    # Left Column: 2 Core Pillars (Box 01)
    bx0, by0, bx1, by1 = 60, 276, 940, 1020
    draw.text((68, 280), "[ 01 ] 2 TRỤ CỘT CÔNG NGHỆ CỐT LÕI", font=get_font(18, True), fill="#1e293b")
    draw.rounded_rectangle([800, 274, 940, 304], radius=6, outline="#2563eb", width=1)
    draw.text((812, 282), "CORE PILLARS", font=get_font(12, True), fill="#2563eb")

    draw.rounded_rectangle([bx0, 316, bx1, by1], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, bx0, 316, bx1, by1)

    # Pillar 1: DCAI
    p1_prog = min(1.0, max(0.0, (t - 0.5) / 0.8))
    if p1_prog > 0:
        c1_y = 340
        draw.rounded_rectangle([bx0 + 24, c1_y, bx1 - 24, c1_y + 300], radius=14, fill="#eff6ff", outline="#93c5fd", width=1)
        draw.rounded_rectangle([bx0 + 44, c1_y + 24, bx0 + 130, c1_y + 76], radius=10, fill="#2563eb")
        draw.text((bx0 + 56, c1_y + 36), "DCAI", font=get_font(20, True), fill="#ffffff")
        draw.text((bx0 + 150, c1_y + 34), "Data-Centric AI (Chuẩn Hóa Dữ Liệu)", font=get_font(22, True), fill="#0f172a")
        
        draw.text((bx0 + 44, c1_y + 96), "• Chuẩn hóa bảng mã Unicode NFC, sửa lỗi gõ tiếng Việt tự động.", font=get_font(16, False), fill="#334155")
        draw.text((bx0 + 44, c1_y + 130), "• Che giấu thông tin định danh (PII Masking) CCCD, SĐT, Email.", font=get_font(16, False), fill="#334155")
        draw.text((bx0 + 44, c1_y + 164), "• Phân loại chuẩn xác theo 10 phân nhóm học vụ tại trường EAUT.", font=get_font(16, False), fill="#334155")
        
        draw.rounded_rectangle([bx0 + 44, c1_y + 215, bx0 + 380, c1_y + 260], radius=8, fill="#dbeafe")
        draw.text((bx0 + 56, c1_y + 226), "Tự động hóa 100% đầu vào không lỗi", font=get_font(15, True), fill="#1d4ed8")

    # Pillar 2: HITL
    p2_prog = min(1.0, max(0.0, (t - 2.5) / 0.8))
    if p2_prog > 0:
        c2_y = 665
        draw.rounded_rectangle([bx0 + 24, c2_y, bx1 - 24, c2_y + 310], radius=14, fill="#f0fdf4", outline="#86efac", width=1)
        draw.rounded_rectangle([bx0 + 44, c2_y + 24, bx0 + 130, c2_y + 76], radius=10, fill="#059669")
        draw.text((bx0 + 56, c2_y + 36), "HITL", font=get_font(20, True), fill="#ffffff")
        draw.text((bx0 + 150, c2_y + 34), "Human-in-the-Loop (Bàn Duyệt Cán Bộ)", font=get_font(22, True), fill="#0f172a")

        draw.text((bx0 + 44, c2_y + 96), "• Cán bộ chuyên môn luôn giữ quyền kiểm chứng và ra quyết định cuối cùng.", font=get_font(16, False), fill="#334155")
        draw.text((bx0 + 44, c2_y + 130), "• Tự động đối soát Căn cứ Quy chế EAUT chính thức và thời hạn SLA.", font=get_font(16, False), fill="#334155")
        draw.text((bx0 + 44, c2_y + 164), "• Phê duyệt và gửi văn bản email chính thức tới sinh viên chỉ với 1 click.", font=get_font(16, False), fill="#334155")

        draw.rounded_rectangle([bx0 + 44, c2_y + 220, bx0 + 370, c2_y + 265], radius=8, fill="#dcfce7")
        draw.text((bx0 + 56, c2_y + 231), "Bảo đảm tính pháp lý & chuẩn mực", font=get_font(15, True), fill="#15803d")

    # Right Column: Performance & Metrics (Box 02)
    rx0, ry0, rx1, ry1 = 980, 276, W - 60, 1020
    draw.text((rx0 + 8, 280), "[ 02 ] NĂNG LỰC VẬN HÀNH & ĐỘ TIN CẬY", font=get_font(18, True), fill="#1e293b")
    draw.rounded_rectangle([rx1 - 150, 274, rx1, 304], radius=6, outline="#059669", width=1)
    draw.text((rx1 - 138, 282), "PERFORMANCE", font=get_font(12, True), fill="#059669")

    draw.rounded_rectangle([rx0, 316, rx1, ry1], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, rx0, 316, rx1, ry1)

    cnt_prog = min(1.0, max(0.0, (t - 4.0) / 3.0))

    # Metric 1: 100% Offline
    m1_val = int(cnt_prog * 100)
    draw.rounded_rectangle([rx0 + 24, 350, rx1 - 24, 520], radius=14, fill="#f8fafc", outline="#e2e8f0", width=1)
    draw.text((rx0 + 50, 380), f"{m1_val}%", font=get_font(52, True), fill="#0284c7")
    draw.text((rx0 + 230, 385), "VẬN HÀNH HOÀN TOÀN OFFLINE", font=get_font(22, True), fill="#0f172a")
    draw.text((rx0 + 230, 430), "Bảo mật dữ liệu sinh viên tuyệt đối tại chỗ, không gửi thông tin ra đám mây.", font=get_font(16, False), fill="#475569")

    # Metric 2: <10ms
    m2_val = max(10, int(150 - cnt_prog * 140))
    draw.rounded_rectangle([rx0 + 24, 550, rx1 - 24, 720], radius=14, fill="#f8fafc", outline="#e2e8f0", width=1)
    draw.text((rx0 + 50, 580), f"<{m2_val}ms", font=get_font(52, True), fill="#2563eb")
    draw.text((rx0 + 230, 585), "TỐC ĐỘ PHẢN HỒI SUY LUẬN", font=get_font(22, True), fill="#0f172a")
    draw.text((rx0 + 230, 630), "Rút ngắn thời gian xử lý hồ sơ từ vài ngày xuống dưới 10 mili-giây tức thì.", font=get_font(16, False), fill="#475569")

    # Metric 3: >94%
    m3_val = min(94.2, cnt_prog * 94.2)
    draw.rounded_rectangle([rx0 + 24, 750, rx1 - 24, 920], radius=14, fill="#f8fafc", outline="#e2e8f0", width=1)
    draw.text((rx0 + 50, 780), f"{m3_val:.1f}%", font=get_font(52, True), fill="#059669")
    draw.text((rx0 + 230, 785), "ĐỘ CHÍNH XÁC PHÂN LUỒNG AI", font=get_font(22, True), fill="#0f172a")
    draw.text((rx0 + 230, 830), "Định luồng tự động chuẩn xác về đúng phòng ban chức năng giải quyết.", font=get_font(16, False), fill="#475569")

    return im

# ==================== PHẦN 2: GIẢI THÍCH KIẾN TRÚC DCAI 5 BƯỚC ====================
def render_frame_part2(t, dur):
    cur_sec = 15.56 + t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base_16_9(
        draw, cur_sec,
        "DATA-CENTRIC AI ARCHITECTURE", "PIPELINE // 5-STAGE",
        "KIẾN TRÚC", "DCAI 5 BƯỚC KHÉP KÍN",
        "Tự động hóa toàn diện luồng dữ liệu học vụ từ tiếp nhận, phân loại đến đối soát quy chế EAUT."
    )

    bx0, by0, bx1, by1 = 60, 276, W - 60, 1020
    draw.text((68, 280), "[ 01 ] QUY TRÌNH TIỀN XỬ LÝ & ĐỐI SOÁT QUY CHẾ HỌC VỤ", font=get_font(18, True), fill="#1e293b")
    draw.rounded_rectangle([W - 240, 274, W - 60, 304], radius=6, outline="#0284c7", width=1)
    draw.text((W - 228, 282), "OFFLINE // RAG SECURE", font=get_font(12, True), fill="#0284c7")

    draw.rounded_rectangle([bx0, 316, bx1, by1], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, bx0, 316, bx1, by1)

    # 5 Stages Timing
    active_idx = 0
    if t >= 14.0: active_idx = 4
    elif t >= 10.5: active_idx = 3
    elif t >= 6.5: active_idx = 2
    elif t >= 3.0: active_idx = 1

    stages = [
        ("01", "Cổng Tiếp Nhận\nSinh Viên 24/7", "Chuẩn hóa bảng mã Unicode NFC\nsửa lỗi gõ tiếng Việt tự động.", "#2563eb"),
        ("02", "Bảo Vệ Riêng Tư\n(PII Masking)", "Che giấu CCCD, số điện thoại\nemail bằng token an toàn.", "#7c3aed"),
        ("03", "Phân Luồng AI\n& Phòng Ban", "Độ chính xác >94.2%\nđịnh tuyến 10 nhóm thủ tục.", "#0284c7"),
        ("04", "Tra Cứu Quy Chế\nRAG & SLA", "Trích dẫn PROC_TC_01\nđối soát ngân hàng 24-48h.", "#059669"),
        ("05", "Bàn Duyệt Cán Bộ\n(Human-in-the-Loop)", "Cán bộ chuyên môn kiểm tra\nký duyệt email gửi sinh viên.", "#d97706")
    ]

    card_w = 320
    gap = 40
    start_x = bx0 + 35

    for idx, (num, name, desc, col) in enumerate(stages):
        cx = start_x + idx * (card_w + gap)
        cy = 380
        ch = 440
        is_active = (idx == active_idx)

        # Connecting arrow
        if idx < len(stages) - 1:
            arr_x0 = cx + card_w
            arr_x1 = arr_x0 + gap
            arr_y = cy + 220
            line_col = col if (idx <= active_idx) else "#cbd5e1"
            draw.line([(arr_x0, arr_y), (arr_x1, arr_y)], fill=line_col, width=4)
            # Animated pulse traveling across
            pulse_x = arr_x0 + int((math.sin(t * 8.0) * 0.5 + 0.5) * gap)
            draw.ellipse([pulse_x - 4, arr_y - 4, pulse_x + 4, arr_y + 4], fill=col if idx <= active_idx else "#94a3b8")

        card_fill = "#f0fdf4" if (is_active and col == "#059669") else ("#eff6ff" if is_active else "#f8fafc")
        card_border = col if is_active else "#e2e8f0"
        card_width = 3 if is_active else 1

        draw.rounded_rectangle([cx, cy, cx + card_w, cy + ch], radius=16, fill=card_fill, outline=card_border, width=card_width)

        # Number Badge
        draw.rounded_rectangle([cx + 20, cy + 24, cx + 70, cy + 74], radius=10, fill=col if is_active else "#e2e8f0")
        draw.text((cx + 30, cy + 34), num, font=get_font(20, True), fill="#ffffff" if is_active else "#64748b")

        if is_active:
            draw.rounded_rectangle([cx + card_w - 130, cy + 24, cx + card_w - 20, cy + 54], radius=6, fill=col)
            draw.text((cx + card_w - 120, cy + 30), "CURRENT", font=get_font(11, True), fill="#ffffff")

        # Stage Name & Description
        draw.text((cx + 20, cy + 96), name, font=get_font(20, True), fill="#0f172a" if is_active else "#334155")
        draw.text((cx + 20, cy + 180), desc, font=get_font(15, False), fill="#475569")

        # Dynamic sub widget inside active card
        if num == "03":
            draw.text((cx + 20, cy + 270), "Độ tin cậy AI:", font=get_font(14, True), fill="#0284c7")
            p_fill = min(1.0, max(0.0, (t - 6.5) / 2.0)) if active_idx >= 2 else 0.0
            cur_acc = p_fill * 94.2
            draw.rounded_rectangle([cx + 20, cy + 300, cx + card_w - 20, cy + 322], radius=8, fill="#e2e8f0")
            draw.rounded_rectangle([cx + 20, cy + 300, cx + 20 + int((card_w - 40) * (cur_acc / 100.0)), cy + 322], radius=8, fill="#0284c7")
            draw.text((cx + 20, cy + 332), f"Chính xác: {cur_acc:.1f}%", font=get_font(14, True), fill="#0284c7")
        elif num == "04":
            draw.rounded_rectangle([cx + 20, cy + 270, cx + 180, cy + 304], radius=6, fill="#dcfce7", outline="#86efac", width=1)
            draw.text((cx + 30, cy + 276), "PROC_TC_01", font=get_font(14, True), fill="#15803d")
            draw.text((cx + 20, cy + 320), "SLA: 24 - 48h làm việc", font=get_font(14, True), fill="#059669")
        elif num == "01":
            draw.text((cx + 20, cy + 270), "NFC Normalized: [OK]", font=get_font(14, True), fill="#2563eb")
        elif num == "02":
            draw.text((cx + 20, cy + 270), "Mask PII: [SECURED]", font=get_font(14, True), fill="#7c3aed")
        elif num == "05":
            draw.text((cx + 20, cy + 270), "Ký duyệt email: [READY]", font=get_font(14, True), fill="#d97706")

    # Bottom Banner inside Part 2
    draw.rounded_rectangle([bx0 + 24, 880, bx1 - 24, 980], radius=12, fill="#f8fafc", outline="#e2e8f0", width=1)
    draw.text((bx0 + 50, 915), "⚡ NGUYÊN TẮC VẬN HÀNH:", font=get_font(18, True), fill="#1e3a8a")
    draw.text((bx0 + 330, 917), "100% dữ liệu học vụ được xử lý nội bộ an toàn, bảo đảm quyền riêng tư và quy chế đào tạo EAUT.", font=get_font(16, False), fill="#334155")

    return im

# ==================== PHẦN 4: TỔNG KẾT & HIỆU NĂNG ====================
def render_frame_part4(t, dur):
    cur_sec = 55.50 + t
    im = Image.new("RGB", (W, H), "#f8fafc")
    draw = ImageDraw.Draw(im)

    draw_hud_base_16_9(
        draw, cur_sec,
        "SYSTEM BENCHMARK & PRODUCTION READY", "PRODUCTION // VERIFIED",
        "TỔNG KẾT", "& HIỆU NĂNG ĐỘT PHÁ",
        "Hệ thống EduSupportAI đã được kiểm chứng thực tế và sẵn sàng triển khai toàn diện tại EAUT."
    )

    bx0, by0, bx1, by1 = 60, 276, W - 60, 1020
    draw.text((68, 280), "[ 01 ] KẾT QUẢ THỰC CHỨNG & CHỈ SỐ VẬN HÀNH", font=get_font(18, True), fill="#1e293b")
    draw.rounded_rectangle([W - 200, 274, W - 60, 304], radius=6, outline="#059669", width=1)
    draw.text((W - 188, 282), "BENCHMARK 100%", font=get_font(12, True), fill="#059669")

    draw.rounded_rectangle([bx0, 316, bx1, by1], radius=16, fill="#ffffff", outline="#cbd5e1", width=1)
    draw_corner_brackets(draw, bx0, 316, bx1, by1)

    cnt_prog = min(1.0, max(0.0, t / 2.5))

    # 3 Large Metric Cards horizontally
    card_w = 560
    gap = 40
    start_x = bx0 + 40
    m_y = 360
    m_h = 360

    # Metric 1: 43 / 43 Tests
    n_tests = int(cnt_prog * 43)
    draw.rounded_rectangle([start_x, m_y, start_x + card_w, m_y + m_h], radius=16, fill="#f0fdf4", outline="#86efac", width=2)
    draw.text((start_x + 40, m_y + 40), f"{n_tests} / 43", font=get_font(64, True), fill="#15803d")
    draw.text((start_x + 40, m_y + 140), "KỊCH BẢN KIỂM THỬ THÀNH CÔNG", font=get_font(22, True), fill="#0f172a")
    draw.text((start_x + 40, m_y + 185), "• 100% Test cases tự động vượt qua.\n• Bảo đảm tính toàn vẹn cơ sở dữ liệu.\n• Kiểm soát lỗi định danh và quy chế chuẩn.", font=get_font(16, False), fill="#334155")
    draw.rounded_rectangle([start_x + 40, m_y + 280, start_x + 240, m_y + 325], radius=8, fill="#dcfce7")
    draw.text((start_x + 55, m_y + 292), "100% TEST PASS", font=get_font(14, True), fill="#15803d")

    # Metric 2: <10ms
    ms_val = max(10, int(160 - cnt_prog * 150))
    c2_x = start_x + card_w + gap
    draw.rounded_rectangle([c2_x, m_y, c2_x + card_w, m_y + m_h], radius=16, fill="#eff6ff", outline="#93c5fd", width=2)
    draw.text((c2_x + 40, m_y + 40), f"<{ms_val}ms", font=get_font(64, True), fill="#1d4ed8")
    draw.text((c2_x + 40, m_y + 140), "TỐC ĐỘ PHẢN HỒI SUY LUẬN", font=get_font(22, True), fill="#0f172a")
    draw.text((c2_x + 40, m_y + 185), "• Phân loại chuyên môn dưới 10 mili-giây.\n• Rút ngắn thời gian xử lý từ vài ngày.\n• Tự động soạn thảo email phản hồi tức thì.", font=get_font(16, False), fill="#334155")
    draw.rounded_rectangle([c2_x + 40, m_y + 280, c2_x + 260, m_y + 325], radius=8, fill="#dbeafe")
    draw.text((c2_x + 55, m_y + 292), "REAL-TIME LATENCY", font=get_font(14, True), fill="#1d4ed8")

    # Metric 3: 100% Offline
    off_val = int(cnt_prog * 100)
    c3_x = c2_x + card_w + gap
    draw.rounded_rectangle([c3_x, m_y, c3_x + card_w, m_y + m_h], radius=16, fill="#faf5ff", outline="#d8b4fe", width=2)
    draw.text((c3_x + 40, m_y + 40), f"{off_val}%", font=get_font(64, True), fill="#7e22ce")
    draw.text((c3_x + 40, m_y + 140), "BẢO MẬT DỮ LIỆU TẠI CHỖ", font=get_font(22, True), fill="#0f172a")
    draw.text((c3_x + 40, m_y + 185), "• Vận hành độc lập không phụ thuộc Internet.\n• Toàn bộ hồ sơ sinh viên lưu trữ nội bộ.\n• Tuân thủ nghiêm ngặt chuẩn an toàn thông tin.", font=get_font(16, False), fill="#334155")
    draw.rounded_rectangle([c3_x + 40, m_y + 280, c3_x + 240, m_y + 325], radius=8, fill="#f3e8ff")
    draw.text((c3_x + 55, m_y + 292), "AIR-GAPPED READY", font=get_font(14, True), fill="#7e22ce")

    # Final Slogan Banner
    draw.rounded_rectangle([start_x, 780, bx1 - 40, 960], radius=16, fill="#1d4ed8")
    draw.text((start_x + 60, 830), "EDUSUPPORT AI — CHUẨN HÓA DỮ LIỆU, NÂNG TẦM HỌC VỤ ĐẠI HỌC ĐÔNG Á", font=get_font(28, True), fill="#ffffff")
    draw.text((start_x + 60, 890), "Hệ thống đã sẵn sàng triển khai chính thức cho toàn thể sinh viên và cán bộ giảng viên.", font=get_font(18, False), fill="#bfdbfe")

    return im

def render_part_clip(part_id, render_func):
    audio_path = AUDIO_DIR / f"{part_id}.mp3"
    clip_path = CLIPS_DIR / f"{part_id}.mp4"

    dur_str = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]).decode().strip()
    dur = float(dur_str)

    # Check if already rendered
    if clip_path.exists() and clip_path.stat().st_size > 100000:
        print(f"\n-> [CACHE HIT] {clip_path.name} already exists ({dur:.2f}s). Skipping render.")
        return clip_path, dur

    total_frames = int(dur * FPS)
    print(f"\n-> Rendering 16:9 Full HD [{part_id}]: duration={dur:.2f}s ({total_frames} frames)...")

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
        proc.stdin.write(frame_im.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"   + Hoàn tất: {clip_path.name}")
    return clip_path, dur

def process_part3_demo():
    print("\n-> Chuẩn bị Part 3 (Live Screen Recording Demo)...")
    raw_video = OUTPUT_DIR / "web_test_live_demo.mp4"
    audio_path = AUDIO_DIR / "part3_demo.mp3"
    out_clip = CLIPS_DIR / "part3_demo.mp4"

    # Get durations
    v_dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(raw_video)]).decode().strip())
    a_dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]).decode().strip())
    
    speed_factor = v_dur / a_dur
    print(f"   + Raw Video: {v_dur:.2f}s | Target Audio: {a_dur:.2f}s | Speed factor: {speed_factor:.3f}x")

    # Use exact coordinates: y=1000 and y=1013
    vf_filter = (
        f"setpts=PTS/{speed_factor:.4f},"
        "scale=1920:1080,"
        "fps=30,"
        "drawbox=x=40:y=1000:w=680:h=46:color=black@0.75:t=fill,"
        "drawbox=x=40:y=1000:w=680:h=46:color=red@0.9:t=2,"
        "drawtext=fontfile=/usr/share/fonts/noto/NotoSans-Bold.ttf:text='🔴 LIVE DEMO // TRẢI NGHIỆM THỰC TẾ TRÊN HỆ THỐNG EAUT':fontcolor=white:fontsize=18:x=56:y=1013"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-i", str(audio_path),
        "-r", "30",
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_clip)
    ]
    subprocess.run(cmd, check=True)
    print(f"   + Hoàn tất Part 3 Demo: {out_clip.name} ({a_dur:.2f}s)")
    return out_clip, a_dur

def assemble_master_video(parts_info):
    print("\n-> Ghép nối toàn bộ 4 phần thành Master Video kết hợp với hiệu ứng xfade và nhạc nền...")
    xfade_dur = 0.5
    
    cmd = ["ffmpeg", "-y"]
    for c_path, _ in parts_info:
        cmd.extend(["-i", str(c_path)])
    
    bgm_path = Path("/tmp/bgm_tech.wav")
    has_bgm = bgm_path.exists()
    if has_bgm:
        cmd.extend(["-i", str(bgm_path)])

    filter_lines = []
    
    # Video crossfades
    cur_offset = parts_info[0][1] - xfade_dur
    prev_v = "0:v"
    for i in range(1, len(parts_info)):
        out_v = f"v{i}"
        filter_lines.append(f"[{prev_v}][{i}:v]xfade=transition=fade:duration={xfade_dur}:offset={cur_offset:.2f}[{out_v}]")
        prev_v = out_v
        if i < len(parts_info) - 1:
            cur_offset += parts_info[i][1] - xfade_dur

    # Audio crossfades
    prev_a = "0:a"
    for i in range(1, len(parts_info)):
        out_a = f"a{i}"
        filter_lines.append(f"[{prev_a}][{i}:a]acrossfade=d={xfade_dur}[{out_a}]")
        prev_a = out_a

    # BGM mixing
    final_a = prev_a
    if has_bgm:
        filter_lines.append(f"[4:a]volume=0.08[bgm]")
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
        str(MASTER_VIDEO)
    ])

    print("-> Đang thực thi lệnh kết xuất FFmpeg Master Video...")
    subprocess.run(cmd, check=True)
    print(f"\n🎉 HOÀN TẤT MASTER VIDEO TỔNG HỢP (FULL HD 1080p): {MASTER_VIDEO}")

def main():
    print("=== BẮT ĐẦU DỰNG MASTER VIDEO TỔNG HỢP (GIỚI THIỆU + GIẢI THÍCH + LIVE DEMO) ===")
    parts_info = []

    # Part 1: Intro
    c1, d1 = render_part_clip("part1_intro", render_frame_part1)
    parts_info.append((c1, d1))

    # Part 2: Explain
    c2, d2 = render_part_clip("part2_explain", render_frame_part2)
    parts_info.append((c2, d2))

    # Part 3: Live Demo
    c3, d3 = process_part3_demo()
    parts_info.append((c3, d3))

    # Part 4: Summary
    c4, d4 = render_part_clip("part4_summary", render_frame_part4)
    parts_info.append((c4, d4))

    # Assemble
    assemble_master_video(parts_info)

if __name__ == "__main__":
    main()
