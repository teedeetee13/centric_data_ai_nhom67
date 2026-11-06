# -*- coding: utf-8 -*-
"""
Module: src.quality_profiler
Quét hồ sơ chất lượng dữ liệu (Data Quality Profiling & Health Check).
Sử dụng chung một định nghĩa chất lượng duy nhất từ src.cleaner:
- Tính toán chính xác trên dữ liệu nạp vào (không số liệu giả định)
- Phát hiện rỗng, quá ngắn, trùng lặp tuyệt đối, gần trùng lặp và các loại PII
"""

from pathlib import Path
import pandas as pd
import numpy as np
from src.cleaner import clean_dataframe

def profile_dataset(df_or_path, text_col=None) -> dict:
    """
    Phân tích toàn diện chất lượng và độ an toàn của tập dữ liệu.
    Nhận vào DataFrame hoặc đường dẫn tệp CSV/Excel.
    """
    if isinstance(df_or_path, (str, Path)):
        path = Path(df_or_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy tệp: {path}")
        df = pd.read_csv(path) if path.suffix.lower() == '.csv' else pd.read_excel(path)
    else:
        df = df_or_path.copy()

    total_records = len(df)
    if total_records == 0:
        return {'total_records': 0, 'usable_records': 0, 'null_count': 0, 'usable_ratio': 0.0}

    # Tự động tìm cột văn bản phù hợp nếu chưa chỉ định
    text_col = text_col or next((c for c in ('raw_text', 'clean_text', 'content', 'noi_dung', 'text') if c in df.columns), df.columns[0])
    
    out = clean_dataframe(df, text_col)
    flags = out['quality_flags']
    
    usable_count = int(out['is_usable'].sum())
    usable_ratio = round(float(usable_count / total_records * 100), 2)
    null_count = int(flags.str.contains('empty').sum())
    short_records = int(flags.str.contains('too_short').sum())
    short_ratio = round(float(short_records / total_records * 100), 2)
    exact_duplicates = int(flags.str.contains('exact_duplicate').sum())
    exact_duplicate_ratio = round(float(exact_duplicates / total_records * 100), 2)
    near_duplicates = int(flags.str.contains('near_duplicate').sum())
    pii_records = int(flags.str.contains('has_').sum())
    
    phone_count = int(flags.str.contains('has_phone').sum())
    email_count = int(flags.str.contains('has_email').sum())
    mssv_count = int(flags.str.contains('has_student_id').sum())

    health_score = max(0, int(100 - (
        (null_count / total_records) * 35 +
        (exact_duplicates / total_records) * 25 +
        (short_records / total_records) * 20 +
        (pii_records / total_records) * 20
    )))

    return {
        'total_records': total_records,
        'usable_records': usable_count,
        'usable_ratio': usable_ratio,
        'null_count': null_count,
        'short_records': short_records,
        'short_ratio': short_ratio,
        'exact_duplicates': exact_duplicates,
        'exact_duplicate_ratio': exact_duplicate_ratio,
        'near_duplicates': near_duplicates,
        'pii_records': pii_records,
        'pii_stats': {
            'total_pii': pii_records,
            'phone_count': phone_count,
            'email_count': email_count,
            'mssv_count': mssv_count
        },
        'health_score': health_score,
        'df_processed': out
    }

if __name__ == "__main__":
    prof = profile_dataset("data/raw/synthetic_demo_424.csv")
    print(prof)
