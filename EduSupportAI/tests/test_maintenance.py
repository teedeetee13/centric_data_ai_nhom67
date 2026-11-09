"""Kiểm thử công cụ bảo trì trên CSDL tạm."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from src.config import PROCEDURE_KB_PATH
from src.database import get_connection, get_contact, init_db, save_contact
from src.maintenance import backup, check_knowledge_base, purge, restore, status


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp.name)
        self.db = self.root / 'app.db'
        init_db(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_rotates_and_restore_recovers_data(self):
        save_contact('REQ_1', 'sv@example.org', self.db)
        folder = self.root / 'bk'
        files = [backup(folder, keep=2, db_path=self.db) for _ in range(3)]
        self.assertEqual(sorted(folder.glob('*.db')), files[1:])

        save_contact('REQ_1', 'da-sua@example.org', self.db)
        safety = restore(files[-1], db_path=self.db)
        self.assertEqual(get_contact('REQ_1', self.db), 'sv@example.org')
        self.assertTrue(safety.exists())

    def test_restore_refuses_a_corrupt_file(self):
        bad = self.root / 'hong.db'
        bad.write_bytes(b'khong phai sqlite')
        save_contact('REQ_1', 'sv@example.org', self.db)
        with self.assertRaises(ValueError):
            restore(bad, db_path=self.db)
        self.assertEqual(get_contact('REQ_1', self.db), 'sv@example.org')

    def test_purge_only_counts_until_applied(self):
        save_contact('MOI', 'moi@example.org', self.db)
        save_contact('CU', 'cu@example.org', self.db)
        old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat(timespec='seconds')
        with get_connection(self.db) as conn:
            conn.execute("UPDATE request_contacts SET created_at=? WHERE record_id='CU'", (old,))

        self.assertEqual(purge(db_path=self.db)['request_contacts'], 1)
        self.assertEqual(get_contact('CU', self.db), 'cu@example.org')

        purge(apply=True, db_path=self.db)
        self.assertIsNone(get_contact('CU', self.db))
        self.assertEqual(get_contact('MOI', self.db), 'moi@example.org')

    def test_status_reports_counts(self):
        self.assertEqual(status(self.db)['tong_yeu_cau'], 0)

    def test_current_knowledge_base_is_valid(self):
        self.assertEqual(check_knowledge_base(), [])

    def test_broken_procedure_is_reported(self):
        data = json.loads(PROCEDURE_KB_PATH.read_text(encoding='utf-8'))
        data['procedures'][0]['topic'] = 'Khong_ton_tai'
        data['procedures'][1]['id'] = data['procedures'][0]['id']
        del data['procedures'][2]['steps'][0]['time']
        path = self.root / 'kb.json'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        errors = check_knowledge_base(procedure_path=path)
        self.assertTrue(any('chủ đề không hợp lệ' in e for e in errors))
        self.assertTrue(any('trùng mã' in e for e in errors))
        self.assertTrue(any('thiếu time' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
