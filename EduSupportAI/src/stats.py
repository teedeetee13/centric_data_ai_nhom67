# -*- coding: utf-8 -*-
"""
Module: src.stats
Tính các chỉ số thống kê từ yêu cầu và nhật ký duyệt (không phụ thuộc giao diện).
"""

import json
from collections import Counter
from datetime import datetime, timezone

from src.config import PROCEDURE_KB_PATH, TOPICS

REVIEWED = ('reviewed_approve', 'reviewed_edit_label')


def _parse(stamp):
    try:
        value = datetime.fromisoformat(str(stamp).replace(' ', 'T'))
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _ratio(part, whole):
    return part / whole if whole else 0.0


def procedure_names():
    data = json.loads(PROCEDURE_KB_PATH.read_text(encoding='utf-8'))
    return {p['id']: p['name'] for p in data['procedures']}


def compute_statistics(rows, logs, now=None):
    """rows: list_requests(); logs: review_history(). Trả về dict chỉ số và các bảng đếm."""
    now = now or datetime.now(timezone.utc)
    total = len(rows)
    status = Counter(r['status'] for r in rows)
    pending = [r for r in rows if r['status'] == 'pending_review']
    reviewed = [r for r in rows if r['status'] in REVIEWED]

    handle_hours = []
    for r in reviewed:
        start, end = _parse(r.get('processed_at')), _parse(r.get('reviewed_at'))
        if start and end:
            handle_hours.append((end - start).total_seconds() / 3600)
    pending_ages = [(now - t).total_seconds() / 86400 for t in (_parse(r['processed_at']) for r in pending) if t]

    names = procedure_names()
    procedures = Counter(r['matched_kb_id'] for r in rows if str(r.get('matched_kb_id') or '').startswith('QT'))
    usable = [r for r in rows if r['is_usable']]

    return {
        'total': total,
        'pending': len(pending),
        'urgent_pending': sum(r['priority_level'] == 'Khẩn cấp' for r in pending),
        'reviewed': len(reviewed),
        'rejected': status.get('reviewed_reject', 0),
        'auto_approved': sum('tự động' in str(log.get('officer_notes', '')).lower() for log in logs),
        'oldest_pending_days': max(pending_ages) if pending_ages else 0.0,
        'avg_handle_hours': sum(handle_hours) / len(handle_hours) if handle_hours else None,
        'procedure_match_rate': _ratio(len([r for r in usable if str(r.get('matched_kb_id') or '').startswith('QT')]), len(usable)),
        'pii_rate': _ratio(sum('has_' in str(r['quality_flags']) for r in rows), total),
        'unusable_rate': _ratio(total - len(usable), total),
        'mean_confidence': _ratio(sum(r['confidence_score'] for r in usable), len(usable)),
        'label_change_rate': _ratio(status.get('reviewed_edit_label', 0), len(reviewed)),
        'by_topic': {TOPICS.get(k, k): v for k, v in Counter(r['predicted_topic'] for r in rows).most_common()},
        'by_priority': {p: sum(r['priority_level'] == p for r in rows) for p in ('Khẩn cấp', 'Cao', 'Bình thường', 'Thấp')},
        'by_status': {
            'Chờ duyệt': len(pending),
            'Đã duyệt': status.get('reviewed_approve', 0),
            'Duyệt, đổi nhãn': status.get('reviewed_edit_label', 0),
            'Từ chối': status.get('reviewed_reject', 0),
        },
        'top_procedures': [(pid, names.get(pid, pid), n) for pid, n in procedures.most_common(8)],
    }
