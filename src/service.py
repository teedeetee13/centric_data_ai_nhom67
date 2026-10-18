# -*- coding: utf-8 -*-
"""
Module: src.service
Tầng Service điều phối toàn bộ chuỗi xử lý đầu - cuối:
Đầu vào thô -> Làm sạch & Che PII -> Phân loại Machine Learning -> Tra cứu quy chế FAQ -> Soạn thảo bản nháp & Đánh giá lý do rà soát
"""

import warnings
from src.cleaner import clean_text_single
from src.config import MODEL_PATH
from src.faq_engine import FAQEngine
from src.model import EduSupportClassifier, KEYWORDS_URGENT, KEYWORDS_HIGH, KEYWORDS_LOW

def load_classifier():
    """Tải mô hình phân loại đã được huấn luyện và tuần tự hóa."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return EduSupportClassifier().load(str(MODEL_PATH))

def priority_reason(text: str) -> str:
    """Giải trình lý do gán mức độ ưu tiên nghiệp vụ."""
    t_lower = text.lower()
    for label, keywords in [('Khẩn cấp', KEYWORDS_URGENT), ('Cao', KEYWORDS_HIGH), ('Thấp', KEYWORDS_LOW)]:
        for word in keywords:
            if word in t_lower:
                return f"Quy tắc mức {label}: phát hiện từ khóa '{word}'."
    return "Không có từ khóa ưu tiên đặc biệt; phân luồng mức Bình thường."

class RequestService:
    def __init__(self, classifier=None, faq=None):
        self.classifier = classifier if classifier is not None else load_classifier()
        self.faq = faq if faq is not None else FAQEngine()

    def process(self, raw_text: str) -> dict:
        """Thực thi toàn bộ luồng xử lý phản ánh sinh viên."""
        if isinstance(raw_text, str) and len(raw_text) > 8000:
            raise ValueError("Hệ thống tiếp nhận tối đa 8.000 ký tự cho mỗi yêu cầu phản ánh.")
        
        result = clean_text_single(raw_text)
        result.pop('raw_text', None)
        result['priority_reason'] = priority_reason(result['clean_text'])
        result['review_reasons'] = []

        if result['is_usable']:
            pred = self.classifier.predict_single(result['clean_text'])
            result.update(pred)
            draft = self.faq.generate_draft_response(result['clean_text'], pred['predicted_topic'])
            result.update({
                'department': draft['department'],
                'matched_kb_id': draft['matched_kb_id'],
                'articles': draft.get('articles', []),
                'draft_response': draft['draft_text']
            })

            if pred['confidence_score'] < 0.60:
                result['review_reasons'].append("Độ tự tin phân loại dưới 60%; cần cán bộ xác minh nhóm chuyên môn.")
            if not draft.get('articles'):
                result['review_reasons'].append("Chưa tìm thấy điều khoản quy chế đủ tương đồng để viện dẫn.")
            elif not all(a.get('verified', False) for a in draft['articles']):
                result['review_reasons'].append("Tài liệu tham chiếu thuộc dạng minh họa, chưa xác minh quy định chính thức.")
        else:
            result.update({
                'predicted_topic': 'Khac',
                'confidence_score': 0.0,
                'priority_level': 'Thấp',
                'department': 'Bộ phận tiếp nhận',
                'matched_kb_id': None,
                'articles': [],
                'draft_response': (
                    "Chào bạn, nội dung chưa đủ thông tin để xử lý. "
                    "Bạn vui lòng bổ sung mô tả vấn đề, thời điểm và việc cần hỗ trợ. Trân trọng."
                )
            })
            result['review_reasons'].append("Nội dung rỗng hoặc quá ngắn (dưới 12 ký tự).")

        if result['quality_flags']:
            result['review_reasons'].append("Có cờ chất lượng: " + ", ".join(result['quality_flags']))

        result['needs_review'] = bool(result['review_reasons'])
        return result
