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

def normalize_unicode_and_whitespace(text: str) -> str:
    """Chuẩn hóa Unicode NFC và dọn dẹp khoảng trắng thừa, giữ lại ngắt dòng phân đoạn."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFC', text)
    lines = [re.sub(r'[^\S\r\n]+', ' ', line).strip() for line in text.splitlines()]
    clean_text = '\n'.join(lines).strip()
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    return clean_text

def parse_student_feedback(raw_text: str) -> dict:
    """
    Tách nội dung phản ánh thành 3 phần rõ ràng:
    - student_message: Nội dung sinh viên trực tiếp nhập / phản ánh cốt lõi
    - issue: Vấn đề phân loại đã chọn (nếu có tiền tố 'Vấn đề ghi nhận:')
    - contacts: Thông tin liên hệ sinh viên (nếu có tiền tố 'Thông tin liên hệ:')
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {"issue": "", "contacts": "", "student_message": ""}

    content = raw_text.strip()
    issue = ""
    contacts = ""

    # 1. Trích xuất Thông tin liên hệ (nếu có)
    m_contact = re.search(r'Thông tin liên hệ:\s*(.+)$', content, re.IGNORECASE | re.DOTALL)
    if m_contact:
        contacts = m_contact.group(1).strip()
        content = content[:m_contact.start()].strip()

    # 2. Trích xuất Vấn đề ghi nhận (nếu có)
    m_issue = re.search(r'Vấn đề ghi nhận:\s*([^.\n]+(?:\.[^.\n]+)*?)(?:\.\s*|\n|$)', content, re.IGNORECASE)
    if m_issue:
        issue = m_issue.group(1).strip()
        content = content[m_issue.end():].strip()

    student_msg = content.strip(' .;\n')
    if not student_msg and issue:
        student_msg = issue
    elif not student_msg:
        student_msg = raw_text.strip()

    return {
        "issue": issue,
        "contacts": contacts,
        "student_message": student_msg
    }

def mask_pii(text: str) -> tuple[str, list[str]]:
    """
    Che giấu PII thành các token chuẩn hóa: [PHONE], [EMAIL], [STUDENT_ID], [URL].
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
    return hashlib.md5(canonical.encode('utf-8')).hexdigest()

def clean_text_single(raw_text: str, mask_pii_flag: bool = True) -> dict:
    """
    Hàm làm sạch đơn lẻ phục vụ kiểm thử nhanh và tích hợp trực tiếp trên Giao diện Streamlit.
    Hỗ trợ tùy chọn mask_pii_flag (mặc định True). Khi mask_pii_flag=False, bảo toàn nguyên vẹn nội dung.
    """
    norm = normalize_unicode_and_whitespace(raw_text)
    masked, pii_flags = mask_pii(norm)
    
    clean_val = masked if mask_pii_flag else norm
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
        "clean_text": clean_val,
        "quality_flags": flags,
        "is_usable": is_usable,
        "char_len": len(clean_val)
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
                for previous in corpus:
                    if min(len(text), len(previous)) / max(len(text), len(previous)) < 0.85:
                        continue
                    if difflib.SequenceMatcher(None, text.lower(), previous.lower()).ratio() >= 0.93:
                        flags.append('near_duplicate')
                        usable = False
                        break
                if usable:
                    corpus.append(text)

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
