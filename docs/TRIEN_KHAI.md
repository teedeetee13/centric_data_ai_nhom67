# Triển khai EduSupportAI

Theo thiết kế trong thuyết minh, hệ thống chạy **nội bộ** (on-premises): dữ liệu sinh viên không rời máy chủ của trường.
Chọn một trong ba cách dưới đây.

| Cách | Dùng khi | Cần gì |
| :--- | :--- | :--- |
| 1. Máy cá nhân | Demo, phát triển | Python 3.12 |
| 2. Mạng nội bộ không Docker | Thí điểm nhanh trên một máy Windows | Python 3.12, mật khẩu cán bộ |
| 3. Docker | Máy chủ của trường | Docker, mật khẩu cán bộ |

## 1. Máy cá nhân

Nhấp đúp `EduSupportAI/CHAY_DEMO_WINDOWS.bat`. Ứng dụng chỉ nghe ở `127.0.0.1`, khu vực cán bộ mở tự do.

## 2. Mạng nội bộ không Docker

```powershell
cd EduSupportAI
$env:EDUSUPPORT_OFFICER_PASSWORD = "mot-chuoi-dai-ngau-nhien"
.venv\Scripts\python.exe run_mvp.py --lan
```

Máy khác truy cập `http://<IP-máy-này>:8501`. `--lan` từ chối chạy nếu chưa đặt mật khẩu.

## 3. Docker

```bash
cd EduSupportAI
cp .env.example .env      # điền EDUSUPPORT_OFFICER_PASSWORD
docker compose up -d --build                  # bản nháp theo mẫu
docker compose --profile llm up -d --build    # kèm mô hình ngôn ngữ (tải khoảng 1,9 GB)
```

Mặc định chỉ mở ở `127.0.0.1:8501`. CSDL nằm trong volume `app-data`. Sao lưu:

```bash
docker compose exec app python -c "import sqlite3; s=sqlite3.connect('/data/edusupport.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d)"
```

Hình `ollama` trong compose chạy bằng CPU; muốn dùng GPU cần cài NVIDIA Container Toolkit và thêm cấu hình `gpus`.

## Danh sách kiểm tra trước khi cho người khác dùng

- [ ] Có văn bản đồng ý của Nhà trường về xử lý dữ liệu sinh viên; đối chiếu Luật Bảo vệ dữ liệu cá nhân và văn bản hướng dẫn hiện hành.
- [ ] Mật khẩu cán bộ dài, ngẫu nhiên, không dùng lại.
- [ ] **Đặt sau reverse proxy HTTPS** nếu mở ngoài máy chủ: Streamlit tự nó chỉ chạy HTTP, mật khẩu sẽ đi dạng rõ.
- [ ] Không mở thẳng ra Internet. Chỉ mở trong mạng trường hoặc VPN.
- [ ] Quy trình và FAQ đã được phòng ban xác nhận.
- [ ] Có lịch sao lưu CSDL.
- [ ] Đọc mục quyền sở hữu trong Thể lệ cuộc thi (mục VI, VII) trước khi dùng sản phẩm ngoài cuộc thi.

## Giới hạn hiện tại

- Một mật khẩu chung cho mọi cán bộ: chưa phân quyền theo từng người hoặc từng phòng, nhật ký duyệt chưa ghi tên người duyệt.
- SQLite phù hợp một máy chủ và lượng cán bộ nhỏ; quy mô lớn hơn cần chuyển PostgreSQL.
- Mô hình ngôn ngữ xử lý mỗi lần một bản nháp; yêu cầu đến khi đang bận sẽ dùng bản nháp theo mẫu.
