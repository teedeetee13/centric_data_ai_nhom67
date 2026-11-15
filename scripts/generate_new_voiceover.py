# -*- coding: utf-8 -*-
"""
Script: scripts/generate_new_voiceover.py
Tạo 6 tệp âm thanh thuyết minh cho 6 phân cảnh video demo EduSupportAI bằng gTTS (Google Vietnamese TTS).
"""

from pathlib import Path
from gtts import gTTS

ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT_DIR / "output" / "audio_new"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

SCENES = [
    {
        "id": "scene1",
        "title": "Mở đầu & Giới thiệu tổng quan EduSupportAI",
        "text": (
            "Kính chào quý thầy cô và các bạn. Đây là video báo cáo và giới thiệu hệ thống EduSupportAI – "
            "giải pháp chuyển đổi số thông minh trong công tác tiếp nhận, phân loại và giải quyết phản ánh học vụ sinh viên "
            "tại Trường Đại học Công nghệ Đông Á. Ứng dụng tiếp cận Data-Centric AI kết hợp Bàn duyệt Human-in-the-Loop, "
            "giúp rút ngắn thời gian xử lý từ vài ngày xuống dưới mười mili-giây với độ chính xác phân luồng trên 94 phần trăm."
        )
    },
    {
        "id": "scene2",
        "title": "Cổng tiếp nhận Học vụ Sinh viên trực tuyến",
        "text": (
            "Đầu tiên là Cổng tiếp nhận học vụ trực tuyến 24/7 dành riêng cho sinh viên. "
            "Giao diện trực quan cho phép người học gửi phản ánh thuận tiện kèm mã sinh viên, số điện thoại và tệp tài liệu minh chứng. "
            "Điểm nổi bật là cơ chế Data-Centric tự động làm sạch Unicode NFC và che giấu dữ liệu định danh PII, "
            "đồng thời hiển thị cam kết thời hạn giải quyết SLA minh bạch cho từng nhóm dịch vụ học vụ."
        )
    },
    {
        "id": "scene3",
        "title": "Kiến trúc DCAI 5 bước & Tra cứu Quy chế RAG",
        "text": (
            "Trái tim của EduSupportAI là chuỗi suy luận năm bước hoạt động hoàn toàn cục bộ và ngoại tuyến. "
            "Sau khi làm sạch dữ liệu, mô hình máy học TF-IDF kép kết hợp hồi quy Logistic phân loại chuẩn xác 7 nhóm chuyên môn. "
            "Tiếp đó, hệ thống thực hiện tra cứu RAG từ các tài liệu quy chế chính thức của EAUT, "
            "sinh chuỗi suy luận Chain-of-Thought chặt chẽ và áp dụng rào chắn kiểm định an toàn trước khi phân luồng xử lý."
        )
    },
    {
        "id": "scene4",
        "title": "Bàn duyệt Cán bộ & Quản lý Phân luồng Học vụ",
        "text": (
            "Trên màn hình là Bàn duyệt hồ sơ học vụ dành cho cán bộ quản lý. "
            "Hệ thống đã được nâng cấp tối ưu với hai bộ lọc rõ ràng: phản ánh cần đưa về đơn vị xem xét và phản ánh đã gửi. "
            "Đặc biệt, đối với các phản ánh đã xử lý, hệ thống đã loại bỏ mức độ ưu tiên và gắn nhãn xác nhận đã giải quyết kèm thời gian chính thức, "
            "đồng thời đối chiếu chuẩn xác căn cứ quy chế đào tạo EAUT theo từng thủ tục nghiệp vụ."
        )
    },
    {
        "id": "scene5",
        "title": "Nội dung Email Giải quyết gửi tới Sinh viên",
        "text": (
            "Đây là văn bản email giải quyết chính thức được sinh tự động theo quy chuẩn Sapphire Academic của Đại học Công nghệ Đông Á. "
            "Email hiển thị đầy đủ, trang trọng từ bảng tóm tắt hồ sơ tiếp nhận, nội dung hướng dẫn nghiệp vụ rõ ràng từ Phòng Tài chính Kế toán, "
            "đến thông tin hotline và kênh hỗ trợ Một cửa trực tiếp, giúp sinh viên nắm bắt kết quả giải quyết một cách nhanh chóng và an tâm nhất."
        )
    },
    {
        "id": "scene6",
        "title": "Tổng kết & Giá trị Thực tiễn",
        "text": (
            "Tổng kết lại, EduSupportAI đã vượt qua 100 phần trăm các bài kiểm thử tự động, vận hành ổn định trên nền tảng Docker và sẵn sàng triển khai thực tế. "
            "Hệ thống giúp giảm trên 80 phần trăm áp lực xử lý thủ công cho cán bộ, đồng thời mang đến trải nghiệm học vụ hiện đại, minh bạch và tin cậy "
            "cho toàn thể sinh viên Trường Đại học Công nghệ Đông Á. Xin chân thành cảm ơn!"
        )
    }
]

def generate_all_audio():
    print(f"=== BẮT ĐẦU TẠO GIỌNG ĐỌC THUYẾT MINH THẾ HỆ MỚI ({len(SCENES)} CẢNH) ===")
    for sc in SCENES:
        out_path = AUDIO_DIR / f"{sc['id']}.mp3"
        print(f"-> Đang tạo âm thanh cho {sc['id']}: {sc['title']}...")
        tts = gTTS(text=sc["text"], lang="vi", slow=False)
        tts.save(str(out_path))
        print(f"   + Đã lưu thành công: {out_path} ({out_path.stat().st_size} bytes)")
    print("🎉 Hoàn tất toàn bộ 6 file âm thanh thuyết minh!")

if __name__ == "__main__":
    generate_all_audio()
