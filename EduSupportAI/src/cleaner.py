# -*- coding: utf-8 -*-
"""
Module: src.cleaner
Pipeline làm sạch dữ liệu và bảo mật PII theo triết lý Data-Centric AI (DCAI):
1. Chuẩn hóa font Unicode dựng sẵn (NFC) & khoảng trắng
2. Che giấu thông tin định danh cá nhân PII ([PHONE], [EMAIL], [STUDENT_ID], [URL])
3. Phát hiện và gắn cờ câu rỗng, câu quá ngắn (< 12 ký tự)
4. Khử trùng lặp tuyệt đối (Canonical MD5 Hash) và gần trùng lặp (SequenceMatcher >= 0.93)
5. Xuất tập dữ liệu sạch chuẩn hóa, không rò rỉ dữ liệu gốc
"""

import os
import re
import hashlib
import unicodedata
import difflib
import pandas as pd

# Regex patterns chuẩn hóa cho PII tiếng Việt, sinh viên EAUT và URL
REGEX_PHONE = re.compile(r'(?<!\w)(?:\+?84|0)[ .()-]?[35789](?:[ .()-]*\d){8}(?!\w)')
REGEX_EMAIL = re.compile(r'[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}')
REGEX_STUDENT_ID = re.compile(r'(?<!\w)20\d{6,8}(?!\w)')
REGEX_CONTEXT_ID = re.compile(r'((?:mssv|mã\s*(?:sinh\s*viên|sv))\s*[:\-]?\s*)([a-zA-Z0-9]{6,15})\b', re.I)
REGEX_URL = re.compile(r'(?:https?://|www\.)[^\s<>]+', re.I)
REGEX_NATIONAL_ID = re.compile(r'(?<!\w)0\d{11}(?!\w)')
REGEX_CONTEXT_NATIONAL_ID = re.compile(r'((?:cccd|cmnd|căn\s*cước(?:\s*công\s*dân)?|chứng\s*minh(?:\s*nhân\s*dân)?)\s*(?:số|là)?\s*[:\-]?\s*)(\d{9,12})(?!\w)', re.I)
REGEX_BANK_ACCOUNT = re.compile(r'((?:stk|số\s*tài\s*khoản|so\s*tai\s*khoan)\s*(?:ngân\s*hàng\s*)?(?:số|là)?\s*[:\-]?\s*)(\d[\d .\-]{5,20}\d)(?!\w)', re.I)
REGEX_NAME_CONTEXT = re.compile(r'((?i:(?:em|mình|tôi)\s+tên\s+(?:là\s+)?|tên\s+(?:của\s+)?(?:em|mình|tôi)\s+là\s+|họ\s+(?:và\s+)?tên\s*(?:là\s*)?[:\-]?\s*))((?:\w+\s*){2,5})')
# Ký tự vô hình và điều khiển: có thể chèn vào giữa số để né bộ lọc PII
REGEX_INVISIBLE = re.compile('[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f­​-‏‪-‮⁠-⁤﻿]')

def normalize_unicode_and_whitespace(text: str) -> str:
    """Chuẩn hóa Unicode NFC và dọn dẹp khoảng trắng thừa."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFC', REGEX_INVISIBLE.sub('', text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _mask_name(match):
    """Chỉ che khi sau cụm "em tên là" có ít nhất hai từ viết hoa liên tiếp (dạng họ tên)."""
    words = match.group(2).split()
    count = 0
    for word in words:
        if not word[0].isupper():
            break
        count += 1
    if count < 2:
        return match.group(0)
    tail = ' '.join(words[count:])
    trailing = ' ' if match.group(2)[-1].isspace() else ''
    return f"{match.group(1)}[NAME]{' ' + tail if tail else ''}{trailing}"


def mask_pii(text: str) -> tuple[str, list[str]]:
    """
    Che giấu PII thành các token chuẩn hóa: [PHONE], [EMAIL], [STUDENT_ID], [URL],
    [NATIONAL_ID], [BANK_ACCOUNT], [NAME].
    Trả về (text_đã_che, danh_sách_cờ_pii).
    """
    pii_flags = []
    
    if REGEX_URL.search(text):
        pii_flags.append('has_url')
        text = REGEX_URL.sub('[URL]', text)
    
    if REGEX_PHONE.search(text):
        pii_flags.append("has_phone")
        text = REGEX_PHONE.sub('[PHONE]', text)

    if REGEX_EMAIL.search(text):
        pii_flags.append("has_email")
        text = REGEX_EMAIL.sub('[EMAIL]', text)

    if REGEX_CONTEXT_NATIONAL_ID.search(text) or REGEX_NATIONAL_ID.search(text):
        pii_flags.append('has_national_id')
        text = REGEX_CONTEXT_NATIONAL_ID.sub(lambda m: m.group(1) + '[NATIONAL_ID]', text)
        text = REGEX_NATIONAL_ID.sub('[NATIONAL_ID]', text)

    if REGEX_BANK_ACCOUNT.search(text):
        pii_flags.append('has_bank_account')
        text = REGEX_BANK_ACCOUNT.sub(lambda m: m.group(1) + '[BANK_ACCOUNT]', text)

    named = REGEX_NAME_CONTEXT.sub(_mask_name, text)
    if named != text:
        pii_flags.append('has_name')
        text = named

    if REGEX_STUDENT_ID.search(text):
        pii_flags.append("has_student_id")
        text = REGEX_STUDENT_ID.sub('[STUDENT_ID]', text)

    if REGEX_CONTEXT_ID.search(text):
        if 'has_student_id' not in pii_flags:
            pii_flags.append('has_student_id')
        text = REGEX_CONTEXT_ID.sub(lambda m: m.group(1) + '[STUDENT_ID]', text)

    return text, pii_flags

def get_canonical_hash(text: str) -> str:
    """Tạo mã băm MD5 chuẩn tắc để phát hiện trùng lặp tuyệt đối (bỏ qua dấu câu, viết hoa)."""
    canonical = re.sub(r'[^\w\s]', '', text.lower())
    canonical = re.sub(r'\s+', ' ', canonical).strip()
    return hashlib.md5(canonical.encode('utf-8'), usedforsecurity=False).hexdigest()

def clean_text_single(raw_text: str) -> dict:
    """
    Hàm làm sạch đơn lẻ phục vụ kiểm thử nhanh và tích hợp trực tiếp trên Giao diện Streamlit.
    """
    norm = normalize_unicode_and_whitespace(raw_text)
    masked, pii_flags = mask_pii(norm)
    
    flags = list(pii_flags)
    is_usable = True

    if not norm:
        flags.append('empty')
        is_usable = False
    elif len(norm) < 12:
        flags.append("too_short")
        is_usable = False

    return {
        "raw_text": raw_text,
        "clean_text": masked,
        "quality_flags": flags,
        "is_usable": is_usable,
        "char_len": len(masked)
    }

def clean_dataframe(df, text_col='raw_text'):
    """
    Làm sạch toàn bộ DataFrame phục vụ thống kê chất lượng và xuất dữ liệu an toàn.
    Đầu ra chỉ chứa các cột đã chuẩn hóa, không mang theo cột thô gốc.
    """
    if text_col not in df.columns:
        raise ValueError('Không tìm thấy cột nội dung đã chọn.')
    
    rows, seen, corpus = [], set(), []
    for position, value in enumerate(df[text_col].tolist(), start=1):
        result = clean_text_single(value)
        text = result['clean_text']
        flags = list(result['quality_flags'])
        digest = get_canonical_hash(text)
        usable = result['is_usable']

        if digest in seen:
            flags.append('exact_duplicate')
            usable = False
        else:
            seen.add(digest)
            if usable and len(text) > 20:
                lowered = text.lower()
                for previous_len, matcher in corpus:
                    if min(len(text), previous_len) / max(len(text), previous_len) < 0.85:
                        continue
                    # quick_ratio là cận trên rẻ của ratio: loại phần lớn cặp mà không đổi kết quả
                    matcher.set_seq1(lowered)
                    if matcher.quick_ratio() >= 0.93 and matcher.ratio() >= 0.93:
                        flags.append('near_duplicate')
                        usable = False
                        break
                if usable:
                    corpus.append((len(text), difflib.SequenceMatcher(None, '', lowered)))

        rows.append({
            'row_number': position,
            'clean_text': text,
            'quality_flags': ';'.join(flags) if flags else 'CLEAN',
            'is_usable': usable,
            'char_length': len(text)
        })

    return pd.DataFrame(rows, columns=['row_number', 'clean_text', 'quality_flags', 'is_usable', 'char_length'])

def run_cleaning_pipeline(raw_path=None, processed_path=None):
    """Thực thi pipeline làm sạch và xuất dữ liệu an toàn ra tệp CSV."""
    from src.config import ROOT, RAW_DEMO_PATH
    raw_path = raw_path or RAW_DEMO_PATH
    processed_path = processed_path or (ROOT / 'data' / 'processed' / 'dataset_clean.csv')
    
    frame = pd.read_csv(raw_path)
    clean = clean_dataframe(frame, 'raw_text')
    os.makedirs(os.path.dirname(str(processed_path)), exist_ok=True)
    clean.to_csv(processed_path, index=False, encoding='utf-8')
    print(f"[*] Đã xuất {len(clean)} dòng, {int(clean.is_usable.sum())} dòng dùng được vào {processed_path}")
    return clean

if __name__ == "__main__":
    run_cleaning_pipeline()
