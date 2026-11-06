# -*- coding: utf-8 -*-
"""
Kiểm thử tự động cho module src/email_service:
- Kiểm tra tạo nội dung email giải quyết chuẩn hóa, không emoji
- Kiểm tra chế độ Mock Dispatch khi chưa có thông tin đăng nhập SMTP
- Kiểm tra chế độ gửi SMTP thực tế (sử dụng mock smtplib)
- Kiểm tra lưu vết kiểm toán vào CSDL SQLite
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.database import init_db
from src.email_service import (
    DEFAULT_TEST_EMAIL,
    build_resolution_email,
    init_email_table,
    list_email_dispatches,
    send_resolution_email,
)

class EmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "test_email.db")
        self.patcher = patch.dict(os.environ, {"EDUSUPPORT_DB_PATH": self.db_path})
        self.patcher.start()
        init_db(self.db_path)
        init_email_table(self.db_path)

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_build_resolution_email(self):
        subj, body = build_resolution_email(
            record_id="REQ_UNITTEST1",
            topic="Hoc_phi",
            department="Phòng Tài chính - Kế toán",
            resolution_text="Đã gạch nợ học phí thành công cho sinh viên.",
            confidence_score=0.88,
            is_auto_approved=True
        )
        self.assertIn("REQ_UNITTEST1", subj)
        self.assertIn("REQ_UNITTEST1", body)
        self.assertIn("Học phí & Chính sách", body)
        self.assertIn("88.0%", body)
        self.assertIn("Tự động bởi AI", body)

    def test_send_simulated_dispatch(self):
        ok, msg = send_resolution_email(
            recipient_email=DEFAULT_TEST_EMAIL,
            subject="Test Tiêu đề",
            body_text="Nội dung kiểm thử gửi mail",
            record_id="REQ_MOCK",
            db_path=self.db_path
        )
        self.assertTrue(ok)
        self.assertIn("mô phỏng", msg)
        dispatches = list_email_dispatches(db_path=self.db_path)
        self.assertEqual(len(dispatches), 1)
        self.assertEqual(dispatches[0]["recipient_email"], DEFAULT_TEST_EMAIL)
        self.assertEqual(dispatches[0]["dispatch_mode"], "simulated")
        self.assertEqual(dispatches[0]["status"], "success")

    def test_invalid_email_rejected(self):
        ok, msg = send_resolution_email(
            recipient_email="invalid_address",
            subject="Test",
            body_text="Body",
            db_path=self.db_path
        )
        self.assertFalse(ok)
        self.assertIn("không hợp lệ", msg)

    @patch("smtplib.SMTP")
    def test_smtp_real_dispatch(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        override = {
            "server": "smtp.gmail.com",
            "port": "587",
            "user": "test_sender@eaut.edu.vn",
            "password": "secret_password"
        }

        ok, msg = send_resolution_email(
            recipient_email="kennysk114239@gmail.com",
            subject="Tiêu đề SMTP thực",
            body_text="Nội dung giải quyết",
            record_id="REQ_REAL",
            smtp_override=override,
            db_path=self.db_path
        )
        self.assertTrue(ok)
        self.assertIn("thành công qua máy chủ SMTP", msg)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test_sender@eaut.edu.vn", "secret_password")
        mock_server.sendmail.assert_called_once()

        dispatches = list_email_dispatches(db_path=self.db_path)
        self.assertEqual(len(dispatches), 1)
        self.assertEqual(dispatches[0]["dispatch_mode"], "smtp_real")
        self.assertEqual(dispatches[0]["status"], "success")

if __name__ == "__main__":
    unittest.main()
