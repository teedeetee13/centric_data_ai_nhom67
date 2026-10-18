# -*- coding: utf-8 -*-
"""
Module: src.config
Đường dẫn tập trung, biến môi trường và định nghĩa danh mục dùng chung.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "best_classifier.joblib"
KB_PATH = ROOT / "data" / "kb" / "eaut_faq_kb.csv"
RAW_DEMO_PATH = ROOT / "data" / "raw" / "synthetic_demo_424.csv"

TOPICS = {
    "Hoc_phi": "Học phí & Chính sách",
    "Lich_hoc_lich_thi": "Lịch học & Lịch thi",
    "Diem_khao_thi": "Điểm số & Khảo thí",
    "Thu_tuc_hanh_chinh": "Thủ tục hành chính",
    "Co_so_vat_chat": "Cơ sở vật chất",
    "He_thong_CNTT": "Hệ thống CNTT",
    "Khac": "Ý kiến khác"
}

def database_path():
    """Lấy đường dẫn CSDL SQLite từ biến môi trường hoặc mặc định data/edusupport.db."""
    return Path(os.environ.get("EDUSUPPORT_DB_PATH", ROOT / "data" / "edusupport.db"))

def describe_flags(flags):
    """Diễn giải danh sách cờ chất lượng dữ liệu sang tiếng Việt."""
    values = flags.split(";") if isinstance(flags, str) else (flags or [])
    labels = {
        "CLEAN": "Không có cờ cảnh báo",
        "empty": "Nội dung rỗng",
        "too_short": "Nội dung quá ngắn",
        "has_phone": "Đã bảo mật SĐT",
        "has_email": "Đã bảo mật Email",
        "has_student_id": "Đã bảo mật Mã SV",
        "has_url": "Đã bảo mật Đường dẫn",
        "exact_duplicate": "Trùng lặp 100%",
        "near_duplicate": "Gần trùng lặp"
    }
    return ", ".join(labels.get(v, v) for v in values) or "Không có cờ cảnh báo"
