# -*- coding: utf-8 -*-
"""Unit tests for the dedicated Student Portal (app/student_portal.py)."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.database import list_requests, get_request

class StudentPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'EDUSUPPORT_DB_PATH': str(Path(self.temp.name) / 'student_portal.db')})
        self.env.start()
        self.app = AppTest.from_file(str(ROOT / 'app' / 'student_portal.py'), default_timeout=30).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_student_intake_submission(self):
        self.app.text_input(key='sp_fullname').input('Trần Thị Hoa')
        self.app.text_input(key='sp_mssv').input('2023608888')
        self.app.text_input(key='sp_email').input('hoa.tran@eaut.edu.vn')
        self.app.text_input(key='sp_issue').input('Xin cấp giấy xác nhận tạm hoãn NVQS')
        self.app.text_area(key='sp_text').input('Em cần xin giấy xác nhận sinh viên để nộp cho ban chỉ huy quân sự phường trước ngày 20/11.')
        
        # Click Gửi phiếu hỗ trợ
        submit_btn = next(b for b in self.app.button if 'Gửi' in b.label)
        submit_btn.click().run()
        self.assertFalse(self.app.exception)

        reqs = list_requests()
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]['source_type'], 'portal_student')
        self.assertIn('2023608888', reqs[0]['clean_text'])

if __name__ == '__main__':
    unittest.main()
