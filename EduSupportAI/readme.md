# EduSupportAI — Mã nguồn

Giới thiệu dự án xem [README ở thư mục gốc](../README.md). Tài liệu này dành cho người đọc và sửa code.

## Luồng xử lý một yêu cầu

```text
Câu hỏi sinh viên
 -> cleaner            chuẩn hóa NFC, loại ký tự vô hình, che PII
 -> model              phân loại 7 nhóm (TF-IDF từ + ký tự, Logistic Regression) và độ tự tin
 -> luật từ khóa       mức ưu tiên
 -> procedure_engine   ghép 1 trong 33 quy trình, có cổng từ khóa neo
      có quy trình     phiếu ticket: đơn vị đầu mối, hồ sơ, các bước, hạn xử lý, thông tin còn thiếu
                       local_llm soạn nháp chỉ từ quy trình; dữ kiện lạ -> dùng bản nháp theo mẫu
      không có         faq_engine: FAQ tham chiếu, cán bộ xác minh
 -> Bàn duyệt cán bộ   duyệt, đổi nhãn, từ chối; ghi review_logs
```

Thứ tự gọi nằm trong `src/service.py`.

## Cấu trúc

```text
app/                 Giao diện Streamlit, chỉ hiển thị và gọi src/service.py
  main.py            Ghép 3 tab
  styles.css         Kiểu dáng
  components/        auth, demo_guide, intake, result_view, workbench, dashboard
src/                 Lõi xử lý, không phụ thuộc giao diện
  config.py          Đường dẫn, ngưỡng, biến môi trường
  service.py         Luồng xử lý, điều kiện tự động duyệt
  cleaner.py         Làm sạch, che PII, khử trùng
  model.py           Phân loại, luật ưu tiên, huấn luyện
  procedure_engine.py, faq_engine.py, local_llm.py
  database.py        SQLite
  email_service.py   Gửi email (mô phỏng nếu chưa cấu hình SMTP)
  maintenance.py     Sao lưu, khôi phục, dọn dữ liệu, kiểm tra kho tri thức
data/kb/             Kho quy trình, FAQ, tập đánh giá định tuyến
data/raw, splits/    Dữ liệu mô phỏng và tập train / val / test
models/              Mô hình phân loại đã huấn luyện
experiments/         Các thực nghiệm và báo cáo JSON
tests/               Kiểm thử
```

## Cài đặt và chạy

Windows: nhấp đúp `CHAY_DEMO_WINDOWS.bat`. Thủ công (Python 3.12):

```bash
py -3.12 -m venv .venv                    # macOS/Linux: python3.12 -m venv .venv
.venv\Scripts\activate                    # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python run_mvp.py
```

CSDL `data/edusupport.db` được tạo rỗng ở lần chạy đầu. Cấu hình xem `.env.example`.

## Lệnh thường dùng

| Việc | Lệnh |
| :--- | :--- |
| Kiểm thử | `python -m unittest discover -s tests -t .` |
| Kiểm tra lỗi tĩnh | `ruff check .` |
| Kiểm tra kho tri thức | `python -m src.maintenance check-kb` |
| Huấn luyện lại phân loại | `python -m src.model` |
| Đánh giá định tuyến quy trình | `python -m experiments.eval_procedure_routing` |
| Thực nghiệm bổ sung dữ liệu | `python -m experiments.eval_procedure_augmentation` |
| Đánh giá không rò rỉ mẫu câu | `python -m experiments.run_group_holdout` |

`experiments/run_experiments.py` cho F1 = 1,0 vì test trùng mẫu câu với train; không dùng số này để báo cáo.

## Tài liệu liên quan

[Quy ước đóng góp](../CONTRIBUTING.md) · [Sổ tay vận hành](../docs/VAN_HANH.md) · [Kiểm thử và hiệu năng](../docs/KIEM_THU.md) · [Sơ đồ và số liệu](../docs/SO_DO_HE_THONG_EDUSUPPORT_AI.md) · [Kịch bản demo](../docs/DEMO_5_PHUT.md)
