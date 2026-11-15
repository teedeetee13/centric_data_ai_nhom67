# -*- coding: utf-8 -*-
"""
Tests for Local Learning Machine, Document Parser and Trace Logger.
"""
import unittest
from src.doc_parser import build_procedure_catalog
from src.local_machine import get_local_machine
from src.trace_logger import ExecutionTrace

class LocalMachineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.machine = get_local_machine()

    def test_01_catalog_extraction(self):
        catalog = build_procedure_catalog()
        self.assertGreaterEqual(len(catalog), 10)
        proc_ids = [p["proc_id"] for p in catalog]
        self.assertIn("PROC_DT_01", proc_ids)
        self.assertIn("PROC_CTSV_01", proc_ids)
        self.assertIn("PROC_CSVC_01", proc_ids)

    def test_02_procedure_retrieval(self):
        # Query về chuyển ngành
        matches = self.machine.retrieve_procedure("Em muốn xin chuyển ngành học từ QTKD sang Công nghệ thông tin")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["proc_id"], "PROC_DT_01")
        self.assertIn("Quyết định số 348", matches[0]["legal_basis"])

    def test_03_procedure_retrieval_facilities(self):
        # Query về điều hòa hỏng
        matches = self.machine.retrieve_procedure("Điều hòa phòng học tầng 4 nhà B bị hỏng chảy nước")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["proc_id"], "PROC_CSVC_01")
        self.assertIn("180", matches[0]["legal_basis"])

    def test_04_trace_logging_execution(self):
        result = self.machine.process_request_with_trace(
            "Em muốn xin giấy xác nhận sinh viên để hoãn nghĩa vụ quân sự, sđt 0912345678"
        )
        self.assertIn("execution_trace", result)
        self.assertIn("terminal_log", result)
        trace = result["execution_trace"]
        self.assertEqual(len(trace["steps"]), 5)
        self.assertIn("has_phone", result["quality_flags"])
        self.assertNotIn("0912345678", result["clean_text"])
        self.assertIn("[PHONE]", result["clean_text"])
        self.assertIn("PROC_CTSV_01", result["matched_procedure"]["proc_id"])
        self.assertIn("118", result["matched_procedure"]["legal_basis"])
        self.assertTrue(result["reasoning_steps"])

    def test_05_terminal_log_format(self):
        trace = ExecutionTrace("TRACE_TEST_001", "REQ_TEST_001")
        step = trace.new_step(1, "TEST_STEP", "Testing step description")
        step.add_log("This is a test log message")
        step.finish(status="SUCCESS", metric=123)
        trace.finalize()
        term_log = trace.format_terminal_log()
        self.assertIn("EDUSUPPORT-AI :: LOCAL LEARNING MACHINE EXECUTION TRACE LOG", term_log)
        self.assertIn("TRACE_TEST_001", term_log)
        self.assertIn("BƯỚC 1", term_log)
        self.assertIn("metric: 123", term_log)

    def test_06_borrow_facilities_diagnosis_and_direct_email(self):
        from src.cleaner import parse_student_feedback
        sample_input = (
            "Vấn đề ghi nhận: Đăng ký mượn phòng học, Hội trường và Thiết bị ngoài giờ. "
            "em muốn đăng ký mượn mic và điều khiển điều hòa cho phòng học "
            "Thông tin liên hệ: Mã sinh viên 1234234567, Số điện thoại 1234567823, Email a@mail.com."
        )
        parsed = parse_student_feedback(sample_input)
        self.assertEqual(parsed["student_message"], "em muốn đăng ký mượn mic và điều khiển điều hòa cho phòng học")
        self.assertIn("Đăng ký mượn phòng học", parsed["issue"])
        self.assertIn("1234234567", parsed["contacts"])

        matches = self.machine.retrieve_procedure(sample_input, predicted_topic="Co_so_vat_chat")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["proc_id"], "PROC_CSVC_02")

        steps, draft = self.machine.reason_and_synthesize(sample_input, "Co_so_vat_chat", matches[0])
        # Đảm bảo email đi thẳng vào trọng tâm, không liệt kê quy trình rườm rà
        self.assertNotIn("[CHẨN ĐOÁN VẤN ĐỀ", draft)
        self.assertNotIn("Trình tự các bước thực hiện:", draft)
        self.assertNotIn("Tình huống nhận diện: Báo hỏng", draft)
        self.assertIn("mượn micro", draft.lower())
        self.assertIn("Chào bạn,", draft)
        self.assertIn("Trân trọng.", draft)

if __name__ == "__main__":
    unittest.main()
