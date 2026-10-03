# -*- coding: utf-8 -*-
"""
Module: src.cleaner
Pipeline làm sạch dữ liệu và bảo mật PII theo triết lý Data-Centric AI (DCAI):
1. Chuẩn hóa font Unicode dựng sẵn (NFC) & khoảng trắng
2. Che giấu thông tin định danh cá nhân PII ([PHONE], [EMAIL], [STUDENT_ID])
3. Phát hiện và gắn cờ câu quá ngắn (< 12 ký tự)
4. Khử trùng lặp tuyệt đối (Canonical MD5 Hash) và gần trùng lặp (SequenceMatcher >= 0.93)
5. Xuất tập dữ liệu sạch và phân chia Train / Val / Test (Fixed Test Set 70 mẫu niêm phong)
"""

import os
import re
import hashlib
import unicodedata
import difflib
import pandas as pd
from sklearn.model_selection import train_test_split

# Regex patterns cho PII tiếng Việt và sinh viên EAUT
REGEX_PHONE = re.compile(r'(\b0[3|5|7|8|9][0-9]{8}\b)')
REGEX_EMAIL = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
REGEX_STUDENT_ID = re.compile(r'(\b(20[0-9]{6}|[0-9]{8,10})\b)')

def normalize_unicode_and_whitespace(text: str) -> str:
    """Chuẩn hóa Unicode NFC và dọn dẹp khoảng trắng thừa."""
    if not isinstance(text, str):
        return ""
    # Chuẩn hóa Unicode dựng sẵn (NFC)
    text = unicodedata.normalize('NFC', text)
    # Gộp khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def mask_pii(text: str) -> tuple[str, list[str]]:
    """
    Che giấu PII thành các token chuẩn hóa: [PHONE], [EMAIL], [STUDENT_ID].
    Trả về (text_đã_che, danh_sách_cờ_pii).
    """
    pii_flags = []
    
    if REGEX_PHONE.search(text):
        pii_flags.append("has_phone")
        text = REGEX_PHONE.sub('[PHONE]', text)

    if REGEX_EMAIL.search(text):
        pii_flags.append("has_email")
        text = REGEX_EMAIL.sub('[EMAIL]', text)

    if REGEX_STUDENT_ID.search(text):
        pii_flags.append("has_student_id")
        text = REGEX_STUDENT_ID.sub('[STUDENT_ID]', text)

    return text, pii_flags

def get_canonical_hash(text: str) -> str:
    """Tạo mã băm MD5 chuẩn tắc để phát hiện trùng lặp tuyệt đối (bỏ qua dấu câu, viết hoa)."""
    canonical = re.sub(r'[^\w\s]', '', text.lower())
    canonical = re.sub(r'\s+', ' ', canonical).strip()
    return hashlib.md5(canonical.encode('utf-8')).hexdigest()

def clean_text_single(raw_text: str) -> dict:
    """
    Hàm làm sạch đơn lẻ phục vụ kiểm thử nhanh và tích hợp trực tiếp trên Giao diện Streamlit.
    """
    norm = normalize_unicode_and_whitespace(raw_text)
    masked, pii_flags = mask_pii(norm)
    
    flags = list(pii_flags)
    is_usable = True

    if len(norm) < 12:
        flags.append("too_short")
        is_usable = False

    return {
        "raw_text": raw_text,
        "clean_text": masked,
        "quality_flags": flags,
        "is_usable": is_usable,
        "char_len": len(masked)
    }

def run_cleaning_pipeline(
    raw_path="data/raw/synthetic_demo_424.csv",
    processed_path="data/processed/dataset_clean.csv",
    splits_dir="data/splits"
):
    """
    Thực thi toàn bộ quy trình làm sạch từ tệp dữ liệu thô:
    - Gắn thẻ chất lượng
    - Khử trùng lặp
    - Lưu tệp sạch
    - Tách tập dữ liệu train / val / test_sealed
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Không tìm thấy tệp đầu vào: {raw_path}")

    df = pd.read_csv(raw_path)
    print(f"[*] Tiếp nhận {len(df)} bản ghi từ {raw_path}")

    clean_records = []
    seen_hashes = {}
    cleaned_corpus = [] # Lưu các câu sạch để so sánh SequenceMatcher

    for idx, row in df.iterrows():
        raw_text = str(row["raw_text"])
        res = clean_text_single(raw_text)
        
        flags = res["quality_flags"]
        is_usable = res["is_usable"]
        clean_t = res["clean_text"]

        # Kiểm tra trùng lặp tuyệt đối (Canonical Hash)
        c_hash = get_canonical_hash(clean_t)
        if c_hash in seen_hashes:
            flags.append("exact_duplicate")
            is_usable = False
        else:
            seen_hashes[c_hash] = row["record_id"]

            # Nếu không trùng tuyệt đối, kiểm tra gần trùng lặp (SequenceMatcher >= 0.93)
            # Chỉ kiểm tra với các câu có độ dài > 20 ký tự
            if is_usable and len(clean_t) > 20:
                is_near = False
                for prev_id, prev_text in cleaned_corpus[-50:]: # So với 50 câu gần nhất
                    sim = difflib.SequenceMatcher(None, clean_t, prev_text).ratio()
                    if sim >= 0.93:
                        flags.append(f"near_duplicate_{prev_id}")
                        is_usable = False
                        is_near = True
                        break
                if not is_near:
                    cleaned_corpus.append((row["record_id"], clean_t))

        record_data = dict(row)
        record_data["clean_text"] = clean_t
        record_data["quality_flags"] = ";".join(flags) if flags else "CLEAN"
        record_data["is_usable"] = is_usable
        record_data["char_length"] = len(clean_t)
        clean_records.append(record_data)

    df_clean = pd.DataFrame(clean_records)
    
    os.makedirs(os.path.dirname(processed_path), exist_ok=True)
    df_clean.to_csv(processed_path, index=False, encoding="utf-8")
    print(f"[*] Đã xuất dữ liệu sạch tại: {processed_path}")

    # Thống kê kết quả làm sạch
    total = len(df_clean)
    usable_count = df_clean["is_usable"].sum()
    exact_dups = df_clean["quality_flags"].str.contains("exact_duplicate").sum()
    near_dups = df_clean["quality_flags"].str.contains("near_duplicate").sum()
    pii_count = df_clean["quality_flags"].str.contains("has_").sum()
    short_count = df_clean["quality_flags"].str.contains("too_short").sum()

    print("\n--- BÁO CÁO CHỈ SỐ LÀM SẠCH DỮ LIỆU ---")
    print(f"Tổng số mẫu tiếp nhận: {total}")
    print(f"- Số mẫu hợp lệ sử dụng được (is_usable = True): {usable_count} ({usable_count/total*100:.2f}%)")
    print(f"- Số mẫu trùng lặp tuyệt đối đã khử: {exact_dups} ({exact_dups/total*100:.2f}%)")
    print(f"- Số mẫu gần trùng lặp đã gắn cờ: {near_dups} ({near_dups/total*100:.2f}%)")
    print(f"- Số mẫu chứa PII đã che giấu an toàn: {pii_count} ({pii_count/total*100:.2f}%)")
    print(f"- Số mẫu quá ngắn đã loại bỏ: {short_count} ({short_count/total*100:.2f}%)")

    # Phân chia dữ liệu Train / Val / Test (Fixed Test Set 70 mẫu niêm phong)
    usable_df = df_clean[df_clean["is_usable"] == True].copy()
    os.makedirs(splits_dir, exist_ok=True)

    # Cố định test_sealed.csv với đúng 70 mẫu phân tầng đều qua 7 lớp (10 mẫu/lớp)
    test_sealed_list = []
    for label, group in usable_df.groupby("target_label_gold"):
        test_sealed_list.append(group.sample(n=min(len(group), 10), random_state=42))
    test_sealed = pd.concat(test_sealed_list).sample(frac=1.0, random_state=42).reset_index(drop=True)

    # Lấy các mẫu còn lại làm Train và Val
    remaining_df = usable_df[~usable_df["record_id"].isin(test_sealed["record_id"])].copy()

    # Phân chia Train (80%) và Val (20%) có stratified
    train_df, val_df = train_test_split(
        remaining_df,
        test_size=0.20,
        random_state=42,
        stratify=remaining_df["target_label_gold"]
    )

    test_path = os.path.join(splits_dir, "test_sealed.csv")
    train_path = os.path.join(splits_dir, "train.csv")
    val_path = os.path.join(splits_dir, "val.csv")

    test_sealed.to_csv(test_path, index=False, encoding="utf-8")
    train_df.to_csv(train_path, index=False, encoding="utf-8")
    val_df.to_csv(val_path, index=False, encoding="utf-8")

    print(f"\n[*] Đã phân chia tập dữ liệu chuẩn mốc thực nghiệm:")
    print(f"    - Fixed Test Set (niêm phong E0-E3): {len(test_sealed)} mẫu -> {test_path}")
    print(f"    - Train Set: {len(train_df)} mẫu -> {train_path}")
    print(f"    - Validation Set: {len(val_df)} mẫu -> {val_path}")

    return df_clean

if __name__ == "__main__":
    run_cleaning_pipeline()
