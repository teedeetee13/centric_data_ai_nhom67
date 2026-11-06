"""Kiểm thử xử lý ticket theo quy trình nghiệp vụ và mô hình ngôn ngữ cục bộ."""
import json
import unittest
from datetime import date

from src.config import PROCEDURE_KB_PATH
from src.local_llm import LocalLLM, ungrounded_facts
from src.procedure_engine import ProcedureEngine, add_working_days, context_for_llm
from src.service import RequestService


class FakeLLM:
    """Mô hình giả lập: trả về đúng văn bản được cấu hình, kèm kiểm tra bám nguồn thật."""
    model = 'fake-local'

    def __init__(self, reply=None):
        self.reply = reply
        self.calls = []

    def generate_reply(self, question, context):
        self.calls.append((question, context))
        if self.reply is None:
            return None
        bad = ungrounded_facts(self.reply, context, question)
        return {'text': self.reply, 'model': self.model, 'grounded': not bad, 'ungrounded_facts': bad}

    def status(self):
        return 'fake'


class ProcedureMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ProcedureEngine()

    def top(self, text):
        found = self.engine.match(text, top_k=1)
        return found[0]['procedure']['id'] if found else None

    def test_kb_is_well_formed(self):
        data = json.loads(PROCEDURE_KB_PATH.read_text(encoding='utf-8'))
        ids = [p['id'] for p in data['procedures']]
        self.assertEqual(len(ids), len(set(ids)))
        for proc in data['procedures']:
            self.assertTrue(proc['steps'] and proc['keywords'] and proc['receiving_unit'], proc['id'])
            self.assertIn(proc['source'], data['sources'])

    def test_paraphrases_route_to_expected_procedure(self):
        cases = {
            'em xin bao luu hoc ky nay duoc khong a': 'QT04',
            'Em năm 2 muốn chuyển ngành sang Kế toán thì làm sao': 'QT01',
            'Em được gọi đi khám nghĩa vụ quân sự, trường có cấp giấy không': 'QT19',
            'Em làm mất thẻ SV rồi ạ': 'QT12',
            'xin giay xn sv': 'QT11',
            'Nhà em hộ cận nghèo, em có được giảm học phí không': 'QT18',
            'Hết hạn bảo lưu rồi giờ em muốn quay lại trường học tiếp': 'QT05',
            'Máy chiếu phòng 302 không lên hình': 'QT28',
            'Em nợ 8 tín chỉ có được làm khóa luận không': 'QT09',
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.top(text), expected)

    def test_out_of_scope_questions_do_not_match(self):
        for text in ['Giúp em với', 'Wifi thư viện yếu quá', 'Điểm thi của em bị sai, em muốn phúc khảo',
                     'Cho em hỏi hạn nộp học phí kỳ này là ngày nào',
                     'Lớp em muốn xin đổi lịch học môn Tiếng Anh chuyên ngành']:
            with self.subTest(text=text):
                self.assertIsNone(self.top(text))

    def test_ticket_plan_sla_and_missing_info(self):
        proc = next(p for p in self.engine.procedures if p['id'] == 'QT11')
        monday = date(2026, 11, 2)
        plan = self.engine.build_ticket_plan('Em cần giấy xác nhận sinh viên', proc, 0.9, today=monday)
        self.assertEqual(plan['sla_due_date'], '2026-11-04')
        self.assertEqual(plan['missing_info'], ['Mã sinh viên'])
        self.assertEqual(plan['status'], 'Chờ sinh viên bổ sung thông tin')
        self.assertTrue(plan['next_action'].startswith('Sinh viên & P.CTSV'))
        nvqs = next(p for p in self.engine.procedures if p['id'] == 'QT19')
        self.assertTrue(self.engine.build_ticket_plan('x', nvqs, 0.9)['next_action'].startswith('Sinh viên & P.CTSV'))
        plan = self.engine.build_ticket_plan('Em cần giấy xác nhận sinh viên, MSSV [STUDENT_ID]', proc, 0.9, today=monday)
        self.assertEqual(plan['missing_info'], [])

    def test_working_days_skip_weekend(self):
        self.assertEqual(add_working_days(date(2026, 11, 6), 1), date(2026, 11, 9))


class GroundingTests(unittest.TestCase):
    def test_invented_numbers_and_forms_are_flagged(self):
        context = 'Thời gian giải quyết: 02 ngày làm việc. Hồ sơ: BM01a. Căn cứ QĐ 118/QĐ-ĐHCNĐA.'
        self.assertEqual(ungrounded_facts('Bạn nộp BM01a, nhận sau 2 ngày theo 118/QĐ-ĐHCNĐA.', context), [])
        self.assertEqual(ungrounded_facts('Bạn nộp BM07, nhận sau 5 ngày.', context), ['5', 'BM07'])

    def test_list_numbering_is_not_a_fact(self):
        self.assertEqual(ungrounded_facts('1. Nộp đơn\n2. Chờ kết quả', 'Không có số'), [])

    def test_llm_off_mode_never_calls_ollama(self):
        llm = LocalLLM(mode='off', host='http://127.0.0.1:9')
        self.assertFalse(llm.is_available())
        self.assertIsNone(llm.generate_reply('câu hỏi', 'ngữ cảnh'))


class ServiceTicketTests(unittest.TestCase):
    QUESTION = 'Em muốn xin bảo lưu kết quả học tập kỳ này vì gia đình khó khăn, mã sinh viên 20991234.'

    @classmethod
    def setUpClass(cls):
        base = RequestService()
        cls.parts = dict(classifier=base.classifier, faq=base.faq, procedures=base.procedures)

    def service(self, reply):
        return RequestService(llm=FakeLLM(reply), **self.parts)

    def test_procedure_ticket_routes_and_uses_template_without_llm(self):
        result = self.service(None).process(self.QUESTION)
        self.assertEqual(result['matched_kb_id'], 'QT04')
        self.assertEqual(result['department'], 'Phòng Công tác sinh viên (Bộ phận Một cửa)')
        self.assertEqual(result['draft_source'], 'template')
        self.assertTrue(result['articles'][0]['verified'])
        self.assertIn('04 tuần', result['draft_response'])
        self.assertNotIn('20991234', result['draft_response'])

    def test_grounded_llm_draft_is_used_and_flagged_for_review(self):
        reply = ('Chào bạn,\nBạn nộp Đơn BM01 tại Bộ phận Một cửa P.CTSV chậm nhất trong vòng 04 tuần '
                 'kể từ khi học kỳ mới bắt đầu. Thời gian giải quyết tối đa 07 ngày.\nTrân trọng.')
        result = self.service(reply).process(self.QUESTION)
        self.assertEqual(result['draft_source'], 'llm')
        self.assertEqual(result['draft_response'], reply)
        self.assertTrue(result['needs_review'])

    def test_hallucinated_llm_draft_falls_back_to_template(self):
        reply = 'Chào bạn, bạn nộp mẫu BM99 và đóng lệ phí 200.000 đồng, kết quả sau 30 ngày. Trân trọng.'
        result = self.service(reply).process(self.QUESTION)
        self.assertEqual(result['draft_source'], 'template_fallback')
        self.assertNotIn('BM99', result['draft_response'])
        self.assertTrue(any('BM99' in r for r in result['review_reasons']))

    def test_question_without_procedure_keeps_faq_flow(self):
        fake = FakeLLM('không được gọi')
        result = RequestService(llm=fake, **self.parts).process('Wifi ở sảnh nhà A không kết nối được')
        self.assertIsNone(result['ticket_plan'])
        self.assertEqual(fake.calls, [])

    def test_low_confidence_uses_procedure_topic_and_keeps_model_guess(self):
        result = self.service(None).process('hong dieu hoa phong 302')
        self.assertEqual(result['matched_kb_id'], 'QT28')
        self.assertEqual(result['predicted_topic'], 'Co_so_vat_chat')
        if result['confidence_score'] < 0.60:
            self.assertIn('model_topic', result)

    def test_procedure_questions_classified_confidently_after_augmentation(self):
        result = self.service(None).process('Em vừa có lệnh gọi nhập ngũ, em muốn xin giấy tạm hoãn nghĩa vụ quân sự thì làm thế nào ạ?')
        self.assertEqual(result['predicted_topic'], 'Thu_tuc_hanh_chinh')
        self.assertGreaterEqual(result['confidence_score'], 0.60)

    def test_faq_entries_aligned_with_school_documents(self):
        import pandas as pd
        from src.config import KB_PATH
        kb = pd.read_csv(KB_PATH, dtype=str).fillna('').set_index('kb_id')
        for kb_id in ['KB002', 'KB009', 'KB010', 'KB011', 'KB012']:
            self.assertEqual(kb.loc[kb_id, 'verified'], 'true')
            self.assertTrue(kb.loc[kb_id, 'source_url'])
        self.assertIn('30 ngày kể từ ngày khai giảng', kb.loc['KB002', 'content_extract'])
        self.assertNotIn('24h', kb.loc['KB010', 'content_extract'])

    def test_context_only_contains_procedure_content(self):
        engine = self.parts['procedures']
        match = engine.match(self.QUESTION, top_k=1)[0]
        plan = engine.build_ticket_plan(self.QUESTION, match['procedure'], match['score'])
        context = context_for_llm(plan)
        self.assertIn('BM01', context)
        self.assertNotIn('[STUDENT_ID]', context)


if __name__ == '__main__':
    unittest.main()
