# -*- coding: utf-8 -*-
"""
Module: src.faq_engine
Engine tra cứu quy chế học vụ và tự động gợi ý bản nháp phản hồi.
Tích hợp cơ chế kiểm soát chất lượng:
- Ngưỡng Cosine tối thiểu (0.15) ngăn việc ép câu hỏi vô nghĩa khớp quy chế
- Phân biệt rõ nguồn tài liệu đã xác minh và tài liệu minh họa
- Định dạng bản nháp chuẩn mực hành chính, không emoji
"""

import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.config import KB_PATH

class FAQEngine:
    def __init__(self, kb_path=None, min_similarity=0.15):
        self.kb_path = kb_path or str(KB_PATH)
        self.min_similarity = min_similarity
        self.df_kb = pd.read_csv(self.kb_path).fillna('')
        
        corpus = self.df_kb['question_standard'] + ' ' + self.df_kb['content_extract']
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.kb_vectors = self.vectorizer.fit_transform(corpus)

    def search_regulations(self, query_text: str, filter_topic: str = None, top_k: int = 2) -> list[dict]:
        """Tra cứu điều khoản quy chế dựa trên độ tương đồng Cosine Similarity."""
        sims = cosine_similarity(self.vectorizer.transform([query_text]), self.kb_vectors)[0]
        results = []
        for idx, score in enumerate(sims):
            if float(score) < self.min_similarity:
                continue
            row = self.df_kb.iloc[idx]
            source = str(row.get('source_url', '')).strip()
            verified = str(row.get('verified', '')).lower() in ('true', '1', 'yes') and bool(source)
            results.append({
                'kb_id': row['kb_id'],
                'topic': row['topic'],
                'question_standard': row['question_standard'],
                'content_extract': row['content_extract'],
                'department': row['department'],
                'source_url': source,
                'verified': bool(verified),
                'similarity_score': round(float(score), 4),
                'rank_score': float(score) + (0.10 if row['topic'] == filter_topic else 0.0)
            })
        return sorted(results, key=lambda r: r['rank_score'], reverse=True)[:top_k]

    def generate_draft_response(self, query_text: str, predicted_topic: str = None) -> dict:
        """Tự động tạo bản nháp câu trả lời có cấu trúc và dẫn nguồn quy chế cho Cán bộ rà soát."""
        articles = self.search_regulations(query_text, filter_topic=predicted_topic, top_k=2)
        if not articles:
            return {
                'matched_kb_id': None,
                'matched_regulation': None,
                'department': 'Bộ phận tiếp nhận',
                'similarity_score': 0.0,
                'articles': [],
                'draft_text': 'Chào bạn, bộ phận hỗ trợ đã tiếp nhận nội dung. Hiện chưa có tài liệu đủ phù hợp để trả lời cụ thể. Bạn vui lòng bổ sung thông tin để cán bộ xác minh và hướng dẫn. Trân trọng.'
            }
        
        item = articles[0]
        if item['verified']:
            draft = (
                f"Chào bạn,\n\n"
                f"Theo tài liệu {item['kb_id']} ({item['question_standard']}):\n"
                f"{item['content_extract']}\n\n"
                f"Đơn vị gợi ý liên hệ: {item['department']}.\n\n"
                f"Trân trọng."
            )
        else:
            draft = (
                f"BẢN NHÁP DEMO — CHƯA XÁC MINH QUY ĐỊNH\n\n"
                f"Chào bạn,\n"
                f"Bộ phận hỗ trợ đã tiếp nhận yêu cầu về {item['question_standard'].lower()}. "
                f"Đơn vị được gợi ý để cán bộ xác minh là {item['department']}. "
                f"Cán bộ cần đối chiếu tài liệu hiện hành và bổ sung hướng dẫn cụ thể trước khi sử dụng.\n\n"
                f"Trân trọng."
            )

        return {
            'matched_kb_id': item['kb_id'],
            'matched_regulation': item['question_standard'],
            'department': item['department'],
            'similarity_score': item['similarity_score'],
            'articles': articles,
            'draft_text': draft
        }

if __name__ == "__main__":
    faq = FAQEngine()
    test_res = faq.generate_draft_response("Em nộp học phí qua ngân hàng rồi mà cổng vẫn báo nợ", "Hoc_phi")
    print(test_res["draft_text"])
