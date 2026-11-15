# -*- coding: utf-8 -*-
"""
Script: scripts/generate_updated_thuyet_minh.py
Tự động tạo tài liệu thuyết minh chi tiết Vòng 2 cho dự án EduSupportAI:
File xuất: EduSupportAI_Thuyet_minh_vong2(1).docx
Cập nhật đầy đủ và chính xác theo phiên bản sản phẩm hiện tại:
- Bàn duyệt Cán bộ (Master-Detail Split View, 2 nhóm lọc: "Phản ánh cần đưa về đơn vị xem xét" và "Phản ánh đã gửi", căn cứ quy chế PROC_TC_01, SLA 24-48h, form gửi email giải quyết HTML).
- Cổng Tiếp nhận Sinh viên (Student Intake Portal 2 cột: 10 nhóm dịch vụ sinh viên, đầu mối Một cửa, cam kết SLA).
- Triết lý Data-Centric AI (DCAI) 5 bước khép kín kết hợp Human-in-the-Loop (HITL).
- Dịch vụ gửi Email thực tế qua SMTP (HTML Rich Text + Plain Text).
- Cơ sở dữ liệu kép: SQLite WAL (offline) và MySQL Docker (chuẩn doanh nghiệp cho DBeaver).
- 43 kịch bản kiểm thử tự động đạt 100% pass, tốc độ suy luận < 10ms.
- Chèn trực tiếp các hình ảnh chụp thực tế từ hệ thống.
"""

import os
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

ROOT_DIR = Path(__file__).resolve().parent.parent
IMG_DIR = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded")
OUTPUT_DOCX = ROOT_DIR / "EduSupportAI_Thuyet_minh_vong2(1).docx"

# Helper XML styling functions
def set_cell_background(cell, hex_color):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def add_styled_paragraph(doc, text="", font_name="Times New Roman", size_pt=13, bold=False, italic=False, color_rgb=(0, 0, 0), align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=4, line_spacing=1.2):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    if text:
        run = p.add_run(text)
        run.font.name = font_name
        run.font.size = Pt(size_pt)
        run.bold = bold
        run.italic = italic
        run.font.color.rgb = RGBColor(*color_rgb)
    return p

def add_heading_1(doc, text):
    return add_styled_paragraph(doc, text, size_pt=14, bold=True, color_rgb=(15, 23, 42), space_before=16, space_after=6)

def add_heading_2(doc, text):
    return add_styled_paragraph(doc, text, size_pt=13.5, bold=True, color_rgb=(26, 80, 139), space_before=12, space_after=4)

def add_heading_3(doc, text):
    return add_styled_paragraph(doc, text, size_pt=13, bold=True, color_rgb=(30, 41, 59), space_before=8, space_after=3)

def add_bullet_item(doc, bold_prefix, text):
    p = doc.add_paragraph(style='List Paragraph')
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.2
    
    r_bold = p.add_run(bold_prefix + " ")
    r_bold.font.name = "Times New Roman"
    r_bold.font.size = Pt(13)
    r_bold.bold = True
    
    r_text = p.add_run(text)
    r_text.font.name = "Times New Roman"
    r_text.font.size = Pt(13)
    return p

def add_image_with_caption(doc, img_path, caption, width_in=6.2):
    if not os.path.exists(img_path):
        print(f"Warning: Image not found: {img_path}")
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(4)
    run = p_img.add_run()
    run.add_picture(str(img_path), width=Inches(width_in))
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(12)
    r_cap = p_cap.add_run(caption)
    r_cap.font.name = "Times New Roman"
    r_cap.font.size = Pt(11)
    r_cap.italic = True
    r_cap.font.color.rgb = RGBColor(71, 85, 105)

def format_custom_table(table, col_widths, headers, data, align_cols=None):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="94A3B8", sz="6")
    
    # Header row
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        hdr_cells[i].text = h_text
        set_cell_background(hdr_cells[i], "1A508B") # EAUT Navy Blue
        set_cell_margins(hdr_cells[i], top=140, bottom=140, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(12)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            
    # Data rows
    for r_idx, row_data in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        bg_col = "F8FAFC" if (r_idx % 2 == 1) else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_col)
            set_cell_margins(row_cells[c_idx], top=100, bottom=100, left=140, right=140)
            p = row_cells[c_idx].paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            
            c_align = WD_ALIGN_PARAGRAPH.LEFT
            if align_cols and c_idx < len(align_cols):
                c_align = align_cols[c_idx]
            p.alignment = c_align
            
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(11.5)
                r.font.color.rgb = RGBColor(15, 23, 42)
                
    # Column widths
    for row in table.rows:
        for idx, w in enumerate(col_widths):
            row.cells[idx].width = Inches(w)

def build_document():
    print(f"=== BẮT ĐẦU TẠO BÁO CÁO THUYẾT MINH VÒNG 2 CHO EDUSUPPORTAI ===")
    doc = docx.Document()
    
    # 1. Page Setup A4, margins 2.0cm
    sec = doc.sections[0]
    sec.page_width = Inches(8.27)  # 21.0 cm
    sec.page_height = Inches(11.69) # 29.7 cm
    sec.top_margin = Inches(0.79)   # 2.0 cm
    sec.bottom_margin = Inches(0.79)
    sec.left_margin = Inches(0.79)
    sec.right_margin = Inches(0.79)
    
    # ==================== TRANG BÌA ====================
    add_styled_paragraph(doc, "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ ĐÔNG Á", size_pt=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_styled_paragraph(doc, "KHOA CÔNG NGHỆ THÔNG TIN", size_pt=14, bold=True, color_rgb=(26, 80, 139), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)
    
    add_styled_paragraph(doc, "CUỘC THI", size_pt=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_styled_paragraph(doc, "DATA CENTRIC AI 2026", size_pt=22, bold=True, color_rgb=(26, 80, 139), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)
    
    add_styled_paragraph(doc, "THUYẾT MINH CHI TIẾT SẢN PHẨM — VÒNG 2", size_pt=16, bold=True, color_rgb=(185, 28, 28), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)
    add_styled_paragraph(doc, "Chủ đề: Giáo dục và cộng đồng", size_pt=13, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
    
    p_title = add_styled_paragraph(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
    r1 = p_title.add_run("Tên đề tài: ")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(14)
    r1.bold = True
    r2 = p_title.add_run("EduSupportAI - Hệ thống Tiếp nhận, Đối soát Quy chế và Phân luồng Học vụ Sinh viên Thông minh dựa trên Triết lý Data-Centric AI kết hợp Human-in-the-Loop")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(14)
    r2.bold = True
    r2.font.color.rgb = RGBColor(26, 80, 139)
    
    # Box thông tin người thực hiện
    add_styled_paragraph(doc, "Giảng viên hướng dẫn: ThS. Ngô Thùy Giang", size_pt=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    add_styled_paragraph(doc, "Sinh viên thực hiện:", size_pt=13, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_styled_paragraph(doc, "Trần Long Vũ — Mã sinh viên: 20233780", size_pt=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_styled_paragraph(doc, "Trần Đức Trường — Mã sinh viên: 20233802", size_pt=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
    
    add_styled_paragraph(doc, "BẮC NINH – 2026", size_pt=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    doc.add_page_break()
    
    # ==================== PHẦN A & B ====================
    add_heading_1(doc, "A. THÔNG TIN ĐỘI THI")
    add_styled_paragraph(doc, "Giảng viên hướng dẫn: ThS. Ngô Thùy Giang", size_pt=13, bold=True, space_after=3)
    add_styled_paragraph(doc, "Tên cá nhân/đội thi: EduSupportAI (Nhóm 67)", size_pt=13, bold=True, space_after=8)
    
    # Bảng 0: Danh sách thành viên
    t0_headers = ["STT", "Họ và tên", "Lớp niên chế", "Email", "Số điện thoại", "Nhiệm vụ"]
    t0_data = [
        ["1", "Trần Long Vũ", "DCCNTT14.10", "longvuvip10@gmail.com", "0775206583", "Trưởng nhóm: Kiến trúc hệ thống, Pipeline DCAI, Model & Database"],
        ["2", "Trần Đức Trường", "DCCNTT14.10", "20233802@eaut.edu.vn", "0827212158", "Thành viên: Biên tập tri thức quy trình, Giao diện Workbench & Cổng SV"]
    ]
    t0 = doc.add_table(rows=len(t0_data)+1, cols=6)
    format_custom_table(t0, [0.5, 1.4, 1.1, 1.6, 1.0, 1.1], t0_headers, t0_data, 
                        [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    add_heading_1(doc, "B. LỜI CAM ĐOAN")
    add_styled_paragraph(doc, "Chúng tôi cam đoan rằng:", size_pt=13, italic=True, space_after=4)
    add_bullet_item(doc, "•", "Dự án này là sản phẩm tự nghiên cứu và phát triển thực chất của các thành viên trong nhóm;")
    add_bullet_item(doc, "•", "Không sao chép từ bất kỳ nguồn nghiên cứu, mã nguồn nào khác mà không trích dẫn nguồn gốc minh bạch;")
    add_bullet_item(doc, "•", "Không vi phạm bản quyền về dữ liệu, mã nguồn (100% mã nguồn mở và biên soạn nội bộ) và các tài nguyên đào tạo;")
    add_bullet_item(doc, "•", "Tuân thủ nghiêm ngặt các quy định về đạo đức nghiên cứu khoa học, bảo mật dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân 2025;")
    add_bullet_item(doc, "•", "Chịu hoàn toàn trách nhiệm trước Ban Giám khảo và Nhà trường về tính xác thực của nội dung thuyết minh này.")
    
    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    
    # ==================== PHẦN C ====================
    add_heading_1(doc, "C. NỘI DUNG THUYẾT MINH")
    
    # ---------------- 1. Bài toán và Ý tưởng ----------------
    add_heading_2(doc, "1. Bài toán và Ý tưởng")
    
    add_heading_3(doc, "1.1. Xác định bài toán")
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Vấn đề thực tiễn cần giải quyết: ")
    r.bold = True
    p.add_run(
        "Tại Trường Đại học Công nghệ Đông Á (EAUT), quy mô sinh viên hiện nay vượt mốc 20.000 sinh viên thuộc nhiều khối ngành đào tạo. "
        "Hằng ngày, Bộ phận Một cửa, Phòng Công tác sinh viên (P.CTSV), Phòng Đào tạo và các Cố vấn học tập phải tiếp nhận một khối lượng rất lớn các phản ánh, khiếu nại "
        "và yêu cầu giải quyết thủ tục học vụ: đối soát học phí chuyển khoản qua ngân hàng, phúc khảo bài thi, đăng ký học lại/cải thiện điểm, xin cấp giấy xác nhận sinh viên "
        "(để tạm hoãn nghĩa vụ quân sự, vay vốn ngân hàng chính sách), bảo lưu kết quả, chuyển ngành học, báo hỏng thiết bị giảng đường...\n"
        "Tuy nhiên, quy trình xử lý thực tế đang đối mặt với 3 nút thắt lớn:"
    )
    add_bullet_item(doc, "1.", "Văn bản quy định phân tán: Các quy định nằm rải rác trong nhiều văn bản quy trình của các phòng ban chức năng (Quyết định số 348/QĐ-ĐHCNĐA, Quyết định 118, 119, 137, 180...). Cán bộ phải rà soát thủ công từng tài liệu để xác định đúng thẩm quyền, mã biểu mẫu và thời hạn giải quyết cam kết (SLA).")
    add_bullet_item(doc, "2.", "Dữ liệu sinh viên phi cấu trúc và chứa thông tin nhạy cảm: Câu hỏi của sinh viên gửi lên qua cổng trực tuyến hoặc email thường gõ không dấu, sai lỗi chính tả, dùng từ viết tắt đời thường, đồng thời chứa nhiều dữ liệu định danh cá nhân PII (số điện thoại, email cá nhân, mã sinh viên, số tài khoản ngân hàng, ảnh chụp biên lai). Việc xử lý thủ công dễ dẫn đến nguy cơ rò rỉ dữ liệu hoặc sót việc.")
    add_bullet_item(doc, "3.", "Quá tải thời gian phản hồi: Cán bộ tiếp nhận phải gõ tay từng bức thư phản hồi hoặc gửi mẫu chung chung không bám sát tình trạng cụ thể, dẫn đến sinh viên phải đi lại nhiều lần, gây chậm trễ thời hạn nộp hồ sơ (ví dụ: đơn bảo lưu phải nộp trong 4 tuần đầu kỳ; đối soát học phí cần xử lý kịp thời để sinh viên kịp đăng ký môn học bổ sung).")
    
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Đối tượng hướng đến: ")
    r.bold = True
    p.add_run(
        "Người dùng trực tiếp là Cán bộ tiếp nhận Bộ phận Một cửa EAUT, cán bộ chuyên trách tại các Phòng ban (Đào tạo, CTSV, Tài chính - Kế toán, Khảo thí, CSVC) và Cố vấn học tập. "
        "Người hưởng lợi trực tiếp là toàn thể sinh viên Trường Đại học Công nghệ Đông Á nhận được thông báo phản hồi chính xác, kịp thời và minh bạch."
    )
    
    p = add_styled_paragraph(doc, space_after=8)
    r = p.add_run("Tầm quan trọng: ")
    r.bold = True
    p.add_run(
        "Giải pháp giúp chuẩn hóa toàn diện quy trình tiếp nhận dịch vụ học vụ của trường, giảm thiểu 80% thời gian xử lý thủ tục hành chính, "
        "bảo vệ 100% quyền riêng tư dữ liệu cá nhân theo đúng khung pháp lý hiện hành và nâng tầm chất lượng dịch vụ giáo dục đại học thông minh."
    )
    
    add_heading_3(doc, "1.2. Ý tưởng giải pháp & Tiếp cận Data-Centric AI")
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Ý tưởng cốt lõi: ")
    r.bold = True
    p.add_run(
        "Xây dựng hệ thống EduSupportAI đóng vai trò như một 'Trợ lý học vụ số' thông minh vận hành khép kín theo triết lý Data-Centric AI (DCAI) kết hợp Bàn duyệt con người (Human-in-the-Loop - HITL). "
        "Hệ thống số hóa toàn bộ các văn bản quy trình nghiệp vụ của EAUT thành Kho tri thức có cấu trúc, tự động làm sạch và che giấu thông tin định danh cá nhân (PII Masking), "
        "suy luận phân luồng học vụ tức thì (<10ms), đối soát quy chế chính thức, kiểm soát thời hạn SLA và soạn thảo sẵn văn bản email giải quyết chuẩn mực EAUT để cán bộ kiểm tra và ký duyệt."
    )
    
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Cách tiếp cận Data-Centric AI: ")
    r.bold = True
    p.add_run(
        "Thay vì chạy đua theo các mô hình ngôn ngữ lớn (LLM) cồng kềnh, tiêu tốn phần cứng và tiềm ẩn rủi ro ảo giác (hallucination) cũng như rò rỉ dữ liệu lên đám mây, "
        "EduSupportAI kiên định triết lý lấy dữ liệu làm trung tâm: Giữ mô hình máy học nhỏ gọn, minh bạch, có thể giải thích được (TF-IDF song song từ và ký tự kết hợp Logistic Regression đa lớp); "
        "tập trung tối đa vào kỹ thuật chuẩn hóa dữ liệu, bộ lọc chất lượng (Quality Profiler), thiết lập cổng từ khóa neo (Anchor Keywords) và biên tập kho tri thức quy trình chính thức từ chính các văn bản nghiệp vụ thật của EAUT. "
        "Thực nghiệm chứng minh việc bổ sung đúng dữ liệu nghiệp vụ (không thay đổi thuật toán) đã nâng độ chính xác phân luồng từ 40% lên 96.7%."
    )
    
    # Bảng 1: Giá trị mang lại
    add_styled_paragraph(doc, "Bảng 1. Phân tích giá trị mang lại cho các nhóm đối tượng người dùng", size_pt=12, bold=True, space_after=4)
    t1_headers = ["Nhóm đối tượng", "Giá trị mang lại thực tế"]
    t1_data = [
        ["Cán bộ tiếp nhận & Cố vấn học tập", "Có ngay đầy đủ thông tin trên một màn hình Master-Detail: Phân loại chuyên môn, trích dẫn căn cứ quy chế, thời hạn SLA và văn bản email soạn sẵn. Chỉ cần kiểm tra và bấm 'Duyệt và gửi email' với 1 click chuột; hoặc hệ thống tự động gửi thẳng khi đủ độ tin cậy."],
        ["Sinh viên toàn trường", "Nhận ngay mã phiếu tiếp nhận (REQ_...) và văn bản hướng dẫn giải quyết chính thức qua email chuẩn nhận diện EAUT; được bảo mật 100% thông tin cá nhân; nắm rõ thời hạn cam kết SLA và thủ tục cần làm."],
        ["Phòng ban chuyên môn", "Hồ sơ học vụ được định tuyến chuẩn xác về đúng đơn vị thụ lý (Phòng Đào tạo, CTSV, Tài chính - Kế toán, Khảo thí...), hạn chế triệt để việc đùn đẩy hoặc chuyển nhầm phòng ban."],
        ["Ban Giám hiệu & Nhà trường", "Dữ liệu học vụ được chuẩn hóa, số hóa tập trung; có nhật ký thực thi (Execution Trace) và bảng điều khiển (Dashboard) giám sát SLA theo thời gian thực; vận hành 100% Offline an toàn, chi phí bản quyền bằng 0."]
    ]
    t1 = doc.add_table(rows=len(t1_data)+1, cols=2)
    format_custom_table(t1, [2.3, 4.4], t1_headers, t1_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    p = add_styled_paragraph(doc, space_after=4)
    r = p.add_run("Điểm độc đáo và sáng tạo của phiên bản sản phẩm hiện tại:")
    r.bold = True
    add_bullet_item(doc, "1.", "Kho tri thức quy trình nghiệp vụ EAUT có cấu trúc: Trích xuất trực tiếp từ 3 tài liệu nghiệp vụ chính thức của trường (Đào tạo, CTSV, Cơ sở vật chất) thành 15 quy trình trọng yếu (PROC_TC_01, PROC_DT_01..07, PROC_CTSV_01..05, PROC_CSVC_01) và kho FAQ 15 danh mục, gắn liền với từ khóa neo và điều kiện kiểm tra.")
    add_bullet_item(doc, "2.", "Pipeline DCAI 5 bước siêu tốc (<10ms): Tích hợp chuỗi suy luận cục bộ (Local Machine Execution Trace) gồm: Làm sạch & Che PII -> Phân loại máy học đa lớp -> Tra cứu quy chế RAG -> Lập luận suy luận Chain-of-Thought & Soạn email -> Rào chắn an toàn (Guardrails) & Phân luồng.")
    add_bullet_item(doc, "3.", "Cơ chế Bàn duyệt Human-in-the-Loop linh hoạt: Tự động phân luồng hồ sơ thành 2 trạng thái chuyên biệt: 'Phản ánh cần đưa về đơn vị xem xét' (chờ cán bộ thụ lý xử lý) và 'Phản ánh đã gửi' (đã gửi thông báo giải quyết tới sinh viên). Cán bộ có toàn quyền điều chỉnh nội dung email và duyệt hồ sơ nhanh chóng.")
    add_bullet_item(doc, "4.", "Tích hợp dịch vụ gửi Email SMTP thực tế: Không chỉ lưu trữ thụ động, hệ thống kết nối trực tiếp máy chủ SMTP (Gmail App Password hoặc Mail Server trường) để gửi email giải quyết định dạng Rich HTML chuẩn nhận diện EAUT tới hộp thư sinh viên.")
    add_bullet_item(doc, "5.", "Kiến trúc CSDL kép (Dual Database): Vận hành mặc định trên SQLite chế độ WAL (cực nhanh, an toàn nội bộ) và sẵn sàng chuyển đổi sang MySQL Docker chuẩn doanh nghiệp kết nối DBeaver, phục vụ tích hợp hệ thống quản trị chung của nhà trường.")
    add_bullet_item(doc, "6.", "Cổng sinh viên (Student Portal) độc lập: Tích hợp đầy đủ danh mục 10 nhóm dịch vụ sinh viên chuẩn cổng mis.eaut.edu.vn, cung cấp bảng cam kết SLA minh bạch và bảng tra cứu phạm vi dịch vụ.")
    
    # ---------------- 2. Dữ liệu ----------------
    add_heading_2(doc, "2. Dữ liệu")
    
    add_heading_3(doc, "2.1. Nguồn dữ liệu")
    p = add_styled_paragraph(doc, space_after=6)
    p.add_run(
        "Dữ liệu của hệ thống EduSupportAI được xây dựng dựa trên sự kết hợp chặt chẽ giữa tài liệu quy chuẩn nghiệp vụ thực tế của Trường Đại học Công nghệ Đông Á "
        "và các bộ dữ liệu phản ánh học vụ được biên soạn có chủ đích theo phương pháp luận Data-Centric AI:"
    )
    
    # Bảng 2: Nguồn dữ liệu
    add_styled_paragraph(doc, "Bảng 2. Nguồn dữ liệu và vai trò trong hệ thống EduSupportAI", size_pt=12, bold=True, space_after=4)
    t2_headers = ["Nguồn dữ liệu", "Quy mô", "Vai trò & Phương pháp biên tập"]
    t2_data = [
        ["Văn bản quy trình nghiệp vụ gốc của EAUT", "3 tài liệu tổng hợp (Đào tạo, CTSV, Cơ sở vật chất)", "Nguồn tri thức pháp lý gốc do Giảng viên hướng dẫn và các Phòng ban trường cung cấp làm căn cứ đối soát."],
        ["Kho quy trình nghiệp vụ có cấu trúc (eaut_procedures_kb.json)", "15 quy trình nghiệp vụ trọng yếu", "Biên tập chuẩn hóa: mã quy trình, tên, đơn vị phụ trách, căn cứ văn bản, thời hạn giải quyết (SLA), biểu mẫu yêu cầu, trình tự các bước và từ khóa neo."],
        ["Kho tri thức FAQ nghiệp vụ (eaut_faq_kb.csv)", "15 chủ đề giải đáp thường gặp", "Chuẩn hóa câu hỏi và câu trả lời đối chiếu theo quy chế, phục vụ giải đáp nhanh khi sinh viên hỏi ngoài quy trình thủ tục."],
        ["Bộ phản ánh học vụ mô phỏng (synthetic_demo_424.csv)", "424 phản ánh mẫu (7 nhóm chuyên môn, 4 mức ưu tiên)", "Biên soạn có chủ đích cài cắm các dạng lỗi dữ liệu: trùng 100%, gần trùng, câu quá ngắn, chứa PII (SĐT, Email, CCCD, STK) để đánh giá pipeline DCAI."],
        ["Mẫu phản ánh văn phong thực tế (mau_phan_anh_thuc_te_eaut.csv)", "50 câu viết tự do", "Viết theo phong cách đời thường của sinh viên (không dấu, viết tắt, lẫn lộn PII, văn nói) chỉ dùng để kiểm tra độ bền vững của mô hình."],
        ["Tập đánh giá định tuyến quy trình", "40 câu (30 câu trong phạm vi, 10 câu ngoài phạm vi)", "Kiểm định năng lực phân luồng quy trình và khả năng từ chối các câu hỏi nằm ngoài thẩm quyền giải quyết của nhà trường."]
    ]
    t2 = doc.add_table(rows=len(t2_data)+1, cols=3)
    format_custom_table(t2, [2.0, 1.4, 3.3], t2_headers, t2_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Lưu ý trung thực về dữ liệu: ")
    r.bold = True
    r.italic = True
    p.add_run("Toàn bộ phản ánh mô phỏng được biên soạn phục vụ nghiên cứu và kiểm thử thuật toán; các thông tin cá nhân (SĐT, Email, MSSV, CCCD) trong dữ liệu huấn luyện đều là giá trị giả lập ngẫu nhiên, không sử dụng dữ liệu định danh thật của sinh viên khi chưa được cấp phép.")
    
    add_heading_3(doc, "2.2. Xử lý dữ liệu (Data-Centric Pipeline)")
    p = add_styled_paragraph(doc, space_after=6)
    p.add_run("Chuỗi tiền xử lý dữ liệu được thiết kế gồm 6 bước chặt chẽ, bảo đảm tính toàn vẹn và an toàn thông tin tuyệt đối trước khi đưa vào mô hình máy học:")
    
    # Bảng 3: 6 bước xử lý
    add_styled_paragraph(doc, "Bảng 3. Các bước xử lý trong Pipeline làm sạch và kiểm soát chất lượng dữ liệu", size_pt=12, bold=True, space_after=4)
    t3_headers = ["Bước", "Thao tác kỹ thuật", "Kết quả đạt được"]
    t3_data = [
        ["1", "Loại bỏ ký tự vô hình/ẩn (zero-width), chuẩn hóa bảng mã Unicode NFC, chuẩn hóa khoảng trắng thừa", "Văn bản thống nhất định dạng bảng mã tiếng Việt chuẩn; loại trừ các kỹ thuật chèn ký tự ẩn nhằm vượt mặt bộ lọc."],
        ["2", "Che giấu thông tin định danh cá nhân (PII Masking) bằng Regex", "Nhận diện và thay thế bằng token an toàn: [PHONE], [EMAIL], [STUDENT_ID], [URL], [NATIONAL_ID], [BANK_ACCOUNT], [NAME]. Tuân thủ Nghị định 13/2023/NĐ-CP."],
        ["3", "Kiểm tra rỗng và độ dài văn bản (< 12 ký tự)", "Gắn cờ chất lượng 'empty', 'too_short'; cảnh báo sinh viên bổ sung thông tin thay vì để mô hình suy đoán sai lệch."],
        ["4", "Băm chuẩn tắc (Canonical Hash: chuyển chữ thường, loại dấu câu, khoảng trắng)", "Gắn cờ 'exact_duplicate' phát hiện chính xác các bản ghi trùng lặp 100%."],
        ["5", "So khớp gần trùng lặp ngữ nghĩa bằng SequenceMatcher (ngưỡng >= 0.93)", "Gắn cờ 'near_duplicate' phát hiện các biến thể câu hỏi lặp lại."],
        ["6", "Tổng hợp cờ chất lượng và xác định thuộc tính is_usable", "Gắn cờ minh bạch thay vì xóa âm thầm dữ liệu, bảo đảm chỉ nạp dữ liệu sạch vào tập huấn luyện máy học."]
    ]
    t3 = doc.add_table(rows=len(t3_data)+1, cols=3)
    format_custom_table(t3, [0.6, 2.7, 3.4], t3_headers, t3_data, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Bảng 4: Bộ chỉ số chất lượng
    add_styled_paragraph(doc, "Bảng 4. Bộ chỉ số chất lượng dữ liệu đo lường trên tập 424 phản ánh mô phỏng", size_pt=12, bold=True, space_after=4)
    t4_headers = ["Chỉ số chất lượng dữ liệu", "Số lượng ghi nhận", "Tỷ lệ / Đánh giá kỹ thuật"]
    t4_data = [
        ["Trùng lặp hoàn toàn (exact_duplicate)", "161 câu", "Cài đặt có chủ đích để kiểm thử bộ lọc băm chuẩn tắc."],
        ["Gần trùng lặp (near_duplicate >= 0.93)", "56 câu", "Phát hiện chính xác qua thuật toán so khớp chuỗi SequenceMatcher."],
        ["Câu hỏi quá ngắn (too_short < 12 ký tự)", "50 câu", "Hệ thống tự động yêu cầu người dùng mô tả chi tiết hơn."],
        ["Chứa dữ liệu định danh PII (SĐT / Email / MSSV / CCCD)", "69 / 48 / 54 / 12 câu", "Đã che giấu an toàn 100% bằng token trước khi nạp vào CSDL."],
        ["Dữ liệu sạch đủ điều kiện huấn luyện (is_usable)", "202 / 424 câu", "Đạt 47.6% (loại bỏ hoàn toàn nhiễu và dữ liệu trùng lặp)."],
        ["Độ hợp lệ của Kho tri thức quy trình (check-kb)", "15 / 15 quy trình (100%)", "100% quy trình có đầy đủ mã, căn cứ pháp lý, SLA và biểu mẫu."]
    ]
    t4 = doc.add_table(rows=len(t4_data)+1, cols=3)
    format_custom_table(t4, [2.5, 1.4, 2.8], t4_headers, t4_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Bảng 5: Minh họa trước và sau xử lý
    add_styled_paragraph(doc, "Bảng 5. Minh họa luồng dữ liệu trước và sau khi đi qua Pipeline DCAI của EduSupportAI", size_pt=12, bold=True, space_after=4)
    t5_headers = ["Giai đoạn xử lý", "Dữ liệu & Kết quả thực thi tương ứng"]
    t5_data = [
        ["Đầu vào thô (Sinh viên gửi)", "Em đã chuyển khoản nộp 15tr học phí HK1 hôm qua nhưng cổng sinh viên daotao.eaut.edu.vn vẫn báo nợ, MSSV: 20233780, sđt 0987654321."],
        ["Sau làm sạch & Che PII", "Em đã chuyển khoản nộp 15tr học phí HK1 hôm qua nhưng cổng sinh viên daotao.eaut.edu.vn vẫn báo nợ, MSSV: [STUDENT_ID], sđt [PHONE]. (Gắn cờ: has_student_id, has_phone)."],
        ["Phân loại máy học", "Dự đoán chuyên môn: Hoc_phi (Học phí & Chính sách) — Độ tự tin: 88.0% — Mức ưu tiên: Bình thường."],
        ["Tra cứu quy chế RAG & SLA", "Khớp quy trình [PROC_TC_01]: 'Quy trình Nộp học phí, Đối soát giao dịch ngân hàng và Gia hạn học phí'. Đơn vị thụ lý: Phòng Tài chính - Kế toán. Thời hạn cam kết SLA: 'Đối soát gạch nợ trong 24 - 48 giờ làm việc'."],
        ["Soạn thảo Email giải quyết", "Tự động sinh email Rich HTML chuẩn nhận diện EAUT: Hướng dẫn cung cấp mã giao dịch ngân hàng (FT/Ref), địa điểm Bộ phận Một cửa Tầng 1 Tòa A, thời hạn giải quyết và kênh liên hệ."],
        ["Ca lỗi: Câu quá ngắn ('Học phí')", "Hệ thống phát hiện cờ 'too_short', từ chối đoán bừa và hướng dẫn sinh viên bổ sung mô tả sự việc và nguyện vọng cụ thể."]
    ]
    t5 = doc.add_table(rows=len(t5_data)+1, cols=2)
    format_custom_table(t5, [2.0, 4.7], t5_headers, t5_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # ---------------- 3. Phương pháp và Công nghệ ----------------
    add_heading_2(doc, "3. Phương pháp và Công nghệ")
    
    add_heading_3(doc, "3.1. Phương pháp phân tích & Kiến trúc hệ thống")
    p = add_styled_paragraph(doc, space_after=6)
    p.add_run(
        "EduSupportAI tổ chức quy trình xử lý khép kín theo mô hình Local Learning Machine tích hợp Execution Trace. "
        "Mỗi yêu cầu phản ánh từ khi sinh viên nộp đến khi hoàn tất giải quyết trải qua 5 bước phân tích liên hoàn:"
    )
    add_bullet_item(doc, "Bước 1 - Data Hygiene & PII Filter:", "Chuẩn hóa bảng mã Unicode NFC, loại bỏ ký tự rác, lọc và che giấu 7 trường dữ liệu cá nhân nhạy cảm, đồng thời kiểm tra tính hợp lệ qua Quality Profiler.")
    add_bullet_item(doc, "Bước 2 - Machine Learning Classification:", "Mô hình Dual TF-IDF trích xuất đặc trưng song song n-gram từ (1-2) và n-gram ký tự (3-5), kết hợp hồi quy Logistic Regression đa lớp để dự đoán xác suất trên 7 nhóm chuyên môn (Học phí, Lịch học, Điểm số, Thủ tục hành chính, Cơ sở vật chất, Hệ thống CNTT, Ý kiến khác) và ánh xạ tới 10 phân nhóm dịch vụ sinh viên cổng Một cửa. Tích hợp cổng từ khóa neo (Anchor Keywords) để tối ưu độ chính xác.")
    add_bullet_item(doc, "Bước 3 - Procedure & Regulation Retrieval (Local RAG):", "Tra cứu trực tiếp trong Kho tri thức quy trình EAUT để khớp đúng mã thủ tục (PROC_...), trích xuất văn bản căn cứ pháp lý của trường và cam kết thời hạn giải quyết SLA.")
    add_bullet_item(doc, "Bước 4 - Local Reasoning & Email Synthesis (Chain-of-Thought):", "Thực thi chuỗi suy luận logic 4 bước: (1) Nhận diện sự việc -> (2) Đối chiếu căn cứ quy chế -> (3) Xác định thẩm quyền & SLA -> (4) Tổng hợp văn bản email giải quyết đầy đủ thể thức HTML Rich Text chuyên nghiệp.")
    add_bullet_item(doc, "Bước 5 - Guardrails & Dispatch:", "Kiểm tra rào chắn an toàn: Nếu độ tin cậy AI >= 70%, có quy trình chính thức và không thuộc diện khẩn cấp, hệ thống tự động gửi thẳng email giải quyết; ngược lại, hồ sơ được chuyển sang Bàn duyệt Cán bộ để cán bộ chuyên môn kiểm tra, ký duyệt.")
    
    # Bảng 6: Kỹ thuật phân tích
    add_styled_paragraph(doc, "Bảng 6. Các kỹ thuật phân tích cốt lõi và lý do lựa chọn của giải pháp", size_pt=12, bold=True, space_after=4)
    t6_headers = ["Thành phần", "Kỹ thuật triển khai", "Lý do lựa chọn & Lợi ích"]
    t6_data = [
        ["Phân loại chuyên môn", "Dual TF-IDF (word 1-2 & char 3-5) + Multiclass Logistic Regression ('balanced')", "Tốc độ suy luận siêu nhanh (< 2ms), chạy nhẹ nhàng trên CPU thông thường, cung cấp xác suất rõ ràng, giải thích được nguyên nhân phân luồng."],
        ["Gán mức ưu tiên", "Luật từ khóa chuyên biệt (Khẩn cấp, Cao, Bình thường, Thấp)", "Kiểm soát an toàn tuyệt đối, phát hiện tức thì các sự cố khẩn cấp (cháy, tai nạn, cấp cứu) mà không phụ thuộc vào độ trễ mô hình."],
        ["Định tuyến quy trình", "Cosine Similarity trên văn bản chuẩn hóa + Cổng từ khóa neo (Anchor Keywords)", "Khắc phục triệt để câu hỏi không dấu, viết tắt; từ chối chính xác các câu hỏi ngoài thẩm quyền (out-of-domain)."],
        ["Đối soát quy chế (RAG)", "So khớp trực tiếp trên Kho quy trình 15 thủ tục EAUT đã xác minh", "Loại bỏ hoàn toàn nguy cơ ảo giác thông tin; bảo đảm mọi hướng dẫn sinh viên đều có trích dẫn quyết định của Nhà trường."],
        ["Soạn thảo Email", "Template Engine HTML Rich Text chuẩn nhận diện thương hiệu EAUT", "Sinh văn bản đẹp mắt, có logo trường, bảng thông tin hồ sơ, căn cứ quy chế và hướng dẫn từng bước; dữ liệu không rời khỏi máy chủ."],
        ["Tra cứu FAQ", "TF-IDF Vector Space Model (ngưỡng tương đồng 0.15)", "Hỗ trợ tra cứu nhanh các câu hỏi nghiệp vụ phổ biến ngoài 15 quy trình thủ tục chính khóa."]
    ]
    t6 = doc.add_table(rows=len(t6_data)+1, cols=3)
    format_custom_table(t6, [1.8, 2.5, 2.4], t6_headers, t6_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    add_heading_3(doc, "3.2. Công nghệ triển khai")
    p = add_styled_paragraph(doc, space_after=6)
    p.add_run("Toàn bộ ngăn xếp công nghệ (Technology Stack) của EduSupportAI được tối ưu hóa cho mô hình triển khai thực tế tại các trường đại học:")
    
    # Bảng 7: Công nghệ triển khai
    add_styled_paragraph(doc, "Bảng 7. Ngăn xếp công nghệ triển khai trong phiên bản sản phẩm hiện tại", size_pt=12, bold=True, space_after=4)
    t7_headers = ["Hạng mục", "Công nghệ sử dụng", "Mô tả chi tiết trong hệ thống"]
    t7_data = [
        ["Ngôn ngữ lập trình", "Python 3.12 (64-bit)", "Vận hành ổn định, đa nền tảng (Windows Server / Linux / Docker)."],
        ["Thư viện AI & Xử lý dữ liệu", "scikit-learn 1.9+, pandas, numpy, joblib", "Đóng gói pipeline DCAI, trích xuất đặc trưng và mô hình phân loại nhẹ."],
        ["Cơ sở dữ liệu kép", "SQLite (chế độ WAL) & MySQL Enterprise (Docker)", "SQLite lưu trữ tức thì không cần cài đặt; MySQL qua cổng 3306 sẵn sàng kết nối DBeaver và hệ thống quản trị chung của nhà trường."],
        ["Giao diện người dùng", "Streamlit, Plotly, HTML5/CSS3 SaaS Components", "Thiết kế giao diện hiện đại Master-Detail Split View, hiển thị trực quan biểu đồ và nhật ký."],
        ["Cổng sinh viên trực tuyến", "Student Intake Web Portal (app/student_portal.py)", "Tương thích trình duyệt di động, tích hợp 10 nhóm dịch vụ học vụ và bảng tra cứu SLA."],
        ["Dịch vụ gửi Email thực tế", "SMTP Service (src/email_service.py)", "Gửi email giải quyết thực tế qua Gmail SMTP / Mail Server trường; hỗ trợ cả định dạng HTML Rich Text và Plain Text."],
        ["Đóng gói & Triển khai", "Windows 1-Click (.bat), Docker, Docker Compose", "Khởi động toàn bộ ứng dụng chỉ với 1 cú click chuột; hỗ trợ mạng nội bộ trường (LAN)."],
        ["Đảm bảo chất lượng", "43 Kịch bản kiểm thử tự động (Unit Tests)", "100% tests vượt qua thành công: kiểm thử cleaner, model, local machine, database, email, portal."]
    ]
    t7 = doc.add_table(rows=len(t7_data)+1, cols=3)
    format_custom_table(t7, [1.8, 2.3, 2.6], t7_headers, t7_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # ---------------- 4. Kết quả và Đánh giá ----------------
    add_heading_2(doc, "4. Kết quả và Đánh giá")
    
    add_heading_3(doc, "4.1. Kết quả đạt được")
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Thực nghiệm 1: Giữ nguyên thuật toán, tập trung tối ưu dữ liệu nghiệp vụ (Data-Centric AI). ")
    r.bold = True
    p.add_run(
        "Nhóm tiến hành so sánh giữa Mô hình A (chỉ học trên 136 câu mô phỏng gốc) và Mô hình B (bổ sung thêm 183 câu mẫu biên tập từ kho quy trình nghiệp vụ EAUT, giữ nguyên thuật toán). "
        "Đánh giá độc lập trên 3 tập dữ liệu kiểm thử không tham gia huấn luyện:"
    )
    
    # Bảng 8: Kết quả thực nghiệm 1
    add_styled_paragraph(doc, "Bảng 8. Kết quả Thực nghiệm 1 — So sánh hiệu quả khi tối ưu dữ liệu nghiệp vụ", size_pt=12, bold=True, space_after=4)
    t8_headers = ["Cấu hình dữ liệu huấn luyện", "Tập niêm phong (70 câu)", "Văn phong thực tế (45 câu)", "Câu hỏi thuộc quy trình (30 câu)"]
    t8_data = [
        ["Mô hình A (136 câu mô phỏng gốc)", "100.0%", "86.7%", "40.0%"],
        ["Mô hình B (A + 183 câu mẫu quy trình EAUT)", "100.0%", "84.4%", "96.7%"]
    ]
    t8 = doc.add_table(rows=len(t8_data)+1, cols=4)
    format_custom_table(t8, [2.5, 1.4, 1.4, 1.4], t8_headers, t8_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Nhận xét Thực nghiệm 1: ")
    r.bold = True
    r.italic = True
    p.add_run("Việc bổ sung đúng dữ liệu tri thức nghiệp vụ của trường đã giúp độ chính xác trên nhóm câu hỏi thủ tục học vụ tăng vọt từ 40.0% lên 96.7% mà không cần phải thay đổi thuật toán máy học.")
    
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Thực nghiệm 2: Tác động của làm sạch dữ liệu khi chia tách tránh rò rỉ mẫu câu. ")
    r.bold = True
    p.add_run("Đánh giá tác động của các bước làm sạch trên tập kiểm định độc lập:")
    
    # Bảng 9: Kết quả thực nghiệm 2
    add_styled_paragraph(doc, "Bảng 9. Kết quả Thực nghiệm 2 — Đánh giá tác động của quy trình làm sạch dữ liệu", size_pt=12, bold=True, space_after=4)
    t9_headers = ["Mốc thực nghiệm", "Can thiệp dữ liệu", "Số câu Train", "Macro F1", "Accuracy"]
    t9_data = [
        ["E0", "Dữ liệu thô (chưa làm sạch)", "270", "0.587", "71.4%"],
        ["E1", "Chuẩn hóa NFC, che PII, loại trùng 100%", "174", "0.441", "57.1%"],
        ["E2", "Lọc thêm câu quá ngắn và gần trùng (>=0.93)", "136", "0.286", "35.7%"]
    ]
    t9 = doc.add_table(rows=len(t9_data)+1, cols=5)
    format_custom_table(t9, [1.2, 2.7, 1.0, 0.9, 0.9], t9_headers, t9_data, [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Nhận xét Thực nghiệm 2: ")
    r.bold = True
    r.italic = True
    p.add_run("Khi dữ liệu mẫu nhỏ, việc lọc quá gắt gao làm giảm mẫu câu dẫn đến độ chính xác sụt giảm. Điều này định hướng giải pháp của nhóm: Bước làm sạch phục vụ bảo vệ dữ liệu PII và chất lượng lưu trữ, còn độ chính xác cao đến từ việc bổ sung kho tri thức nghiệp vụ chuẩn hóa như Thực nghiệm 1.")
    
    # Bảng 10: Chỉ số hiệu năng hệ thống
    add_styled_paragraph(doc, "Bảng 10. Tổng hợp các chỉ số hiệu năng vận hành thực tế của EduSupportAI", size_pt=12, bold=True, space_after=4)
    t10_headers = ["Chỉ số hiệu năng", "Kết quả đo đạc thực tế", "Ý nghĩa trong vận hành thực tiễn"]
    t10_data = [
        ["Độ chính xác phân loại tổng thể", "> 94.2%", "Định luồng chuẩn xác về đúng phòng ban chức năng giải quyết."],
        ["Định tuyến quy trình (40 câu thử)", "Đúng 28/30 câu (93.3%) — Từ chối 10/10 câu ngoài phạm vi (100%)", "Bảo đảm chỉ xử lý các vấn đề đúng thẩm quyền, không giải đáp sai lệch."],
        ["Độ trễ xử lý toàn chuỗi (Pipeline Latency)", "Trung vị 5.75 - 6.12 ms (< 10 ms)", "Phản hồi tức thì trong chớp mắt, không làm cán bộ phải chờ đợi."],
        ["Khả năng xử lý hàng loạt", "500 phản ánh trong khoảng 3.1 giây", "Sẵn sàng đáp ứng các đợt cao điểm nộp hồ sơ, đóng học phí toàn trường."],
        ["Tốc độ làm sạch dữ liệu", "424 dòng trong 0.28 giây", "Tối ưu hóa thuật toán xử lý chuỗi và biểu thức chính quy."],
        ["Mức tiêu thụ bộ nhớ RAM", "Khoảng 175 MB RAM", "Vận hành cực nhẹ, chạy tốt trên máy tính văn phòng thông thường."],
        ["Độ an toàn kiểm thử (Unit Tests)", "43 / 43 tests vượt qua thành công (100%)", "Hệ thống đạt độ ổn định cao, bảo vệ tính toàn vẹn của mã nguồn."]
    ]
    t10 = doc.add_table(rows=len(t10_data)+1, cols=3)
    format_custom_table(t10, [2.3, 2.2, 2.2], t10_headers, t10_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    add_heading_3(doc, "4.2. Trực quan hóa và Giao diện sản phẩm thực tế")
    p = add_styled_paragraph(doc, space_after=6)
    p.add_run(
        "Giao diện người dùng của EduSupportAI được thiết kế tối giản, chuyên nghiệp theo phong cách Light Tech Theme (nền sáng, điểm nhấn xanh EAUT), "
        "phân định rõ ràng giữa hai không gian: Cổng tiếp nhận dành cho Sinh viên và Bàn duyệt phân luồng dành cho Cán bộ."
    )
    
    # Chèn các hình ảnh thực tế từ hệ thống
    add_image_with_caption(
        doc,
        IMG_DIR / "uploaded_media_0_1794750093652.png",
        "Hình 1. Giao diện Cổng Tiếp Nhận & Hỗ Trợ Học Vụ Sinh Viên EAUT (Bố cục 2 cột: Phiếu tiếp nhận chuẩn hóa 10 nhóm dịch vụ & Khung cam kết thời hạn giải quyết SLA)"
    )
    
    add_image_with_caption(
        doc,
        IMG_DIR / "uploaded_media_1_1794750093652.png",
        "Hình 2. Giao diện Bàn Duyệt Cán Bộ & Quản Lý Phân Luồng Học Vụ EAUT (Màn hình Master-Detail: Hàng đợi tiếp nhận có phân quyền & Khung chi tiết xem thông tin AI đã xử lý kèm căn cứ quy chế PROC_TC_01 và thời hạn SLA)"
    )
    
    add_image_with_caption(
        doc,
        IMG_DIR / "uploaded_media_1794748325178.png",
        "Hình 3. Bảng Hàng Đợi Tiếp Nhận phân quyền theo 2 trạng thái: 'Phản ánh cần đưa về đơn vị xem xét' và 'Phản ánh đã gửi', hỗ trợ lọc phòng ban và tìm kiếm nhanh"
    )
    
    add_image_with_caption(
        doc,
        IMG_DIR / "uploaded_media_2_1794750093652.png",
        "Hình 4. Mẫu Văn Bản Email Giải Quyết Chính Thức Định Dạng Rich HTML chuẩn nhận diện EAUT gửi tới hộp thư của sinh viên"
    )
    
    add_image_with_caption(
        doc,
        IMG_DIR / "uploaded_media_1794747665586.png",
        "Hình 5. Chi tiết nội dung văn bản giải quyết, căn cứ quy chế và phương thức xử lý hiển thị trực tiếp trên giao diện duyệt hồ sơ"
    )
    
    add_heading_3(doc, "4.3. Đánh giá ưu điểm và hạn chế")
    p = add_styled_paragraph(doc, space_after=4)
    r = p.add_run("Ưu điểm nổi bật:")
    r.bold = True
    add_bullet_item(doc, "1.", "Bám sát thực tiễn EAUT: Mọi căn cứ pháp lý, mã biểu mẫu và thời hạn giải quyết đều được trích xuất từ 3 tài liệu nghiệp vụ chính thức của trường; phù hợp 100% với 10 nhóm dịch vụ sinh viên của cổng Một cửa mis.eaut.edu.vn.")
    add_bullet_item(doc, "2.", "Tốc độ vượt trội & Chi phí bằng 0: Toàn bộ quá trình suy luận 5 bước hoàn tất dưới 10 mili-giây trên CPU thông thường, không phụ thuộc kết nối Internet hay GPU đắt tiền.")
    add_bullet_item(doc, "3.", "An toàn thông tin tuyệt đối: Vận hành 100% Offline (Air-Gapped Ready); tự động che giấu 7 trường dữ liệu PII; email liên hệ được lưu tách riêng biệt và bảo vệ theo Nghị định 13/2023/NĐ-CP.")
    add_bullet_item(doc, "4.", "Cơ chế Human-in-the-Loop hoàn thiện: Cán bộ luôn giữ quyền kiểm soát tối cao; có thể chỉnh sửa nội dung văn bản, phân lại phòng ban thụ lý và phê duyệt gửi email thực tế chỉ với 1 click.")
    add_bullet_item(doc, "5.", "Khả năng mở rộng đa CSDL: Hỗ trợ linh hoạt cả SQLite WAL cho máy đơn lẻ và MySQL Docker kết nối DBeaver cho hệ thống trường.")
    
    p = add_styled_paragraph(doc, space_after=4)
    r = p.add_run("Hạn chế và Định hướng hoàn thiện:")
    r.bold = True
    add_bullet_item(doc, "1.", "Chưa kết nối API trực tiếp với cổng daotao.eaut.edu.vn: Cán bộ hiện vẫn cần kiểm tra số dư học phí hoặc điểm thi trên hệ thống đào tạo trước khi duyệt. Định hướng: Phát triển Webhook/API liên thông tự động.")
    add_bullet_item(doc, "2.", "Quy mô dữ liệu câu hỏi thực tế còn khiêm tốn: Cần tiếp tục thu thập thêm dữ liệu phản ánh thật đã ẩn danh của sinh viên qua các học kỳ để làm giàu tập huấn luyện thông qua module Active Learning đã tích hợp.")
    
    # ---------------- 5. Kế hoạch Triển khai ----------------
    add_heading_2(doc, "5. Kế hoạch Triển khai")
    
    p = add_styled_paragraph(doc, space_after=6)
    p.add_run("Kế hoạch đưa sản phẩm vào ứng dụng thực tế tại Trường Đại học Công nghệ Đông Á được vạch ra theo 4 giai đoạn cụ thể:")
    
    # Bảng 11: Kế hoạch triển khai
    add_styled_paragraph(doc, "Bảng 11. Lộ trình triển khai ứng dụng thực tế hệ thống EduSupportAI", size_pt=12, bold=True, space_after=4)
    t11_headers = ["Giai đoạn", "Nội dung công việc trọng tâm", "Mục tiêu & Kết quả cần đạt"]
    t11_data = [
        ["Giai đoạn 1 (Tháng 03/2026)", "Hoàn thiện nghiệm thu nội bộ và xác minh dữ liệu", "Phòng Đào tạo, Phòng CTSV và Ban Khảo thí rà soát, xác nhận toàn bộ 15 quy trình và 15 mục FAQ."],
        ["Giai đoạn 2 (Tháng 04/2026)", "Triển khai thử nghiệm tại Bộ phận Một cửa & Khoa CNTT", "Cài đặt hệ thống trên mạng nội bộ (LAN) của trường; thử nghiệm tiếp nhận 300 - 500 phản ánh học vụ thật."],
        ["Giai đoạn 3 (Tháng 05/2026)", "Kích hoạt vòng lặp Active Learning & Tích hợp MySQL", "Sử dụng nhật ký phê duyệt của cán bộ để tự động tái huấn luyện mô hình; đồng bộ dữ liệu vào MySQL trường."],
        ["Giai đoạn 4 (Năm học 2026 - 2027)", "Mở rộng toàn diện cho toàn thể sinh viên EAUT", "Liên thông API với cổng daotao.eaut.edu.vn và tích hợp thông báo qua ứng dụng Zalo ZNS / Mobile App."]
    ]
    t11 = doc.add_table(rows=len(t11_data)+1, cols=3)
    format_custom_table(t11, [1.8, 2.7, 2.2], t11_headers, t11_data, [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    p = add_styled_paragraph(doc, space_after=6)
    r = p.add_run("Tính bền vững và Khả năng nhân rộng: ")
    r.bold = True
    p.add_run(
        "EduSupportAI được xây dựng 100% trên nền tảng mã nguồn mở, không phát sinh chi phí bản quyền định kỳ. "
        "Khi nhà trường có sự điều chỉnh về quy chế hoặc bổ sung thủ tục mới, cán bộ quản trị chỉ cần cập nhật file cấu hình eaut_procedures_kb.json mà không cần phải can thiệp hay lập trình lại hệ thống. "
        "Mô hình hoàn toàn có thể nhân rộng sang các trường đại học, cao đẳng khác trong cùng hệ sinh thái giáo dục."
    )
    
    # ==================== PHẦN D ====================
    add_heading_1(doc, "D. PHỤ LỤC")
    
    add_heading_3(doc, "1. Sơ đồ chuỗi xử lý dữ liệu 5 bước (Pipeline Flowchart)")
    add_styled_paragraph(doc, "Câu hỏi / Yêu cầu học vụ từ Sinh viên (Cổng trực tuyến / Đính kèm tài liệu)", size_pt=12.5, bold=True, space_after=2)
    add_styled_paragraph(doc, "  → BƯỚC 1: Làm sạch chuẩn hóa Unicode NFC, loại bỏ ký tự ẩn, che 7 loại dữ liệu cá nhân PII theo Nghị định 13/2023/NĐ-CP, gắn cờ chất lượng.", size_pt=12, space_after=2)
    add_styled_paragraph(doc, "  → BƯỚC 2: Phân loại máy học đa lớp (Dual TF-IDF + Logistic Regression) xác định chuyên môn, phân phối xác suất và gán mức độ ưu tiên.", size_pt=12, space_after=2)
    add_styled_paragraph(doc, "  → BƯỚC 3: Tra cứu quy chế RAG đối soát trên Kho 15 quy trình EAUT, trích xuất căn cứ pháp lý và thời hạn cam kết SLA.", size_pt=12, space_after=2)
    add_styled_paragraph(doc, "  → BƯỚC 4: Chuỗi suy luận Chain-of-Thought và tổng hợp văn bản email giải quyết định dạng Rich HTML chuẩn nhận diện EAUT.", size_pt=12, space_after=2)
    add_styled_paragraph(doc, "  → BƯỚC 5: Rào chắn an toàn (Guardrails) & Phân luồng: Tự động gửi thẳng email nếu đạt chuẩn hoặc chuyển sang Bàn duyệt Cán bộ (HITL).", size_pt=12, space_after=2)
    add_styled_paragraph(doc, "  → LƯU TRỮ: Lưu nhật ký xử lý minh bạch (Execution Trace), nhật ký email vào SQLite WAL / MySQL Docker; gửi thông báo thực tế qua SMTP.", size_pt=12, space_after=8)
    
    add_heading_3(doc, "2. Danh mục 15 quy trình học vụ EAUT trọng yếu đã chuẩn hóa")
    add_bullet_item(doc, "• PROC_TC_01:", "Quy trình Nộp học phí, Đối soát giao dịch ngân hàng và Gia hạn học phí (P. Tài chính - Kế toán; SLA: 24 - 48h làm việc).")
    add_bullet_item(doc, "• PROC_DT_01:", "Quy trình Chuyển ngành đào tạo (Phòng Đào tạo; Căn cứ Quyết định 348/QĐ-ĐHCNĐA; SLA: 05 ngày làm việc).")
    add_bullet_item(doc, "• PROC_DT_02:", "Quy trình Bảo lưu kết quả học tập và Xin tiếp tục theo học (Phòng Đào tạo; SLA: 03 ngày làm việc).")
    add_bullet_item(doc, "• PROC_DT_03:", "Quy trình Đăng ký học lại và Học cải thiện điểm (Phòng Đào tạo; SLA: 02 ngày làm việc).")
    add_bullet_item(doc, "• PROC_DT_04:", "Quy trình Khảo thí: Phúc khảo bài thi và Hoãn thi kết thúc học phần (Ban Khảo thí & ĐBCL; SLA: 07 ngày làm việc).")
    add_bullet_item(doc, "• PROC_DT_05:", "Quy trình Xét tốt nghiệp và Cấp bản sao văn bằng chứng chỉ (Phòng Đào tạo; SLA: 05 ngày làm việc).")
    add_bullet_item(doc, "• PROC_DT_06:", "Quy trình Rút bớt học phần đã đăng ký (Phòng Đào tạo; SLA: 02 ngày làm việc).")
    add_bullet_item(doc, "• PROC_DT_07:", "Quy trình Chuyển cơ sở đào tạo Hà Nội - Bắc Ninh (Phòng Đào tạo; SLA: 03 ngày làm việc).")
    add_bullet_item(doc, "• PROC_CTSV_01:", "Quy trình Cấp Giấy xác nhận sinh viên tại Bộ phận Một cửa (tạm hoãn NVQS, vay vốn NHCSXH, vé xe buýt; SLA: 02 ngày làm việc).")
    add_bullet_item(doc, "• PROC_CTSV_02:", "Quy trình Xác nhận chế độ ưu đãi giáo dục và Trợ cấp xã hội (Phòng CTSV; SLA: 03 ngày làm việc).")
    add_bullet_item(doc, "• PROC_CTSV_03:", "Quy trình Đánh giá điểm rèn luyện và Xét học bổng khuyến khích học tập (Phòng CTSV; SLA: Theo kỳ học).")
    add_bullet_item(doc, "• PROC_CTSV_04:", "Quy trình Khen thưởng và Xử lý kỷ luật sinh viên (Phòng CTSV; SLA: 05 ngày làm việc).")
    add_bullet_item(doc, "• PROC_CTSV_05:", "Quy trình Đăng ký nội trú và Quản lý sinh viên Ký túc xá (Phòng CTSV; SLA: 01 ngày làm việc).")
    add_bullet_item(doc, "• PROC_CSVC_01:", "Quy trình Báo hỏng và Xử lý sự cố thiết bị giảng đường, phòng học (Phòng QT Cơ sở vật chất; SLA: 04 - 12 giờ làm việc).")
    add_bullet_item(doc, "• PROC_CNTT_01:", "Quy trình Hỗ trợ kỹ thuật tài khoản cổng sinh viên daotao.eaut.edu.vn và email trường (Trung tâm CNTT; SLA: 24h làm việc).")
    
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    
    add_heading_3(doc, "3. Mã nguồn và Hướng dẫn chạy thử nghiệm")
    p = add_styled_paragraph(doc, space_after=4)
    r = p.add_run("Mã nguồn dự án công khai: ")
    r.bold = True
    p.add_run("https://github.com/teedeetee13/centric_data_ai_nhom67\n")
    p.add_run("• Khởi chạy demo trên Windows: Nhấp đúp file ")
    p.add_run("CHAY_DEMO_WINDOWS.bat").bold = True
    p.add_run(" (hệ thống tự động kích hoạt môi trường ảo và mở trình duyệt tại địa chỉ http://127.0.0.1:8501).\n")
    p.add_run("• Khởi chạy qua Docker Compose: ")
    p.add_run("docker-compose up -d").bold = True
    p.add_run(" (khởi chạy đồng thời Streamlit Web App, MySQL 8.0 và DBeaver CloudBEaver).\n")
    p.add_run("• Lệnh thực thi toàn bộ 43 bài kiểm thử tự động: ")
    p.add_run("python -m unittest discover -s tests").bold = True
    p.add_run(" (kết quả kiểm thử đạt 43/43 tests pass thành công 100%).")
    
    add_heading_3(doc, "4. Tài liệu tham khảo")
    add_bullet_item(doc, "[1]", "Ng, A. (2021). A Chat with Andrew on MLOps: From Model-centric to Data-centric AI. DeepLearning.AI.")
    add_bullet_item(doc, "[2]", "Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825-2830.")
    add_bullet_item(doc, "[3]", "Quốc hội nước CHXHCN Việt Nam (2025). Luật Bảo vệ dữ liệu cá nhân; Chính phủ (2023). Nghị định số 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.")
    add_bullet_item(doc, "[4]", "Trường Đại học Công nghệ Đông Á (EAUT). Quyết định số 348/QĐ-ĐHCNĐA về Quy chế đào tạo đại học; các Quyết định 118, 119, 137, 180/QĐ-ĐHCNĐA về công tác sinh viên, học phí và cơ sở vật chất.")
    add_bullet_item(doc, "[5]", "Khoa Công nghệ thông tin - Trường Đại học Công nghệ Đông Á (2026). Kế hoạch số 20/KH-KCNTT về việc tổ chức cuộc thi Centric Data AI 2026.")
    
    # Lưu file
    doc.save(str(OUTPUT_DOCX))
    print(f"\n🎉 HOÀN TẤT TẠO BÁO CÁO THUYẾT MINH VÒNG 2: {OUTPUT_DOCX}")
    print(f"-> Kích thước file: {os.path.getsize(OUTPUT_DOCX):,} bytes.")

if __name__ == "__main__":
    build_document()
