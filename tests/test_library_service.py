# -*- coding: utf-8 -*-
"""
Unit tests for EAUT Library Database & Service (Phương án A).
"""

import unittest
from src.database import (
    init_db,
    search_library_books,
    get_student_library_borrows,
    get_library_book,
    list_library_categories
)
from src.library_service import (
    is_library_inquiry,
    extract_student_id_from_text,
    query_library_data,
    build_library_live_block,
    augment_response_with_library_data
)
from src.service import RequestService

class TestLibraryService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_seed_books_and_borrows_exist(self):
        books = search_library_books(limit=50)
        self.assertGreaterEqual(len(books), 10)
        categories = list_library_categories()
        self.assertIn("Công nghệ thông tin", categories)

    def test_02_search_books_accent_and_unaccent(self):
        # Có dấu
        res1 = search_library_books("Kỹ thuật phần mềm")
        self.assertGreaterEqual(len(res1), 1)
        self.assertEqual(res1[0]["book_id"], "BK_IT_001")
        self.assertIn("Kệ A3", res1[0]["location"])

        # Không dấu
        res2 = search_library_books("ky thuat phan mem")
        self.assertGreaterEqual(len(res2), 1)
        self.assertEqual(res2[0]["book_id"], "BK_IT_001")

        # Tìm theo chuyên ngành
        it_books = search_library_books(category="Công nghệ thông tin")
        self.assertGreaterEqual(len(it_books), 3)

    def test_03_student_borrows_lookup_and_fine_calculation(self):
        # Sinh viên mượn đúng hạn
        borrows_valid = get_student_library_borrows("2022601234")
        self.assertGreaterEqual(len(borrows_valid), 1)
        self.assertEqual(borrows_valid[0]["status"], "Đang mượn")
        self.assertEqual(borrows_valid[0]["fine_amount"], 0)

        # Sinh viên quá hạn (MSSV 2021600123 mượn từ 2026-10-20, hạn 2026-10-27)
        borrows_overdue = get_student_library_borrows("2021600123")
        self.assertGreaterEqual(len(borrows_overdue), 1)
        item = borrows_overdue[0]
        self.assertEqual(item["status"], "Quá hạn")
        self.assertGreater(item["fine_amount"], 0)
        # Kiểm tra công thức phạt 5.000đ/ngày
        self.assertEqual(item["fine_amount"], item["overdue_days"] * 5000)

    def test_04_extract_student_id_from_text(self):
        t1 = "Em mssv: 2022601234 cần hỏi về hạn trả sách"
        self.assertEqual(extract_student_id_from_text(t1), "2022601234")

        t2 = "Mã sinh viên 2021600123 kiểm tra tiền phạt"
        self.assertEqual(extract_student_id_from_text(t2), "2021600123")

        t3 = "Tôi là cựu sinh viên 2019123456"
        self.assertEqual(extract_student_id_from_text(t3), "2019123456")

    def test_05_query_library_data_book_availability(self):
        query = "Cho em hỏi thư viện trường mình còn cuốn Giáo trình Kỹ thuật phần mềm không ạ và ở kệ nào?"
        res = query_library_data(query)
        self.assertTrue(res["is_library"])
        self.assertTrue(res["has_live_data"])
        self.assertGreaterEqual(len(res["books_found"]), 1)
        self.assertEqual(res["books_found"][0]["book_id"], "BK_IT_001")
        self.assertGreater(res["books_found"][0]["available_copies"], 0)

        block = build_library_live_block(res)
        self.assertIn("Kệ A3 - Tầng 2 Thư viện EAUT", block)
        self.assertIn("CÒN 3/10 CUỐN", block)

    def test_06_query_library_data_student_borrow_status(self):
        query = "Em mã sinh viên 2021600123 muốn kiểm tra xem đang mượn sách gì và có bị phạt quá hạn không ạ?"
        res = query_library_data(query)
        self.assertTrue(res["is_library"])
        self.assertTrue(res["has_live_data"])
        self.assertEqual(res["student_id"], "2021600123")
        self.assertGreaterEqual(len(res["student_borrows"]), 1)

        block = build_library_live_block(res)
        self.assertIn("QUÁ HẠN", block)
        self.assertIn("5.000đ/ngày", block)

    def test_07_request_service_integration(self):
        service = RequestService()
        result = service.process(
            "Em muốn hỏi cuốn Giáo trình Kỹ thuật phần mềm còn sách ở thư viện trường không ạ?",
            mask_pii=False
        )
        self.assertIn("library_lookup", result)
        lib_data = result.get("library_lookup")
        self.assertTrue(lib_data.get("has_live_data"))
        self.assertGreaterEqual(len(lib_data.get("books_found", [])), 1)

        # Kiểm tra văn bản giải đáp có tích hợp thông tin kệ sách
        draft = result.get("procedure_draft_response", "")
        self.assertIn("Kệ A3 - Tầng 2 Thư viện EAUT", draft)
        self.assertIn("CÒN 3/10 CUỐN SẴN SÀNG", draft)

if __name__ == "__main__":
    unittest.main()
