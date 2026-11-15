# EduSupportAI — Nhóm 67, Centric Data AI 2026

Hỗ trợ **cố vấn học tập và Phòng Công tác sinh viên** (Trường Đại học Công nghệ Đông Á) xử lý thắc mắc của sinh viên.
Mỗi câu hỏi được che thông tin cá nhân, phân loại, **ghép với 1 trong 33 quy trình nghiệp vụ của trường** để lập phiếu xử lý
(đơn vị đầu mối, hồ sơ, các bước, hạn xử lý), rồi soạn bản nháp bằng mô hình ngôn ngữ chạy ngay trên máy.
Khi vận hành thật, cán bộ là người duyệt cuối cùng. Hướng tiếp cận: **Data-Centric AI**.

## Chạy thử (Windows)

1. Cài **Python 3.12** ([python.org](https://www.python.org/downloads/release/python-3120/)), tích *Add Python to PATH*.
2. Nhấp đúp **`EduSupportAI/CHAY_DEMO_WINDOWS.bat`**. Lần đầu tự cài thư viện (cần Internet, 3–5 phút); không đóng cửa sổ đen.
3. Trình duyệt tự mở `http://127.0.0.1:8501`. Chọn một tình huống ở khung **Câu hỏi mẫu**, bấm **Điền vào ô nội dung** rồi **Gửi**. Muốn xem thống kê: tab **Thống kê** → **Công cụ cán bộ** → **Nạp dữ liệu mẫu**.

## Tài liệu

Toàn bộ trong một tệp: **[docs/TAI_LIEU.md](docs/TAI_LIEU.md)** (sử dụng, triển khai, vận hành, kỹ thuật, số liệu, quy ước đóng góp).
Kế hoạch và sơ đồ của vòng 1 nằm ở [docs/luu_tru/](docs/luu_tru/).

```text
EduSupportAI/   Mã nguồn (Python 3.12, Streamlit, scikit-learn, SQLite, Ollama tùy chọn)
docs/           TAI_LIEU.md và thư mục lưu trữ
.github/        CI, Dependabot, mẫu Pull Request
```

## Giới hạn hiện tại

Dữ liệu huấn luyện và đánh giá là **dữ liệu mô phỏng** do nhóm biên soạn; chưa có câu hỏi thật của sinh viên.
10/15 mục FAQ là nội dung minh họa. Mọi số liệu chạy lại được bằng các lệnh trong tài liệu.
