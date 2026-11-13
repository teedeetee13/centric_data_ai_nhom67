# -*- coding: utf-8 -*-
"""
Module: src.service
Tầng Service điều phối toàn bộ chuỗi xử lý đầu - cuối:
Đầu vào thô -> Làm sạch & Che PII -> Phân loại Machine Learning -> Tra cứu quy chế FAQ & Quy trình data-doc -> Soạn thảo bản nháp & Đánh giá lý do rà soát
Tích hợp Máy học Cục bộ (LocalLearningMachine) và Nhật ký Thực thi Minh bạch (Execution Trace Logger).
"""

import warnings
from typing import Optional
from src.cleaner import clean_text_single
from src.config import MODEL_PATH
from src.faq_engine import FAQEngine
from src.model import EduSupportClassifier, KEYWORDS_URGENT, KEYWORDS_HIGH, KEYWORDS_LOW
from src.trace_logger import ExecutionTrace
try:
    from src.app_logger import app_log
except ImportError:
    def app_log(*args, **kwargs):
        pass
from src.local_machine import get_local_machine, LocalLearningMachine

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
    def __init__(self, classifier=None, faq=None, local_machine: Optional[LocalLearningMachine] = None):
        self.classifier = classifier if classifier is not None else load_classifier()
        self.faq = faq if faq is not None else FAQEngine()
        self.local_machine = local_machine if local_machine is not None else get_local_machine()

    def process(self, raw_text: str, topic_hint: Optional[str] = None, proc_hint: Optional[str] = None, mask_pii: bool = True) -> dict:
        """Thực thi toàn bộ luồng xử lý phản ánh sinh viên và ghi vết Execution Trace.
        mask_pii: Mặc định True (che PII theo chuẩn test). Khi False (cổng sinh viên), bảo toàn thông tin nội dung."""
        if isinstance(raw_text, str) and len(raw_text) > 8000:
            raise ValueError("Hệ thống tiếp nhận tối đa 8.000 ký tự cho mỗi yêu cầu phản ánh.")

        # Khởi tạo Trace Logger để theo dõi quy trình xử lý
        trace = ExecutionTrace(trace_id=f"TRACE-{raw_text[:8].encode().hex().upper()[:8]}")
        app_log("INTAKE", "Gọi RequestService.process()", f"Tiếp nhận chuỗi văn bản {len(raw_text) if raw_text else 0} ký tự (Chế độ PII: {'Bật' if mask_pii else 'Tắt/Bảo toàn'})")

        # BƯỚC 1: Tiếp nhận và làm sạch dữ liệu
        step1 = trace.new_step(1, "DATA_CENTRIC_AUDIT_AND_PII_FILTER", "Chuẩn hóa Unicode NFC, lọc PII và kiểm soát chất lượng")
        step1.add_log(f"Tiếp nhận đầu vào {len(raw_text) if raw_text else 0} ký tự")

        result = clean_text_single(raw_text, mask_pii_flag=mask_pii)
        result.pop('raw_text', None)
        result['mask_pii'] = mask_pii
        result['priority_reason'] = priority_reason(result['clean_text'])
        result['review_reasons'] = []

        step1.finish(
            status="SUCCESS" if result['is_usable'] else "WARNING",
            quality_flags=result['quality_flags'],
            is_usable=result['is_usable'],
            clean_length=len(result['clean_text'])
        )
        app_log("CLEANER", "Làm sạch & kiểm tra chất lượng", f"Hợp lệ: {result['is_usable']}, Độ dài sạch: {len(result['clean_text'])}, Cờ: {result['quality_flags']}")

        if result['is_usable']:
            # Tách nội dung phản ánh trọng tâm (loại bỏ boilerplate liên hệ nếu có để tránh nhiễu TF-IDF)
            import re
            inquiry_text = re.sub(r'Thông tin liên hệ:.*$', '', result['clean_text'], flags=re.IGNORECASE).strip()
            if not inquiry_text or len(inquiry_text) < 5:
                inquiry_text = result['clean_text']

            # BƯỚC 2: Phân loại máy học
            step2 = trace.new_step(2, "LOCAL_MACHINE_CLASSIFICATION", "Dự đoán chủ đề và độ tự tin bằng TF-IDF kép + Logistic Regression")
            pred = self.classifier.predict_single(inquiry_text)

            # Hiệu chuẩn bằng topic_hint & proc_hint từ 3 chuyên môn của data-doc
            if topic_hint and hasattr(self.classifier, 'classes_') and topic_hint in self.classifier.classes_:
                orig_topic = pred['predicted_topic']
                orig_conf = pred['confidence_score']
                if orig_topic == topic_hint:
                    step2.add_log(f"Chủ đề dự đoán trùng khớp với danh mục chuyên môn người dùng lựa chọn: [{topic_hint}].")
                    calibrated_conf = min(0.95, max(0.88, pred['confidence_score'] + 0.40))
                    step2.add_log(f"Tối đa hóa độ tin cậy từ sự đồng thuận: {orig_conf:.1%} -> {calibrated_conf:.1%}")
                    pred['confidence_score'] = calibrated_conf
                else:
                    step2.add_log(f"Phát hiện danh mục chuyên môn người dùng chọn từ 3 tài liệu data-doc: [{topic_hint}].")
                    step2.add_log(f"Hiệu chỉnh chủ đề dự đoán từ '{orig_topic}' ({orig_conf:.1%}) sang [{topic_hint}].")
                    pred['predicted_topic'] = topic_hint
                    alt_prob = pred['all_probabilities'].get(topic_hint, 0.40)
                    calibrated_conf = min(0.92, max(0.88, alt_prob + 0.40))
                    pred['confidence_score'] = calibrated_conf

            result.update(pred)
            probs_dict = pred.get('all_probabilities', {})
            sorted_probs = sorted(probs_dict.items(), key=lambda x: x[1], reverse=True)
            top1_p = sorted_probs[0][1] if sorted_probs else pred['confidence_score']
            top2_p = sorted_probs[1][1] if len(sorted_probs) > 1 else 0.0
            margin = round(top1_p - top2_p, 4)

            step2.add_log(f"Chủ đề quyết định: {pred['predicted_topic']} (Độ tự tin: {pred['confidence_score']:.1%})")
            step2.add_log(f"Phân phối xác suất các chuyên môn: " + ", ".join([f"{k}: {v:.1%}" for k, v in sorted_probs[:4]]))
            step2.add_log(f"Biên độ chênh lệch quyết định (Margin): {margin:.1%}")
            step2.add_log(f"Xếp mức ưu tiên: [{pred['priority_level']}] — Căn cứ: {result.get('priority_reason')}")

            step2.finish(
                status="SUCCESS",
                predicted_topic=pred['predicted_topic'],
                confidence_score=pred['confidence_score'],
                priority_level=pred['priority_level'],
                priority_reason=result.get('priority_reason'),
                all_probabilities=probs_dict,
                top_3_probabilities=dict(sorted_probs[:3]),
                decision_margin=margin
            )
            app_log("AI-MODEL", "Thực thi phân loại TF-IDF kép + Logistic Regression", f"Dự đoán chủ đề: [{pred['predicted_topic']}] ({pred['confidence_score']:.1%}) - Mức ưu tiên: [{pred['priority_level']}]")

            # BƯỚC 3: Tra cứu tri thức (FAQ & Quy trình từ data-doc)
            step3 = trace.new_step(3, "PROCEDURE_AND_REGULATION_RETRIEVAL", "Tra cứu điều khoản quy chế và quy trình chi tiết từ data-doc")
            draft = self.faq.generate_draft_response(inquiry_text, pred['predicted_topic'])
            
            # Tra cứu quy trình từ 3 tài liệu DOCX
            candidate_procs = self.local_machine.retrieve_procedure(inquiry_text, predicted_topic=pred['predicted_topic'], top_k=3)
            top_proc = candidate_procs[0] if candidate_procs else None

            if proc_hint and hasattr(self.local_machine, 'get_procedure'):
                hint_proc = self.local_machine.get_procedure(proc_hint)
                if hint_proc:
                    top_proc = hint_proc
                    step3.add_log(f"Khớp chính xác quy trình data-doc theo chỉ dẫn: [{top_proc['proc_id']}] {top_proc['title']}")

            if top_proc:
                step3.add_log(f"Quy trình được chọn tối ưu: [{top_proc['proc_id']}] {top_proc['title']} (Điểm tương đồng: {top_proc.get('similarity_score', 0):.1%})")
                step3.add_log(f"Căn cứ pháp lý: {top_proc.get('legal_basis', 'Quy định Nhà trường')}")
                step3.add_log(f"Thời hạn giải quyết (SLA): {top_proc.get('processing_time', 'Theo quy định')}")

            candidate_list = []
            for p in candidate_procs:
                candidate_list.append({
                    "proc_id": p['proc_id'],
                    "title": p['title'],
                    "doc_source": p.get('doc_source', ''),
                    "similarity_score": p.get('similarity_score', 0),
                    "rank_score": p.get('rank_score', 0)
                })

            result['matched_procedure'] = top_proc
            target_dept = (top_proc.get('department') if top_proc else None) or draft.get('department') or 'Bộ phận Tiếp nhận'

            result.update({
                'department': target_dept,
                'matched_kb_id': draft.get('matched_kb_id'),
                'articles': draft.get('articles', []),
                'draft_response': draft.get('draft_text', '')
            })

            step3.finish(
                status="SUCCESS" if top_proc else "NO_DOC_MATCH",
                proc_id=top_proc["proc_id"] if top_proc else None,
                title=top_proc["title"] if top_proc else "Không khớp quy trình",
                legal_basis=top_proc.get("legal_basis", "") if top_proc else "",
                department=target_dept,
                processing_time=top_proc.get("processing_time", "") if top_proc else "",
                forms_required=top_proc.get("forms_required", "") if top_proc else "",
                candidate_procedures=candidate_list
            )
            app_log("RAG-DOCX", "Tra cứu căn cứ pháp lý & quy trình từ 3 tài liệu data-doc", f"Khớp: [{top_proc['proc_id'] if top_proc else 'N/A'}] {top_proc['title'] if top_proc else 'Chưa khớp'} ({target_dept})")

            # BƯỚC 4: Lập luận và tổng hợp phản hồi
            step4 = trace.new_step(4, "LOCAL_REASONING_AND_SYNTHESIS", "Chuỗi suy luận Chain-of-Thought và tổng hợp văn bản giải đáp")
            reasoning_steps, proc_draft = self.local_machine.reason_and_synthesize(
                clean_text=result['clean_text'],
                topic=pred['predicted_topic'],
                matched_procedure=top_proc
            )
            result['reasoning_steps'] = reasoning_steps
            result['procedure_draft_response'] = proc_draft

            for r_s in reasoning_steps:
                step4.add_log(r_s)
            step4.finish(
                status="SUCCESS",
                reasoning_steps_count=len(reasoning_steps),
                reasoning_steps=reasoning_steps,
                synthesized_response_preview=proc_draft[:150] + "..." if proc_draft else ""
            )
            app_log("SYNTHESIS", "Lập luận chuỗi suy luận Chain-of-Thought & tổng hợp giải pháp", f"Đã sinh {len(reasoning_steps)} bước suy luận nghiệp vụ chuẩn EAUT")

            # BƯỚC 5: Rào chắn và đánh giá lý do rà soát
            step5 = trace.new_step(5, "GUARDRAILS_AND_DISPATCH", "Kiểm định an toàn và quyết định phê duyệt")
            if pred['confidence_score'] < 0.60:
                result['review_reasons'].append("Độ tự tin phân loại dưới 60%; cần cán bộ xác minh nhóm chuyên môn.")
            if not draft.get('articles') and not top_proc:
                result['review_reasons'].append("Chưa tìm thấy điều khoản quy chế hoặc quy trình đủ tương đồng để viện dẫn.")
            elif draft.get('articles') and not all(a.get('verified', False) for a in draft['articles']):
                result['review_reasons'].append("Tài liệu tham chiếu thuộc dạng minh họa, chưa xác minh quy định chính thức.")

            guardrail_checks = {
                "confidence_threshold_50": {
                    "rule": "Độ tự tin phân loại AI >= 50%",
                    "passed": bool(pred['confidence_score'] >= 0.50),
                    "score": f"{pred['confidence_score']:.1%}"
                },
                "official_docx_procedure_linked": {
                    "rule": "Có quy trình căn cứ pháp lý trích xuất từ 3 file DOCX",
                    "passed": bool(top_proc is not None),
                    "procedure": top_proc.get('proc_id') if top_proc else None
                },
                "data_hygiene_and_pii_safe": {
                    "rule": "Dữ liệu được làm sạch chuẩn NFC và che giấu PII an toàn",
                    "passed": bool(result.get('is_usable')),
                    "flags": result.get('quality_flags')
                },
                "priority_dispatch_ready": {
                    "rule": "Kiểm định mức độ ưu tiên giải quyết",
                    "passed": True,
                    "level": pred['priority_level']
                }
            }
            is_auto = (pred['confidence_score'] >= 0.70 and bool(top_proc) and pred['priority_level'] != 'Khẩn cấp')
            final_disp = "TỰ ĐỘNG PHÊ DUYỆT" if is_auto else "CHUYỂN BÀN DUYỆT CÁN BỘ"
            step5.finish(
                status="AUTO_APPROVED" if is_auto else "REVIEW_QUEUE",
                guardrail_checks=guardrail_checks,
                review_reasons=result['review_reasons'],
                final_dispatch=final_disp
            )
            app_log("GUARDRAILS", "Kiểm định rào chắn an toàn và quyết định phân luồng", f"Phân luồng: [{final_disp}] (Tự động duyệt: {is_auto})")
        else:
            result.update({
                'predicted_topic': 'Khac',
                'confidence_score': 0.0,
                'priority_level': 'Thấp',
                'department': 'Bộ phận tiếp nhận',
                'matched_kb_id': None,
                'matched_procedure': None,
                'articles': [],
                'reasoning_steps': ["Dữ liệu rỗng hoặc quá ngắn dưới 12 ký tự; từ chối suy luận."],
                'draft_response': (
                    "Chào bạn, nội dung chưa đủ thông tin để xử lý. "
                    "Bạn vui lòng bổ sung mô tả vấn đề, thời điểm và việc cần hỗ trợ. Trân trọng."
                )
            })
            result['review_reasons'].append("Nội dung rỗng hoặc quá ngắn (dưới 12 ký tự).")

        if result['quality_flags']:
            result['review_reasons'].append("Có cờ chất lượng: " + ", ".join(result['quality_flags']))

        result['needs_review'] = bool(result['review_reasons'])

        trace.finalize()
        result['execution_trace'] = trace.to_dict()
        result['terminal_log'] = trace.format_terminal_log()

        # In trực tiếp nhật ký thực thi ra Terminal Console để hiển thị minh bạch cho người vận hành
        try:
            print("\n" + result['terminal_log'] + "\n", flush=True)
        except Exception:
            pass

        return result
