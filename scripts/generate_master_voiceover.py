# -*- coding: utf-8 -*-
"""
Script: scripts/generate_master_voiceover.py
Tạo 4 đoạn thuyết minh tiếng Việt chuẩn, dứt khoát, trôi chảy:
- Bỏ qua kiểm thử (không nhắc đến test cases/kịch bản kiểm thử).
- Tập trung vào luồng: Tạo phản ánh ở trang phản ánh -> Chuyển qua tiếp nhận xem thông tin đã xử lý.
"""

from pathlib import Path
import subprocess
from gtts import gTTS

ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT_DIR / "output" / "audio_master"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

PARTS = [
    {
        "id": "part1_intro",
        "title": "Phần 1: Giới thiệu & Định vị giải pháp EduSupportAI",
        "text": (
            "EduSupportAI là hệ thống chuyển đổi số học vụ thông minh tại Đại học Công nghệ Đông Á. "
            "Ứng dụng triết lý Data-Centric AI kết hợp bàn duyệt Human-in-the-Loop, "
            "hệ thống tối ưu hóa toàn diện từ khâu tiếp nhận đến khâu giải quyết phản ánh sinh viên."
        ),
        "speed": 1.25
    },
    {
        "id": "part2_explain",
        "title": "Phần 2: Giải thích Kiến trúc DCAI 5 bước & Tra cứu RAG",
        "text": (
            "Quy trình xử lý khép kín gồm năm bước: "
            "Dữ liệu gửi lên được tự động chuẩn hóa bảng mã Unicode NFC và che giấu thông tin định danh cá nhân PII. "
            "Mô hình AI phân loại chính xác trên 94 phần trăm, "
            "tự động đối soát quy chế nhà trường và chuyển hồ sơ về đúng đơn vị thụ lý hoàn toàn offline."
        ),
        "speed": 1.25
    },
    {
        "id": "part3_demo",
        "title": "Phần 3: Demo Thực tế - Tạo phản ánh & Xem thông tin đã xử lý tại bàn tiếp nhận",
        "text": (
            "Trước hết, sinh viên gửi phản ánh học vụ trực tuyến tại cổng tiếp nhận. "
            "Dữ liệu ngay lập tức được AI tiếp nhận và xử lý tự động. "
            "Chuyển sang bàn duyệt của cán bộ, hồ sơ mới lập tức xuất hiện trong hàng đợi. "
            "Tại đây, cán bộ xem đầy đủ thông tin AI đã xử lý: từ phân loại chuyên môn, "
            "trích xuất căn cứ quy chế chính thức, kiểm soát thời hạn SLA đối soát ngân hàng "
            "đến văn bản email soạn sẵn, sẵn sàng phê duyệt gửi sinh viên."
        ),
        "speed": 1.22
    },
    {
        "id": "part4_summary",
        "title": "Phần 4: Tổng kết Giá trị Thực tiễn (Không kiểm thử)",
        "text": (
            "Với khả năng tiếp nhận tự động 24/7, tốc độ phản hồi tức thì dưới mười mili-giây "
            "và bảo mật dữ liệu tuyệt đối tại chỗ, "
            "EduSupportAI chuẩn hóa dữ liệu, nâng tầm chất lượng phục vụ học vụ tại Đại học Công nghệ Đông Á."
        ),
        "speed": 1.25
    }
]

def main():
    print("=== TẠO VOICE OVER MỚI (BỎ KIỂM THỬ - DEMO TẠO PHẢN ÁNH -> XỬ LÝ TIẾP NHẬN) ===")
    total_dur = 0.0

    for item in PARTS:
        p_id = item["id"]
        title = item["title"]
        text = item["text"]
        spd = item["speed"]
        print(f"\n-> Tạo audio cho {p_id}: {title}...")

        raw_p = AUDIO_DIR / f"{p_id}_raw.mp3"
        final_p = AUDIO_DIR / f"{p_id}.mp3"

        tts = gTTS(text=text, lang="vi", slow=False)
        tts.save(str(raw_p))

        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_p),
            "-filter:a", f"atempo={spd}",
            "-b:a", "192k",
            str(final_p)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        dur_out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(final_p)
        ]).decode().strip()
        dur = float(dur_out)
        total_dur += dur
        print(f"   + Hoàn tất: {final_p.name} ({dur:.2f}s)")

    print(f"\n🎉 TỔNG THỜI LƯỢNG AUDIO: {total_dur:.2f}s (~{int(total_dur)} giây)")

if __name__ == "__main__":
    main()
