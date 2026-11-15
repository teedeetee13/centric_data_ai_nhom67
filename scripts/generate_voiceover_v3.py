# -*- coding: utf-8 -*-
"""
Script: scripts/generate_voiceover_v3.py
Tạo 5 tệp âm thanh thuyết minh cho 5 phân cảnh video phong cách Tech HUD Reel 60s
Giọng đọc: Chuẩn tự nhiên, dứt khoát, trôi chảy, tốc độ nhanh chuẩn keynote/reel (atempo=1.28).
"""

from pathlib import Path
import subprocess
from gtts import gTTS

ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT_DIR / "output" / "audio_v3"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

SCENES = [
    {
        "id": "scene1",
        "title": "Tổng quan & Định vị giải pháp EduSupportAI",
        "text": (
            "EduSupportAI là hệ thống chuyển đổi số học vụ thông minh tại Đại học Công nghệ Đông Á. "
            "Ứng dụng triết lý Data-Centric AI kết hợp bàn duyệt Human-in-the-Loop, "
            "hệ thống tối ưu hóa toàn diện từ khâu tiếp nhận đến khâu giải quyết phản ánh sinh viên."
        )
    },
    {
        "id": "scene2",
        "title": "Cổng tiếp nhận Sinh viên trực tuyến 24/7",
        "text": (
            "Cổng sinh viên trực tuyến hoạt động liên tục 24/7. "
            "Dữ liệu gửi lên được tự động chuẩn hóa bảng mã Unicode NFC, "
            "che giấu thông tin định danh cá nhân PII và hiển thị cam kết thời hạn giải quyết SLA minh bạch cho từng nhóm dịch vụ."
        )
    },
    {
        "id": "scene3",
        "title": "Kiến trúc DCAI 5 bước & Tra cứu Quy chế RAG",
        "text": (
            "Quy trình xử lý khép kín gồm năm bước: "
            "Dữ liệu sạch được mô hình AI phân loại chính xác trên 94 phần trăm. "
            "Cơ chế RAG tự động truy xuất quy chế nhà trường, "
            "định tuyến hồ sơ đến đúng đơn vị thụ lý mà không cần gửi dữ liệu lên đám mây."
        )
    },
    {
        "id": "scene4",
        "title": "Bàn duyệt Cán bộ & Quản lý Phân luồng",
        "text": (
            "Bàn duyệt cán bộ được tinh gọn thành hai nhóm phản ánh: Cần đơn vị xem xét và Đã gửi. "
            "Hệ thống loại bỏ trường dữ liệu ưu tiên thừa ở hồ sơ đã duyệt, "
            "tự động đính kèm quy chế tài chính và thời hạn đối soát giao dịch ngân hàng."
        )
    },
    {
        "id": "scene5",
        "title": "Email Giải quyết & Hiệu năng Đột phá",
        "text": (
            "Email phản hồi được định dạng trang trọng theo chuẩn nhận diện EAUT, "
            "sẵn sàng gửi tới sinh viên sau khi cán bộ duyệt. "
            "Với bốn mươi ba kịch bản kiểm thử thành công và tốc độ dưới mười mili-giây, "
            "EduSupportAI nâng tầm chất lượng phục vụ học vụ toàn diện."
        )
    }
]

def main():
    print("=== BẮT ĐẦU TẠO VOICE OVER V3 (60s FAST & DECISIVE TECH PACING) ===")
    total_dur = 0.0

    for item in SCENES:
        scene_id = item["id"]
        title = item["title"]
        text = item["text"]
        print(f"\n-> Đang tạo voice cho {scene_id}: {title}...")

        raw_path = AUDIO_DIR / f"{scene_id}_raw.mp3"
        final_path = AUDIO_DIR / f"{scene_id}.mp3"

        tts = gTTS(text=text, lang="vi", slow=False)
        tts.save(str(raw_path))

        # Speed up with atempo=1.28 for crisp, fluent delivery
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_path),
            "-filter:a", "atempo=1.28",
            "-b:a", "192k",
            str(final_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Get duration
        dur_out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(final_path)
        ]).decode().strip()
        dur = float(dur_out)
        total_dur += dur
        print(f"   + Hoàn tất: {final_path.name} ({dur:.2f}s)")

    print(f"\n🎉 TỔNG THỜI LƯỢNG VOICE OVER: {total_dur:.2f}s (~{int(total_dur)} giây - Chuẩn 60s Tech Reel!)")

if __name__ == "__main__":
    main()
