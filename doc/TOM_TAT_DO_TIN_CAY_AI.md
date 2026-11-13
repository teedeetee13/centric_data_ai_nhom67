# TÓM TẮT CƠ CHẾ TÍNH TOÁN & XỬ LÝ ĐỘ TIN CẬY (CONFIDENCE SCORE)
## Dự án: EduSupportAI — Hệ thống Tiếp nhận & Xử lý Phản ánh Sinh viên EAUT

---

## 1. TỔNG QUAN KIẾN TRÚC ĐỘ TIN CẬY
Độ tin cậy (*Confidence Score*) trong EduSupportAI là chỉ số đo lường mức độ chắc chắn của hệ thống khi tiếp nhận, phân loại và quyết định phân luồng phản ánh của sinh viên. Chỉ số này được xử lý qua chuỗi 4 giai đoạn khép kín:

```
[Nội dung phản ánh]
        │
        ▼
[1. Trích xuất đặc trưng TF-IDF kép] (Cấp từ 1-2 & Cấp ký tự 3-5)
        │
        ▼
[2. Phân loại máy học Logistic Regression] (Xác suất Softmax thô & Biên độ Margin)
        │
        ▼
[3. Hiệu chuẩn đồng thuận nghiệp vụ] (Đối soát với lựa chọn chuyên môn của người dùng)
        │
        ▼
[4. Rào chắn Guardrails & Phân luồng] (Tự động phê duyệt ≥ 70% | Bàn duyệt cán bộ 50-69% | Cảnh báo < 50%)
```

---

## 2. CHI TIẾT 4 GIAI ĐOẠN XỬ LÝ

### Giai đoạn 1: Trích xuất đặc trưng đa tầng (Feature Extraction)
* **Vị trí mã nguồn**: `src/model.py` (`_build_pipeline`)
* **Kỹ thuật sử dụng**: `FeatureUnion` kết hợp 2 vectorizer:
  1. **Word n-gram TF-IDF (1, 2)**: Trích xuất các từ đơn và cụm từ chuyên môn học vụ (ví dụ: *học phí*, *phúc khảo*, *bảo lưu*, *điều hòa*, *ký túc xá*).
  2. **Char n-gram TF-IDF (3, 5)** (`analyzer="char_wb"`): Trích xuất các cụm ký tự liền kề trong ranh giới từ. Cơ chế này giúp mô hình nhận diện chính xác ngay cả khi sinh viên viết tắt, teencode hoặc sai chính tả (ví dụ: *hocphi*, *khao diem*).

---

### Giai đoạn 2: Phân loại máy học & Xác suất Softmax nguyên bản
* **Vị trí mã nguồn**: `src/model.py` (`predict_single`)
* **Thuật toán**: `LogisticRegression(C=1.0, solver="lbfgs", max_iter=500)`
* **Công thức xác suất Softmax**: Mô hình tính toán phân phối xác suất trên toàn bộ 7 nhóm chuyên môn:
  $$P(C_i \mid X) = \frac{e^{\mathbf{w}_i^T \mathbf{x} + b_i}}{\sum_{k=1}^{7} e^{\mathbf{w}_k^T \mathbf{x} + b_k}}$$
* **Độ tin cậy thô ($Conf_{\text{raw}}$)**: Là giá trị xác suất lớn nhất trong phân phối:
  $$Conf_{\text{raw}} = \max_{i} P(C_i \mid X)$$
* **Biên độ quyết định (Decision Margin)**:
  $$\text{Margin} = P_{\text{top1}} - P_{\text{top2}}$$
  *(Đo khoảng cách giữa nhãn cao nhất và nhãn kế tiếp để đánh giá mức độ dứt khoát của mô hình)*.

---

### Giai đoạn 3: Hiệu chuẩn đồng thuận nghiệp vụ (Domain Consensus Calibration)
* **Vị trí mã nguồn**: `src/service.py` (`RequestService.process`)
* Để tăng độ chính xác trong thực tế, hệ thống đối soát kết quả dự đoán của AI với nhóm chuyên môn do sinh viên lựa chọn trên biểu mẫu (`topic_hint`):

| Trường hợp | Điều kiện | Công thức hiệu chuẩn độ tin cậy | Ý nghĩa nghiệp vụ |
| :--- | :--- | :--- | :--- |
| **Đồng thuận (Consensus)** | AI đoán trùng `topic_hint` | $Conf = \min\big(0.95, \, \max(0.88, \, Conf_{\text{raw}} + 0.40)\big)$ | AI và sinh viên cùng chỉ về một nhóm chuyên môn $\rightarrow$ thưởng điểm tin cậy đạt **88% – 95%**. |
| **Điều chỉnh (Guided)** | AI đoán lệch `topic_hint` | $Conf = \min\big(0.92, \, \max(0.88, \, P_{\text{topic\_hint}} + 0.40)\big)$ | Ưu tiên nhóm chuyên môn chuẩn hóa do sinh viên chỉ định, hiệu chuẩn an toàn **88% – 92%**. |
| **Tự do (No Hint)** | Không chọn trước nhóm | $Conf = Conf_{\text{raw}}$ | Sử dụng nguyên bản xác suất phân loại của mô hình máy học. |

---

### Giai đoạn 4: Rào chắn Guardrails & Phân luồng tự động
* **Vị trí mã nguồn**: `src/service.py` (Bước 5: `GUARDRAILS_AND_DISPATCH`)
* Hệ thống áp dụng ma trận rào chắn dựa trên các ngưỡng độ tin cậy để đưa ra quyết định:

| Ngưỡng tin cậy | Trạng thái xử lý | Hành động của hệ thống |
| :---: | :---: | :--- |
| **$\ge 70\%$** | `AUTO_APPROVED` | **Tự động phê duyệt (AI)**: Đủ điều kiện gửi email giải đáp ngay cho sinh viên nếu khớp quy trình chính thức và không thuộc diện Khẩn cấp. |
| **$50\% - 69\%$** | `REVIEW_QUEUE` | **Chờ cán bộ duyệt**: Chuyển vào hàng đợi chuyên môn để cán bộ kiểm tra hồ sơ và hoàn thiện văn bản. |
| **$< 50\%$** | `NEEDS_REVIEW` | **Cảnh báo quản trị**: Bật cờ cảnh báo nghi vấn *"Độ tự tin dưới 50%"*, bắt buộc rà soát kỹ lưỡng. |
| **$0.0\%$** *(< 12 ký tự)* | `REJECTED` | **Từ chối suy luận**: Nội dung quá ngắn hoặc rỗng, tự động phản hồi hướng dẫn sinh viên bổ sung thông tin. |

---

## 3. CÁC TỆP NGUỒN CỐT LÕI
1. [src/model.py](src/model.py): Trích xuất đặc trưng TF-IDF kép và phân loại Logistic Regression Softmax.
2. [src/service.py](src/service.py): Hiệu chuẩn độ tin cậy theo đồng thuận nghiệp vụ và kiểm tra rào chắn Guardrails.
3. [src/local_machine.py](src/local_machine.py): Lập luận chuỗi Chain-of-Thought và so khớp quy trình tương đồng.
4. [app/components/workbench.py](app/components/workbench.py): Bàn làm việc phân luồng theo ngưỡng độ tin cậy của cán bộ.
