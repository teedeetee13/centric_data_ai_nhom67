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
    build_rich_resolution_email,
    build_rejection_email,
    build_intake_confirmation_email,
    init_email_table,
    list_email_dispatches,
    send_resolution_email,
    get_smtp_config,
    save_smtp_credentials,
    test_smtp_connection,
    load_dotenv_file,
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

    def test_build_rich_resolution_email_html(self):
        proc_info = {
            "proc_id": "PROC_TC_01",
            "title": "Quy trình Nộp học phí và Đối soát ngân hàng",
            "legal_basis": "Quyết định Quản lý Tài chính EAUT",
            "processing_time": "24 - 48 giờ làm việc",
            "forms_required": "Biên lai chuyển khoản ngân hàng"
        }
        subj, plain, html_body = build_rich_resolution_email(
            record_id="REQ_RICH_001",
            topic="Hoc_phi",
            department="Phòng Tài chính - Kế toán",
            resolution_text="Kế toán đã kiểm tra và đối soát gạch nợ học phí cho sinh viên.",
            confidence_score=0.95,
            is_auto_approved=True,
            student_name="Nguyễn Văn An",
            student_id="2022601234",
            procedure_info=proc_info
        )
        self.assertIn("REQ_RICH_001", subj)
        self.assertIn("Nguyễn Văn An", plain)
        self.assertIn("2022601234", plain)
        self.assertIn("PROC_TC_01", plain)
        # Kiểm tra nội dung HTML
        self.assertIn("<!DOCTYPE html>", html_body)
        self.assertIn("TRƯỜNG ĐẠI HỌC CÔNG NGHỆ ĐÔNG Á", html_body)
        self.assertIn("REQ_RICH_001", html_body)
        self.assertIn("Nguyễn Văn An", html_body)
        self.assertIn("2022601234", html_body)
        self.assertIn("Phòng Kế toán - Tầng 1, Tòa nhà A", html_body)

    def test_build_rejection_email_guidance(self):
        subj, plain, html_body = build_rejection_email(
            record_id="REQ_REJ_001",
            topic="Diem_khao_thi",
            department="Phòng Quản lý Đào tạo & Khảo thí",
            reason_notes="Đơn xin phúc khảo nộp quá hạn 07 ngày sau khi công bố điểm thi theo quy chế.",
            student_name="Trần Thị Mai",
            student_id="2021600123"
        )
        self.assertIn("REQ_REJ_001", subj)
        self.assertIn("Trần Thị Mai", plain)
        self.assertIn("quá hạn 07 ngày", plain)
        self.assertIn("HƯỚNG DẪN KHẮC PHỤC", plain)
        self.assertIn("<!DOCTYPE html>", html_body)
        self.assertIn("THÔNG BÁO TẠM DỪNG THỤ LÝ", html_body)
        self.assertIn("quá hạn 07 ngày", html_body)

    def test_build_intake_confirmation_email(self):
        subj, plain, html_body = build_intake_confirmation_email(
            record_id="REQ_CONF_001",
            topic="Co_so_vat_chat",
            department="Phòng Quản trị - Cơ sở vật chất",
            clean_text="Điều hòa phòng 402 nhà B bị hỏng chảy nước.",
            priority_level="Cao",
            student_name="Lê Hoàng Long",
            student_id="2023602111",
            estimated_sla="12 - 24 giờ làm việc"
        )
        self.assertIn("REQ_CONF_001", subj)
        self.assertIn("Xác nhận tiếp nhận phản ánh học vụ", subj)
        self.assertIn("Lê Hoàng Long", plain)
        self.assertIn("12 - 24 giờ làm việc", plain)
        self.assertIn("<!DOCTYPE html>", html_body)
        self.assertIn("XÁC NHẬN TIẾP NHẬN YÊU CẦU", html_body)
        self.assertIn("Điều hòa phòng 402 nhà B", html_body)

    def test_save_smtp_credentials_and_load(self):
        env_file = Path(self.temp.name) / ".env.test"
        save_smtp_credentials("test_user@gmail.com", "abcd efgh ijkl mnop", env_path=env_file)
        self.assertTrue(env_file.exists())
        content = env_file.read_text(encoding="utf-8")
        self.assertIn("GMAIL_USER=test_user@gmail.com", content)
        self.assertIn("GMAIL_APP_PASSWORD=abcdefghijklmnop", content)

        # Kiểm tra nạp lại qua load_dotenv_file
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMAIL_USER", None)
            os.environ.pop("GMAIL_APP_PASSWORD", None)
            load_dotenv_file(filepath=env_file)
            self.assertEqual(os.environ.get("GMAIL_USER"), "test_user@gmail.com")
            self.assertEqual(os.environ.get("GMAIL_APP_PASSWORD"), "abcdefghijklmnop")

    def test_test_smtp_connection_validation(self):
        ok, msg = test_smtp_connection("", "")
        self.assertFalse(ok)
        self.assertIn("đầy đủ", msg)

        ok, msg = test_smtp_connection("invalid_email", "password123")
        self.assertFalse(ok)
        self.assertIn("không hợp lệ", msg)

    @patch("smtplib.SMTP")
    def test_test_smtp_connection_mock_success(self, mock_smtp):
        mock_instance = MagicMock()
        mock_smtp.return_value = mock_instance
        ok, msg = test_smtp_connection("user@gmail.com", "abcd efgh ijkl mnop")
        self.assertTrue(ok)
        self.assertIn("thành công", msg)
        mock_instance.starttls.assert_called_once()
        mock_instance.login.assert_called_once_with("user@gmail.com", "abcdefghijklmnop")
        mock_instance.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_test_smtp_connection_mock_auth_failure(self, mock_smtp):
        mock_instance = MagicMock()
        mock_smtp.return_value = mock_instance
        mock_instance.login.side_effect = Exception("535 5.7.8 Username and Password not accepted")
        ok, msg = test_smtp_connection("user@gmail.com", "wrongpass")
        self.assertFalse(ok)
        self.assertIn("không đúng", msg)

if __name__ == "__main__":
    unittest.main()
