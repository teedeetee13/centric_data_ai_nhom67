# -*- coding: utf-8 -*-
"""
Module: experiments.run_experiments
Thực thi chuỗi thực nghiệm chuẩn Data-Centric AI (E0 -> E3) trên Fixed Test Set (70 mẫu niêm phong):
- E0 (Baseline): Dữ liệu thô kịch bản, chỉ dropna, TF-IDF từ đơn, Logistic Regression mặc định.
- E1: Tiền xử lý chuẩn hóa Unicode NFC, che giấu PII, khử trùng lặp Canonical MD5.
- E2: Loại bỏ triệt để câu quá ngắn (< 12 ký tự), lọc gần trùng lặp, rà soát nhãn nhất quán.
- E3 (Tối ưu DCAI): Tích hợp Char n-grams (3-5), cân bằng trọng số lớp ('balanced'), tinh chỉnh tham số C.
"""

import os
import json
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, accuracy_score

def run_all_experiments(
    raw_path="data/raw/synthetic_demo_424.csv",
    clean_path="data/processed/dataset_clean.csv",
    test_path="data/splits/test_sealed.csv",
    train_path="data/splits/train.csv",
    output_json="experiments/benchmark_results.json"
):
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    
    # 1. Nạp Fixed Test Set niêm phong
    test_df = pd.read_csv(test_path)
    y_test = test_df["target_label_gold"]

    results = {}

    print("================================================================================")
    print("      CHƯƠNG TRÌNH THỰC NGHIỆM ĐÁNH GIÁ DATA-CENTRIC AI (EDUSUPPORTAI)         ")
    print("================================================================================")
    print(f"[*] Tập kiểm chuẩn niêm phong (Fixed Test Set): {len(test_df)} mẫu.")

    # -------------------------------------------------------------------------
    # E0: Baseline (Dữ liệu thô kịch bản ban đầu, chỉ dropna)
    # -------------------------------------------------------------------------
    raw_df = pd.read_csv(raw_path)
    # Loại bỏ các mẫu trùng ID với test set để đảm bảo tính khách quan
    train_e0 = raw_df[~raw_df["record_id"].isin(test_df["record_id"])].dropna(subset=["raw_text"])

    pipe_e0 = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 1), min_df=1)),
        ("clf", LogisticRegression(C=1.0, solver="lbfgs", random_state=42, max_iter=500))
    ])
    pipe_e0.fit(train_e0["raw_text"], train_e0["target_label_gold"])
    preds_e0 = pipe_e0.predict(test_df["raw_text"])

    f1_macro_e0 = f1_score(y_test, preds_e0, average="macro")
    acc_e0 = accuracy_score(y_test, preds_e0)
    results["E0"] = {
        "name": "E0: Dữ liệu thô (Baseline)",
        "intervention": "Dữ liệu ban đầu, chỉ dropna, TF-IDF từ đơn (1-1)",
        "macro_f1": float(np.round(f1_macro_e0, 4)),
        "accuracy": float(np.round(acc_e0, 4)),
        "delta": "+0.00%"
    }

    # -------------------------------------------------------------------------
    # E1: Tiền xử lý chuẩn hóa Unicode NFC + Che PII + Khử trùng Canonical MD5
    # -------------------------------------------------------------------------
    clean_df = pd.read_csv(clean_path)
    # E1 giữ lại các bản ghi không bị exact duplicate
    train_e1 = clean_df[
        (~clean_df["record_id"].isin(test_df["record_id"])) &
        (~clean_df["quality_flags"].str.contains("exact_duplicate"))
    ]

    pipe_e1 = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(C=1.0, solver="lbfgs", random_state=42, max_iter=500))
    ])
    pipe_e1.fit(train_e1["clean_text"], train_e1["target_label_gold"])
    preds_e1 = pipe_e1.predict(test_df["clean_text"])

    f1_macro_e1 = f1_score(y_test, preds_e1, average="macro")
    acc_e1 = accuracy_score(y_test, preds_e1)
    results["E1"] = {
        "name": "E1: Chuẩn hóa NFC, Che PII & Khử trùng lặp",
        "intervention": "Unicode NFC, [PHONE]/[EMAIL]/[MSSV], khử MD5 hash trùng 100%",
        "macro_f1": float(np.round(f1_macro_e1, 4)),
        "accuracy": float(np.round(acc_e1, 4)),
        "delta": f"+{(f1_macro_e1 - f1_macro_e0)*100:.2f}%"
    }

    # -------------------------------------------------------------------------
    # E2: Loại bỏ triệt để câu quá ngắn (< 12 ký tự) & Gần trùng lặp (is_usable = True)
    # -------------------------------------------------------------------------
    train_e2 = clean_df[
        (~clean_df["record_id"].isin(test_df["record_id"])) &
        (clean_df["is_usable"] == True)
    ]

    pipe_e2 = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(C=1.0, solver="lbfgs", random_state=42, max_iter=500))
    ])
    pipe_e2.fit(train_e2["clean_text"], train_e2["target_label_gold"])
    preds_e2 = pipe_e2.predict(test_df["clean_text"])

    f1_macro_e2 = f1_score(y_test, preds_e2, average="macro")
    acc_e2 = accuracy_score(y_test, preds_e2)
    results["E2"] = {
        "name": "E2: Khử ồn đa ý & Lọc mẫu lỗi (< 12 ký tự)",
        "intervention": "Chỉ giữ is_usable=True, loại sạch câu quá ngắn và near duplicate",
        "macro_f1": float(np.round(f1_macro_e2, 4)),
        "accuracy": float(np.round(acc_e2, 4)),
        "delta": f"+{(f1_macro_e2 - f1_macro_e1)*100:.2f}%"
    }

    # -------------------------------------------------------------------------
    # E3: Tối ưu Data-Centric toàn diện: Char n-grams (3-5) + Cân bằng trọng số lớp
    # -------------------------------------------------------------------------
    train_e3 = pd.read_csv(train_path)

    pipe_e3 = FeatureUnion([
        ("word_tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("char_tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True))
    ])
    
    full_pipe_e3 = Pipeline([
        ("features", pipe_e3),
        ("clf", LogisticRegression(C=1.5, solver="lbfgs", class_weight="balanced", random_state=42, max_iter=500))
    ])
    full_pipe_e3.fit(train_e3["clean_text"], train_e3["target_label_gold"])
    preds_e3 = full_pipe_e3.predict(test_df["clean_text"])

    f1_macro_e3 = f1_score(y_test, preds_e3, average="macro")
    acc_e3 = accuracy_score(y_test, preds_e3)
    results["E3"] = {
        "name": "E3: Tối ưu DCAI + Char n-grams + Cân bằng lớp",
        "intervention": "Trích xuất kép Word+Char n-grams, C=1.5, class_weight='balanced'",
        "macro_f1": float(np.round(f1_macro_e3, 4)),
        "accuracy": float(np.round(acc_e3, 4)),
        "delta": f"+{(f1_macro_e3 - f1_macro_e2)*100:.2f}%"
    }

    # Lưu kết quả
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Hiển thị bảng tổng kết
    print("\n" + "="*85)
    print(f"{'Mốc':<6} | {'Mô tả can thiệp Data-Centric':<42} | {'Macro F1':<10} | {'Độ chính xác':<12} | {'Tăng trưởng':<10}")
    print("-" * 85)
    for k, v in results.items():
        print(f"{k:<6} | {v['name'][:42]:<42} | {v['macro_f1']:<10.4f} | {v['accuracy']:<12.4f} | {v['delta']:<10}")
    print("="*85)
    print(f"\n[+] Tổng tăng trưởng từ Baseline (E0) lên Tối ưu (E3): +{(f1_macro_e3 - f1_macro_e0)*100:.2f}% Macro F1.")
    print(f"[+] Kết quả chi tiết đã được lưu tại: {output_json}\n")

    return results

if __name__ == "__main__":
    run_all_experiments()
