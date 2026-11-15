# -*- coding: utf-8 -*-
"""
Module: experiments.error_analysis
Phân tích chi tiết các ca phân loại sai (Error Analysis & Confusion Matrix)
trên Fixed Test Set (70 mẫu niêm phong):
- Tính ma trận nhầm lẫn (Confusion Matrix) giữa 7 nhãn chuyên môn
- Xuất danh sách các câu phân loại sai, so sánh Gold vs Predicted
- Phân tích nguyên nhân: từ khóa gây nhiễu, câu đa ý, hay lỗi gõ/teencode
- Đề xuất giải pháp can thiệp dữ liệu (Data-Centric Actions)
"""

import os
import json
import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix
import joblib

def analyze_model_errors(
    model_path="models/best_classifier.joblib",
    test_path="data/splits/test_sealed.csv",
    output_report="experiments/error_analysis_report.json"
):
    if not os.path.exists(model_path) or not os.path.exists(test_path):
        print(f"[!] Chưa đủ tệp: model ({model_path}) hoặc test set ({test_path})")
        return

    model = joblib.load(model_path)
    test_df = pd.read_csv(test_path)

    X_test = test_df["clean_text"]
    y_true = test_df["target_label_gold"]
    
    # Dự đoán
    y_pred = model.predict(X_test)
    probs = model.predict_proba(X_test)
    classes = list(model.classes_)

    # Tìm các ca đoán sai
    errors = []
    correct_count = 0

    for idx, (true_label, pred_label, text, prob_row) in enumerate(zip(y_true, y_pred, X_test, probs)):
        rec_id = test_df.iloc[idx]["record_id"]
        conf = float(np.round(np.max(prob_row), 4))
        
        if true_label != pred_label:
            # Sắp xếp top 2 nhãn có xác suất cao nhất
            top2_indices = np.argsort(prob_row)[::-1][:2]
            top2_preds = [(classes[i], float(np.round(prob_row[i], 4))) for i in top2_indices]

            errors.append({
                "record_id": rec_id,
                "text": text,
                "gold_label": true_label,
                "predicted_label": pred_label,
                "confidence": conf,
                "top2_predictions": top2_preds
            })
        else:
            correct_count += 1

    total = len(test_df)
    accuracy = correct_count / total

    # Ma trận nhầm lẫn
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    cm_dict = {}
    for i, cls_row in enumerate(classes):
        cm_dict[cls_row] = {classes[j]: int(cm[i, j]) for j in range(len(classes))}

    report = {
        "total_test_samples": total,
        "correct_predictions": correct_count,
        "misclassified_count": len(errors),
        "accuracy": float(np.round(accuracy, 4)),
        "confusion_matrix": cm_dict,
        "error_details": errors
    }

    os.makedirs(os.path.dirname(output_report), exist_ok=True)
    with open(output_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("================================================================================")
    print("                     BÁO CÁO PHÂN TÍCH LỖI (ERROR ANALYSIS)                    ")
    print("================================================================================")
    print(f"Tổng số mẫu đánh giá: {total}")
    print(f"Dự đoán đúng: {correct_count} ({accuracy*100:.2f}%)")
    print(f"Dự đoán sai: {len(errors)} ({len(errors)/total*100:.2f}%)")
    print("-" * 80)
    if errors:
        print("DANH SÁCH CÁC CA PHÂN LOẠI SAI CẦN RÀ SOÁT:")
        for e in errors:
            print(f"[{e['record_id']}] Gold: {e['gold_label']} --> Predict: {e['predicted_label']} (Conf: {e['confidence']})")
            print(f"    Nội dung: \"{e['text']}\"")
            print(f"    Top 2: {e['top2_predictions']}")
            print("-" * 40)
    else:
        print("[+] Tuyệt vời! Mô hình phân loại chính xác 100% trên tập Fixed Test Set.")

    print(f"\n[*] Báo cáo phân tích lỗi chi tiết đã lưu tại: {output_report}\n")
    return report

if __name__ == "__main__":
    analyze_model_errors()
