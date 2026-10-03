# -*- coding: utf-8 -*-
"""
Module: src.data_generator
Tạo tập dữ liệu kịch bản mô phỏng chuẩn (Synthetic / Controlled Demo Dataset) gồm 424 bản ghi.
Bao quát 7 nhóm chuyên môn, cài cắm có chủ đích các ca biên:
- 55 bản ghi trùng lặp tuyệt đối (12.97%)
- 17 bản ghi gần trùng lặp (4.01%)
- 32 bản ghi chứa PII (SĐT, Email, MSSV)
- 20 bản ghi quá ngắn (< 12 ký tự)
"""

import os
import random
import csv

CATEGORIES = [
    "Hoc_phi",
    "Lich_hoc_lich_thi",
    "Diem_khao_thi",
    "Thu_tuc_hanh_chinh",
    "Co_so_vat_chat",
    "He_thong_CNTT",
    "Khac"
]

PRIORITIES = ["Khẩn cấp", "Cao", "Bình thường", "Thấp"]

BASE_TEMPLATES = {
    "Hoc_phi": [
        ("Em đã đóng học phí qua tài khoản ngân hàng từ hôm qua nhưng cổng sinh viên vẫn báo chưa nộp, mã sinh viên của em là {mssv}.", "Bình thường"),
        ("Cho em hỏi hạn nộp học phí kỳ này là ngày nào ạ, em tìm trên web không thấy thông báo.", "Bình thường"),
        ("Em làm đơn xin gia hạn nộp học phí do hoàn cảnh gia đình khó khăn đột xuất thì cần nộp giấy tờ gì và nộp ở đâu ạ?", "Cao"),
        ("Em muốn hỏi về chính sách miễn giảm học phí cho sinh viên con thương binh, hồ sơ nộp về phòng nào?", "Bình thường"),
        ("Hôm nay là hạn cuối nộp học phí mà ngân hàng báo lỗi giao dịch, em có bị đình chỉ thi không ạ cứu em với!", "Khẩn cấp"),
        ("Học phí kỳ phụ hè tính bao nhiêu tiền một tín chỉ vậy ạ, đóng trước ngày thi bao nhiêu lâu?", "Thấp"),
        ("Em bị tính nhầm số tiền học phí môn Lập trình Python, trên cổng báo 3 tín chỉ nhưng lại thu 4 tín chỉ.", "Cao"),
        ("Học phí", "Bình thường"), # Quá ngắn
    ],
    "Lich_hoc_lich_thi": [
        ("Lịch thi kết thúc học phần môn Cơ sở dữ liệu bị trùng giờ với môn Mạng máy tính vào ngày 15/10, em phải làm sao ạ?", "Khẩn cấp"),
        ("Cho em hỏi khi nào có thời khóa biểu học kỳ 1 năm học 2026 cho khóa K14 ạ?", "Bình thường"),
        ("Em bị ốm phải nhập viện đúng ngày thi môn Toán cao cấp, em có được hoãn thi không và thủ tục thế nào?", "Khẩn cấp"),
        ("Lớp học phần tiếng Anh B1 bị hủy do thiếu sĩ số, em muốn chuyển sang lớp khác thì liên hệ thầy cô nào?", "Cao"),
        ("Thầy cô cho em xin lịch thi lại và học lại của các môn học kỳ trước với ạ.", "Bình thường"),
        ("Phòng học 402 nhà B sáng nay khóa cửa, cả lớp đang đứng ngoài hành lang không vào học được.", "Cao"),
        ("Lịch thi", "Bình thường"), # Quá ngắn
        ("Trùng ca thi", "Cao"), # Quá ngắn
    ],
    "Diem_khao_thi": [
        ("Điểm thi kết thúc học phần môn Trí tuệ nhân tạo của em trên cổng bị sai, bài thi giấy em làm tốt mà điểm chỉ có 2.0, em muốn làm đơn phúc khảo.", "Cao"),
        ("Hạn nộp đơn phúc khảo bài thi học kỳ 2 là đến ngày nào vậy ạ, nộp tại phòng Khảo thí ở tầng mấy?", "Bình thường"),
        ("Em xin cấp bảng điểm tạm thời để đi xin thực tập doanh nghiệp thì bao lâu lấy được ạ?", "Bình thường"),
        ("Điểm chuyên cần và kiểm tra giữa kỳ của em bị giảng viên nhập nhầm thành 0 điểm, liên hệ ai để sửa ạ?", "Cao"),
        ("Cổng thông tin báo thiếu điểm môn Giáo dục quốc phòng nên em chưa đủ điều kiện xét tốt nghiệp đợt này.", "Khẩn cấp"),
        ("Xem điểm", "Bình thường"), # Quá ngắn
    ],
    "Thu_tuc_hanh_chinh": [
        ("Em cần xin giấy xác nhận sinh viên để làm hồ sơ tạm hoãn nghĩa vụ quân sự tại địa phương, xin ở phòng nào ạ?", "Cao"),
        ("Em bị mất thẻ sinh viên thì làm lại ở đâu, chi phí bao nhiêu và cần mang ảnh thẻ cỡ mấy?", "Bình thường"),
        ("Thủ tục xin chuyển ngành học từ Công nghệ thông tin sang Khoa học dữ liệu cần điều kiện gì về điểm GPA ạ?", "Bình thường"),
        ("Em muốn xin rút hồ sơ gốc để đi du học thì quy trình các bước như thế nào và cần chữ ký của những ai?", "Cao"),
        ("Giấy xác nhận sinh viên vay vốn ngân hàng chính sách xã hội lấy ở đâu vậy ạ?", "Bình thường"),
        ("Mất thẻ SV", "Bình thường"), # Quá ngắn
    ],
    "Co_so_vat_chat": [
        ("Điều hòa phòng 305 nhà C bị hỏng chảy nước lênh láng ra sàn nhà, máy chiếu cũng không bật lên được, nóng quá không học nổi.", "Cao"),
        ("Bãi giữ xe tầng hầm nhà A buổi sáng hay bị ùn tắc do máy quét thẻ nhận diện chậm, đề nghị nhà trường kiểm tra lại.", "Bình thường"),
        ("Ký túc xá phòng 204 bị mất nước sinh hoạt từ sáng đến giờ, mong ban quản lý khắc phục sớm.", "Khẩn cấp"),
        ("Mic và loa phòng giảng đường 501 bị rè và mất tiếng liên tục, giảng viên nói sinh viên ngồi dưới không nghe thấy gì.", "Bình thường"),
        ("Bàn ghế phòng tự học thư viện tầng 2 bị gãy chân rất nguy hiểm, cần thay mới.", "Thấp"),
        ("Hỏng điều hòa", "Thấp"), # Quá ngắn
    ],
    "He_thong_CNTT": [
        ("Em quên mật khẩu đăng nhập vào cổng thông tin sinh viên daotao.eaut.edu.vn, ấn quên mật khẩu không gửi mã về email.", "Cao"),
        ("Hệ thống đăng ký tín chỉ bị nghẽn mạng từ 8h sáng, em không thể bấm nút lưu môn học được.", "Khẩn cấp"),
        ("Email sinh viên đuôi @eaut.edu.vn của em bị khóa không nhận được thư của giảng viên gửi tài liệu.", "Cao"),
        ("App sinh viên trên điện thoại báo lỗi kết nối máy chủ 500 không xem được điểm danh.", "Bình thường"),
        ("Lỗi mạng wifi trường ở tầng 3 nhà B rất yếu, cứ kết nối được 2 phút lại bị ngắt mạng.", "Thấp"),
        ("Quên pass", "Cao"), # Quá ngắn
    ],
    "Khac": [
        ("Cho em hỏi thông tin về câu lạc bộ tiếng Anh và câu lạc bộ Lập trình của trường mình sinh hoạt vào thứ mấy hàng tuần?", "Thấp"),
        ("Nhà trường có tổ chức xe đưa đón sinh viên về quê dịp Tết Nguyên đán không ạ?", "Thấp"),
        ("Em muốn đăng ký tham gia chiến dịch Mùa hè xanh năm nay thì liên hệ văn phòng Đoàn trường ở đâu?", "Bình thường"),
        ("Đề nghị trường mở rộng thêm nhiều cây xanh và khu vực nghỉ ngơi có mái che cho sinh viên trong giờ chuyển tiết.", "Thấp"),
        ("Alo trường ơi", "Thấp"), # Quá ngắn
    ]
}

SAMPLE_PHONES = ["0987654321", "0912345678", "0978112233", "0356789012", "0909123456"]
SAMPLE_EMAILS = ["longvu.tran@gmail.com", "ductruong2004@yahoo.com", "sv.eaut@student.edu.vn", "contact.me@gmail.com"]
SAMPLE_MSSVS = ["20991234", "2022601234", "2021008899", "2023554433"]

def generate_synthetic_dataset(total_records=424, output_path="data/raw/synthetic_demo_424.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    random.seed(42)

    records = []
    record_id = 1001

    # 1. Sinh các câu hỏi gốc từ templates
    base_pool = []
    for topic, templates in BASE_TEMPLATES.items():
        for text_tmpl, priority in templates:
            phone = random.choice(SAMPLE_PHONES)
            email = random.choice(SAMPLE_EMAILS)
            mssv = random.choice(SAMPLE_MSSVS)
            
            text = text_tmpl.replace("{mssv}", mssv).replace("{phone}", phone).replace("{email}", email)
            base_pool.append({
                "topic": topic,
                "text": text,
                "priority": priority
            })

    # Nhân bản với biến thể văn phong tiếng Việt (viết tắt, thêm thông tin liên hệ, teencode nhẹ)
    prefixes = ["Thưa thầy cô, ", "Dạ em chào thầy cô, ", "Cho em hỏi với ạ: ", "Em xin phép hỏi, ", "Admin ơi, ", ""]
    suffixes = [
        "", 
        " Em cảm ơn ạ.", 
        f" Số điện thoại em là {random.choice(SAMPLE_PHONES)}.", 
        f" Email của em: {random.choice(SAMPLE_EMAILS)}.",
        f" Mã sinh viên {random.choice(SAMPLE_MSSVS)}.",
        " Mong thầy cô hỗ trợ sớm giúp em."
    ]

    while len(records) < 352: # Dành ra 55 trùng 100% và 17 gần trùng
        item = random.choice(base_pool)
        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)
        
        # Nếu câu quá ngắn thì không thêm tiền tố hậu tố để giữ nguyên đặc trưng lỗi
        if len(item["text"]) < 15:
            full_text = item["text"]
        else:
            full_text = f"{prefix}{item['text']}{suffix}"

        records.append({
            "record_id": f"REC_{record_id}",
            "raw_text": full_text,
            "source_type": "controlled_demo",
            "created_at": "2026-09-25 08:30:00",
            "target_label_gold": item["topic"],
            "priority_gold": item["priority"],
            "note": "Ban đầu biên soạn"
        })
        record_id += 1

    # 2. Cài cắm 55 bản ghi trùng lặp tuyệt đối (Exact Duplicates)
    exact_dup_sources = random.sample(records[:150], 25)
    for _ in range(55):
        chosen = random.choice(exact_dup_sources)
        records.append({
            "record_id": f"REC_{record_id}",
            "raw_text": chosen["raw_text"], # Trùng 100%
            "source_type": "controlled_demo",
            "created_at": "2026-09-25 09:15:00",
            "target_label_gold": chosen["target_label_gold"],
            "priority_gold": chosen["priority_gold"],
            "note": "Cài cắm trùng lặp chính xác 100%"
        })
        record_id += 1

    # 3. Cài cắm 17 bản ghi gần trùng lặp (Near Duplicates - thay đổi dấu câu hoặc khoảng trắng)
    near_dup_sources = random.sample(records[50:200], 10)
    for _ in range(17):
        chosen = random.choice(near_dup_sources)
        t = chosen["raw_text"]
        # Thay đổi nhẹ: thêm dấu chấm, dấu cách thừa
        modified_text = t.strip() + " ... " if not t.endswith(".") else t[:-1] + " !"
        records.append({
            "record_id": f"REC_{record_id}",
            "raw_text": modified_text,
            "source_type": "controlled_demo",
            "created_at": "2026-09-25 10:00:00",
            "target_label_gold": chosen["target_label_gold"],
            "priority_gold": chosen["priority_gold"],
            "note": "Cài cắm gần trùng lặp (SequenceMatcher >= 0.93)"
        })
        record_id += 1

    # Shuffle lại để phân bổ ngẫu nhiên
    random.shuffle(records)

    # Ghi ra CSV dùng thư viện chuẩn csv
    fieldnames = ["record_id", "raw_text", "source_type", "created_at", "target_label_gold", "priority_gold", "note"]
    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row)

    print(f"[*] Đã sinh thành công {len(records)} bản ghi mô phỏng tại: {output_path}")

    # Đếm số lượng theo nhóm
    topic_counts = {}
    for r in records:
        topic_counts[r["target_label_gold"]] = topic_counts.get(r["target_label_gold"], 0) + 1
    for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {t}: {c} bản ghi")

    return records

if __name__ == "__main__":
    generate_synthetic_dataset()
