# -*- coding: utf-8 -*-
"""
Module: src.faq_engine
Engine tra cứu quy chế học vụ và tự động gợi ý bản nháp phản hồi (DRAFT RESPONSE GENERATOR).
- Nạp kho tri thức quy chế từ data/kb/eaut_faq_kb.csv (hoặc SQLite knowledge_base)
- Trích xuất TF-IDF và tính độ tương đồng Cosine Similarity
- Tìm kiếm điều khoản quy định phù hợp nhất với thắc mắc của sinh viên
- Tự động biên tập bản nháp phản hồi có cấu trúc chuẩn mực:
  + Chào hỏi lịch sự
  + Trích dẫn điều khoản quy chế (Mã KB, Tên văn bản)
  + Hướng dẫn quy trình xử lý cụ thể
  + Chỉ định phòng ban phụ trách tiếp nhận & xử lý
"""

import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kb", "eaut_faq_kb.csv")

class FAQEngine:
    def __init__(self, kb_path=KB_DEFAULT_PATH):
        self.kb_path = kb_path
        self.df_kb = None
        self.vectorizer = None
        self.kb_vectors = None
        self._load_and_index()

    def _load_and_index(self):
        """Nạp dữ liệu tri thức và xây dựng chỉ mục ma trận TF-IDF."""
        if not os.path.exists(self.kb_path):
            raise FileNotFoundError(f"Không tìm thấy kho tri thức quy chế tại: {self.kb_path}")

        self.df_kb = pd.read_csv(self.kb_path)
        
        # Tạo chuỗi văn bản tổng hợp để tìm kiếm (câu hỏi mẫu + nội dung trích lục + chủ đề)
        corpus = (
            self.df_kb["topic"].fillna("") + " " +
            self.df_kb["question_standard"].fillna("") + " " +
            self.df_kb["content_extract"].fillna("")
        ).tolist()

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True
        )
        self.kb_vectors = self.vectorizer.fit_transform(corpus)
        print(f"[*] FAQ Engine đã lập chỉ mục {len(self.df_kb)} điều khoản quy chế EAUT.")

    def search_regulations(self, query_text: str, filter_topic: str = None, top_k: int = 2) -> list[dict]:
        """
        Tra cứu điều khoản quy chế dựa trên độ tương đồng Cosine Similarity.
        Có thể lọc ưu tiên theo topic đã được phân loại bởi Model.
        """
        if self.vectorizer is None or self.kb_vectors is None:
            return []

        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.kb_vectors)[0]

        results = []
        for idx, score in enumerate(similarities):
            row = self.df_kb.iloc[idx]
            final_score = float(score)

            # Tăng điểm thưởng nếu trùng khớp topic do mô hình dự đoán
            if filter_topic and row["topic"] == filter_topic:
                final_score += 0.25

            results.append({
                "kb_id": row["kb_id"],
                "topic": row["topic"],
                "question_standard": row["question_standard"],
                "content_extract": row["content_extract"],
                "department": row["department"],
                "effective_date": row.get("effective_date", "2025-08-15"),
                "similarity_score": float(np.round(final_score, 4))
            })

        # Sắp xếp giảm dần theo điểm tương đồng
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    def generate_draft_response(self, query_text: str, predicted_topic: str = None) -> dict:
        """
        Tự động tạo bản nháp câu trả lời có cấu trúc dẫn nguồn quy chế cho Cán bộ rà soát.
        """
        matched = self.search_regulations(query_text, filter_topic=predicted_topic, top_k=1)
        
        if not matched or matched[0]["similarity_score"] < 0.15:
            # Trường hợp không tìm thấy quy chế khớp
            draft = (
                "Chào bạn,\n\n"
                "Bộ phận hỗ trợ sinh viên đã tiếp nhận thông tin phản ánh của bạn. "
                "Yêu cầu của bạn đang được chuyển đến ban chuyên môn có thẩm quyền để xác minh và phản hồi trực tiếp qua Cổng thông tin sinh viên hoặc Email trong vòng 24h làm việc.\n\n"
                "Trân trọng cảm ơn bạn."
            )
            return {
                "matched_kb_id": None,
                "matched_regulation": None,
                "draft_text": draft,
                "department": "Ban Tiếp nhận & Xử lý phản hồi",
                "similarity_score": 0.0
            }

        top_match = matched[0]
        kb_id = top_match["kb_id"]
        reg_title = top_match["question_standard"]
        content = top_match["content_extract"]
        dept = top_match["department"]

        draft = (
            f"Chào bạn,\n\n"
            f"Bộ phận hỗ trợ sinh viên Trường ĐH Công nghệ Đông Á xin phản hồi thắc mắc của bạn như sau:\n\n"
            f"[CĂN CỨ QUY CHẾ ({kb_id} - {reg_title})]:\n"
            f"\"{content}\"\n\n"
            f"[HƯỚNG DẪN XỬ LÝ]:\n"
            f"Bạn vui lòng thực hiện theo đúng hướng dẫn trên. Nếu cần nộp hồ sơ hoặc xác minh thêm thông tin, bạn hãy liên hệ trực tiếp tại {dept}.\n\n"
            f"Chúc bạn học tập và rèn luyện tốt!"
        )

        return {
            "matched_kb_id": kb_id,
            "matched_regulation": reg_title,
            "draft_text": draft,
            "department": dept,
            "similarity_score": top_match["similarity_score"]
        }

if __name__ == "__main__":
    engine = FAQEngine()
    test_query = "Em nộp tiền học qua ngân hàng rồi mà cổng vẫn báo nợ thì làm sao?"
    res = engine.generate_draft_response(test_query, predicted_topic="Hoc_phi")
    print("\n--- TEST DRAFT RESPONSE ---")
    print(res["draft_text"])
