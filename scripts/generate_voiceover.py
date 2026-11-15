# -*- coding: utf-8 -*-
"""
Script: scripts/generate_voiceover.py
Tạo 5 tệp âm thanh thuyết minh cho 5 phân cảnh của video demo EduSupportAI bằng gTTS (Google Vietnamese TTS).
"""

import os
from pathlib import Path
from gtts import gTTS

SCENES = [
    {
        "id": "scene1",
        "title": "Mở đầu & Nêu bài toán thực tế",
        "text": (
            "Kính chào quý thầy cô và các bạn. Mỗi kỳ học, các trường đại học phải tiếp nhận hàng nghìn phản ánh học vụ từ sinh viên "
            "về học phí, điểm thi, lịch học đến thủ tục hành chính. Việc xử lý thủ công qua nhiều kênh rời rạc thường dẫn đến chậm trễ, thất lạc "
            "và áp lực khổng lồ cho cán bộ nhà trường. "
            "Để giải quyết triệt để bài toán này, nhóm chúng em đã phát triển EduSupportAI, "
            "Hệ thống tiếp nhận, phân loại và xử lý phản ánh học vụ thông minh theo định hướng Data-Centric AI, "
            "giúp rút ngắn thời gian phản hồi từ nhiều ngày xuống chỉ còn vài giây."
        )
    },
    {
        "id": "scene2",
        "title": "Cổng tiếp nhận Sinh viên & Bảo mật PII",
        "text": (
            "Đầu tiên là trải nghiệm của sinh viên. Chúng em xây dựng Cổng tiếp nhận riêng biệt với giao diện tinh gọn, trực quan, "
            "tập trung tối đa vào trải nghiệm người dùng. "
            "Tại đây, sinh viên chỉ cần nhập mã sinh viên, email và nội dung phản ánh. "
            "Hệ thống ngay lập tức kích hoạt đường ống xử lý dữ liệu, chuẩn hóa tiếng Việt Unicode, "
            "tự động phát hiện và che giấu thông tin cá nhân PII để bảo vệ quyền riêng tư. "
            "Sau khi gửi, sinh viên nhận ngay Mã hồ sơ để theo dõi tiến độ xử lý minh bạch bất kỳ lúc nào."
        )
    },
    {
        "id": "scene3",
        "title": "Máy học Cục bộ & Tra cứu Quy chế RAG",
        "text": (
            "Trái tim của EduSupportAI là mô hình máy học cục bộ kết hợp TF-IDF kép và hồi quy Logistic, "
            "đạt độ chính xác phân loại trên 94 phần trăm qua 7 chuyên môn nghiệp vụ của trường Đại học Công nghệ Đông Á. "
            "Đặc biệt, hệ thống ứng dụng kỹ thuật RAG tra cứu trực tiếp từ các văn bản quy chế và quy trình học vụ nội bộ của Nhà trường. "
            "Từ đó, AI lập luận chuỗi suy luận 5 bước minh bạch, trích xuất chính xác căn cứ pháp lý, tính toán thời hạn cam kết, "
            "và tự động soạn thảo giải pháp trực diện cho sinh viên mà không cần phụ thuộc vào mô hình đám mây bên ngoài."
        )
    },
    {
        "id": "scene4",
        "title": "Phê duyệt 1 chạm & Gửi Email Thực tế qua SMTP",
        "text": (
            "Khi hồ sơ đạt độ tự tin cao, cơ chế rào chắn an toàn kích hoạt phê duyệt tự động. Đồng thời, cán bộ chuyên trách có thể "
            "rà soát và chỉnh sửa bản nháp trên bàn làm việc Human-in-the-Loop. "
            "Chỉ với một cú click duyệt, hệ thống kích hoạt dịch vụ Email gửi kết quả giải quyết trực tiếp đến hòm thư sinh viên qua giao thức Gmail SMTP an toàn. "
            "Thư gửi đi mang giao diện học thuật Sapphire chuyên nghiệp, kèm đầy đủ căn cứ pháp lý và thông tin liên hệ phòng ban. "
            "Toàn bộ tiến trình gửi thư đều được lưu vết kiểm toán chặt chẽ trong cơ sở dữ liệu."
        )
    },
    {
        "id": "scene5",
        "title": "Tổng kết & Sẵn sàng Triển khai",
        "text": (
            "Với kiến trúc Data-Centric vững chắc, vượt qua toàn bộ 43 bài kiểm thử tự động, "
            "hỗ trợ đồng bộ dữ liệu thời gian thực và đóng gói container sẵn sàng, "
            "EduSupportAI mang lại giải pháp toàn diện giúp chuyển đổi số công tác hỗ trợ sinh viên tại trường đại học. "
            "Xin chân thành cảm ơn quý thầy cô và các bạn đã theo dõi video giới thiệu của nhóm chúng em."
        )
    }
]

def generate_all_audio(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for sc in SCENES:
        out_path = out_dir / f"{sc['id']}.mp3"
        print(f"-> Đang tạo âm thanh cho {sc['id']}: {sc['title']}...")
        tts = gTTS(text=sc["text"], lang="vi", slow=False)
        tts.save(str(out_path))
        print(f"   + Đã lưu thành công: {out_path} ({out_path.stat().st_size} bytes)")

if __name__ == "__main__":
    audio_dir = Path(__file__).resolve().parent.parent / "output" / "audio"
    generate_all_audio(audio_dir)
    print("HOÀN TẤT TẠO TOÀN BỘ 5 PHÂN CẢNH VOICE-OVER BẰNG GTTS!")
