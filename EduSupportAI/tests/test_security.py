"""Kiểm thử bảo mật: phân quyền cán bộ, che PII mở rộng, tự động duyệt an toàn, chống ảo giác, email."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.components import auth
from src.cleaner import clean_dataframe, mask_pii, normalize_unicode_and_whitespace
from src.config import ROOT
from src.database import delete_contact, get_contact, init_db, list_requests, save_contact
from src.email_service import send_resolution_email
from src.local_llm import LocalLLM, ungrounded_facts
from src.service import can_auto_approve


class PiiTests(unittest.TestCase):
    def test_extended_pii_is_masked(self):
        cases = {
            'CCCD của em là 001204012345': ('[NATIONAL_ID]', '001204012345'),
            'Căn cước công dân số 012345678': ('[NATIONAL_ID]', '012345678'),
            'Số tài khoản: 1903 5678 9012 ạ': ('[BANK_ACCOUNT]', '1903 5678'),
            'Em tên là Nguyễn Văn An, lớp K14': ('[NAME]', 'Nguyễn Văn'),
            'Họ và tên: Trần Thị Bình': ('[NAME]', 'Trần Thị'),
        }
        for text, (token, leaked) in cases.items():
            with self.subTest(text=text):
                masked, flags = mask_pii(text)
                self.assertIn(token, masked)
                self.assertNotIn(leaked, masked)
                self.assertTrue(flags)

    def test_ordinary_sentences_are_not_masked_as_names(self):
        for text in ['Em tên là sinh viên năm hai', 'Môn học này khó quá', 'Phòng 302 nhà A bị hỏng máy chiếu']:
            with self.subTest(text=text):
                self.assertNotIn('[NAME]', mask_pii(text)[0])

    def test_zero_width_characters_cannot_hide_a_phone_number(self):
        clean = normalize_unicode_and_whitespace('Sđt 09​12‍34﻿5678 ạ')
        self.assertIn('[PHONE]', mask_pii(clean)[0])

    def test_near_duplicate_detection_keeps_behaviour(self):
        import pandas as pd
        base = 'Em đã chuyển học phí hôm qua nhưng cổng thông tin vẫn báo còn nợ học phí kỳ này'
        result = clean_dataframe(pd.DataFrame({'raw_text': [base, base + ' ạ.', 'Máy chiếu phòng 302 không lên hình từ sáng nay']}))
        self.assertEqual(result['is_usable'].tolist(), [True, False, True])


class AutoApproveTests(unittest.TestCase):
    SAFE = {'ticket_plan': {'missing_info': []}, 'is_usable': True, 'draft_source': 'template',
            'priority_level': 'Bình thường', 'confidence_score': 0.9}

    def test_only_safe_cases_are_auto_approved(self):
        self.assertTrue(can_auto_approve(self.SAFE))
        unsafe = [
            {'ticket_plan': None},
            {'ticket_plan': {'missing_info': ['Mã sinh viên']}},
            {'draft_source': 'llm'},
            {'draft_source': 'template_fallback'},
            {'priority_level': 'Khẩn cấp'},
            {'confidence_score': 0.5},
        ]
        for change in unsafe:
            with self.subTest(change=change):
                self.assertFalse(can_auto_approve({**self.SAFE, **change}))

    def test_production_disables_auto_approve_by_default(self):
        with patch.dict(os.environ, {'EDUSUPPORT_ENV': 'production'}):
            self.assertFalse(can_auto_approve(self.SAFE))
        with patch.dict(os.environ, {'EDUSUPPORT_ENV': 'production', 'EDUSUPPORT_AUTO_APPROVE': 'on'}):
            self.assertTrue(can_auto_approve(self.SAFE))


class GroundingExtendedTests(unittest.TestCase):
    CONTEXT = 'Đơn vị đầu mối: Phòng Công tác sinh viên. Trang tra cứu lib.eaut.edu.vn. Thời gian 02 ngày.'

    def test_invented_unit_and_url_are_rejected(self):
        bad = ungrounded_facts('Bạn liên hệ Chi nhánh Công tác sinh viên tại https://lua-dao.example.com', self.CONTEXT)
        self.assertTrue(any('Chi nhánh' in b for b in bad))
        self.assertTrue(any('lua-dao' in b for b in bad))

    def test_units_from_context_are_allowed_regardless_of_case(self):
        self.assertEqual(ungrounded_facts('Bạn đến Phòng Công Tác Sinh Viên, xem lib.eaut.edu.vn trong 2 ngày.', self.CONTEXT), [])

    def test_only_one_generation_runs_at_a_time(self):
        llm = LocalLLM(host='http://127.0.0.1:9', mode='auto')
        llm._available = True
        self.assertTrue(llm._slots.acquire(blocking=False))
        try:
            self.assertIsNone(llm.generate_reply('câu hỏi', 'ngữ cảnh'))
        finally:
            llm._slots.release()


class EmailTests(unittest.TestCase):
    def test_header_injection_address_is_rejected(self):
        ok, _ = send_resolution_email('a@b.vn\nBcc: nan-nhan@example.org', 'Chủ đề', 'Nội dung')
        self.assertFalse(ok)

    def test_contact_is_stored_separately_and_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'c.db'
            init_db(db)
            save_contact('REQ_1', 'sv@example.org', db)
            self.assertEqual(get_contact('REQ_1', db), 'sv@example.org')
            delete_contact('REQ_1', db)
            self.assertIsNone(get_contact('REQ_1', db))


class OfficerGateTests(unittest.TestCase):
    PASSWORD = 'mat-khau-thu-nghiem'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        auth._failures.update(count=0, locked_until=0.0)
        self.env = patch.dict(os.environ, {
            'EDUSUPPORT_DB_PATH': str(Path(self.temp.name) / 'app.db'),
            'EDUSUPPORT_ENV': 'production',
            'EDUSUPPORT_OFFICER_PASSWORD': self.PASSWORD,
        })
        self.env.start()
        self.app = AppTest.from_file(str(ROOT / 'app' / 'main.py'), default_timeout=40).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def labels(self):
        return [b.label for b in self.app.button]

    def login(self, password):
        self.app.text_input(key='officer_password_input').input(password)
        next(b for b in self.app.button if b.label == 'Đăng nhập').click().run()
        self.assertFalse(self.app.exception)

    def test_officer_tools_are_hidden_before_login(self):
        labels = self.labels()
        self.assertNotIn('Gửi email giải quyết mẫu', labels)
        self.assertNotIn('Nạp 3 yêu cầu demo', labels)
        self.assertNotIn('Duyệt và lưu', labels)
        self.assertFalse([b for b in labels if b.startswith('NVQS')])

    def test_student_gets_receipt_without_internal_draft(self):
        self.app.text_area(key='request_text').input('Em muốn xin bảo lưu kết quả học tập kỳ này, mã sinh viên 20991234.')
        next(b for b in self.app.button if b.label == 'Gửi').click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('Mã yêu cầu của bạn' in s.value for s in self.app.success))
        self.assertNotIn('Lưu bản nháp', self.labels())
        self.assertEqual(list_requests()[0]['status'], 'pending_review')

    def test_wrong_password_is_refused_and_correct_password_opens(self):
        self.login('sai-mat-khau')
        self.assertTrue(any('không đúng' in e.value for e in self.app.error))
        self.assertNotIn('Nạp 3 yêu cầu demo', self.labels())
        self.login(self.PASSWORD)
        self.assertIn('Nạp 3 yêu cầu demo', self.labels())
        self.assertIn('Đăng xuất', self.labels())

    def test_repeated_failures_lock_the_form(self):
        for _ in range(auth.MAX_FAILURES):
            self.login('sai-mat-khau')
        self.app.run()
        self.assertTrue(any('quá nhiều lần' in e.value for e in self.app.error))

    def test_production_without_password_stays_locked(self):
        with patch.dict(os.environ, {'EDUSUPPORT_OFFICER_PASSWORD': ''}):
            app = AppTest.from_file(str(ROOT / 'app' / 'main.py'), default_timeout=40).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('đang khóa' in e.value for e in app.error))


if __name__ == '__main__':
    unittest.main()
