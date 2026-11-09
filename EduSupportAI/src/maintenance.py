# -*- coding: utf-8 -*-
"""
Module: src.maintenance
Công cụ bảo trì chạy bằng dòng lệnh, không cần giao diện. Hướng dẫn: docs/VAN_HANH.md
    python -m src.maintenance status
    python -m src.maintenance backup [--dir THU_MUC] [--keep 14]
    python -m src.maintenance restore TEP_SAO_LUU --yes
    python -m src.maintenance purge [--contact-days 90] [--email-days 180] [--apply]
    python -m src.maintenance check-kb
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.config import KB_PATH, MODEL_PATH, PROCEDURE_KB_PATH, TOPICS, database_path
from src.database import get_connection, init_db

BACKUP_PREFIX = 'edusupport_'
REQUIRED_PROCEDURE_FIELDS = ('id', 'name', 'topic', 'receiving_unit', 'legal_basis', 'source', 'aliases', 'keywords', 'steps')
REQUIRED_STEP_FIELDS = ('unit', 'action', 'time')


def default_backup_dir():
    return database_path().parent / 'backups'


def _copy_database(source, target):
    """Dùng API backup của SQLite: an toàn cả khi CSDL đang mở và đang ở chế độ WAL."""
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    # sqlite3.connect dạng with không tự đóng tệp; đóng để Windows cho phép đổi tên, xóa
    src.close()
    dst.close()


def _is_intact(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    except sqlite3.DatabaseError:
        return False
    finally:
        conn.close()


def backup(directory=None, keep=14, db_path=None):
    """Tạo bản sao lưu đã kiểm tra toàn vẹn và chỉ giữ lại `keep` bản mới nhất."""
    source = Path(db_path) if db_path else database_path()
    if not source.exists():
        raise FileNotFoundError(f'Không tìm thấy CSDL: {source}')
    folder = Path(directory) if directory else default_backup_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    target = folder / f'{BACKUP_PREFIX}{stamp}.db'
    _copy_database(source, target)
    if not _is_intact(target):
        target.unlink()
        raise RuntimeError('Bản sao lưu không vượt qua kiểm tra toàn vẹn nên đã bị bỏ.')
    for old in sorted(folder.glob(f'{BACKUP_PREFIX}*.db'))[:-keep]:
        old.unlink()
    return target


def restore(backup_file, db_path=None):
    """Khôi phục từ bản sao lưu; bản hiện tại được lưu lại trước để có thể quay về."""
    source = Path(backup_file)
    if not source.exists() or not _is_intact(source):
        raise ValueError(f'Tệp sao lưu không tồn tại hoặc bị hỏng: {source}')
    target = Path(db_path) if db_path else database_path()
    safety = None
    if target.exists():
        safety = target.with_name(f'{target.stem}_truoc_khoi_phuc.db')
        _copy_database(target, safety)
    _copy_database(source, target)
    return safety


def purge(contact_days=90, email_days=180, apply=False, db_path=None, now=None):
    """Xóa email liên hệ và nhật ký gửi quá hạn lưu trữ. Mặc định chỉ đếm, không xóa."""
    now = now or datetime.now(timezone.utc)
    rules = [('request_contacts', 'created_at', contact_days), ('email_dispatches', 'sent_at', email_days)]
    counts = {}
    with get_connection(db_path) as conn:
        for table, column, days in rules:
            cutoff = (now - timedelta(days=days)).isoformat(timespec='seconds')
            # Tên bảng và cột là hằng trong `rules`, không đến từ người dùng
            counts[table] = conn.execute(f'SELECT COUNT(*) FROM {table} WHERE {column} < ?', (cutoff,)).fetchone()[0]  # nosec B608
            if apply:
                conn.execute(f'DELETE FROM {table} WHERE {column} < ?', (cutoff,))  # nosec B608
    return counts


def check_knowledge_base(procedure_path=None, faq_path=None):
    """Kiểm tra kho quy trình và FAQ trước khi đưa vào dùng. Trả về danh sách lỗi."""
    errors = []
    data = json.loads(Path(procedure_path or PROCEDURE_KB_PATH).read_text(encoding='utf-8'))
    seen = set()
    for proc in data['procedures']:
        pid = proc.get('id', '?')
        if pid in seen:
            errors.append(f'{pid}: trùng mã quy trình')
        seen.add(pid)
        errors += [f'{pid}: thiếu {field}' for field in REQUIRED_PROCEDURE_FIELDS if not proc.get(field)]
        if proc.get('topic') not in TOPICS:
            errors.append(f"{pid}: chủ đề không hợp lệ ({proc.get('topic')})")
        if proc.get('source') not in data.get('sources', {}):
            errors.append(f"{pid}: nguồn không có trong sources ({proc.get('source')})")
        for number, step in enumerate(proc.get('steps') or [], 1):
            errors += [f'{pid} bước {number}: thiếu {field}' for field in REQUIRED_STEP_FIELDS if not step.get(field)]

    faq = pd.read_csv(faq_path or KB_PATH, dtype=str).fillna('')
    errors += [f'{kb_id}: trùng mã FAQ' for kb_id in faq.loc[faq['kb_id'].duplicated(), 'kb_id']]
    errors += [f'{kb_id}: chủ đề không hợp lệ' for kb_id in faq.loc[~faq['topic'].isin(TOPICS), 'kb_id']]
    unsourced = faq[(faq['verified'].str.lower() == 'true') & (faq['source_url'].str.strip() == '')]
    errors += [f'{kb_id}: verified=true nhưng thiếu source_url' for kb_id in unsourced['kb_id']]
    return errors


def status(db_path=None):
    """Số liệu nhanh về tình trạng hệ thống."""
    path = Path(db_path) if db_path else database_path()
    with get_connection(path) as conn:
        total = conn.execute('SELECT COUNT(*) FROM processed_requests').fetchone()[0]
        pending, oldest = conn.execute(
            "SELECT COUNT(*), MIN(processed_at) FROM processed_requests WHERE status='pending_review'").fetchone()
        contacts = conn.execute('SELECT COUNT(*) FROM request_contacts').fetchone()[0]
    backups = sorted(path.parent.joinpath('backups').glob(f'{BACKUP_PREFIX}*.db'))
    return {
        'co_so_du_lieu': str(path),
        'dung_luong_mb': round(path.stat().st_size / 1e6, 2),
        'tong_yeu_cau': total,
        'cho_duyet': pending,
        'cho_duyet_lau_nhat': oldest,
        'email_lien_he_dang_luu': contacts,
        'ban_sao_luu_moi_nhat': backups[-1].name if backups else None,
        'mo_hinh_cap_nhat': datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, timezone.utc).isoformat(timespec='seconds'),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Công cụ bảo trì EduSupportAI')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='Xem tình trạng hệ thống')
    p_backup = commands.add_parser('backup', help='Sao lưu CSDL')
    p_backup.add_argument('--dir')
    p_backup.add_argument('--keep', type=int, default=14)
    p_restore = commands.add_parser('restore', help='Khôi phục CSDL (tắt ứng dụng trước)')
    p_restore.add_argument('file')
    p_restore.add_argument('--yes', action='store_true', help='Xác nhận ghi đè CSDL hiện tại')
    p_purge = commands.add_parser('purge', help='Dọn dữ liệu quá hạn lưu trữ (mặc định chỉ đếm)')
    p_purge.add_argument('--contact-days', type=int, default=90)
    p_purge.add_argument('--email-days', type=int, default=180)
    p_purge.add_argument('--apply', action='store_true', help='Xóa thật')
    commands.add_parser('check-kb', help='Kiểm tra kho quy trình và FAQ')
    args = parser.parse_args(argv)

    if args.command == 'check-kb':
        errors = check_knowledge_base()
        print('\n'.join(errors) if errors else 'Kho tri thức hợp lệ.')
        return 1 if errors else 0
    if args.command == 'restore':
        if not args.yes:
            print('Thao tác này ghi đè CSDL hiện tại. Tắt ứng dụng rồi chạy lại với --yes.')
            return 1
        safety = restore(args.file)
        print(f'Đã khôi phục. Bản trước khi khôi phục: {safety}')
        return 0

    init_db()
    if args.command == 'status':
        for key, value in status().items():
            print(f'{key}: {value}')
    elif args.command == 'backup':
        print(f'Đã sao lưu: {backup(args.dir, args.keep)}')
    elif args.command == 'purge':
        counts = purge(args.contact_days, args.email_days, args.apply)
        print(('Đã xóa: ' if args.apply else 'Sẽ xóa (thêm --apply để xóa thật): ') + str(counts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
