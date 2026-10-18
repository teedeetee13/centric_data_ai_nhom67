"""Regression tests for the demo's real persistence and retrieval failures."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

from src.cleaner import clean_dataframe,clean_text_single
from src.database import (init_db,save_request,get_request,list_requests,
                          save_draft,log_review_action,review_history)
from src.service import RequestService
from src.faq_engine import FAQEngine
from src.quality_profiler import profile_dataset
from app.components.dashboard import analyze_dataframe_realtime,export_csv

class MVPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=RequestService()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/'mvp.db'
        self.patch=patch.dict(os.environ,{'EDUSUPPORT_DB_PATH':str(self.db)})
        self.patch.start()
        init_db()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def new_request(self,text=None,record_id=None):
        result=self.service.process(text or 'Em đã chuyển học phí hôm qua nhưng cổng vẫn báo còn nợ, mã sinh viên 20991234.')
        return save_request(result,record_id=record_id),result

    def test_01_real_model_and_end_to_end_storage(self):
        rid,result=self.new_request()
        self.assertEqual(result['predicted_topic'],'Hoc_phi')
        self.assertGreater(result['confidence_score'],0.)
        self.assertTrue(result['articles'])
        self.assertEqual(len(list_requests(pending_only=True)),1)
        self.assertNotIn('20991234',json.dumps(get_request(rid),ensure_ascii=False))

    def test_02_retry_does_not_create_or_reset_request(self):
        rid,result=self.new_request(record_id='DEMO_001')
        log_review_action(rid,'approve','Hoc_phi','Hoc_phi','Đã kiểm tra. Nội dung phản hồi.')
        save_request(result,record_id=rid)
        self.assertEqual(len(list_requests()),1)
        self.assertEqual(get_request(rid)['status'],'reviewed_approve')
        self.assertEqual(len(review_history()),1)

    def test_03_approve_removes_low_confidence_pii_request(self):
        rid,result=self.new_request()
        log_review_action(rid,'edit_label',result['predicted_topic'],'Thu_tuc_hanh_chinh','Nội dung đã được kiểm tra.','Ghi chú')
        self.assertEqual(list_requests(pending_only=True),[])
        row=get_request(rid)
        self.assertEqual(row['predicted_topic'],'Hoc_phi')
        self.assertEqual(row['final_topic'],'Thu_tuc_hanh_chinh')
        self.assertEqual(row['final_response'],review_history()[0]['final_response'])

    def test_04_duplicate_approval_is_rejected_atomically(self):
        rid,result=self.new_request()
        log_review_action(rid,'approve','Hoc_phi','Hoc_phi','Phản hồi cuối cùng.')
        with self.assertRaises(ValueError):
            log_review_action(rid,'approve','Hoc_phi','Hoc_phi','Lần nhấn thứ hai.')
        self.assertEqual(len(review_history()),1)
        self.assertEqual(get_request(rid)['final_response'],'Phản hồi cuối cùng.')

    def test_05_editable_draft_survives_reload_and_masks_pii(self):
        rid,_=self.new_request()
        save_draft(rid,'Chào bạn,\n\nLiên hệ demo@example.org hoặc 0912 345 678.')
        draft=get_request(rid)['draft_response']
        self.assertIn('\n\n',draft)
        self.assertIn('[EMAIL]',draft)
        self.assertIn('[PHONE]',draft)
        self.assertNotIn('demo@example.org',draft)

    def test_06_pii_formats_and_urls(self):
        value='MSSV SV2026123; số 0912 345 678 và +84 912 345 678; mail demo@example.org; https://example.org/reset?token=DEMO'
        result=clean_text_single(value)
        for original in ('SV2026123','0912 345 678','+84 912 345 678','demo@example.org','https://'):
            self.assertNotIn(original,result['clean_text'])
        for token in ('[STUDENT_ID]','[PHONE]','[EMAIL]','[URL]'):
            self.assertIn(token,result['clean_text'])

    def test_07_short_request_abstains(self):
        result=self.service.process('Giúp em với')
        self.assertFalse(result['is_usable'])
        self.assertEqual(result['articles'],[])
        self.assertEqual(result['confidence_score'],0.)
        self.assertIn('bổ sung',result['draft_response'])

    def test_08_topic_bonus_cannot_force_irrelevant_reference(self):
        result=self.service.faq.generate_draft_response('zxqv plmno','Hoc_phi')
        self.assertEqual(result['articles'],[])
        self.assertIsNone(result['matched_kb_id'])

    def test_09_nan_and_overlapping_errors_are_counted_once(self):
        frame=pd.DataFrame({'raw_text':[None,'','Một câu hỏi hợp lệ về lịch học.']})
        result=analyze_dataframe_realtime(frame,'raw_text')
        self.assertEqual(result['empty_count'],2)
        self.assertEqual(result['usable_count'],1)

    def test_10_upload_export_has_no_original_columns_or_contacts(self):
        frame=pd.DataFrame({'email':['demo@example.org'],
            'raw_text':['Em quên mật khẩu, số 0912 345 678 hoặc demo@example.org.']})
        cleaned=clean_dataframe(frame)
        export=export_csv(cleaned).decode('utf-8-sig')
        self.assertNotIn('raw_text',export)
        self.assertNotIn('demo@example.org',export)
        self.assertNotIn('0912 345 678',export)
        self.assertIn('[EMAIL]',export)

    def test_11_unverified_sources_are_not_official_regulations(self):
        result=self.service.process('Em đã nộp học phí mà vẫn bị báo nợ trên cổng sinh viên.')
        self.assertTrue(result['articles'])
        self.assertTrue(all(not a['verified'] for a in result['articles']))
        self.assertIn('CHƯA XÁC MINH',result['draft_response'])
        self.assertNotIn('24h',result['draft_response'])

    def test_12_reject_and_empty_approval_validation(self):
        rid,_=self.new_request()
        with self.assertRaises(ValueError):
            log_review_action(rid,'approve','Hoc_phi','Hoc_phi','')
        self.assertEqual(len(review_history()),0)
        log_review_action(rid,'reject','Hoc_phi','Khac','Yêu cầu bị từ chối.')
        self.assertEqual(get_request(rid)['status'],'reviewed_reject')
        self.assertFalse(list_requests(pending_only=True))

    def test_13_profile_and_export_use_same_quality_definition(self):
        frame=pd.DataFrame({'raw_text':[None,'','Em xin hỏi lịch học ngày mai của lớp mình.',
                                      'Em xin hỏi lịch học ngày mai của lớp mình.']})
        profile=profile_dataset(frame)
        dashboard=analyze_dataframe_realtime(frame,'raw_text')
        self.assertEqual(profile['null_count'],dashboard['empty_count'])
        self.assertEqual(profile['usable_records'],dashboard['usable_count'])

if __name__=='__main__':
    unittest.main()
