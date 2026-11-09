# EduSupportAI — Nhóm 67, Centric Data AI 2026

Hệ thống hỗ trợ **cố vấn học tập và Phòng Công tác sinh viên** trả lời thắc mắc của sinh viên
(Trường Đại học Công nghệ Đông Á). Mỗi câu hỏi được che thông tin cá nhân, phân loại, **ghép với quy trình
nghiệp vụ của trường** để lập phiếu xử lý (đơn vị đầu mối, hồ sơ, các bước, hạn xử lý), rồi soạn bản nháp trả lời
bằng mô hình ngôn ngữ chạy ngay trên máy. **Khi vận hành thật, cán bộ là người duyệt cuối cùng.**

Hướng tiếp cận: **Data-Centric AI**, tức giữ mô hình nhỏ, minh bạch và tập trung nâng chất lượng dữ liệu, tri thức.

## Chạy thử trong 3 bước (Windows)

1. Cài **Python 3.12** ([python.org](https://www.python.org/downloads/release/python-3120/)), nhớ tích *Add Python to PATH*.
2. Mở thư mục `EduSupportAI`, nhấp đúp **`CHAY_DEMO_WINDOWS.bat`**. Lần đầu tự cài thư viện, cần Internet và mất khoảng 3–5 phút; **không đóng cửa sổ đen**, chờ trình duyệt tự mở.
3. Trình duyệt tự mở `http://127.0.0.1:8501` (mở sớm hơn sẽ báo *refused to connect*). Ở tab *Tiếp nhận yêu cầu*, mở **"Hướng dẫn nhanh và câu hỏi mẫu để demo"**
   và bấm một câu mẫu.

Tùy chọn: cài [Ollama](https://ollama.com) và chạy `ollama pull qwen2.5:3b` để bản nháp do mô hình ngôn ngữ cục bộ soạn.
Không có Ollama thì hệ thống vẫn chạy đầy đủ với bản nháp theo mẫu.

macOS / Linux và cách chạy thủ công: xem [EduSupportAI/readme.md](EduSupportAI/readme.md).

## Nên xem gì

| Muốn biết | Xem ở đâu |
| :--- | :--- |
| Luồng xử lý, cấu trúc code, lệnh thường dùng | [EduSupportAI/readme.md](EduSupportAI/readme.md) |
| Kịch bản demo 5 phút và câu hỏi thường gặp của hội đồng | [docs/DEMO_5_PHUT.md](docs/DEMO_5_PHUT.md) |
| Sơ đồ hệ thống và số liệu thực nghiệm | [docs/SO_DO_HE_THONG_EDUSUPPORT_AI.md](docs/SO_DO_HE_THONG_EDUSUPPORT_AI.md) |
| Kho 33 quy trình nghiệp vụ | [EduSupportAI/data/kb/eaut_quy_trinh.json](EduSupportAI/data/kb/eaut_quy_trinh.json) |
| Kết quả thực nghiệm ngay trong app | tab *Dữ liệu và lịch sử* → "Kết quả thực nghiệm của mô hình" |
| Kết quả kiểm thử và hiệu năng | [docs/KIEM_THU.md](docs/KIEM_THU.md) |
| Hướng dẫn cho sinh viên và cán bộ | [docs/HUONG_DAN_SU_DUNG.md](docs/HUONG_DAN_SU_DUNG.md) |
| Triển khai, vận hành, bảo trì | [docs/VAN_HANH.md](docs/VAN_HANH.md) |
| Quy ước đóng góp code | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Kế hoạch, phân công giai đoạn trước | [docs/luu_tru/](docs/luu_tru/) |

## Cấu trúc repo

```text
.
├── EduSupportAI/      Mã nguồn ứng dụng (Python 3.12, Streamlit)
├── docs/              Sổ tay vận hành, demo, kiểm thử, sơ đồ; luu_tru/ chứa kế hoạch cũ
├── .github/           CI, Dependabot, mẫu Pull Request
├── README.md          Tệp này
└── CONTRIBUTING.md    Quy ước làm việc chung
```

## Giới hạn hiện tại

Dữ liệu huấn luyện và đánh giá là **dữ liệu mô phỏng** do nhóm biên soạn. Kho quy trình biên tập từ tài liệu
hướng dẫn của trường; 10/15 mục FAQ còn là nội dung minh họa. Số liệu trong app và tài liệu đều chạy lại được bằng
các lệnh trong `EduSupportAI/readme.md`, nhưng chưa phản ánh hiệu quả trên câu hỏi thật của sinh viên.
