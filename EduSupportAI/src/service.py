# -*- coding: utf-8 -*-
"""
Module: src.service
Tầng Service điều phối toàn bộ chuỗi xử lý đầu - cuối:
Đầu vào thô -> Làm sạch & Che PII -> Phân loại Machine Learning -> Ghép quy trình nghiệp vụ (ticket)
-> Tra cứu quy chế FAQ -> Soạn bản nháp (LLM cục bộ có kiểm tra bám nguồn, hoặc theo mẫu) & Đánh giá lý do rà soát
"""

import warnings
from src.cleaner import clean_text_single
from src.config import MODEL_PATH
from src.faq_engine import FAQEngine
from src.local_llm import LocalLLM
from src.model import EduSupportClassifier, KEYWORDS_URGENT, KEYWORDS_HIGH, KEYWORDS_LOW
from src.procedure_engine import ProcedureEngine, context_for_llm, render_template_reply

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
    def __init__(self, classifier=None, faq=None, procedures=None, llm=None):
        self.classifier = classifier if classifier is not None else load_classifier()
        self.faq = faq if faq is not None else FAQEngine()
        self.procedures = procedures if procedures is not None else ProcedureEngine()
        self.llm = llm if llm is not None else LocalLLM()

    def _draft_from_procedure(self, clean_text: str, plan: dict) -> dict:
        """Soạn bản nháp từ quy trình: ưu tiên LLM cục bộ, loại bản nháp không bám nguồn."""
        template = render_template_reply(plan)
        generated = self.llm.generate_reply(clean_text, context_for_llm(plan))
        if generated and generated['grounded']:
            return {'text': generated['text'], 'source': 'llm', 'model': generated['model'],
                    'rejected_facts': []}
        if generated:
            return {'text': template, 'source': 'template_fallback', 'model': generated['model'],
                    'rejected_facts': generated['ungrounded_facts']}
        return {'text': template, 'source': 'template', 'model': None, 'rejected_facts': []}

    def process(self, raw_text: str) -> dict:
        """Thực thi toàn bộ luồng xử lý phản ánh sinh viên."""
        if isinstance(raw_text, str) and len(raw_text) > 8000:
            raise ValueError("Hệ thống tiếp nhận tối đa 8.000 ký tự cho mỗi yêu cầu phản ánh.")
        
        result = clean_text_single(raw_text)
        result.pop('raw_text', None)
        result['priority_reason'] = priority_reason(result['clean_text'])
        result['review_reasons'] = []
        result['ticket_plan'] = None
        result['draft_source'] = 'template'

        if result['is_usable']:
            pred = self.classifier.predict_single(result['clean_text'])
            result.update(pred)
            draft = self.faq.generate_draft_response(result['clean_text'], pred['predicted_topic'])
            matches = self.procedures.match(result['clean_text'], pred['predicted_topic'], top_k=1)

            if matches:
                # Có quy trình nghiệp vụ: định tuyến và soạn bản nháp theo quy trình; FAQ chỉ làm tham chiếu phụ
                plan = self.procedures.build_ticket_plan(result['clean_text'], matches[0]['procedure'], matches[0]['score'])
                composed = self._draft_from_procedure(result['clean_text'], plan)
                result.update({
                    'ticket_plan': plan,
                    'department': plan['receiving_unit'],
                    'matched_kb_id': plan['procedure_id'],
                    'articles': [self.procedures.plan_to_article(plan)] + draft.get('articles', [])[:1],
                    'draft_response': composed['text'],
                    'draft_source': composed['source'],
                    'llm_model': composed['model'],
                })
                if composed['source'] == 'llm':
                    result['review_reasons'].append(
                        f"Bản nháp do mô hình ngôn ngữ cục bộ ({composed['model']}) soạn từ quy trình {plan['procedure_id']}; "
                        "cán bộ đọc lại trước khi gửi.")
                if composed['source'] == 'template_fallback':
                    result['review_reasons'].append(
                        "Bản nháp của mô hình ngôn ngữ có dữ kiện không có trong quy trình ("
                        + ", ".join(composed['rejected_facts']) + "); đã thay bằng bản nháp theo mẫu.")
                if plan['missing_info']:
                    result['review_reasons'].append("Sinh viên cần bổ sung: " + ", ".join(plan['missing_info']) + ".")
                if pred['confidence_score'] < 0.60:
                    # Mô hình chưa chắc: ưu tiên chủ đề của quy trình đã khớp qua từ khóa neo, giữ nhãn gốc để đối chiếu
                    result['model_topic'] = pred['predicted_topic']
                    result['predicted_topic'] = plan['topic']
                    result['review_reasons'].append(
                        "Độ tự tin phân loại dưới 60%; đã định tuyến theo quy trình " + plan['procedure_id'] + ", cán bộ xác nhận lại.")
            else:
                result.update({
                    'department': draft['department'],
                    'matched_kb_id': draft['matched_kb_id'],
                    'articles': draft.get('articles', []),
                    'draft_response': draft['draft_text']
                })
                if pred['confidence_score'] < 0.60:
                    result['review_reasons'].append("Độ tự tin phân loại dưới 60%; cần cán bộ xác minh nhóm chuyên môn.")
                if not draft.get('articles'):
                    result['review_reasons'].append("Chưa tìm thấy quy trình hoặc điều khoản quy chế đủ tương đồng để viện dẫn.")
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
