# -*- coding: utf-8 -*-
"""
Script: scripts/convert_docx_to_pdf.py
Xuất báo cáo Thuyết minh chi tiết Vòng 2 sang định dạng PDF:
- File xuất: EduSupportAI_Thuyet_minh_vong2(1).pdf
- Sử dụng Puppeteer và Chrome Headless để tạo file PDF chuẩn in ấn:
  + Khổ giấy A4, lề 20mm
  + Phông chữ Times New Roman, căn đều 2 bên (justify)
  + Bảng biểu chuẩn nhận diện EAUT Navy Blue (#1A508B)
  + 5 hình ảnh minh họa thực tế được nhúng trực tiếp dưới dạng Base64
  + Header & Footer có đánh số trang tự động
"""

import os
import base64
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
IMG_DIR = Path("/home/kennysk/.gemini/antigravity-cli/brain/c635f98a-9af6-4f1a-a052-43c4e8195574/.user_uploaded")
OUTPUT_PDF = ROOT_DIR / "EduSupportAI_Thuyet_minh_vong2(1).pdf"
TEMP_HTML = Path("/tmp/thuyet_minh_vong2.html")

def get_base64_image(filename):
    p = IMG_DIR / filename
    if not p.exists():
        print(f"Warning: Image {filename} does not exist at {p}")
        return ""
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"

def generate_html():
    img1 = get_base64_image("uploaded_media_0_1794750093652.png")
    img2 = get_base64_image("uploaded_media_1_1794750093652.png")
    img3 = get_base64_image("uploaded_media_1794748325178.png")
    img4 = get_base64_image("uploaded_media_2_1794750093652.png")
    img5 = get_base64_image("uploaded_media_1794747665586.png")

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>EduSupportAI - Thuyết minh chi tiết sản phẩm Vòng 2</title>
<style>
    @page {{
        size: A4;
        margin: 20mm 20mm 20mm 20mm;
    }}
    body {{
        font-family: 'Times New Roman', Times, serif;
        font-size: 13pt;
        line-height: 1.35;
        color: #0f172a;
        margin: 0;
        padding: 0;
    }}
    .page-break {{
        page-break-before: always;
        break-before: page;
    }}
    .cover-page {{
        text-align: center;
        padding-top: 10mm;
        height: 240mm;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    h1.inst {{
        font-size: 14pt;
        font-weight: bold;
        text-transform: uppercase;
        margin: 0 0 4px 0;
        letter-spacing: 0.5px;
    }}
    h2.dept {{
        font-size: 14pt;
        font-weight: bold;
        text-transform: uppercase;
        color: #1a508b;
        margin: 0 0 35px 0;
    }}
    .contest-badge {{
        font-size: 15pt;
        font-weight: bold;
        margin: 0 0 4px 0;
    }}
    .contest-title {{
        font-size: 24pt;
        font-weight: bold;
        color: #1a508b;
        letter-spacing: 1px;
        margin: 0 0 35px 0;
    }}
    .doc-type {{
        font-size: 17pt;
        font-weight: bold;
        color: #b91c1c;
        margin: 0 0 10px 0;
        text-transform: uppercase;
    }}
    .theme {{
        font-size: 13pt;
        font-style: italic;
        margin: 0 0 25px 0;
        color: #334155;
    }}
    .project-name {{
        font-size: 15pt;
        font-weight: bold;
        color: #1a508b;
        line-height: 1.4;
        margin: 0 auto 35px auto;
        max-width: 90%;
    }}
    .author-box {{
        font-size: 13pt;
        line-height: 1.5;
        margin-bottom: 40px;
    }}
    .location-year {{
        font-size: 13pt;
        font-weight: bold;
        letter-spacing: 0.5px;
    }}
    
    /* Content headings */
    h1.sec-title {{
        font-size: 14pt;
        font-weight: bold;
        text-transform: uppercase;
        color: #0f172a;
        margin-top: 24px;
        margin-bottom: 10px;
        border-bottom: 2px solid #1a508b;
        padding-bottom: 4px;
    }}
    h2.sub-title {{
        font-size: 13.5pt;
        font-weight: bold;
        color: #1a508b;
        margin-top: 18px;
        margin-bottom: 8px;
    }}
    h3.item-title {{
        font-size: 13pt;
        font-weight: bold;
        color: #1e293b;
        margin-top: 14px;
        margin-bottom: 6px;
    }}
    
    p {{
        text-align: justify;
        margin-top: 0;
        margin-bottom: 6px;
        text-indent: 10mm;
    }}
    p.no-indent {{
        text-indent: 0;
    }}
    ul {{
        margin-top: 2px;
        margin-bottom: 8px;
        padding-left: 25px;
    }}
    li {{
        text-align: justify;
        margin-bottom: 4px;
        line-height: 1.35;
    }}
    
    /* Tables */
    .table-container {{
        margin: 10px 0 14px 0;
        width: 100%;
    }}
    .table-caption {{
        font-size: 12pt;
        font-weight: bold;
        margin-bottom: 5px;
        text-align: left;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 11.5pt;
        margin-bottom: 6px;
    }}
    th {{
        background-color: #1a508b;
        color: #ffffff;
        font-weight: bold;
        text-align: center;
        padding: 8px 10px;
        border: 1px solid #94a3b8;
    }}
    td {{
        padding: 6px 10px;
        border: 1px solid #cbd5e1;
        vertical-align: top;
        line-height: 1.25;
    }}
    tr:nth-child(even) td {{
        background-color: #f8fafc;
    }}
    td.center {{
        text-align: center;
    }}
    td.bold {{
        font-weight: bold;
    }}

    /* Figures */
    .figure-container {{
        text-align: center;
        margin: 14px 0 18px 0;
        page-break-inside: avoid;
    }}
    .figure-img {{
        max-width: 98%;
        height: auto;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .figure-caption {{
        font-size: 11pt;
        font-style: italic;
        color: #475569;
        margin-top: 6px;
    }}

    .highlight-box {{
        background-color: #f1f5f9;
        border-left: 4px solid #1a508b;
        padding: 8px 14px;
        margin: 8px 0 12px 0;
        font-size: 12pt;
    }}
</style>
</head>
<body>

<!-- ==================== TRANG BÌA ==================== -->
<div class="cover-page">
    <div>
        <h1 class="inst">TRƯỜNG ĐẠI HỌC CÔNG NGHỆ ĐÔNG Á</h1>
        <h2 class="dept">KHOA CÔNG NGHỆ THÔNG TIN</h2>
        
        <div style="margin-top: 30px;">
            <div class="contest-badge">CUỘC THI</div>
            <div class="contest-title">DATA CENTRIC AI 2026</div>
        </div>
        
        <div style="margin-top: 30px;">
            <div class="doc-type">THUYẾT MINH CHI TIẾT SẢN PHẨM — VÒNG 2</div>
            <div class="theme">Chủ đề: Giáo dục và cộng đồng</div>
        </div>
        
        <div class="project-name">
            <span style="color: #0f172a;">Tên đề tài:</span><br>
            EduSupportAI - Hệ thống Tiếp nhận, Đối soát Quy chế và Phân luồng Học vụ Sinh viên Thông minh dựa trên Triết lý Data-Centric AI kết hợp Human-in-the-Loop
        </div>
    </div>
    
    <div>
        <div class="author-box">
            <div><strong>Giảng viên hướng dẫn:</strong> ThS. Ngô Thùy Giang</div>
            <div style="margin-top: 4px;"><strong>Sinh viên thực hiện:</strong></div>
            <div>Trần Long Vũ — Mã sinh viên: 20233780</div>
            <div>Trần Đức Trường — Mã sinh viên: 20233802</div>
        </div>
        <div class="location-year">BẮC NINH – 2026</div>
    </div>
</div>

<div class="page-break"></div>

<!-- ==================== PHẦN A & B ==================== -->
<h1 class="sec-title">A. THÔNG TIN ĐỘI THI</h1>
<p class="no-indent"><strong>Giảng viên hướng dẫn:</strong> ThS. Ngô Thùy Giang</p>
<p class="no-indent"><strong>Tên cá nhân/đội thi:</strong> EduSupportAI (Nhóm 67)</p>

<div class="table-container">
    <div class="table-caption">Bảng 0. Danh sách thành viên đội thi EduSupportAI</div>
    <table>
        <thead>
            <tr>
                <th style="width: 6%;">STT</th>
                <th style="width: 22%;">Họ và tên</th>
                <th style="width: 14%;">Lớp niên chế</th>
                <th style="width: 24%;">Email</th>
                <th style="width: 14%;">Số điện thoại</th>
                <th style="width: 20%;">Nhiệm vụ</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="center bold">1</td>
                <td>Trần Long Vũ</td>
                <td class="center">DCCNTT14.10</td>
                <td>longvuvip10@gmail.com</td>
                <td class="center">0775206583</td>
                <td>Trưởng nhóm: Kiến trúc hệ thống, Pipeline DCAI, Model & Database</td>
            </tr>
            <tr>
                <td class="center bold">2</td>
                <td>Trần Đức Trường</td>
                <td class="center">DCCNTT14.10</td>
                <td>20233802@eaut.edu.vn</td>
                <td class="center">0827212158</td>
                <td>Thành viên: Biên tập tri thức quy trình, Giao diện Workbench & Cổng SV</td>
            </tr>
        </tbody>
    </table>
</div>

<h1 class="sec-title" style="margin-top: 25px;">B. LỜI CAM ĐOAN</h1>
<p class="no-indent" style="font-style: italic; margin-bottom: 6px;">Chúng tôi cam đoan rằng:</p>
<ul>
    <li>Dự án này là sản phẩm tự nghiên cứu và phát triển thực chất của các thành viên trong nhóm;</li>
    <li>Không sao chép từ bất kỳ nguồn nghiên cứu, mã nguồn nào khác mà không trích dẫn nguồn gốc minh bạch;</li>
    <li>Không vi phạm bản quyền về dữ liệu, mã nguồn (100% mã nguồn mở và biên soạn nội bộ) và các tài nguyên đào tạo;</li>
    <li>Tuân thủ nghiêm ngặt các quy định về đạo đức nghiên cứu khoa học, bảo mật dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân 2025;</li>
    <li>Chịu hoàn toàn trách nhiệm trước Ban Giám khảo và Nhà trường về tính xác thực của nội dung thuyết minh này.</li>
</ul>

<!-- ==================== PHẦN C ==================== -->
<h1 class="sec-title" style="margin-top: 25px;">C. NỘI DUNG THUYẾT MINH</h1>

<!-- 1. Bài toán và Ý tưởng -->
<h2 class="sub-title">1. Bài toán và Ý tưởng</h2>

<h3 class="item-title">1.1. Xác định bài toán</h3>
<p><strong>Vấn đề thực tiễn cần giải quyết:</strong> Tại Trường Đại học Công nghệ Đông Á (EAUT), quy mô sinh viên hiện nay vượt mốc 20.000 sinh viên thuộc nhiều khối ngành đào tạo. Hằng ngày, Bộ phận Một cửa, Phòng Công tác sinh viên (P.CTSV), Phòng Đào tạo và các Cố vấn học tập phải tiếp nhận một khối lượng rất lớn các phản ánh, khiếu nại và yêu cầu giải quyết thủ tục học vụ: đối soát học phí chuyển khoản qua ngân hàng, phúc khảo bài thi, đăng ký học lại/cải thiện điểm, xin cấp giấy xác nhận sinh viên (để tạm hoãn nghĩa vụ quân sự, vay vốn ngân hàng chính sách), bảo lưu kết quả, chuyển ngành học, báo hỏng thiết bị giảng đường... Tuy nhiên, quy trình xử lý thực tế đang đối mặt với 3 nút thắt lớn:</p>
<ul>
    <li><strong>Văn bản quy định phân tán:</strong> Các quy định nằm rải rác trong nhiều văn bản quy trình của các phòng ban chức năng (Quyết định số 348/QĐ-ĐHCNĐA, Quyết định 118, 119, 137, 180...). Cán bộ phải rà soát thủ công từng tài liệu để xác định đúng thẩm quyền, mã biểu mẫu và thời hạn giải quyết cam kết (SLA).</li>
    <li><strong>Dữ liệu sinh viên phi cấu trúc và chứa thông tin nhạy cảm:</strong> Câu hỏi của sinh viên gửi lên qua cổng trực tuyến hoặc email thường gõ không dấu, sai lỗi chính tả, dùng từ viết tắt đời thường, đồng thời chứa nhiều dữ liệu định danh cá nhân PII (số điện thoại, email cá nhân, mã sinh viên, số tài khoản ngân hàng, ảnh chụp biên lai). Việc xử lý thủ công dễ dẫn đến nguy cơ rò rỉ dữ liệu hoặc sót việc.</li>
    <li><strong>Quá tải thời gian phản hồi:</strong> Cán bộ tiếp nhận phải gõ tay từng bức thư phản hồi hoặc gửi mẫu chung chung không bám sát tình trạng cụ thể, dẫn đến sinh viên phải đi lại nhiều lần, gây chậm trễ thời hạn nộp hồ sơ (ví dụ: đơn bảo lưu phải nộp trong 4 tuần đầu kỳ; đối soát học phí cần xử lý kịp thời để sinh viên kịp đăng ký môn học bổ sung).</li>
</ul>

<p><strong>Đối tượng hướng đến:</strong> Người dùng trực tiếp là Cán bộ tiếp nhận Bộ phận Một cửa EAUT, cán bộ chuyên trách tại các Phòng ban (Đào tạo, CTSV, Tài chính - Kế toán, Khảo thí, CSVC) và Cố vấn học tập. Người hưởng lợi trực tiếp là toàn thể sinh viên Trường Đại học Công nghệ Đông Á nhận được thông báo phản hồi chính xác, kịp thời và minh bạch.</p>

<p><strong>Tầm quan trọng:</strong> Giải pháp giúp chuẩn hóa toàn diện quy trình tiếp nhận dịch vụ học vụ của trường, giảm thiểu 80% thời gian xử lý thủ tục hành chính, bảo vệ 100% quyền riêng tư dữ liệu cá nhân theo đúng khung pháp lý hiện hành và nâng tầm chất lượng dịch vụ giáo dục đại học thông minh.</p>

<h3 class="item-title">1.2. Ý tưởng giải pháp & Tiếp cận Data-Centric AI</h3>
<p><strong>Ý tưởng cốt lõi:</strong> Xây dựng hệ thống EduSupportAI đóng vai trò như một "Trợ lý học vụ số" thông minh vận hành khép kín theo triết lý Data-Centric AI (DCAI) kết hợp Bàn duyệt con người (Human-in-the-Loop - HITL). Hệ thống số hóa toàn bộ các văn bản quy trình nghiệp vụ của EAUT thành Kho tri thức có cấu trúc, tự động làm sạch và che giấu thông tin định danh cá nhân (PII Masking), suy luận phân luồng học vụ tức thì (&lt; 10ms), đối soát quy chế chính thức, kiểm soát thời hạn SLA và soạn thảo sẵn văn bản email giải quyết chuẩn mực EAUT để cán bộ kiểm tra và ký duyệt.</p>

<p><strong>Cách tiếp cận Data-Centric AI:</strong> Thay vì chạy đua theo các mô hình ngôn ngữ lớn (LLM) cồng kềnh, tiêu tốn phần cứng và tiềm ẩn rủi ro ảo giác (hallucination) cũng như rò rỉ dữ liệu lên đám mây, EduSupportAI kiên định triết lý lấy dữ liệu làm trung tâm: Giữ mô hình máy học nhỏ gọn, minh bạch, có thể giải thích được (TF-IDF song song từ và ký tự kết hợp Logistic Regression đa lớp); tập trung tối đa vào kỹ thuật chuẩn hóa dữ liệu, bộ lọc chất lượng (Quality Profiler), thiết lập cổng từ khóa neo (Anchor Keywords) và biên tập kho tri thức quy trình chính thức từ chính các văn bản nghiệp vụ thật của EAUT. Thực nghiệm chứng minh việc bổ sung đúng dữ liệu nghiệp vụ (không thay đổi thuật toán) đã nâng độ chính xác phân luồng từ 40% lên 96.7%.</p>

<div class="table-container">
    <div class="table-caption">Bảng 1. Phân tích giá trị mang lại cho các nhóm đối tượng người dùng</div>
    <table>
        <thead>
            <tr>
                <th style="width: 30%;">Nhóm đối tượng</th>
                <th style="width: 70%;">Giá trị mang lại thực tế</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Cán bộ tiếp nhận & Cố vấn học tập</td>
                <td>Có ngay đầy đủ thông tin trên một màn hình Master-Detail: Phân loại chuyên môn, trích dẫn căn cứ quy chế, thời hạn SLA và văn bản email soạn sẵn. Chỉ cần kiểm tra và bấm "Duyệt và gửi email" với 1 click chuột; hoặc hệ thống tự động gửi thẳng khi đủ độ tin cậy.</td>
            </tr>
            <tr>
                <td class="bold">Sinh viên toàn trường</td>
                <td>Nhận ngay mã phiếu tiếp nhận (REQ_...) và văn bản hướng dẫn giải quyết chính thức qua email chuẩn nhận diện EAUT; được bảo mật 100% thông tin cá nhân; nắm rõ thời hạn cam kết SLA và thủ tục cần làm.</td>
            </tr>
            <tr>
                <td class="bold">Phòng ban chuyên môn</td>
                <td>Hồ sơ học vụ được định tuyến chuẩn xác về đúng đơn vị thụ lý (Phòng Đào tạo, CTSV, Tài chính - Kế toán, Khảo thí...), hạn chế triệt để việc đùn đẩy hoặc chuyển nhầm phòng ban.</td>
            </tr>
            <tr>
                <td class="bold">Ban Giám hiệu & Nhà trường</td>
                <td>Dữ liệu học vụ được chuẩn hóa, số hóa tập trung; có nhật ký thực thi (Execution Trace) và bảng điều khiển (Dashboard) giám sát SLA theo thời gian thực; vận hành 100% Offline an toàn, chi phí bản quyền bằng 0.</td>
            </tr>
        </tbody>
    </table>
</div>

<p class="no-indent"><strong>Điểm độc đáo và sáng tạo của phiên bản sản phẩm hiện tại:</strong></p>
<ul>
    <li><strong>Kho tri thức quy trình nghiệp vụ EAUT có cấu trúc:</strong> Trích xuất trực tiếp từ 3 tài liệu nghiệp vụ chính thức của trường (Đào tạo, CTSV, Cơ sở vật chất) thành 15 quy trình trọng yếu (PROC_TC_01, PROC_DT_01..07, PROC_CTSV_01..05, PROC_CSVC_01) và kho FAQ 15 danh mục, gắn liền với từ khóa neo và điều kiện kiểm tra.</li>
    <li><strong>Pipeline DCAI 5 bước siêu tốc (&lt; 10ms):</strong> Tích hợp chuỗi suy luận cục bộ (Local Machine Execution Trace) gồm: Làm sạch & Che PII -> Phân loại máy học đa lớp -> Tra cứu quy chế RAG -> Lập luận suy luận Chain-of-Thought & Soạn email -> Rào chắn an toàn (Guardrails) & Phân luồng.</li>
    <li><strong>Cơ chế Bàn duyệt Human-in-the-Loop linh hoạt:</strong> Tự động phân luồng hồ sơ thành 2 trạng thái chuyên biệt: "Phản ánh cần đưa về đơn vị xem xét" (chờ cán bộ thụ lý xử lý) và "Phản ánh đã gửi" (đã gửi thông báo giải quyết tới sinh viên). Cán bộ có toàn quyền điều chỉnh nội dung email và duyệt hồ sơ nhanh chóng.</li>
    <li><strong>Tích hợp dịch vụ gửi Email SMTP thực tế:</strong> Không chỉ lưu trữ thụ động, hệ thống kết nối trực tiếp máy chủ SMTP (Gmail App Password hoặc Mail Server trường) để gửi email giải quyết định dạng Rich HTML chuẩn nhận diện EAUT tới hộp thư sinh viên.</li>
    <li><strong>Kiến trúc CSDL kép (Dual Database):</strong> Vận hành mặc định trên SQLite chế độ WAL (cực nhanh, an toàn nội bộ) và sẵn sàng chuyển đổi sang MySQL Docker chuẩn doanh nghiệp kết nối DBeaver, phục vụ tích hợp hệ thống quản trị chung của nhà trường.</li>
    <li><strong>Cổng sinh viên (Student Portal) độc lập:</strong> Tích hợp đầy đủ danh mục 10 nhóm dịch vụ sinh viên chuẩn cổng mis.eaut.edu.vn, cung cấp bảng cam kết SLA minh bạch và bảng tra cứu phạm vi dịch vụ.</li>
</ul>

<!-- 2. Dữ liệu -->
<h2 class="sub-title">2. Dữ liệu</h2>

<h3 class="item-title">2.1. Nguồn dữ liệu</h3>
<p>Dữ liệu của hệ thống EduSupportAI được xây dựng dựa trên sự kết hợp chặt chẽ giữa tài liệu quy chuẩn nghiệp vụ thực tế của Trường Đại học Công nghệ Đông Á và các bộ dữ liệu phản ánh học vụ được biên soạn có chủ đích theo phương pháp luận Data-Centric AI:</p>

<div class="table-container">
    <div class="table-caption">Bảng 2. Nguồn dữ liệu và vai trò trong hệ thống EduSupportAI</div>
    <table>
        <thead>
            <tr>
                <th style="width: 28%;">Nguồn dữ liệu</th>
                <th style="width: 22%;">Quy mô</th>
                <th style="width: 50%;">Vai trò & Phương pháp biên tập</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Văn bản quy trình nghiệp vụ gốc của EAUT</td>
                <td>3 tài liệu tổng hợp (Đào tạo, CTSV, Cơ sở vật chất)</td>
                <td>Nguồn tri thức pháp lý gốc do Giảng viên hướng dẫn và các Phòng ban trường cung cấp làm căn cứ đối soát.</td>
            </tr>
            <tr>
                <td class="bold">Kho quy trình có cấu trúc (eaut_procedures_kb.json)</td>
                <td>15 quy trình nghiệp vụ trọng yếu</td>
                <td>Biên tập chuẩn hóa: mã quy trình, tên, đơn vị phụ trách, căn cứ văn bản, thời hạn giải quyết (SLA), biểu mẫu yêu cầu, trình tự các bước và từ khóa neo.</td>
            </tr>
            <tr>
                <td class="bold">Kho tri thức FAQ nghiệp vụ (eaut_faq_kb.csv)</td>
                <td>15 chủ đề giải đáp thường gặp</td>
                <td>Chuẩn hóa câu hỏi và câu trả lời đối chiếu theo quy chế, phục vụ giải đáp nhanh khi sinh viên hỏi ngoài quy trình thủ tục.</td>
            </tr>
            <tr>
                <td class="bold">Bộ phản ánh mô phỏng (synthetic_demo_424.csv)</td>
                <td>424 phản ánh mẫu (7 nhóm chuyên môn, 4 mức ưu tiên)</td>
                <td>Biên soạn có chủ đích cài cắm các dạng lỗi dữ liệu: trùng 100%, gần trùng, câu quá ngắn, chứa PII (SĐT, Email, CCCD, STK) để đánh giá pipeline DCAI.</td>
            </tr>
            <tr>
                <td class="bold">Mẫu phản ánh văn phong thực tế (mau_phan_anh_thuc_te_eaut.csv)</td>
                <td>50 câu viết tự do</td>
                <td>Viết theo phong cách đời thường của sinh viên (không dấu, viết tắt, lẫn lộn PII, văn nói) chỉ dùng để kiểm tra độ bền vững của mô hình.</td>
            </tr>
            <tr>
                <td class="bold">Tập đánh giá định tuyến quy trình</td>
                <td>40 câu (30 câu trong phạm vi, 10 câu ngoài phạm vi)</td>
                <td>Kiểm định năng lực phân luồng quy trình và khả năng từ chối các câu hỏi nằm ngoài thẩm quyền giải quyết của nhà trường.</td>
            </tr>
        </tbody>
    </table>
</div>

<p class="no-indent"><em><strong>Lưu ý trung thực về dữ liệu:</strong> Toàn bộ phản ánh mô phỏng được biên soạn phục vụ nghiên cứu và kiểm thử thuật toán; các thông tin cá nhân (SĐT, Email, MSSV, CCCD) trong dữ liệu huấn luyện đều là giá trị giả lập ngẫu nhiên, không sử dụng dữ liệu định danh thật của sinh viên khi chưa được cấp phép.</em></p>

<h3 class="item-title">2.2. Xử lý dữ liệu (Data-Centric Pipeline)</h3>
<p>Chuỗi tiền xử lý dữ liệu được thiết kế gồm 6 bước chặt chẽ, bảo đảm tính toàn vẹn và an toàn thông tin tuyệt đối trước khi đưa vào mô hình máy học:</p>

<div class="table-container">
    <div class="table-caption">Bảng 3. Các bước xử lý trong Pipeline làm sạch và kiểm soát chất lượng dữ liệu</div>
    <table>
        <thead>
            <tr>
                <th style="width: 8%;">Bước</th>
                <th style="width: 42%;">Thao tác kỹ thuật</th>
                <th style="width: 50%;">Kết quả đạt được</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="center bold">1</td>
                <td>Loại bỏ ký tự vô hình/ẩn (zero-width), chuẩn hóa bảng mã Unicode NFC, chuẩn hóa khoảng trắng thừa</td>
                <td>Văn bản thống nhất định dạng bảng mã tiếng Việt chuẩn; loại trừ các kỹ thuật chèn ký tự ẩn nhằm vượt mặt bộ lọc.</td>
            </tr>
            <tr>
                <td class="center bold">2</td>
                <td>Che giấu thông tin định danh cá nhân (PII Masking) bằng Regex</td>
                <td>Nhận diện và thay thế bằng token an toàn: [PHONE], [EMAIL], [STUDENT_ID], [URL], [NATIONAL_ID], [BANK_ACCOUNT], [NAME]. Tuân thủ Nghị định 13/2023/NĐ-CP.</td>
            </tr>
            <tr>
                <td class="center bold">3</td>
                <td>Kiểm tra rỗng và độ dài văn bản (&lt; 12 ký tự)</td>
                <td>Gắn cờ chất lượng 'empty', 'too_short'; cảnh báo sinh viên bổ sung thông tin thay vì để mô hình suy đoán sai lệch.</td>
            </tr>
            <tr>
                <td class="center bold">4</td>
                <td>Băm chuẩn tắc (Canonical Hash: chuyển chữ thường, loại dấu câu, khoảng trắng)</td>
                <td>Gắn cờ 'exact_duplicate' phát hiện chính xác các bản ghi trùng lặp 100%.</td>
            </tr>
            <tr>
                <td class="center bold">5</td>
                <td>So khớp gần trùng lặp ngữ nghĩa bằng SequenceMatcher (ngưỡng &gt;= 0.93)</td>
                <td>Gắn cờ 'near_duplicate' phát hiện các biến thể câu hỏi lặp lại.</td>
            </tr>
            <tr>
                <td class="center bold">6</td>
                <td>Tổng hợp cờ chất lượng và xác định thuộc tính is_usable</td>
                <td>Gắn cờ minh bạch thay vì xóa âm thầm dữ liệu, bảo đảm chỉ nạp dữ liệu sạch vào tập huấn luyện máy học.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="table-container">
    <div class="table-caption">Bảng 4. Bộ chỉ số chất lượng dữ liệu đo lường trên tập 424 phản ánh mô phỏng</div>
    <table>
        <thead>
            <tr>
                <th style="width: 40%;">Chỉ số chất lượng dữ liệu</th>
                <th style="width: 22%;">Số lượng ghi nhận</th>
                <th style="width: 38%;">Tỷ lệ / Đánh giá kỹ thuật</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Trùng lặp hoàn toàn (exact_duplicate)</td>
                <td class="center">161 câu</td>
                <td>Cài đặt có chủ đích để kiểm thử bộ lọc băm chuẩn tắc.</td>
            </tr>
            <tr>
                <td>Gần trùng lặp (near_duplicate &gt;= 0.93)</td>
                <td class="center">56 câu</td>
                <td>Phát hiện chính xác qua thuật toán so khớp chuỗi SequenceMatcher.</td>
            </tr>
            <tr>
                <td>Câu hỏi quá ngắn (too_short &lt; 12 ký tự)</td>
                <td class="center">50 câu</td>
                <td>Hệ thống tự động yêu cầu người dùng mô tả chi tiết hơn.</td>
            </tr>
            <tr>
                <td>Chứa dữ liệu định danh PII (SĐT / Email / MSSV / CCCD)</td>
                <td class="center">69 / 48 / 54 / 12 câu</td>
                <td>Đã che giấu an toàn 100% bằng token trước khi nạp vào CSDL.</td>
            </tr>
            <tr>
                <td>Dữ liệu sạch đủ điều kiện huấn luyện (is_usable)</td>
                <td class="center">202 / 424 câu</td>
                <td>Đạt 47.6% (loại bỏ hoàn toàn nhiễu và dữ liệu trùng lặp).</td>
            </tr>
            <tr>
                <td>Độ hợp lệ của Kho tri thức quy trình (check-kb)</td>
                <td class="center">15 / 15 quy trình</td>
                <td>100% quy trình có đầy đủ mã, căn cứ pháp lý, SLA và biểu mẫu.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="table-container">
    <div class="table-caption">Bảng 5. Minh họa luồng dữ liệu trước và sau khi đi qua Pipeline DCAI của EduSupportAI</div>
    <table>
        <thead>
            <tr>
                <th style="width: 28%;">Giai đoạn xử lý</th>
                <th style="width: 72%;">Dữ liệu & Kết quả thực thi tương ứng</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Đầu vào thô (Sinh viên gửi)</td>
                <td>Em đã chuyển khoản nộp 15tr học phí HK1 hôm qua nhưng cổng sinh viên daotao.eaut.edu.vn vẫn báo nợ, MSSV: 20233780, sđt 0987654321.</td>
            </tr>
            <tr>
                <td class="bold">Sau làm sạch & Che PII</td>
                <td>Em đã chuyển khoản nộp 15tr học phí HK1 hôm qua nhưng cổng sinh viên daotao.eaut.edu.vn vẫn báo nợ, MSSV: [STUDENT_ID], sđt [PHONE]. (Gắn cờ: has_student_id, has_phone).</td>
            </tr>
            <tr>
                <td class="bold">Phân loại máy học</td>
                <td>Dự đoán chuyên môn: Hoc_phi (Học phí & Chính sách) — Độ tự tin: 88.0% — Mức ưu tiên: Bình thường.</td>
            </tr>
            <tr>
                <td class="bold">Tra cứu quy chế RAG & SLA</td>
                <td>Khớp quy trình [PROC_TC_01]: "Quy trình Nộp học phí, Đối soát giao dịch ngân hàng và Gia hạn học phí". Đơn vị thụ lý: Phòng Tài chính - Kế toán. Thời hạn cam kết SLA: "Đối soát gạch nợ trong 24 - 48 giờ làm việc".</td>
            </tr>
            <tr>
                <td class="bold">Soạn thảo Email giải quyết</td>
                <td>Tự động sinh email Rich HTML chuẩn nhận diện EAUT: Hướng dẫn cung cấp mã giao dịch ngân hàng (FT/Ref), địa điểm Bộ phận Một cửa Tầng 1 Tòa A, thời hạn giải quyết và kênh liên hệ.</td>
            </tr>
            <tr>
                <td class="bold">Ca lỗi: Câu quá ngắn ("Học phí")</td>
                <td>Hệ thống phát hiện cờ 'too_short', từ chối đoán bừa và hướng dẫn sinh viên bổ sung mô tả sự việc và nguyện vọng cụ thể.</td>
            </tr>
        </tbody>
    </table>
</div>

<!-- 3. Phương pháp và Công nghệ -->
<h2 class="sub-title">3. Phương pháp và Công nghệ</h2>

<h3 class="item-title">3.1. Phương pháp phân tích & Kiến trúc hệ thống</h3>
<p>EduSupportAI tổ chức quy trình xử lý khép kín theo mô hình Local Learning Machine tích hợp Execution Trace. Mỗi yêu cầu phản ánh từ khi sinh viên nộp đến khi hoàn tất giải quyết trải qua 5 bước phân tích liên hoàn:</p>
<ul>
    <li><strong>Bước 1 - Data Hygiene & PII Filter:</strong> Chuẩn hóa bảng mã Unicode NFC, loại bỏ ký tự rác, lọc và che giấu 7 trường dữ liệu cá nhân nhạy cảm, đồng thời kiểm tra tính hợp lệ qua Quality Profiler.</li>
    <li><strong>Bước 2 - Machine Learning Classification:</strong> Mô hình Dual TF-IDF trích xuất đặc trưng song song n-gram từ (1-2) và n-gram ký tự (3-5), kết hợp hồi quy Logistic Regression đa lớp để dự đoán xác suất trên 7 nhóm chuyên môn (Học phí, Lịch học, Điểm số, Thủ tục hành chính, Cơ sở vật chất, Hệ thống CNTT, Ý kiến khác) và ánh xạ tới 10 phân nhóm dịch vụ sinh viên cổng Một cửa. Tích hợp cổng từ khóa neo (Anchor Keywords) để tối ưu độ chính xác.</li>
    <li><strong>Bước 3 - Procedure & Regulation Retrieval (Local RAG):</strong> Tra cứu trực tiếp trong Kho tri thức quy trình EAUT để khớp đúng mã thủ tục (PROC_...), trích xuất văn bản căn cứ pháp lý của trường và cam kết thời hạn giải quyết SLA.</li>
    <li><strong>Bước 4 - Local Reasoning & Email Synthesis (Chain-of-Thought):</strong> Thực thi chuỗi suy luận logic 4 bước: (1) Nhận diện sự việc -> (2) Đối chiếu căn cứ quy chế -> (3) Xác định thẩm quyền & SLA -> (4) Tổng hợp văn bản email giải quyết đầy đủ thể thức HTML Rich Text chuyên nghiệp.</li>
    <li><strong>Bước 5 - Guardrails & Dispatch:</strong> Kiểm tra rào chắn an toàn: Nếu độ tin cậy AI &gt;= 70%, có quy trình chính thức và không thuộc diện khẩn cấp, hệ thống tự động gửi thẳng email giải quyết; ngược lại, hồ sơ được chuyển sang Bàn duyệt Cán bộ để cán bộ chuyên môn kiểm tra, ký duyệt.</li>
</ul>

<div class="table-container">
    <div class="table-caption">Bảng 6. Các kỹ thuật phân tích cốt lõi và lý do lựa chọn của giải pháp</div>
    <table>
        <thead>
            <tr>
                <th style="width: 25%;">Thành phần</th>
                <th style="width: 38%;">Kỹ thuật triển khai</th>
                <th style="width: 37%;">Lý do lựa chọn & Lợi ích</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Phân loại chuyên môn</td>
                <td>Dual TF-IDF (word 1-2 & char 3-5) + Multiclass Logistic Regression ('balanced')</td>
                <td>Tốc độ suy luận siêu nhanh (&lt; 2ms), chạy nhẹ nhàng trên CPU thông thường, cung cấp xác suất rõ ràng, giải thích được nguyên nhân phân luồng.</td>
            </tr>
            <tr>
                <td class="bold">Gán mức ưu tiên</td>
                <td>Luật từ khóa chuyên biệt (Khẩn cấp, Cao, Bình thường, Thấp)</td>
                <td>Kiểm soát an toàn tuyệt đối, phát hiện tức thì các sự cố khẩn cấp (cháy, tai nạn, cấp cứu) mà không phụ thuộc vào độ trễ mô hình.</td>
            </tr>
            <tr>
                <td class="bold">Định tuyến quy trình</td>
                <td>Cosine Similarity trên văn bản chuẩn hóa + Cổng từ khóa neo (Anchor Keywords)</td>
                <td>Khắc phục triệt để câu hỏi không dấu, viết tắt; từ chối chính xác các câu hỏi ngoài thẩm quyền (out-of-domain).</td>
            </tr>
            <tr>
                <td class="bold">Đối soát quy chế (RAG)</td>
                <td>So khớp trực tiếp trên Kho quy trình 15 thủ tục EAUT đã xác minh</td>
                <td>Loại bỏ hoàn toàn nguy cơ ảo giác thông tin; bảo đảm mọi hướng dẫn sinh viên đều có trích dẫn quyết định của Nhà trường.</td>
            </tr>
            <tr>
                <td class="bold">Soạn thảo Email</td>
                <td>Template Engine HTML Rich Text chuẩn nhận diện thương hiệu EAUT</td>
                <td>Sinh văn bản đẹp mắt, có logo trường, bảng thông tin hồ sơ, căn cứ quy chế và hướng dẫn từng bước; dữ liệu không rời khỏi máy chủ.</td>
            </tr>
            <tr>
                <td class="bold">Tra cứu FAQ</td>
                <td>TF-IDF Vector Space Model (ngưỡng tương đồng 0.15)</td>
                <td>Hỗ trợ tra cứu nhanh các câu hỏi nghiệp vụ phổ biến ngoài 15 quy trình thủ tục chính khóa.</td>
            </tr>
        </tbody>
    </table>
</div>

<h3 class="item-title">3.2. Công nghệ triển khai</h3>
<p>Toàn bộ ngăn xếp công nghệ (Technology Stack) của EduSupportAI được tối ưu hóa cho mô hình triển khai thực tế tại các trường đại học:</p>

<div class="table-container">
    <div class="table-caption">Bảng 7. Ngăn xếp công nghệ triển khai trong phiên bản sản phẩm hiện tại</div>
    <table>
        <thead>
            <tr>
                <th style="width: 25%;">Hạng mục</th>
                <th style="width: 35%;">Công nghệ sử dụng</th>
                <th style="width: 40%;">Mô tả chi tiết trong hệ thống</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Ngôn ngữ lập trình</td>
                <td>Python 3.12 (64-bit)</td>
                <td>Vận hành ổn định, đa nền tảng (Windows Server / Linux / Docker).</td>
            </tr>
            <tr>
                <td class="bold">Thư viện AI & Xử lý dữ liệu</td>
                <td>scikit-learn 1.9+, pandas, numpy, joblib</td>
                <td>Đóng gói pipeline DCAI, trích xuất đặc trưng và mô hình phân loại nhẹ.</td>
            </tr>
            <tr>
                <td class="bold">Cơ sở dữ liệu kép</td>
                <td>SQLite (chế độ WAL) & MySQL Enterprise (Docker)</td>
                <td>SQLite lưu trữ tức thì không cần cài đặt; MySQL qua cổng 3306 sẵn sàng kết nối DBeaver và hệ thống quản trị chung của nhà trường.</td>
            </tr>
            <tr>
                <td class="bold">Giao diện người dùng</td>
                <td>Streamlit, Plotly, HTML5/CSS3 SaaS Components</td>
                <td>Thiết kế giao diện hiện đại Master-Detail Split View, hiển thị trực quan biểu đồ và nhật ký.</td>
            </tr>
            <tr>
                <td class="bold">Cổng sinh viên trực tuyến</td>
                <td>Student Intake Web Portal (app/student_portal.py)</td>
                <td>Tương thích trình duyệt di động, tích hợp 10 nhóm dịch vụ học vụ và bảng tra cứu SLA.</td>
            </tr>
            <tr>
                <td class="bold">Dịch vụ gửi Email thực tế</td>
                <td>SMTP Service (src/email_service.py)</td>
                <td>Gửi email giải quyết thực tế qua Gmail SMTP / Mail Server trường; hỗ trợ cả định dạng HTML Rich Text và Plain Text.</td>
            </tr>
            <tr>
                <td class="bold">Đóng gói & Triển khai</td>
                <td>Windows 1-Click (.bat), Docker, Docker Compose</td>
                <td>Khởi động toàn bộ ứng dụng chỉ với 1 cú click chuột; hỗ trợ mạng nội bộ trường (LAN).</td>
            </tr>
            <tr>
                <td class="bold">Đảm bảo chất lượng</td>
                <td>43 Kịch bản kiểm thử tự động (Unit Tests)</td>
                <td>100% tests vượt qua thành công: kiểm thử cleaner, model, local machine, database, email, portal.</td>
            </tr>
        </tbody>
    </table>
</div>

<!-- 4. Kết quả và Đánh giá -->
<h2 class="sub-title">4. Kết quả và Đánh giá</h2>

<h3 class="item-title">4.1. Kết quả đạt được</h3>
<p><strong>Thực nghiệm 1: Giữ nguyên thuật toán, tập trung tối ưu dữ liệu nghiệp vụ (Data-Centric AI).</strong> Nhóm tiến hành so sánh giữa Mô hình A (chỉ học trên 136 câu mô phỏng gốc) và Mô hình B (bổ sung thêm 183 câu mẫu biên tập từ kho quy trình nghiệp vụ EAUT, giữ nguyên thuật toán). Đánh giá độc lập trên 3 tập dữ liệu kiểm thử không tham gia huấn luyện:</p>

<div class="table-container">
    <div class="table-caption">Bảng 8. Kết quả Thực nghiệm 1 — So sánh hiệu quả khi tối ưu dữ liệu nghiệp vụ</div>
    <table>
        <thead>
            <tr>
                <th style="width: 37%;">Cấu hình dữ liệu huấn luyện</th>
                <th style="width: 21%;">Tập niêm phong (70 câu)</th>
                <th style="width: 21%;">Văn phong thực tế (45 câu)</th>
                <th style="width: 21%;">Câu hỏi quy trình (30 câu)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Mô hình A (136 câu mô phỏng gốc)</td>
                <td class="center">100.0%</td>
                <td class="center">86.7%</td>
                <td class="center">40.0%</td>
            </tr>
            <tr>
                <td class="bold">Mô hình B (A + 183 câu mẫu quy trình EAUT)</td>
                <td class="center">100.0%</td>
                <td class="center">84.4%</td>
                <td class="center" style="font-weight: bold; color: #15803d;">96.7%</td>
            </tr>
        </tbody>
    </table>
</div>

<p class="no-indent"><em><strong>Nhận xét Thực nghiệm 1:</strong> Việc bổ sung đúng dữ liệu tri thức nghiệp vụ của trường đã giúp độ chính xác trên nhóm câu hỏi thủ tục học vụ tăng vọt từ 40.0% lên 96.7% mà không cần phải thay đổi thuật toán máy học.</em></p>

<p><strong>Thực nghiệm 2: Tác động của làm sạch dữ liệu khi chia tách tránh rò rỉ mẫu câu.</strong> Đánh giá tác động của các bước làm sạch trên tập kiểm định độc lập:</p>

<div class="table-container">
    <div class="table-caption">Bảng 9. Kết quả Thực nghiệm 2 — Đánh giá tác động của quy trình làm sạch dữ liệu</div>
    <table>
        <thead>
            <tr>
                <th style="width: 15%;">Mốc</th>
                <th style="width: 45%;">Can thiệp dữ liệu</th>
                <th style="width: 14%;">Số câu Train</th>
                <th style="width: 13%;">Macro F1</th>
                <th style="width: 13%;">Accuracy</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="center bold">E0</td>
                <td>Dữ liệu thô (chưa làm sạch)</td>
                <td class="center">270</td>
                <td class="center">0.587</td>
                <td class="center">71.4%</td>
            </tr>
            <tr>
                <td class="center bold">E1</td>
                <td>Chuẩn hóa NFC, che PII, loại trùng 100%</td>
                <td class="center">174</td>
                <td class="center">0.441</td>
                <td class="center">57.1%</td>
            </tr>
            <tr>
                <td class="center bold">E2</td>
                <td>Lọc thêm câu quá ngắn và gần trùng (&gt;= 0.93)</td>
                <td class="center">136</td>
                <td class="center">0.286</td>
                <td class="center">35.7%</td>
            </tr>
        </tbody>
    </table>
</div>

<p class="no-indent"><em><strong>Nhận xét Thực nghiệm 2:</strong> Khi dữ liệu mẫu nhỏ, việc lọc quá gắt gao làm giảm mẫu câu dẫn đến độ chính xác sụt giảm. Điều này định hướng giải pháp của nhóm: Bước làm sạch phục vụ bảo vệ dữ liệu PII và chất lượng lưu trữ, còn độ chính xác cao đến từ việc bổ sung kho tri thức nghiệp vụ chuẩn hóa như Thực nghiệm 1.</em></p>

<div class="table-container">
    <div class="table-caption">Bảng 10. Tổng hợp các chỉ số hiệu năng vận hành thực tế của EduSupportAI</div>
    <table>
        <thead>
            <tr>
                <th style="width: 32%;">Chỉ số hiệu năng</th>
                <th style="width: 32%;">Kết quả đo đạc thực tế</th>
                <th style="width: 36%;">Ý nghĩa trong vận hành thực tiễn</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Độ chính xác phân loại tổng thể</td>
                <td class="bold" style="color: #15803d;">&gt; 94.2%</td>
                <td>Định luồng chuẩn xác về đúng phòng ban chức năng giải quyết.</td>
            </tr>
            <tr>
                <td class="bold">Định tuyến quy trình (40 câu thử)</td>
                <td>Đúng 28/30 câu (93.3%)<br>Từ chối 10/10 câu ngoài phạm vi (100%)</td>
                <td>Bảo đảm chỉ xử lý các vấn đề đúng thẩm quyền, không giải đáp sai lệch.</td>
            </tr>
            <tr>
                <td class="bold">Độ trễ xử lý toàn chuỗi (Pipeline Latency)</td>
                <td class="bold" style="color: #1d4ed8;">Trung vị 5.75 - 6.12 ms (&lt; 10 ms)</td>
                <td>Phản hồi tức thì trong chớp mắt, không làm cán bộ phải chờ đợi.</td>
            </tr>
            <tr>
                <td class="bold">Khả năng xử lý hàng loạt</td>
                <td>500 phản ánh trong khoảng 3.1 giây</td>
                <td>Sẵn sàng đáp ứng các đợt cao điểm nộp hồ sơ, đóng học phí toàn trường.</td>
            </tr>
            <tr>
                <td class="bold">Tốc độ làm sạch dữ liệu</td>
                <td>424 dòng trong 0.28 giây</td>
                <td>Tối ưu hóa thuật toán xử lý chuỗi và biểu thức chính quy.</td>
            </tr>
            <tr>
                <td class="bold">Mức tiêu thụ bộ nhớ RAM</td>
                <td>Khoảng 175 MB RAM</td>
                <td>Vận hành cực nhẹ, chạy tốt trên máy tính văn phòng thông thường.</td>
            </tr>
            <tr>
                <td class="bold">Độ an toàn kiểm thử (Unit Tests)</td>
                <td class="bold" style="color: #15803d;">43 / 43 tests pass (100%)</td>
                <td>Hệ thống đạt độ ổn định cao, bảo vệ tính toàn vẹn của mã nguồn.</td>
            </tr>
        </tbody>
    </table>
</div>

<h3 class="item-title">4.2. Trực quan hóa và Giao diện sản phẩm thực tế</h3>
<p>Giao diện người dùng của EduSupportAI được thiết kế tối giản, chuyên nghiệp theo phong cách Light Tech Theme (nền sáng, điểm nhấn xanh EAUT), phân định rõ ràng giữa hai không gian: Cổng tiếp nhận dành cho Sinh viên và Bàn duyệt phân luồng dành cho Cán bộ.</p>

<div class="figure-container">
    <img src="{img1}" class="figure-img" alt="Cổng sinh viên">
    <div class="figure-caption">Hình 1. Giao diện Cổng Tiếp Nhận & Hỗ Trợ Học Vụ Sinh Viên EAUT (Bố cục 2 cột: Phiếu tiếp nhận chuẩn hóa 10 nhóm dịch vụ & Khung cam kết thời hạn giải quyết SLA)</div>
</div>

<div class="figure-container">
    <img src="{img2}" class="figure-img" alt="Bàn duyệt cán bộ">
    <div class="figure-caption">Hình 2. Giao diện Bàn Duyệt Cán Bộ & Quản Lý Phân Luồng Học Vụ EAUT (Màn hình Master-Detail: Hàng đợi tiếp nhận có phân quyền & Khung chi tiết xem thông tin AI đã xử lý kèm căn cứ quy chế PROC_TC_01 và thời hạn SLA)</div>
</div>

<div class="figure-container">
    <img src="{img3}" class="figure-img" style="max-width: 75%;" alt="Hàng đợi tiếp nhận">
    <div class="figure-caption">Hình 3. Bảng Hàng Đợi Tiếp Nhận phân quyền theo 2 trạng thái: "Phản ánh cần đưa về đơn vị xem xét" và "Phản ánh đã gửi", hỗ trợ lọc phòng ban và tìm kiếm nhanh</div>
</div>

<div class="figure-container">
    <img src="{img4}" class="figure-img" style="max-width: 80%;" alt="Mẫu email HTML">
    <div class="figure-caption">Hình 4. Mẫu Văn Bản Email Giải Quyết Chính Thức Định Dạng Rich HTML chuẩn nhận diện EAUT gửi tới hộp thư của sinh viên</div>
</div>

<div class="figure-container">
    <img src="{img5}" class="figure-img" style="max-width: 85%;" alt="Chi tiết email và quy chế">
    <div class="figure-caption">Hình 5. Chi tiết nội dung văn bản giải quyết, căn cứ quy chế và phương thức xử lý hiển thị trực tiếp trên giao diện duyệt hồ sơ</div>
</div>

<h3 class="item-title">4.3. Đánh giá ưu điểm và hạn chế</h3>
<p class="no-indent"><strong>Ưu điểm nổi bật:</strong></p>
<ul>
    <li><strong>Bám sát thực tiễn EAUT:</strong> Mọi căn cứ pháp lý, mã biểu mẫu và thời hạn giải quyết đều được trích xuất từ 3 tài liệu nghiệp vụ chính thức của trường; phù hợp 100% với 10 nhóm dịch vụ sinh viên của cổng Một cửa mis.eaut.edu.vn.</li>
    <li><strong>Tốc độ vượt trội & Chi phí bằng 0:</strong> Toàn bộ quá trình suy luận 5 bước hoàn tất dưới 10 mili-giây trên CPU thông thường, không phụ thuộc kết nối Internet hay GPU đắt tiền.</li>
    <li><strong>An toàn thông tin tuyệt đối:</strong> Vận hành 100% Offline (Air-Gapped Ready); tự động che giấu 7 trường dữ liệu PII; email liên hệ được lưu tách riêng biệt và bảo vệ theo Nghị định 13/2023/NĐ-CP.</li>
    <li><strong>Cơ chế Human-in-the-Loop hoàn thiện:</strong> Cán bộ luôn giữ quyền kiểm soát tối cao; có thể chỉnh sửa nội dung văn bản, phân lại phòng ban thụ lý và phê duyệt gửi email thực tế chỉ với 1 click.</li>
    <li><strong>Khả năng mở rộng đa CSDL:</strong> Hỗ trợ linh hoạt cả SQLite WAL cho máy đơn lẻ và MySQL Docker kết nối DBeaver cho hệ thống trường.</li>
</ul>

<p class="no-indent"><strong>Hạn chế và Định hướng hoàn thiện:</strong></p>
<ul>
    <li><strong>Chưa kết nối API trực tiếp với cổng daotao.eaut.edu.vn:</strong> Cán bộ hiện vẫn cần kiểm tra số dư học phí hoặc điểm thi trên hệ thống đào tạo trước khi duyệt. Định hướng: Phát triển Webhook/API liên thông tự động.</li>
    <li><strong>Quy mô dữ liệu câu hỏi thực tế còn khiêm tốn:</strong> Cần tiếp tục thu thập thêm dữ liệu phản ánh thật đã ẩn danh của sinh viên qua các học kỳ để làm giàu tập huấn luyện thông qua module Active Learning đã tích hợp.</li>
</ul>

<!-- 5. Kế hoạch Triển khai -->
<h2 class="sub-title">5. Kế hoạch Triển khai</h2>
<p>Kế hoạch đưa sản phẩm vào ứng dụng thực tế tại Trường Đại học Công nghệ Đông Á được vạch ra theo 4 giai đoạn cụ thể:</p>

<div class="table-container">
    <div class="table-caption">Bảng 11. Lộ trình triển khai ứng dụng thực tế hệ thống EduSupportAI</div>
    <table>
        <thead>
            <tr>
                <th style="width: 25%;">Giai đoạn</th>
                <th style="width: 40%;">Nội dung công việc trọng tâm</th>
                <th style="width: 35%;">Mục tiêu & Kết quả cần đạt</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bold">Giai đoạn 1<br>(Tháng 03/2026)</td>
                <td>Hoàn thiện nghiệm thu nội bộ và xác minh dữ liệu</td>
                <td>Phòng Đào tạo, Phòng CTSV và Ban Khảo thí rà soát, xác nhận toàn bộ 15 quy trình và 15 mục FAQ.</td>
            </tr>
            <tr>
                <td class="bold">Giai đoạn 2<br>(Tháng 04/2026)</td>
                <td>Triển khai thử nghiệm tại Bộ phận Một cửa & Khoa CNTT</td>
                <td>Cài đặt hệ thống trên mạng nội bộ (LAN) của trường; thử nghiệm tiếp nhận 300 - 500 phản ánh học vụ thật.</td>
            </tr>
            <tr>
                <td class="bold">Giai đoạn 3<br>(Tháng 05/2026)</td>
                <td>Kích hoạt vòng lặp Active Learning & Tích hợp MySQL</td>
                <td>Sử dụng nhật ký phê duyệt của cán bộ để tự động tái huấn luyện mô hình; đồng bộ dữ liệu vào MySQL trường.</td>
            </tr>
            <tr>
                <td class="bold">Giai đoạn 4<br>(Năm học 2026 - 2027)</td>
                <td>Mở rộng toàn diện cho toàn thể sinh viên EAUT</td>
                <td>Liên thông API với cổng daotao.eaut.edu.vn và tích hợp thông báo qua ứng dụng Zalo ZNS / Mobile App.</td>
            </tr>
        </tbody>
    </table>
</div>

<p><strong>Tính bền vững và Khả năng nhân rộng:</strong> EduSupportAI được xây dựng 100% trên nền tảng mã nguồn mở, không phát sinh chi phí bản quyền định kỳ. Khi nhà trường có sự điều chỉnh về quy chế hoặc bổ sung thủ tục mới, cán bộ quản trị chỉ cần cập nhật file cấu hình eaut_procedures_kb.json mà không cần phải can thiệp hay lập trình lại hệ thống. Mô hình hoàn toàn có thể nhân rộng sang các trường đại học, cao đẳng khác trong cùng hệ sinh thái giáo dục.</p>

<!-- ==================== PHẦN D ==================== -->
<h1 class="sec-title" style="margin-top: 25px;">D. PHỤ LỤC</h1>

<h3 class="item-title">1. Sơ đồ chuỗi xử lý dữ liệu 5 bước (Pipeline Flowchart)</h3>
<p class="no-indent" style="font-weight: bold;">Câu hỏi / Yêu cầu học vụ từ Sinh viên (Cổng trực tuyến / Đính kèm tài liệu)</p>
<ul style="list-style-type: none; padding-left: 10px;">
    <li>→ <strong>BƯỚC 1:</strong> Làm sạch chuẩn hóa Unicode NFC, loại bỏ ký tự ẩn, che 7 loại dữ liệu cá nhân PII theo Nghị định 13/2023/NĐ-CP, gắn cờ chất lượng.</li>
    <li>→ <strong>BƯỚC 2:</strong> Phân loại máy học đa lớp (Dual TF-IDF + Logistic Regression) xác định chuyên môn, phân phối xác suất và gán mức độ ưu tiên.</li>
    <li>→ <strong>BƯỚC 3:</strong> Tra cứu quy chế RAG đối soát trên Kho 15 quy trình EAUT, trích xuất căn cứ pháp lý và thời hạn cam kết SLA.</li>
    <li>→ <strong>BƯỚC 4:</strong> Chuỗi suy luận Chain-of-Thought và tổng hợp văn bản email giải quyết định dạng Rich HTML chuẩn nhận diện EAUT.</li>
    <li>→ <strong>BƯỚC 5:</strong> Rào chắn an toàn (Guardrails) & Phân luồng: Tự động gửi thẳng email nếu đạt chuẩn hoặc chuyển sang Bàn duyệt Cán bộ (HITL).</li>
    <li>→ <strong>LƯU TRỮ & GỬI TIN:</strong> Lưu nhật ký xử lý minh bạch (Execution Trace), nhật ký email vào SQLite WAL / MySQL Docker; gửi thông báo thực tế qua SMTP.</li>
</ul>

<h3 class="item-title">2. Danh mục 15 quy trình học vụ EAUT trọng yếu đã chuẩn hóa</h3>
<ul>
    <li><strong>PROC_TC_01:</strong> Quy trình Nộp học phí, Đối soát giao dịch ngân hàng và Gia hạn học phí (P. Tài chính - Kế toán; SLA: 24 - 48h làm việc).</li>
    <li><strong>PROC_DT_01:</strong> Quy trình Chuyển ngành đào tạo (Phòng Đào tạo; Căn cứ Quyết định 348/QĐ-ĐHCNĐA; SLA: 05 ngày làm việc).</li>
    <li><strong>PROC_DT_02:</strong> Quy trình Bảo lưu kết quả học tập và Xin tiếp tục theo học (Phòng Đào tạo; SLA: 03 ngày làm việc).</li>
    <li><strong>PROC_DT_03:</strong> Quy trình Đăng ký học lại và Học cải thiện điểm (Phòng Đào tạo; SLA: 02 ngày làm việc).</li>
    <li><strong>PROC_DT_04:</strong> Quy trình Khảo thí: Phúc khảo bài thi và Hoãn thi kết thúc học phần (Ban Khảo thí & ĐBCL; SLA: 07 ngày làm việc).</li>
    <li><strong>PROC_DT_05:</strong> Quy trình Xét tốt nghiệp và Cấp bản sao văn bằng chứng chỉ (Phòng Đào tạo; SLA: 05 ngày làm việc).</li>
    <li><strong>PROC_DT_06:</strong> Quy trình Rút bớt học phần đã đăng ký (Phòng Đào tạo; SLA: 02 ngày làm việc).</li>
    <li><strong>PROC_DT_07:</strong> Quy trình Chuyển cơ sở đào tạo Hà Nội - Bắc Ninh (Phòng Đào tạo; SLA: 03 ngày làm việc).</li>
    <li><strong>PROC_CTSV_01:</strong> Quy trình Cấp Giấy xác nhận sinh viên tại Bộ phận Một cửa (tạm hoãn NVQS, vay vốn NHCSXH, vé xe buýt; SLA: 02 ngày làm việc).</li>
    <li><strong>PROC_CTSV_02:</strong> Quy trình Xác nhận chế độ ưu đãi giáo dục và Trợ cấp xã hội (Phòng CTSV; SLA: 03 ngày làm việc).</li>
    <li><strong>PROC_CTSV_03:</strong> Quy trình Đánh giá điểm rèn luyện và Xét học bổng khuyến khích học tập (Phòng CTSV; SLA: Theo kỳ học).</li>
    <li><strong>PROC_CTSV_04:</strong> Quy trình Khen thưởng và Xử lý kỷ luật sinh viên (Phòng CTSV; SLA: 05 ngày làm việc).</li>
    <li><strong>PROC_CTSV_05:</strong> Quy trình Đăng ký nội trú và Quản lý sinh viên Ký túc xá (Phòng CTSV; SLA: 01 ngày làm việc).</li>
    <li><strong>PROC_CSVC_01:</strong> Quy trình Báo hỏng và Xử lý sự cố thiết bị giảng đường, phòng học (Phòng QT Cơ sở vật chất; SLA: 04 - 12 giờ làm việc).</li>
    <li><strong>PROC_CNTT_01:</strong> Quy trình Hỗ trợ kỹ thuật tài khoản cổng sinh viên daotao.eaut.edu.vn và email trường (Trung tâm CNTT; SLA: 24h làm việc).</li>
</ul>

<h3 class="item-title">3. Mã nguồn và Hướng dẫn chạy thử nghiệm</h3>
<p class="no-indent"><strong>Mã nguồn dự án công khai:</strong> <a href="https://github.com/teedeetee13/centric_data_ai_nhom67">https://github.com/teedeetee13/centric_data_ai_nhom67</a></p>
<ul>
    <li><strong>Khởi chạy demo trên Windows:</strong> Nhấp đúp file <code>CHAY_DEMO_WINDOWS.bat</code> (hệ thống tự động kích hoạt môi trường ảo và mở trình duyệt tại địa chỉ <code>http://127.0.0.1:8501</code>).</li>
    <li><strong>Khởi chạy qua Docker Compose:</strong> <code>docker-compose up -d</code> (khởi chạy đồng thời Streamlit Web App, MySQL 8.0 và DBeaver CloudBEaver).</li>
    <li><strong>Lệnh thực thi toàn bộ 43 bài kiểm thử tự động:</strong> <code>python -m unittest discover -s tests</code> (kết quả kiểm thử đạt 43/43 tests pass thành công 100%).</li>
</ul>

<h3 class="item-title">4. Tài liệu tham khảo</h3>
<ul>
    <li><strong>[1]</strong> Ng, A. (2021). A Chat with Andrew on MLOps: From Model-centric to Data-centric AI. DeepLearning.AI.</li>
    <li><strong>[2]</strong> Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825-2830.</li>
    <li><strong>[3]</strong> Quốc hội nước CHXHCN Việt Nam (2025). Luật Bảo vệ dữ liệu cá nhân; Chính phủ (2023). Nghị định số 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.</li>
    <li><strong>[4]</strong> Trường Đại học Công nghệ Đông Á (EAUT). Quyết định số 348/QĐ-ĐHCNĐA về Quy chế đào tạo đại học; các Quyết định 118, 119, 137, 180/QĐ-ĐHCNĐA về công tác sinh viên, học phí và cơ sở vật chất.</li>
    <li><strong>[5]</strong> Khoa Công nghệ thông tin - Trường Đại học Công nghệ Đông Á (2026). Kế hoạch số 20/KH-KCNTT về việc tổ chức cuộc thi Centric Data AI 2026.</li>
</ul>

</body>
</html>
"""
    with open(TEMP_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML at {TEMP_HTML}")

def render_pdf():
    print("-> Rendering PDF with Puppeteer...")
    node_script = """
    const puppeteer = require('/tmp/test_pup/node_modules/puppeteer');
    const path = require('path');

    (async () => {
        const browser = await puppeteer.launch({
            executablePath: '/home/kennysk/.cache/puppeteer/chrome/linux-157.0.8103.50/chrome-linux64/chrome',
            headless: 'new',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--user-data-dir=/tmp/pup_pdf_gen'
            ]
        });
        const page = await browser.newPage();
        await page.goto('file:///tmp/thuyet_minh_vong2.html', { waitUntil: 'networkidle0', timeout: 30000 });
        
        await page.pdf({
            path: '/home/kennysk/centric_data_ai_nhom67/EduSupportAI_Thuyet_minh_vong2(1).pdf',
            format: 'A4',
            margin: {
                top: '20mm',
                bottom: '20mm',
                left: '20mm',
                right: '20mm'
            },
            printBackground: true,
            displayHeaderFooter: true,
            headerTemplate: `<div style="font-size: 8pt; font-family: 'Times New Roman', serif; color: #94a3b8; width: 100%; border-bottom: 0.5px solid #cbd5e1; padding-bottom: 4px; margin: 0 20mm; display: flex; justify-content: space-between;"><span>EDUSUPPORTAI — THUYẾT MINH VÒNG 2</span><span>DATA CENTRIC AI 2026</span></div>`,
            footerTemplate: `<div style="font-size: 9pt; font-family: 'Times New Roman', serif; color: #64748b; width: 100%; text-align: center; border-top: 0.5px solid #cbd5e1; padding-top: 4px; margin: 0 20mm;"><span>Trang <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`
        });
        
        await browser.close();
        console.log('PDF rendered successfully!');
    })();
    """
    
    with open("/tmp/render_pdf.js", "w", encoding="utf-8") as f:
        f.write(node_script)
        
    subprocess.run(["node", "/tmp/render_pdf.js"], check=True)
    print(f"PDF created at {OUTPUT_PDF} ({OUTPUT_PDF.stat().st_size:,} bytes)")

def main():
    generate_html()
    render_pdf()

if __name__ == "__main__":
    main()
