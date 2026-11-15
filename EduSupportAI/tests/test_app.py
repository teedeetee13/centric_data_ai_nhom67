"""Full Streamlit interaction checks on an isolated SQLite database."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.database import list_requests,get_request,review_history
from src.email_service import list_email_dispatches

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
        self.button('Gửi').click().run()
        self.assertFalse(self.app.exception)

    def test_procedure_ticket_plan_is_rendered(self):
        self.submit('Em vừa có lệnh gọi nhập ngũ, em muốn xin giấy tạm hoãn nghĩa vụ quân sự thì làm thế nào ạ?')
        rid=list_requests()[0]['record_id']
        self.assertEqual(get_request(rid)['matched_kb_id'],'QT19')
        labels=[e.label for e in self.app.expander]
        self.assertTrue(any(l.startswith('Phiếu xử lý ticket theo quy trình QT19') for l in labels))
        self.assertTrue(any('Mã sinh viên' in w.value for w in self.app.warning))

    def test_sample_picker_fills_request(self):
        self.app.selectbox(key='sample_choice').select('Gõ không dấu').run()
        self.button('Điền vào ô nội dung').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_area(key='request_text').value,'em xin giay xac nhan sinh vien de lam ve xe buyt a')
        self.button('Gửi').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(get_request(list_requests()[0]['record_id'])['matched_kb_id'],'QT11')

    def test_intake_draft_review_reload_and_idempotency(self):
        self.submit('Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.')
        self.assertEqual(len(list_requests()),1)
        rid=list_requests()[0]['record_id']
        self.button('Gửi').click().run()
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

    def test_sample_import_is_repeatable_and_preserves_approval(self):
        self.button('Nạp dữ liệu mẫu').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(list_requests()),72)
        self.assertTrue(any(m.label=='Khớp quy trình' for m in self.app.metric))
        rid=self.app.selectbox(key='review_id').value
        self.button('Duyệt và lưu').click().run()
        self.assertFalse(self.app.exception)
        self.button('Nạp dữ liệu mẫu').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(list_requests()),72)
        self.assertEqual(get_request(rid)['status'],'reviewed_approve')
        self.assertEqual(len(list_requests(pending_only=True)),71)

    def test_short_request_persists_and_profile_is_available(self):
        self.submit('Giúp em với')
        self.assertFalse(list_requests()[0]['is_usable'])
        self.button('Kiểm tra và che thông tin').click().run()
        self.assertFalse(self.app.exception)
        self.assertIsNotNone(self.app.session_state['profile_result'])
        self.assertEqual(self.app.session_state['profile_result']['total'],424)
        self.assertTrue(any(b.label=='Tải dữ liệu đã che' for b in self.app.get('download_button')))

    def test_high_confidence_auto_approval_and_sample_email(self):
        self.app.text_input(key='intake_test_email_dest').input('demo@example.org').run()
        self.button('Gửi email giải quyết mẫu').click().run()
        self.assertFalse(self.app.exception)
        dispatches = list_email_dispatches()
        self.assertTrue(any(d['recipient_email'] == 'demo@example.org' for d in dispatches))

        high_conf_text = 'Em cần xin giấy xác nhận sinh viên để làm vé xe buýt, mã sinh viên 20991234, email của em: demo@example.org'
        # Ngưỡng hạ xuống để kiểm tra đúng luồng tự duyệt, không phụ thuộc độ tự tin của mô hình hiện tại
        with patch('src.service.AUTO_APPROVE_CONFIDENCE_THRESHOLD', 0.1):
            self.submit(high_conf_text)
        reqs = list_requests()
        high_req = next(r for r in reqs if 'vé xe buýt' in r['clean_text'])
        self.assertEqual(high_req['status'], 'reviewed_approve')
        self.assertEqual(len(list_requests(pending_only=True)), 0)

if __name__=='__main__':
    unittest.main()
