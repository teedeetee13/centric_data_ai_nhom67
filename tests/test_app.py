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

    def open_admin(self):
        if not self.app.session_state.get('show_admin_view', False):
            self.app.button(key='btn_toggle_admin').click().run()
            self.assertFalse(self.app.exception)

    def open_workbench(self):
        if self.app.session_state.get('show_admin_view', False):
            self.app.button(key='btn_toggle_workbench').click().run()
            self.assertFalse(self.app.exception)

    def button(self,label):
        return next(b for b in self.app.button if b.label==label or (label=='Gửi' and 'Gửi' in b.label))

    def submit(self,text):
        self.open_admin()
        self.app.text_area(key='request_text').input(text)
        self.button('Gửi').click().run()
        self.assertFalse(self.app.exception)

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
        
        # Quay về Bàn duyệt hồ sơ để cán bộ kiểm tra và duyệt
        self.open_workbench()
        self.assertEqual(self.app.text_area(key='response_'+rid).value,get_request(rid)['draft_response'])
        self.app.text_area(key='response_'+rid).input('Nội dung cán bộ đã duyệt.')
        self.button('Duyệt và lưu').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(list_requests(pending_only=True),[])
        self.assertEqual(review_history()[0]['final_response'],'Nội dung cán bộ đã duyệt.')
        self.app.run()
        self.assertEqual(len(review_history()),1)

    def test_demo_import_is_repeatable_and_preserves_approval(self):
        self.open_admin()
        self.button('Nạp 3 yêu cầu demo').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(list_requests()),3)
        self.open_workbench()
        rid=self.app.selectbox(key='review_id').value
        self.button('Duyệt và lưu').click().run()
        self.assertFalse(self.app.exception)
        self.open_admin()
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

    def test_high_confidence_auto_approval_and_sample_email(self):
        self.open_admin()
        btn_label = 'Gửi email giải quyết mẫu tới kennysk114239@gmail.com'
        self.button(btn_label).click().run()
        self.assertFalse(self.app.exception)
        dispatches = list_email_dispatches()
        self.assertTrue(any(d['recipient_email'] == 'kennysk114239@gmail.com' for d in dispatches))

        high_conf_text = 'Cổng thông tin báo thiếu điểm môn Giáo dục quốc phòng nên em chưa đủ điều kiện xét tốt nghiệp đợt này. Email của em: kennysk114239@gmail.com'
        self.submit(high_conf_text)
        reqs = list_requests()
        high_req = next(r for r in reqs if 'thiếu điểm môn Giáo dục quốc phòng' in r['clean_text'])
        self.assertEqual(high_req['status'], 'reviewed_approve')
        self.assertGreaterEqual(high_req['confidence_score'], 0.70)
        self.assertEqual(len(list_requests(pending_only=True)), 0)

    def test_workbench_trace_visibility_and_ai_copilot_removed(self):
        # Nạp dữ liệu demo để hiển thị chi tiết hồ sơ
        self.open_admin()
        self.button('Nạp 3 yêu cầu demo').click().run()
        self.assertFalse(self.app.exception)

        # 1. Trên màn hình chính: Không có vết thực thi, không có chữ AI COPILOT
        self.open_workbench()
        main_expanders = [e.label for e in self.app.expander]
        self.assertFalse(any('Vết thực thi' in exp for exp in main_expanders))
        self.assertFalse(any('AI COPILOT' in m.value for m in self.app.markdown))

        # 2. Trong bánh răng (Admin view): Có bàn duyệt tương tự và CÓ vết thực thi
        self.open_admin()
        admin_expanders = [e.label for e in self.app.expander]
        self.assertTrue(any('Vết thực thi' in exp for exp in admin_expanders))
        self.assertFalse(any('AI COPILOT' in m.value for m in self.app.markdown))

if __name__=='__main__':
    unittest.main()
