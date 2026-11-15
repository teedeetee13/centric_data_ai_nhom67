# -*- coding: utf-8 -*-
"""
Script: scripts/dispatch_student_ticket.py
Tạo phản ánh học vụ thực tế và gửi email phản hồi trực tiếp tới 20233780@eaut.edu.vn qua Gmail SMTP.
"""

import sys
import json
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.service import RequestService
from src.database import save_request, get_request, log_review_action, get_connection
from src.email_service import build_rich_resolution_email, send_resolution_email, get_smtp_config

def main():
    student_name = "Sinh viên EAUT"
    student_id = "20233780"
    student_email = "20233780@eaut.edu.vn"

    inquiry_content = (
        "Kính gửi Phòng Tài chính - Kế toán và Phòng Quản lý Đào tạo trường ĐH Công nghệ Đông Á.\n"
        "Em là sinh viên khóa K14, MSSV: 20233780, email: 20233780@eaut.edu.vn.\n"
        "Em đã chuyển khoản nộp học phí học kỳ I năm học 2024 - 2025 vào tài khoản ngân hàng chính thức của Nhà trường từ ngày 12/11/2024, "
        "nội dung chuyển khoản đúng cú pháp: '20233780 Nguyen Van A Nop hoc phi HK1'.\n"
        "Tuy nhiên, hiện tại trên cổng thông tin sinh viên daotao.eaut.edu.vn trạng thái tài chính của em vẫn chưa được gạch nợ. "
        "Kính mong Quý Phòng kiểm tra, đối soát giao dịch ngân hàng và cập nhật trạng thái học phí trên hệ thống giúp em để em kịp đăng ký học phần đợt bổ sung.\n"
        "Em xin chân thành cảm ơn!"
    )

    print(f"=== BẮT ĐẦU QUY TRÌNH XỬ LÝ PHẢN ÁNH THỰC TẾ CHO {student_id} ({student_email}) ===")
    
    # 1. Khởi tạo dịch vụ RequestService và phân tích AI
    service = RequestService()
    print("-> Đang phân loại AI và tra cứu quy trình đối soát học phí...")
    res = service.process(
        raw_text=inquiry_content,
        topic_hint="Hoc_phi",
        proc_hint="PROC_TC_01",
        mask_pii=False  # Bảo toàn thông tin sinh viên thực tế
    )

    print(f"   + Chủ đề dự đoán: {res.get('predicted_topic')}")
    print(f"   + Độ tự tin: {res.get('confidence_score', 0):.2%}")
    print(f"   + Mức ưu tiên: {res.get('priority_level')}")
    print(f"   + Đơn vị phụ trách: {res.get('department')}")

    # 2. Lưu vào CSDL
    rid = save_request(res, source_type="portal_student", mask_pii=False)
    print(f"-> Đã lưu bản ghi vào CSDL SQLite với Mã hồ sơ: {rid}")

    # Lấy nội dung giải pháp tốt nhất
    best_resp = res.get("procedure_draft_response") or res.get("draft_response") or (
        "Chào em,\n"
        "Phòng Tài chính - Kế toán đã tiếp nhận thông tin đối soát học phí của em (MSSV: 20233780).\n"
        "Thời gian đối soát dữ liệu sao kê ngân hàng tự động từ 24h - 48h làm việc. "
        "Bộ phận kế toán đã kiểm tra và tiến hành gạch nợ thủ công trên cổng daotao.eaut.edu.vn. "
        "Em vui lòng đăng nhập lại cổng để kiểm tra lại biên lai điện tử."
    )

    # 3. Phê duyệt hồ sơ trên CSDL
    try:
        log_review_action(
            record_id=rid,
            officer_action="approve",
            original_topic=res.get("predicted_topic", "Hoc_phi"),
            final_topic=res.get("predicted_topic", "Hoc_phi"),
            final_response=best_resp,
            notes="Duyệt giải quyết tự động và gửi email thông báo trực tiếp đến sinh viên qua Gmail SMTP"
        )
        print(f"-> Đã cập nhật trạng thái hồ sơ: reviewed_approve")
    except Exception as e:
        print(f"   Lưu ý cập nhật trạng thái: {e}")

    # 4. Soạn thảo email giao diện HTML Sapphire Academic
    print("-> Đang dựng nội dung Email HTML chuẩn Sapphire Academic & Slate...")
    subj, plain_body, html_body = build_rich_resolution_email(
        record_id=rid,
        topic=res.get("predicted_topic", "Hoc_phi"),
        department=res.get("department", "Phòng Tài chính - Kế toán"),
        resolution_text=best_resp,
        confidence_score=res.get("confidence_score", 0.95),
        is_auto_approved=True,
        student_name=student_name,
        student_id=student_id,
        procedure_info=res.get("matched_procedure")
    )

    # 5. Kiểm tra cấu hình SMTP
    cfg = get_smtp_config()
    print(f"-> Cấu hình SMTP: Host={cfg.get('server')}:{cfg.get('port')}, User={cfg.get('user')}")

    # 6. Gửi Email thực tế qua Gmail SMTP
    print(f"-> Bắt đầu gửi email thực tế tới {student_email}...")
    success, msg = send_resolution_email(
        recipient_email=student_email,
        subject=subj,
        body_text=plain_body,
        body_html=html_body,
        record_id=rid
    )

    print(f"-> Kết quả gửi email: {'THÀNH CÔNG' if success else 'THẤT BẠI'}")
    print(f"   Thông điệp: {msg}")

    # 7. Kiểm tra bản ghi trong bảng email_dispatches
    with get_connection() as conn:
        dispatch_row = conn.execute(
            "SELECT id, record_id, recipient_email, subject, dispatch_mode, status, error_message, sent_at FROM email_dispatches WHERE record_id=? ORDER BY id DESC LIMIT 1",
            (rid,)
        ).fetchone()
        if dispatch_row:
            d = dict(dispatch_row)
            print(f"-> Kiểm tra CSDL bảng email_dispatches: ID={d['id']}, Mode={d['dispatch_mode']}, Status={d['status']}, SentAt={d['sent_at']}")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
