# -*- coding: utf-8 -*-
"""
Module: src.sample_data
Nạp bộ câu hỏi mẫu mở rộng (data/mau_mo_rong.csv) vào hàng chờ để thử và trình diễn.
72 câu mô phỏng, phủ 33 quy trình và 10 loại dịch vụ của cổng hỗ trợ MIS; không dùng để huấn luyện.
"""

import pandas as pd

from src.config import ROOT
from src.database import get_request, save_request

EXTENDED_SAMPLE_PATH = ROOT / 'data' / 'mau_mo_rong.csv'


def load_extended_samples(path=None):
    return pd.read_csv(path or EXTENDED_SAMPLE_PATH, keep_default_na=False)


def import_samples(service, db_path=None):
    """Nạp các câu còn thiếu; nạp lại không tạo bản ghi trùng và giữ nguyên kết quả đã duyệt."""
    added = 0
    for row in load_extended_samples().itertuples():
        record_id = 'MAU_' + row.id
        if get_request(record_id, db_path):
            continue
        # Không gọi mô hình ngôn ngữ cho cả bộ: nạp nhanh, bản nháp theo mẫu
        save_request(service.process(row.text, use_llm=False), record_id=record_id,
                     source_type='controlled_demo', db_path=db_path)
        added += 1
    return added
