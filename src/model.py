# -*- coding: utf-8 -*-
"""
Module: src.model
Lõi trích xuất đặc trưng và mô hình học máy phân loại phản ánh sinh viên:
- Trích xuất đặc trưng kép: Word n-grams (1, 2) kết hợp Char n-grams (3, 5) chống teencode/lỗi gõ
- Thuật toán phân loại: Logistic Regression (L2, OvR)
- Ước lượng độ tự tin (Confidence Score = max(predict_proba))
- Cây quyết định gán mức độ ưu tiên theo từ khóa chuyên môn (Khẩn cấp / Cao / Bình thường / Thấp)
- Hỗ trợ lưu trữ, tải mô hình (.joblib) và suy luận thời gian thực
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score

# Từ khóa kích hoạt mức độ ưu tiên
KEYWORDS_URGENT = [
    "đình chỉ", "sai điểm", "tai nạn", "hết hạn hôm nay", "mất nước",
    "nghẽn mạng", "cứu em", "khẩn cấp", "nhập viện", "trùng ca thi", "trùng lịch thi"
]

KEYWORDS_HIGH = [
    "gia hạn", "phúc khảo", "không thi được", "khóa cửa", "hỏng điều hòa",
    "lỗi giao dịch", "rút hồ sơ", "quên mật khẩu", "quên pass", "khóa tài khoản",
    "chưa nộp", "nhập nhầm"
]

KEYWORDS_LOW = [
    "câu lạc bộ", "xe đưa đón", "cây xanh", "mùa hè xanh", "góp ý",
    "học phí kỳ phụ", "bàn ghế", "wifi yếu"
]

def determine_priority(text: str, default_priority="Bình thường") -> str:
    """Cây quyết định gán mức độ ưu tiên nghiệp vụ."""
    t_lower = text.lower()
    for kw in KEYWORDS_URGENT:
        if kw in t_lower:
            return "Khẩn cấp"
    for kw in KEYWORDS_HIGH:
        if kw in t_lower:
            return "Cao"
    for kw in KEYWORDS_LOW:
        if kw in t_lower:
            return "Thấp"
    return default_priority

class EduSupportClassifier:
    def __init__(self, c_val=1.0, class_weight=None):
        self.c_val = c_val
        self.class_weight = class_weight
        self.model = None
        self.classes_ = []

    def _build_pipeline(self):
        # Trích xuất kết hợp cấp từ và cấp ký tự
        features = FeatureUnion([
            ("word_tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95,
                sublinear_tf=True
            )),
            ("char_tfidf", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=1,
                sublinear_tf=True
            ))
        ])

        classifier = LogisticRegression(
            C=self.c_val,
            solver="lbfgs",
            class_weight=self.class_weight,
            random_state=42,
            max_iter=500
        )

        return Pipeline([
            ("features", features),
            ("clf", classifier)
        ])

    def train(self, X_train, y_train):
        """Huấn luyện pipeline phân loại."""
        self.model = self._build_pipeline()
        self.model.fit(X_train, y_train)
        self.classes_ = list(self.model.classes_)
        return self

    def evaluate(self, X_test, y_test) -> dict:
        """Đánh giá mô hình trên tập kiểm chuẩn."""
        y_pred = self.model.predict(X_test)
        macro_f1 = f1_score(y_test, y_pred, average="macro")
        weighted_f1 = f1_score(y_test, y_pred, average="weighted")
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        return {
            "macro_f1": float(np.round(macro_f1, 4)),
            "weighted_f1": float(np.round(weighted_f1, 4)),
            "report": report,
            "y_pred": list(y_pred)
        }

    def predict_single(self, text: str) -> dict:
        """Dự đoán đơn lẻ thời gian thực cho Streamlit workbench."""
        if self.model is None:
            raise ValueError("Mô hình chưa được huấn luyện hoặc nạp!")

        # Dự đoán xác suất
        probs = self.model.predict_proba([text])[0]
        max_idx = np.argmax(probs)
        predicted_topic = self.classes_[max_idx]
        confidence = float(np.round(probs[max_idx], 4))

        # Phân loại tất cả các xác suất
        topic_probs = {cls_name: float(np.round(p, 4)) for cls_name, p in zip(self.classes_, probs)}
        
        # Mức độ ưu tiên nghiệp vụ
        priority = determine_priority(text)

        return {
            "predicted_topic": predicted_topic,
            "confidence_score": confidence,
            "priority_level": priority,
            "all_probabilities": topic_probs,
            "needs_review": bool(confidence < 0.60)
        }

    def save(self, filepath="models/best_classifier.joblib"):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.model, filepath)
        print(f"[*] Đã lưu mô hình tốt nhất tại: {filepath}")

    def load(self, filepath="models/best_classifier.joblib"):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Không tìm thấy mô hình tại {filepath}")
        self.model = joblib.load(filepath)
        self.classes_ = list(self.model.named_steps["clf"].classes_)
        return self

def train_and_save_production_model(train_path="data/splits/train.csv", model_path="models/best_classifier.joblib"):
    """Huấn luyện mô hình chuẩn triển khai sản phẩm."""
    if not os.path.exists(train_path):
        from src.cleaner import run_cleaning_pipeline
        run_cleaning_pipeline()

    train_df = pd.read_csv(train_path)
    X_train = train_df["clean_text"]
    y_train = train_df["target_label_gold"]

    clf = EduSupportClassifier(c_val=1.5, class_weight="balanced")
    clf.train(X_train, y_train)
    clf.save(model_path)
    return clf

if __name__ == "__main__":
    train_and_save_production_model()
