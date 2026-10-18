"""Full Streamlit interaction checks on an isolated SQLite database."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.database import list_requests,get_request,review_history

class AppFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'EDUSUPPORT_DB_PATH':str(Path(self.temp.name)/'app.db')})
        self.env.start()
        self.app=AppTest.from_file(str(ROOT/'app'/'main.py'),default_timeout=40).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def button(self,label):
        return next(b for b in self.app.button if b.label==label)

    def submit(self,text):
        self.app.text_area(key='request_text').input(text)
        self.button('Phân tích và lưu').click().run()
        self.assertFalse(self.app.exception)

    def test_intake_draft_review_reload_and_idempotency(self):
        self.submit('Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.')
        self.assertEqual(len(list_requests()),1)
        rid=list_requests()[0]['record_id']
        self.button('Phân tích và lưu').click().run()
        self.assertEqual(len(list_requests()),1)
        self.app.text_area(key='intake_draft_'+rid).input('Chào bạn,\n\nCán bộ đã kiểm tra giao dịch.')
        self.button('Lưu bản nháp').click().run()
        self.assertFalse(self.app.exception)
        self.assertIn('Cán bộ đã kiểm tra',get_request(rid)['draft_response'])
        self.assertEqual(self.app.text_area(key='response_'+rid).value,get_request(rid)['draft_response'])
        self.app.text_area(key='response_'+rid).input('Nội dung cán bộ đã duyệt.')
        self.button('Duyệt và lưu').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(list_requests(pending_only=True),[])
        self.assertEqual(review_history()[0]['final_response'],'Nội dung cán bộ đã duyệt.')
        self.app.run()
        self.assertEqual(len(review_history()),1)

    def test_demo_import_is_repeatable_and_preserves_approval(self):
        self.button('Nạp 3 yêu cầu demo').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(list_requests()),3)
        rid=self.app.selectbox(key='review_id').value
        self.button('Duyệt và lưu').click().run()
        self.assertFalse(self.app.exception)
        self.button('Nạp 3 yêu cầu demo').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(list_requests()),3)
        self.assertEqual(get_request(rid)['status'],'reviewed_approve')
        self.assertEqual(len(list_requests(pending_only=True)),2)

    def test_short_request_persists_and_profile_is_available(self):
        self.submit('Giúp em với')
        self.assertFalse(list_requests()[0]['is_usable'])
        self.button('Kiểm tra và che thông tin').click().run()
        self.assertFalse(self.app.exception)
        self.assertIsNotNone(self.app.session_state['profile_result'])
        self.assertEqual(self.app.session_state['profile_result']['total'],424)
        self.assertTrue(any(b.label=='Tải dữ liệu đã che' for b in self.app.get('download_button')))

if __name__=='__main__':
    unittest.main()
