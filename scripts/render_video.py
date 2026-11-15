# -*- coding: utf-8 -*-
"""
Script: scripts/render_video.py
Tạo các khung hình slide 1080p và dựng video hoàn chỉnh (Full HD 1080p, 30fps) bằng FFmpeg.
"""

import os
import subprocess
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
AUDIO_DIR = OUTPUT_DIR / "audio"
FRAMES_DIR = OUTPUT_DIR / "frames"
CLIPS_DIR = OUTPUT_DIR / "clips"

FONT_PATH = "/usr/share/fonts/TTF/DejaVuSans.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"

def get_font(size, bold=False):
    path = FONT_BOLD_PATH if bold else FONT_PATH
    return ImageFont.truetype(path, size)

def create_base_canvas(title="EDUSUPPORT-AI", category="HỆ THỐNG TRỢ LÝ HỌC VỤ THÔNG MINH"):
    """Tạo nền slide 1920x1080 phong cách Sapphire Academic & Slate cao cấp."""
    img = Image.new("RGB", (1920, 1080), color="#090d16")
    draw = ImageDraw.Draw(img)

    # Gradient nền
    for y in range(1080):
        ratio = y / 1080.0
        r = int(9 + ratio * (15 - 9))
        g = int(13 + ratio * (23 - 13))
        b = int(22 + ratio * (42 - 22))
        draw.line([(0, y), (1920, y)], fill=(r, g, b))

    # Thanh header trên cùng
    draw.rectangle([(0, 0), (1920, 80)], fill="#0f172a")
    draw.line([(0, 80), (1920, 80)], fill="#2563eb", width=3)

    # Header text
    f_brand = get_font(20, bold=True)
    f_sub = get_font(16, bold=False)
    draw.text((60, 26), "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ ĐÔNG Á (EAUT)", font=f_brand, fill="#93c5fd")
    draw.text((1400, 28), "CENTRIC DATA AI - NHÓM 67", font=f_sub, fill="#94a3b8")

    # Thanh footer dưới cùng
    draw.rectangle([(0, 1020), (1920, 1080)], fill="#0a0f1d")
    draw.line([(0, 1020), (1920, 1020)], fill="#1e293b", width=2)
    f_foot = get_font(15, bold=False)
    draw.text((60, 1040), "EduSupportAI :: Data-Centric AI & Human-in-the-Loop Academic Support System", font=f_foot, fill="#64748b")
    draw.text((1600, 1040), "Báo cáo Sản phẩm 2024", font=f_foot, fill="#475569")

    return img, draw

def render_scene1_frame():
    """Slide 1: Mở đầu & Giới thiệu tổng quan."""
    img, draw = create_base_canvas()

    # Badge chủ đề
    draw.rounded_rectangle([(60, 130), (450, 175)], radius=8, fill="#1e3a8a", outline="#3b82f6", width=1)
    f_badge = get_font(16, bold=True)
    draw.text((80, 142), "[GIẢI PHÁP HỌC VỤ THẾ HỆ MỚI]", font=f_badge, fill="#bfdbfe")

    # Tiêu đề chính
    f_h1 = get_font(52, bold=True)
    draw.text((60, 200), "EduSupportAI", font=f_h1, fill="#ffffff")

    f_h2 = get_font(26, bold=True)
    draw.text((60, 280), "Hệ thống Tiếp nhận, Phân loại & Xử lý Phản ánh Học vụ Sinh viên", font=f_h2, fill="#60a5fa")

    f_p = get_font(18, bold=False)
    draw.text((60, 335), "Ứng dụng tiếp cận Data-Centric AI (DCAI) kết hợp Bàn làm việc Kiểm duyệt Human-in-the-Loop", font=f_p, fill="#94a3b8")

    # 3 Thẻ bài toán & giá trị
    cards = [
        ("THỰC TRẠNG QUÁ TẢI", "Hàng nghìn thắc mắc mỗi kỳ thi cử, học phí gửi phân tán qua nhiều kênh không đồng nhất, cán bộ xử lý thủ công gây chậm trễ.", "#ef4444", "#7f1d1d"),
        ("ĐỘ CHÍNH XÁC CAO (94%+)", "Máy học cục bộ TF-IDF kép + Logistic Regression phân luồng chuẩn xác 7 nhóm chuyên môn học vụ EAUT.", "#10b981", "#064e3b"),
        ("TỐC ĐỘ XỬ LÝ SIÊU TỐC", "Rút ngắn thời gian từ 3 - 5 ngày làm việc xuống dưới 10 mili-giây, gửi email giải đáp tự động tới sinh viên.", "#3b82f6", "#1e3a8a"),
    ]

    for i, (ctitle, cdesc, cborder, cbg) in enumerate(cards):
        x = 60 + i * 590
        y = 420
        w = 560
        h = 240
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=12, fill="#111827", outline=cborder, width=2)
        draw.rounded_rectangle([(x + 20, y + 20), (x + 360, y + 60)], radius=6, fill=cbg)
        draw.text((x + 32, y + 28), ctitle, font=get_font(16, bold=True), fill="#ffffff")

        # Chia dòng mô tả
        words = cdesc.split()
        lines = []
        cur = []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 42:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))

        for li, line in enumerate(lines[:5]):
            draw.text((x + 24, y + 80 + li * 28), line, font=get_font(16, bold=False), fill="#cbd5e1")

    # Thẻ cam kết kỹ thuật
    draw.rounded_rectangle([(60, 710), (1800, 960)], radius=12, fill="#0f172a", outline="#334155", width=1)
    draw.text((90, 735), "ĐẶC TRƯNG CÔNG NGHỆ NỔI BẬT", font=get_font(20, bold=True), fill="#38bdf8")
    
    pillars = [
        "1. Data-Centric AI Pipeline: Làm sạch Unicode NFC, lọc PII tự động, không để rò rỉ dữ liệu.",
        "2. Tra cứu RAG Quy chế EAUT: Trích xuất điều khoản và quy trình chuẩn (PROC_...) từ 3 tệp DOCX chính thức.",
        "3. Độc lập 100% Offline: Máy học nhẹ, không phụ thuộc OpenAI/API đám mây, an toàn thông tin tuyệt đối.",
        "4. Phê duyệt & Gửi Email Thực tế: Tích hợp SMTP Gmail TLS 587, giao diện Sapphire Academic chuẩn đại học."
    ]
    for pi, pill in enumerate(pillars):
        draw.text((90, 785 + pi * 40), pill, font=get_font(18, bold=False), fill="#e2e8f0")

    path = FRAMES_DIR / "frame_scene1.png"
    img.save(path)
    return path

def render_scene2_frame():
    """Slide 2: Cổng tiếp nhận Sinh viên & Lọc PII."""
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 120), (450, 165)], radius=8, fill="#065f46", outline="#10b981", width=1)
    draw.text((80, 132), "[GIAO DIỆN NGƯỜI DÙNG SINH VIÊN]", font=get_font(16, bold=True), fill="#a7f3d0")

    draw.text((60, 185), "Cổng Tiếp nhận Phản ánh Dành riêng cho Sinh viên", font=get_font(44, bold=True), fill="#ffffff")
    draw.text((60, 245), "Tối giản, thân thiện, bảo mật thông tin cá nhân và tra cứu tiến độ thời gian thực", font=get_font(20, bold=False), fill="#94a3b8")

    # Cột trái: Các ưu điểm & tính năng
    left_x = 60
    cards = [
        ("1. BẢO MẬT & LỌC PII TỰ ĐỘNG", "Nhận diện và che giấu tự động số điện thoại, số CCCD, tài khoản ngân hàng để bảo đảm quyền riêng tư theo chuẩn bảo vệ dữ liệu."),
        ("2. TIẾP NHẬN ĐA ĐỊNH DẠNG", "Hỗ trợ gõ trực tiếp hoặc tải tệp tài liệu đính kèm (PDF, DOCX, TXT) tự động trích xuất nội dung văn bản."),
        ("3. CẤP MÃ HỒ SƠ & CAM KẾT SLA", "Hệ thống cấp ngay mã định danh REQ_... và hiển thị thời hạn giải quyết cam kết (24h - 48h làm việc)."),
        ("4. TRA CỨU TIẾN ĐỘ 1 CHẠM", "Sinh viên chủ động tra cứu trạng thái tiếp nhận, cán bộ thụ lý và kết quả giải đáp bằng Mã hồ sơ hoặc MSSV.")
    ]

    for ci, (title, desc) in enumerate(cards):
        y = 310 + ci * 155
        draw.rounded_rectangle([(left_x, y), (left_x + 760, y + 135)], radius=10, fill="#111827", outline="#1e3a8a", width=1)
        draw.text((left_x + 20, y + 18), title, font=get_font(18, bold=True), fill="#60a5fa")
        
        words = desc.split()
        lines = []
        cur = []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 55:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:3]):
            draw.text((left_x + 20, y + 54 + li * 24), line, font=get_font(15, bold=False), fill="#cbd5e1")

    # Cột phải: Chèn Screenshot Cổng Sinh viên
    ss_path = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_1794726921880.png")
    if ss_path.exists():
        ss = Image.open(ss_path).convert("RGB")
        # Resize tỷ lệ phù hợp với khung
        ss_resized = ss.resize((960, 620), Image.Resampling.LANCZOS)
        # Khung viền sang trọng
        draw.rounded_rectangle([(870, 310), (1850, 950)], radius=12, fill="#0f172a", outline="#3b82f6", width=2)
        img.paste(ss_resized, (880, 320))
        draw.text((880, 960), "Hình ảnh thực tế: Cổng Tiếp nhận Sinh viên (app/student_portal.py)", font=get_font(15, bold=False), fill="#94a3b8")

    path = FRAMES_DIR / "frame_scene2.png"
    img.save(path)
    return path

def render_scene3_frame():
    """Slide 3: Máy học Cục bộ & Tra cứu Quy chế RAG."""
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 120), (450, 165)], radius=8, fill="#581c87", outline="#a855f7", width=1)
    draw.text((80, 132), "[CÔNG NGHỆ LÕI & TRÍ TUỆ NHÂN TẠO]", font=get_font(16, bold=True), fill="#e9d5ff")

    draw.text((60, 185), "Máy học Cục bộ & RAG Quy chế Đào tạo EAUT", font=get_font(44, bold=True), fill="#ffffff")
    draw.text((60, 245), "Suy luận Chain-of-Thought 5 bước minh bạch và trích xuất căn cứ pháp lý từ 3 file DOCX", font=get_font(20, bold=False), fill="#94a3b8")

    # Cột trái: Ảnh chụp Luồng suy luận CoT
    ss_path = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_1794732462989.png")
    if ss_path.exists():
        ss = Image.open(ss_path).convert("RGB")
        ss_resized = ss.resize((960, 620), Image.Resampling.LANCZOS)
        draw.rounded_rectangle([(60, 310), (1040, 950)], radius=12, fill="#0f172a", outline="#8b5cf6", width=2)
        img.paste(ss_resized, (70, 320))
        draw.text((70, 960), "Hình ảnh: Nhật ký thực thi suy luận Chain-of-Thought 5 bước (Trace Logger)", font=get_font(15, bold=False), fill="#94a3b8")

    # Cột phải: Khối kỹ thuật
    right_x = 1070
    tech_cards = [
        ("BƯỚC 1: DATA-CENTRIC HYGIENE", "Làm sạch ký tự Unicode NFC, kiểm soát độ dài và rà quét cờ chất lượng đầu vào."),
        ("BƯỚC 2: TF-IDF KÉP + LOGISTIC REGRESSION", "Phân loại 7 nhóm chuyên môn (Học phí, Điểm thi, Lịch học, CSVC, CNTT, Hành chính, Khác) với độ tự tin trên 94%."),
        ("BƯỚC 3: RAG NỘI BỘ TỪ DATA-DOC", "Tự động liên kết đúng quy trình chuẩn (ví dụ PROC_TC_01), trích xuất điều khoản và cam kết SLA."),
        ("BƯỚC 4: CHAIN-OF-THOUGHT SYNTHESIS", "Tổng hợp văn bản hướng dẫn giải quyết có căn cứ, ngôn từ trang trọng, chuẩn mực đại học."),
        ("BƯỚC 5: GUARDRAILS & ROUTING", "Kiểm định ngưỡng an toàn: Tự động phê duyệt khi tin cậy cao hoặc chuyển bàn duyệt cán bộ.")
    ]

    for ti, (title, desc) in enumerate(tech_cards):
        y = 310 + ti * 125
        draw.rounded_rectangle([(right_x, y), (right_x + 780, y + 110)], radius=8, fill="#111827", outline="#334155", width=1)
        draw.text((right_x + 18, y + 14), title, font=get_font(16, bold=True), fill="#c084fc")
        
        words = desc.split()
        lines = []
        cur = []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 56:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:2]):
            draw.text((right_x + 18, y + 46 + li * 22), line, font=get_font(14, bold=False), fill="#cbd5e1")

    path = FRAMES_DIR / "frame_scene3.png"
    img.save(path)
    return path

def render_scene4_frame():
    """Slide 4: Bàn làm việc Cán bộ & Gửi Email Thực tế SMTP."""
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 120), (450, 165)], radius=8, fill="#1e3a8a", outline="#3b82f6", width=1)
    draw.text((80, 132), "[BÀN LÀM VIỆC & DISPATCH THỰC TẾ]", font=get_font(16, bold=True), fill="#93c5fd")

    draw.text((60, 185), "Phê duyệt Human-in-the-Loop & Gửi Email SMTP", font=get_font(44, bold=True), fill="#ffffff")
    draw.text((60, 245), "Kết nối máy chủ Gmail SMTP gửi thư kết quả giải quyết trực tiếp đến tài khoản sinh viên", font=get_font(20, bold=False), fill="#94a3b8")

    # Cột trái: Khối tính năng cán bộ
    left_x = 60
    cards = [
        ("1. BÀN DUYỆT HUMAN-IN-THE-LOOP", "Cán bộ xem nhanh tóm tắt hồ sơ, đối soát dữ liệu thư viện/công nợ thời gian thực và chỉnh sửa bản nháp linh hoạt trước khi duyệt."),
        ("2. GIAO DỊCH NGUYÊN TỬ (ATOMIC LOCK)", "Kiểm tra trạng thái thời gian thực chống thao tác duyệt trùng lặp hoặc xung đột bản ghi giữa nhiều cán bộ."),
        ("3. EMAIL GIAO DIỆN SAPPHIRE ACADEMIC", "Thư gửi đi định dạng song song (HTML responsive + Plain text), bố cục chuẩn nhận diện trường ĐH Công nghệ Đông Á."),
        ("4. GỬI THỰC TẾ QUA GMAIL SMTP", "Tích hợp giao thức TLS bảo mật (smtp.gmail.com:587), lưu vết kiểm toán toàn diện trong bảng email_dispatches.")
    ]

    for ci, (title, desc) in enumerate(cards):
        y = 310 + ci * 155
        draw.rounded_rectangle([(left_x, y), (left_x + 760, y + 135)], radius=10, fill="#111827", outline="#1e3a8a", width=1)
        draw.text((left_x + 20, y + 18), title, font=get_font(18, bold=True), fill="#38bdf8")
        
        words = desc.split()
        lines = []
        cur = []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 55:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:3]):
            draw.text((left_x + 20, y + 54 + li * 24), line, font=get_font(15, bold=False), fill="#cbd5e1")

    # Cột phải: Screenshot Bàn duyệt & Email
    ss_path = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded/uploaded_media_1794733800765.png")
    if ss_path.exists():
        ss = Image.open(ss_path).convert("RGB")
        ss_resized = ss.resize((960, 620), Image.Resampling.LANCZOS)
        draw.rounded_rectangle([(870, 310), (1850, 950)], radius=12, fill="#0f172a", outline="#0284c7", width=2)
        img.paste(ss_resized, (880, 320))
        draw.text((880, 960), "Hình ảnh thực tế: Bàn làm việc Cán bộ duyệt phản ánh & kích hoạt gửi Email", font=get_font(15, bold=False), fill="#94a3b8")

    path = FRAMES_DIR / "frame_scene4.png"
    img.save(path)
    return path

def render_scene5_frame():
    """Slide 5: Tổng kết & Sẵn sàng Triển khai."""
    img, draw = create_base_canvas()

    draw.rounded_rectangle([(60, 120), (450, 165)], radius=8, fill="#065f46", outline="#10b981", width=1)
    draw.text((80, 132), "[TỔNG KẾT & HIỆU QUẢ THỰC TIỄN]", font=get_font(16, bold=True), fill="#a7f3d0")

    draw.text((60, 185), "EduSupportAI — Sẵn Sàng Triển Khai Thực Tế", font=get_font(44, bold=True), fill="#ffffff")
    draw.text((60, 245), "Giải pháp toàn diện thúc đẩy chuyển đổi số quản lý học vụ tại Trường Đại học Công nghệ Đông Á", font=get_font(20, bold=False), fill="#94a3b8")

    # 4 Khối số liệu ấn tượng
    stats = [
        ("43 / 43", "BÀI KIỂM THỬ PASS (100%)", "Toàn bộ bài test Pipeline, CSDL, Machine Learning và Email Service đều vượt qua kiểm định tự động.", "#10b981", "#064e3b"),
        ("< 10 MS", "TỐC ĐỘ XỬ LÝ CHUỖI", "Thời gian suy luận máy học cục bộ cực nhanh, không phụ thuộc kết nối Internet ngoài.", "#3b82f6", "#1e3a8a"),
        ("100% OFFLINE", "AN TOÀN DỮ LIỆU TUYỆT ĐỐI", "Mô hình và cơ sở dữ liệu chạy hoàn toàn nội bộ, bảo mật thông tin sinh viên theo quy định.", "#8b5cf6", "#4c1d95"),
        ("DOCKER READY", "ĐỒNG BỘ DỮ LIỆU ĐA NỀN TẢNG", "Sẵn sàng khởi chạy qua Docker, đồng bộ tự động song song SQLite và MySQL thời gian thực.", "#f59e0b", "#78350f"),
    ]

    for i, (metric, title, desc, cborder, cbg) in enumerate(stats):
        x = 60 + i * 445
        y = 320
        w = 425
        h = 320
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=12, fill="#111827", outline=cborder, width=2)
        draw.text((x + 24, y + 24), metric, font=get_font(44, bold=True), fill=cborder)
        draw.text((x + 24, y + 84), title, font=get_font(16, bold=True), fill="#ffffff")
        
        words = desc.split()
        lines = []
        cur = []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 32:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        for li, line in enumerate(lines[:4]):
            draw.text((x + 24, y + 130 + li * 26), line, font=get_font(15, bold=False), fill="#cbd5e1")

    # Băng chuyền lời kết
    draw.rounded_rectangle([(60, 680), (1800, 950)], radius=12, fill="#0f172a", outline="#2563eb", width=2)
    draw.text((100, 720), "GIÁ TRỊ XÃ HỘI & Ý NGHĨA THỰC TIỄN", font=get_font(24, bold=True), fill="#60a5fa")
    
    conclusions = [
        "• Đối với Sinh viên: Phản ánh được giải đáp nhanh chóng, rõ ràng, minh bạch tiến độ và quy chế mọi lúc mọi nơi.",
        "• Đối với Cán bộ: Giảm hơn 80% áp lực thủ công, tập trung xử lý các trường hợp đặc thù cần thẩm định chuyên sâu.",
        "• Đối với Nhà trường: Nâng cao sự hài lòng của người học, tối ưu hóa quy trình hành chính Một cửa hướng tới Đại học số."
    ]
    for ci, ctext in enumerate(conclusions):
        draw.text((100, 775 + ci * 48), ctext, font=get_font(18, bold=False), fill="#e2e8f0")

    path = FRAMES_DIR / "frame_scene5.png"
    img.save(path)
    return path

def build_clips():
    """Dựng từng clip cho từng phân cảnh khớp với thời lượng file âm thanh."""
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    scenes = [
        ("scene1", render_scene1_frame()),
        ("scene2", render_scene2_frame()),
        ("scene3", render_scene3_frame()),
        ("scene4", render_scene4_frame()),
        ("scene5", render_scene5_frame()),
    ]

    for sc_id, frame_path in scenes:
        audio_path = AUDIO_DIR / f"{sc_id}.mp3"
        clip_path = CLIPS_DIR / f"{sc_id}.mp4"

        # Lấy thời lượng audio bằng ffprobe
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(audio_path)
        ]
        duration = float(subprocess.check_output(probe_cmd).decode().strip())
        print(f"-> Phân cảnh [{sc_id}]: Thời lượng {duration:.2f}s...")

        # Dựng video mp4 1080p, 30fps bằng ffmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(frame_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-t", str(duration + 0.5), # Dư 0.5s để âm thanh không bị ngắt cụt
            "-shortest",
            str(clip_path)
        ]
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   + Đã dựng thành công: {clip_path}")

def concat_final_video():
    """Ghép 5 phân cảnh thành video Full HD 1080p hoàn chỉnh."""
    concat_list = CLIPS_DIR / "concat_list.txt"
    lines = [f"file '{CLIPS_DIR / f'scene{i}.mp4'}'" for i in range(1, 6)]
    concat_list.write_text("\n".join(lines), encoding="utf-8")

    final_video = OUTPUT_DIR / "edusupport_ai_review_demo.mp4"
    print(f"-> Đang ghép nối toàn bộ 5 phân cảnh thành {final_video}...")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(final_video)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"🎉 HOÀN TẤT XUẤT VIDEO REVIEW SẢN PHẨM: {final_video}")
    return final_video

if __name__ == "__main__":
    print("=== BẮT ĐẦU QUY TRÌNH DỰNG VIDEO REVIEW SẢN PHẨM TỰ ĐỘNG ===")
    build_clips()
    concat_final_video()
