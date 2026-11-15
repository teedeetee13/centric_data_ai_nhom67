"""Kiểm thử thống kê và bộ dữ liệu mẫu mở rộng."""
from datetime import datetime, timezone
import json
import unittest

from src.config import PROCEDURE_KB_PATH, TOPICS
from src.sample_data import load_extended_samples
from src.stats import compute_statistics


def row(rid, status='pending_review', kb='QT04', flags='CLEAN', usable=1, conf=0.8, prio='Bình thường',
        processed='2026-11-10T00:00:00+00:00', reviewed=None):
    return {'record_id': rid, 'status': status, 'matched_kb_id': kb, 'quality_flags': flags, 'is_usable': usable,
            'confidence_score': conf, 'priority_level': prio, 'predicted_topic': 'Thu_tuc_hanh_chinh',
            'processed_at': processed, 'reviewed_at': reviewed}


class StatisticsTests(unittest.TestCase):
    def test_counts_and_rates(self):
        rows = [
            row('A', prio='Khẩn cấp', flags='has_phone'),
            row('B', status='reviewed_approve', reviewed='2026-11-10T02:00:00+00:00'),
            row('C', status='reviewed_edit_label', kb='KB001', reviewed='2026-11-10T04:00:00+00:00'),
            row('D', status='reviewed_reject', kb=None, usable=0, conf=0.0, flags='too_short'),
        ]
        logs = [{'officer_notes': 'AI tự động phê duyệt'}, {'officer_notes': ''}]
        s = compute_statistics(rows, logs, now=datetime(2026, 11, 12, tzinfo=timezone.utc))
        self.assertEqual((s['total'], s['pending'], s['urgent_pending'], s['reviewed'], s['rejected']), (4, 1, 1, 2, 1))
        self.assertEqual(s['auto_approved'], 1)
        self.assertAlmostEqual(s['avg_handle_hours'], 3.0)
        self.assertAlmostEqual(s['oldest_pending_days'], 2.0)
        self.assertAlmostEqual(s['procedure_match_rate'], 2 / 3)
        self.assertAlmostEqual(s['label_change_rate'], 0.5)
        self.assertEqual(s['top_procedures'][0][0], 'QT04')

    def test_empty_input(self):
        s = compute_statistics([], [])
        self.assertEqual(s['total'], 0)
        self.assertIsNone(s['avg_handle_hours'])


class ExtendedSampleTests(unittest.TestCase):
    def test_sample_set_covers_all_procedures_and_is_valid(self):
        data = load_extended_samples()
        procedures = {p['id'] for p in json.loads(PROCEDURE_KB_PATH.read_text(encoding='utf-8'))['procedures']}
        self.assertEqual(set(data['procedure']) - {''}, procedures)
        self.assertTrue(set(data['topic']) <= set(TOPICS))
        self.assertEqual(data['dich_vu_mis'].nunique(), 10)
        self.assertTrue(data['id'].is_unique)


if __name__ == '__main__':
    unittest.main()
