# -*- coding: utf-8 -*-
"""
Module: src.quality_profiler
Quét hồ sơ chất lượng dữ liệu (Data Quality Profiling & Health Check).
Phân tích các chỉ số:
- Tổng số bản ghi, số bản ghi hợp lệ (is_usable)
- Tỷ lệ dữ liệu rỗng / thiếu
- Tỷ lệ trùng lặp tuyệt đối & gần trùng lặp
- Tỷ lệ bản ghi chứa thông tin định danh nhạy cảm (PII: SĐT, Email, MSSV)
- Tỷ lệ câu quá ngắn (< 12 ký tự)
- Phân bố độ dài câu (Min, Max, Mean, Median)
- Phân bố theo 7 nhóm chuyên môn và 4 mức ưu tiên
"""

import os
import json
import pandas as pd
import numpy as np

def profile_dataset(df_or_path) -> dict:
    """
    Phân tích toàn diện sức khỏe dữ liệu đầu vào.
    Nhận vào DataFrame hoặc đường dẫn tệp CSV/Excel.
    """
    if isinstance(df_or_path, str):
        if not os.path.exists(df_or_path):
            raise FileNotFoundError(f"Không tìm thấy tệp: {df_or_path}")
        if df_or_path.endswith(".csv"):
            df = pd.read_csv(df_or_path)
        else:
            df = pd.read_excel(df_or_path)
    else:
        df = df_or_path.copy()

    total_records = len(df)
    if total_records == 0:
        return {"error": "Tập dữ liệu rỗng"}

    # 1. Kiểm tra trường văn bản
    text_col = "clean_text" if "clean_text" in df.columns else ("raw_text" if "raw_text" in df.columns else df.columns[1])
    texts = df[text_col].fillna("").astype(str)

    # 2. Các chỉ số cơ bản
    null_count = df[text_col].isna().sum() + (texts.str.strip() == "").sum()
    null_ratio = float(null_count / total_records)

    # 3. Phân tích độ dài văn bản
    lengths = texts.apply(len)
    short_count = (lengths < 12).sum()
    short_ratio = float(short_count / total_records)

    length_stats = {
        "min": int(lengths.min()),
        "max": int(lengths.max()),
        "mean": float(np.round(lengths.mean(), 1)),
        "median": float(lengths.median())
    }

    # 4. Phân tích cờ chất lượng (quality_flags) nếu có
    has_flags = "quality_flags" in df.columns
    if has_flags:
        flags_series = df["quality_flags"].fillna("").astype(str)
        exact_dups = int(flags_series.str.contains("exact_duplicate").sum())
        near_dups = int(flags_series.str.contains("near_duplicate").sum())
        pii_phones = int(flags_series.str.contains("has_phone").sum())
        pii_emails = int(flags_series.str.contains("has_email").sum())
        pii_mssvs = int(flags_series.str.contains("has_student_id").sum())
        pii_total = int(flags_series.str.contains("has_").sum())
        usable_count = int(df["is_usable"].sum()) if "is_usable" in df.columns else (total_records - exact_dups - short_count)
    else:
        # Nếu chưa có cờ thì tính nhanh sơ bộ
        exact_dups = int(texts.duplicated().sum())
        near_dups = 0
        pii_phones = int(texts.str.contains(r'0[3|5|7|8|9]\d{8}').sum())
        pii_emails = int(texts.str.contains(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+').sum())
        pii_mssvs = int(texts.str.contains(r'20\d{6}').sum())
        pii_total = int(((texts.str.contains(r'0[3|5|7|8|9]\d{8}')) | (texts.str.contains(r'@[a-zA-Z0-9-]+\.'))).sum())
        usable_count = total_records - exact_dups - short_count

    usable_ratio = float(usable_count / total_records)
    duplicate_ratio = float(exact_dups / total_records)
    pii_ratio = float(pii_total / total_records)

    # 5. Phân bố theo danh mục và mức độ ưu tiên
    topic_col = "target_label_gold" if "target_label_gold" in df.columns else ("predicted_topic" if "predicted_topic" in df.columns else None)
    topic_dist = df[topic_col].value_counts().to_dict() if topic_col else {}

    priority_col = "priority_gold" if "priority_gold" in df.columns else ("priority_level" if "priority_level" in df.columns else None)
    priority_dist = df[priority_col].value_counts().to_dict() if priority_col else {}

    # 6. Đánh giá xếp hạng sức khỏe dữ liệu (Data Health Score trên thang 100)
    # Trừ điểm vì: rỗng (-25), trùng lặp (-20), PII lộ (-30), câu quá ngắn (-15)
    health_score = max(0, int(100 - (null_ratio * 40 + duplicate_ratio * 25 + short_ratio * 20 + (pii_ratio * 15 if not has_flags else 0))))

    profile = {
        "total_records": int(total_records),
        "usable_records": int(usable_count),
        "usable_ratio": float(np.round(usable_ratio * 100, 2)),
        "null_count": int(null_count),
        "null_ratio": float(np.round(null_ratio * 100, 2)),
        "exact_duplicates": int(exact_dups),
        "exact_duplicate_ratio": float(np.round(duplicate_ratio * 100, 2)),
        "near_duplicates": int(near_dups),
        "short_records": int(short_count),
        "short_ratio": float(np.round(short_ratio * 100, 2)),
        "pii_stats": {
            "total_pii": int(pii_total),
            "phone_count": int(pii_phones),
            "email_count": int(pii_emails),
            "mssv_count": int(pii_mssvs),
            "pii_ratio": float(np.round(pii_ratio * 100, 2))
        },
        "length_stats": length_stats,
        "topic_distribution": topic_dist,
        "priority_distribution": priority_dist,
        "health_score": health_score
    }

    return profile

if __name__ == "__main__":
    prof = profile_dataset("data/processed/dataset_clean.csv")
    print(json.dumps(prof, indent=2, ensure_ascii=False))
