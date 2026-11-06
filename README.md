# EduSupportAI — Nhóm 67, Centric Data AI 2026

Hệ thống hỗ trợ **cố vấn học tập và Phòng Công tác sinh viên** trả lời thắc mắc của sinh viên
(Trường Đại học Công nghệ Đông Á). Mỗi câu hỏi được che thông tin cá nhân, phân loại, **ghép với quy trình
nghiệp vụ của trường** để lập phiếu xử lý (đơn vị đầu mối, hồ sơ, các bước, hạn xử lý), rồi soạn bản nháp trả lời
bằng mô hình ngôn ngữ chạy ngay trên máy. **Cán bộ luôn là người duyệt cuối cùng.**

Hướng tiếp cận: **Data-Centric AI**, tức giữ mô hình nhỏ, minh bạch và tập trung nâng chất lượng dữ liệu, tri thức.

## Chạy thử trong 3 bước (Windows)

1. Cài **Python 3.12** ([python.org](https://www.python.org/downloads/release/python-3120/)), nhớ tích *Add Python to PATH*.
2. Mở thư mục `EduSupportAI`, nhấp đúp **`CHAY_DEMO_WINDOWS.bat`** (lần đầu tự cài thư viện, cần Internet).
3. Trình duyệt mở `http://127.0.0.1:8501`. Ở tab *Tiếp nhận yêu cầu*, mở **"Hướng dẫn nhanh và câu hỏi mẫu để demo"**
   và bấm một câu mẫu.

Tùy chọn: cài [Ollama](https://ollama.com) và chạy `ollama pull qwen2.5:3b` để bản nháp do mô hình ngôn ngữ cục bộ soạn.
Không có Ollama thì hệ thống vẫn chạy đầy đủ với bản nháp theo mẫu.

macOS / Linux và cách chạy thủ công: xem [EduSupportAI/readme.md](EduSupportAI/readme.md) mục 6.

## Nên xem gì

| Muốn biết | Xem ở đâu |
| :--- | :--- |
| Hệ thống làm gì, kiến trúc, module | [EduSupportAI/readme.md](EduSupportAI/readme.md) |
| Kịch bản demo 5 phút và câu hỏi thường gặp của hội đồng | [EduSupportAI/DEMO_5_PHUT.md](EduSupportAI/DEMO_5_PHUT.md) |
| Sơ đồ hệ thống và số liệu thực nghiệm | [EduSupportAI/SO_DO_HE_THONG_EDUSUPPORT_AI.md](EduSupportAI/SO_DO_HE_THONG_EDUSUPPORT_AI.md) |
| Kho 33 quy trình nghiệp vụ | [EduSupportAI/data/kb/eaut_quy_trinh.json](EduSupportAI/data/kb/eaut_quy_trinh.json) |
| Kết quả thực nghiệm ngay trong app | tab *Dữ liệu và lịch sử* → "Kết quả thực nghiệm của mô hình" |
| Thuyết minh, kế hoạch, phân công nhóm | [docs/](docs/) |
| Quy ước đóng góp code | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Cấu trúc repo

```text
.
├── EduSupportAI/      Mã nguồn ứng dụng (Python 3.12, Streamlit)
├── docs/              Thuyết minh, phân tích kế hoạch, phân công nhóm
├── .github/workflows  CI: tự chạy kiểm tra lỗi và kiểm thử khi push / mở Pull Request
├── README.md          Tệp này
└── CONTRIBUTING.md    Quy ước làm việc chung
```

## Giới hạn hiện tại

Dữ liệu huấn luyện và đánh giá là **dữ liệu mô phỏng** do nhóm biên soạn. Kho quy trình biên tập từ tài liệu
hướng dẫn của trường; 10/15 mục FAQ còn là nội dung minh họa. Số liệu trong app và tài liệu đều chạy lại được bằng
các lệnh trong `EduSupportAI/readme.md`, nhưng chưa phản ánh hiệu quả trên câu hỏi thật của sinh viên.
