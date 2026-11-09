# Sổ tay triển khai, vận hành và bảo trì

Lệnh `python -m src.maintenance ...` chạy trong thư mục `EduSupportAI`, dùng Python của môi trường đã cài.
Với Docker, thêm tiền tố `docker compose exec app`.

## 1. Triển khai

Hệ thống chạy nội bộ: dữ liệu sinh viên không rời máy chủ của trường.

| Cách | Dùng khi | Lệnh |
| :--- | :--- | :--- |
| Máy cá nhân | Demo, phát triển | Nhấp đúp `EduSupportAI/CHAY_DEMO_WINDOWS.bat`, lần đầu chờ 3–5 phút để cài thư viện |
| Mạng nội bộ, không Docker | Thí điểm trên một máy Windows | Đặt `$env:EDUSUPPORT_OFFICER_PASSWORD = "..."`, rồi `.venv\Scripts\python.exe run_mvp.py --lan` |
| Docker | Máy chủ của trường | `cp .env.example .env`, điền mật khẩu, rồi `docker compose up -d --build` |

Muốn có mô hình ngôn ngữ: cài Ollama và `ollama pull qwen2.5:3b` (hai cách đầu), hoặc thêm `--profile llm` (Docker, chạy bằng CPU nếu chưa cấu hình GPU).
Toàn bộ biến cấu hình nằm trong `EduSupportAI/.env.example`.

**Trước khi cho người khác dùng:**

- [ ] Có văn bản đồng ý của Nhà trường; đối chiếu Luật Bảo vệ dữ liệu cá nhân và văn bản hướng dẫn hiện hành.
- [ ] Mật khẩu cán bộ dài, ngẫu nhiên.
- [ ] Đặt sau reverse proxy HTTPS; Streamlit chỉ có HTTP nên mật khẩu đi dạng rõ nếu mở trực tiếp.
- [ ] Chỉ mở trong mạng trường hoặc VPN, không mở ra Internet.
- [ ] Phòng ban đã xác nhận nội dung quy trình và FAQ.
- [ ] Đã đặt lịch sao lưu (mục 3).
- [ ] Đã đọc mục VI, VII Thể lệ cuộc thi về quyền sở hữu sản phẩm.

## 2. Lịch vận hành

| Tần suất | Việc | Cách làm |
| :--- | :--- | :--- |
| Hằng ngày | Xem hàng chờ, ca chờ lâu | `status`, hoặc tab Bàn duyệt |
| Hằng ngày (tự động) | Sao lưu | Mục 3 |
| Hằng tháng | Dọn dữ liệu quá hạn | `purge`, xem kết quả rồi `purge --apply` |
| Hằng tháng | Thử khôi phục một bản sao lưu sang tệp khác | Mục 3 |
| Hằng tháng | Xử lý Pull Request cập nhật thư viện | Mục 5 |
| Đầu mỗi học kỳ, khi có quy định mới | Cập nhật quy trình, FAQ | Mục 4 |
| Mỗi 6 tháng, khi có người nghỉ | Đổi mật khẩu cán bộ | Đổi biến môi trường, khởi động lại |

## 3. Sao lưu và khôi phục

```bash
python -m src.maintenance backup          # lưu vào thư mục backups cạnh CSDL, giữ 14 bản
python -m src.maintenance status          # xem bản sao lưu mới nhất
```

Đặt lịch hằng ngày trên Windows (chạy một lần, sửa đường dẫn):

```bash
schtasks /Create /SC DAILY /ST 22:00 /TN EduSupportAI-Backup /TR "cmd /c cd /d D:\duong-dan\EduSupportAI && .venv\Scripts\python.exe -m src.maintenance backup"
```

Linux dùng cron: `0 22 * * * cd /duong-dan/EduSupportAI && docker compose exec -T app python -m src.maintenance backup`.
Nên chép thư mục sao lưu sang một ổ hoặc máy khác; bản sao lưu vẫn chứa nội dung đã che và email liên hệ.

Khôi phục: tắt ứng dụng, chạy lệnh dưới, bật lại. Bản đang có được giữ trong `edusupport_truoc_khoi_phuc.db`.

```bash
python -m src.maintenance restore duong-dan/edusupport_XXXX.db --yes
```

## 4. Cập nhật tri thức và mô hình

1. Sửa `data/kb/eaut_quy_trinh.json` hoặc `eaut_faq_kb.csv` theo mục 3 của [CONTRIBUTING.md](../CONTRIBUTING.md).
2. `python -m src.maintenance check-kb`
3. `python -m experiments.eval_procedure_routing` và so với kết quả cũ.
4. Nếu đổi câu mẫu của quy trình: `python -m src.model` để huấn luyện lại, rồi `python -m experiments.eval_procedure_augmentation`.
5. Chạy kiểm thử, mở Pull Request. Ứng dụng tự nạp lại khi tệp tri thức hoặc mô hình thay đổi; với Docker cần `docker compose up -d --build`.

## 5. Cập nhật thư viện

Dependabot tự mở Pull Request hằng tháng; CI kiểm tra và quét lỗ hổng hằng tuần. CI xanh thì gộp.
`scikit-learn` được cố định và loại khỏi Dependabot: khi nâng phiên bản phải huấn luyện lại mô hình trong cùng Pull Request.

## 6. Xử lý sự cố

| Hiện tượng | Nguyên nhân thường gặp | Xử lý |
| :--- | :--- | :--- |
| Thanh trạng thái ghi "Bản nháp theo mẫu" | Ollama chưa chạy hoặc thiếu model | `ollama serve`, `ollama pull qwen2.5:3b`. Hệ thống vẫn dùng được |
| Trình duyệt báo *refused to connect* | App chưa chạy xong hoặc cửa sổ đen đã đóng | Lần đầu chờ 3–5 phút; nếu cửa sổ đã đóng thì chạy lại `.bat` |
| Bản nháp đầu tiên rất lâu | Đang nạp model | Chờ; các lần sau khoảng vài giây |
| Tab cán bộ báo đang khóa | Thiếu `EDUSUPPORT_OFFICER_PASSWORD` | Đặt biến, khởi động lại |
| Báo nhập sai quá nhiều lần | Đã sai 5 lần | Chờ 5 phút hoặc khởi động lại |
| Báo không nạp được mô hình | Sai phiên bản scikit-learn hoặc thiếu tệp | Cài lại `requirements.txt`; chạy `python -m src.model` |
| Máy khác không vào được ở `--lan` | Tường lửa chặn cổng 8501 | Mở cổng cho mạng nội bộ |
| CSDL hỏng | Mất điện, hỏng ổ | Khôi phục theo mục 3 |
| Nghi lộ mật khẩu hoặc dữ liệu | | Tắt ứng dụng, đổi mật khẩu, kiểm tra tab nhật ký, báo đầu mối của trường |

Nhật ký ứng dụng: cửa sổ dòng lệnh, hoặc `docker compose logs app`. Kiểm tra sống: `http://<máy-chủ>:8501/_stcore/health`.

## 7. Giới hạn hiện tại

- Một mật khẩu chung; nhật ký duyệt chưa ghi tên cán bộ; chưa phân quyền theo phòng.
- SQLite phù hợp một máy chủ và số cán bộ nhỏ; mở rộng cần PostgreSQL.
- Mô hình ngôn ngữ xử lý mỗi lần một bản nháp; yêu cầu đến khi đang bận dùng bản theo mẫu.
- Nhật ký duyệt chưa được dùng để huấn luyện lại.
