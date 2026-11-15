# Tài liệu EduSupportAI

1. [Sử dụng](#1-sử-dụng) · 2. [Cài đặt và triển khai](#2-cài-đặt-và-triển-khai) · 3. [Vận hành, bảo trì](#3-vận-hành-bảo-trì) · 4. [Kỹ thuật](#4-kỹ-thuật) · 5. [Kiểm thử và số liệu](#5-kiểm-thử-và-số-liệu) · 6. [Quy ước đóng góp](#6-quy-ước-đóng-góp)

## 1. Sử dụng

Bản **demo** (máy cá nhân) mở sẵn mọi tab và có câu hỏi mẫu. Bản **chính thức** yêu cầu cán bộ đăng nhập; sinh viên chỉ thấy biên nhận.

**Sinh viên:** tab *Gửi yêu cầu* → viết nội dung (việc gì, ở đâu, khi nào) → điền mã SV, email nếu muốn nhận kết quả qua thư → **Gửi**, ghi lại mã yêu cầu. Nếu câu hỏi thuộc quy trình, phiếu xử lý hiện đơn vị tiếp nhận, hồ sơ, các bước và thời hạn.

**Cán bộ:** tab *Bàn duyệt* → xem chỉ số hàng chờ, lọc, chọn yêu cầu → đối chiếu tham chiếu (**QTxx** là quy trình của trường, **KBxx** là FAQ; mục "chưa xác minh" phải tự kiểm tra) → đọc, sửa bản nháp → **Lưu nháp**, **Duyệt và lưu** (gửi kết quả nếu có email) hoặc **Từ chối** (ghi lý do). Thao tác đã duyệt không sửa lại được và được lưu nhật ký.

**Thống kê:** tab *Thống kê* hiện 8 chỉ số (tổng, chờ duyệt, đã xử lý, thời gian xử lý, khớp quy trình, thông tin cá nhân đã che, độ tự tin, cán bộ đổi nhãn) và 4 biểu đồ. *Công cụ cán bộ* ở cuối tab: nạp 72 câu mẫu, nạp tệp từ MIS (tối đa 200 dòng), kiểm tra chất lượng tệp, tải dữ liệu đã che, email thử, huấn luyện lại.

**Đọc kết quả:** *độ tự tin* là xác suất của mô hình, không phải độ chính xác, dưới 60% cần xác nhận lại nhóm; *mức ưu tiên* do luật từ khóa; *hạn xử lý* tính theo ngày làm việc, chưa trừ ngày lễ.

## 2. Cài đặt và triển khai

| Cách | Dùng khi | Lệnh (trong thư mục `EduSupportAI`) |
| :--- | :--- | :--- |
| Máy cá nhân | Demo, thí điểm trên máy cán bộ | Nhấp đúp `CHAY_DEMO_WINDOWS.bat`; lần đầu chờ 3–5 phút cài thư viện, **không đóng cửa sổ đen** |
| Mạng nội bộ | Nhiều cán bộ dùng chung một máy | Đặt `EDUSUPPORT_OFFICER_PASSWORD`, rồi `.venv\Scripts\python.exe run_mvp.py --lan` |
| Docker | Máy chủ của trường | `cp .env.example .env`, điền mật khẩu, `docker compose up -d --build` (thêm `--profile llm` để có mô hình ngôn ngữ) |

Cài thủ công (macOS/Linux hoặc khi phát triển): `python3.12 -m venv .venv`, kích hoạt, `pip install -r requirements-dev.txt`, `python run_mvp.py`.
Mô hình ngôn ngữ (tùy chọn): cài [Ollama](https://ollama.com), `ollama pull qwen2.5:3b`; không có thì bản nháp dùng mẫu câu. Cấu hình xem `EduSupportAI/.env.example`.

**Trước khi cho người khác dùng:** có văn bản đồng ý của Nhà trường; mật khẩu cán bộ dài, ngẫu nhiên; đặt sau HTTPS nếu ra khỏi máy chủ; chỉ mở trong mạng trường hoặc VPN; phòng ban đã xác nhận quy trình và FAQ; đã đặt lịch sao lưu; đã đọc mục VI, VII Thể lệ cuộc thi về quyền sở hữu.

## 3. Vận hành, bảo trì

Công cụ `python -m src.maintenance <lệnh>` (Docker: thêm `docker compose exec app` phía trước):

| Lệnh | Việc | Khi nào |
| :--- | :--- | :--- |
| `status` | Hàng chờ, ca chờ lâu nhất, bản sao lưu mới nhất | Hằng ngày |
| `backup` | Sao lưu có kiểm tra toàn vẹn, giữ 14 bản | Hằng ngày (đặt lịch bên dưới) |
| `restore <tệp> --yes` | Khôi phục (tắt app trước); giữ lại bản đang có | Khi CSDL hỏng |
| `purge`, `purge --apply` | Đếm, rồi xóa email liên hệ và nhật ký gửi quá hạn | Hằng tháng |
| `check-kb` | Kiểm tra kho quy trình và FAQ | Mỗi lần sửa tri thức |

Đặt lịch sao lưu trên Windows:
`schtasks /Create /SC DAILY /ST 22:00 /TN EduSupportAI-Backup /TR "cmd /c cd /d D:\duong-dan\EduSupportAI && .venv\Scripts\python.exe -m src.maintenance backup"`

**Cập nhật quy định:** sửa `data/kb/eaut_quy_trinh.json` hoặc `eaut_faq_kb.csv` (mục 6) → `check-kb` → `python -m experiments.eval_procedure_routing` → nếu đổi câu mẫu thì `python -m src.model` → chạy kiểm thử → Pull Request.
**Thư viện:** Dependabot mở Pull Request hằng tháng, CI quét lỗ hổng hằng tuần. `scikit-learn` được cố định; nâng cấp phải huấn luyện lại mô hình. **Mật khẩu cán bộ:** đổi 6 tháng một lần hoặc khi có người nghỉ.

| Sự cố | Xử lý |
| :--- | :--- |
| Trình duyệt báo *refused to connect* | App chưa lên xong hoặc cửa sổ đen đã đóng; lần đầu chờ 3–5 phút, hoặc chạy lại `.bat` |
| Thanh trạng thái ghi "Bản nháp theo mẫu" | Mở Ollama, `ollama pull qwen2.5:3b`; hệ thống vẫn dùng được |
| Tab cán bộ báo đang khóa / nhập sai quá nhiều lần | Đặt `EDUSUPPORT_OFFICER_PASSWORD`; chờ 5 phút hoặc khởi động lại |
| Không nạp được mô hình | Cài lại `requirements.txt`, chạy `python -m src.model` |
| Máy khác không vào được ở `--lan` | Mở cổng 8501 trên tường lửa cho mạng nội bộ |
| Nghi lộ mật khẩu hoặc dữ liệu | Tắt app, đổi mật khẩu, kiểm tra nhật ký, báo đầu mối của trường |

## 4. Kỹ thuật

```text
Câu hỏi → cleaner (NFC, loại ký tự ẩn, che 7 loại PII) → model (7 nhóm + độ tự tin) → luật ưu tiên
       → procedure_engine (1 trong 33 quy trình, cổng từ khóa neo)
            có: phiếu ticket + local_llm soạn nháp chỉ từ quy trình (dữ kiện lạ → bản theo mẫu)
            không: faq_engine tham chiếu
       → tự duyệt ca an toàn (tùy chọn) hoặc Bàn duyệt cán bộ → SQLite + nhật ký
```

```text
EduSupportAI/
  app/main.py, styles.css, components/   Giao diện: chỉ hiển thị, gọi src/service.py
  src/                                   Lõi xử lý, không phụ thuộc giao diện (config, service, cleaner,
                                         model, procedure_engine, faq_engine, local_llm, database,
                                         email_service, maintenance)
  data/kb/                               Kho quy trình, FAQ, tập đánh giá định tuyến
  data/raw, data/splits/                 Dữ liệu mô phỏng, train / val / test
  models/, experiments/, tests/
```

| Việc | Lệnh |
| :--- | :--- |
| Kiểm thử, kiểm tra lỗi tĩnh | `python -m unittest discover -s tests -t .` · `ruff check .` |
| Huấn luyện lại phân loại | `python -m src.model` |
| Đánh giá định tuyến / bổ sung dữ liệu / không rò rỉ mẫu câu | `python -m experiments.eval_procedure_routing` · `eval_procedure_augmentation` · `run_group_holdout` |

`experiments/run_experiments.py` cho F1 = 1,0 vì test trùng mẫu câu với train; không dùng để báo cáo.

## 5. Kiểm thử và số liệu

Kiểm tra ngày 08–13/11/2026, Windows 11, Python 3.12: 64/64 kiểm thử qua; ruff sạch; pip-audit không có lỗ hổng đã biết; nhấp đúp `.bat` chạy được (lần đầu khoảng 3,5 phút); `--lan` từ chối chạy khi thiếu mật khẩu; CI GitHub xanh cả kiểm thử và đóng gói Docker.

| Chỉ số | Kết quả |
| :--- | :--- |
| Bổ sung câu mẫu quy trình (giữ nguyên thuật toán) | Câu hỏi CTSV 40% → 96,7%; văn phong thực tế 86,7% → 84,4% |
| Đánh giá không rò rỉ mẫu câu (28 câu test) | Macro F1: thô 0,587 → lọc trùng 0,441 → lọc thêm 0,286 |
| Định tuyến quy trình | Đúng 28/30 trong phạm vi; từ chối đúng 10/10 ngoài phạm vi |
| Bộ mẫu mở rộng 72 câu (33 quy trình, 10 loại dịch vụ MIS) | Định tuyến đúng 95,8%; từ chối đúng 100%; câu không dấu 85,7% |
| Bản nháp mô hình ngôn ngữ (10 câu) | 9 qua kiểm tra bám nguồn; khoảng 2,5 giây/bản (GPU 4 GB) |
| Xử lý một câu / 500 câu (không LLM) | 3,8 ms / 3,1 giây |
| Làm sạch 424 / 1.500 dòng | 0,28 / 1,72 giây |

Chưa kiểm tra: truy cập từ máy khác thật, gửi email SMTP thật, dữ liệu thật của sinh viên. Mọi tập đánh giá đều do nhóm viết.

## 6. Quy ước đóng góp

- **Đặt code đúng chỗ:** logic ở `src/` (không import streamlit); mỗi khối giao diện một tệp trong `app/components/`; CSS ở `app/styles.css`; đường dẫn, ngưỡng, biến môi trường ở `src/config.py`; tệp vượt khoảng 350 dòng thì tách.
- **Thêm quy trình:** thêm phần tử `QTxx` vào `eaut_quy_trinh.json` đủ trường như quy trình có sẵn (`keywords` viết có dấu; 3–6 `aliases`, ít nhất 1 câu không dấu). Chỉ ghi nội dung có trong văn bản gốc. FAQ chỉ đặt `verified=true` khi có `source_url`. Câu mẫu demo: `SAMPLES` trong `app/components/demo_guide.py`.
- **Không commit:** dữ liệu thật, `.env`, mật khẩu, CSDL. Số liệu đưa vào tài liệu phải chạy lại được.
- **Nhánh và Pull Request:** không commit thẳng `main`; nhánh không dấu (`ten/tinh-nang`); mỗi commit một việc; gộp qua Pull Request khi CI xanh và có người xem.
- **Tài liệu:** sửa tệp này thay vì tạo tệp mới; tài liệu hết dùng chuyển vào `docs/luu_tru/`.
