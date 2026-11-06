# -*- coding: utf-8 -*-
"""
Module: src.procedure_engine
Engine xử lý ticket theo quy trình nghiệp vụ EAUT (kho data/kb/eaut_quy_trinh.json):
- Ghép câu hỏi với quy trình phù hợp nhất (TF-IDF word + char trên văn bản bỏ dấu, chịu được gõ không dấu)
- Định tuyến ticket tới đơn vị đầu mối tiếp nhận theo quy trình
- Lập phiếu xử lý: điều kiện, hồ sơ cần chuẩn bị, các bước - đơn vị - thời gian, hạn xử lý dự kiến (SLA)
- Phát hiện thông tin còn thiếu để yêu cầu sinh viên bổ sung
- Soạn bản nháp theo mẫu (luôn có, dùng làm phương án dự phòng khi không có mô hình ngôn ngữ cục bộ)
"""

import json
import re
import unicodedata
from datetime import date, timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import FeatureUnion

from src.config import PROCEDURE_KB_PATH


# Từ đệm, xưng hô trong câu hỏi của sinh viên (đã bỏ dấu); loại khỏi so khớp để điểm phản ánh nội dung nghiệp vụ
STOPWORDS = set('''
em e anh chi minh toi thay co ban cho hoi xin a da ah oi voi nhe nha ha the thi la ma va hay hoac
co khong ko k duoc dc muon can phai lam sao nao gi j nhu nay kia do roi chua nua cung van dang se
bi cua o tai de vi nen neu khi luc giup ho voi a vay ve len xuong ra vao mot nhung cac cai
'''.split())

# Viết tắt hay gặp trong tin nhắn của sinh viên
ABBREVIATIONS = {'sv': 'sinh viên', 'svien': 'sinh viên', 'mssv': 'mã sinh viên', 'clb': 'câu lạc bộ',
                 'gvhd': 'giảng viên hướng dẫn', 'nvqs': 'nghĩa vụ quân sự', 'drl': 'rèn luyện',
                 'xn': 'xác nhận', 'gxn': 'giấy xác nhận'}


def normalize_text(text: str) -> str:
    """Chữ thường NFC, bỏ dấu câu, mở rộng viết tắt (giữ nguyên dấu tiếng Việt)."""
    words = re.sub(r'[^\w\s]', ' ', unicodedata.normalize('NFC', str(text).lower())).split()
    return ' '.join(ABBREVIATIONS.get(w, w) for w in words)


def remove_diacritics(text: str) -> str:
    text = unicodedata.normalize('NFD', text).replace('đ', 'd')
    return ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt và chuẩn hóa chữ thường để so khớp câu gõ có dấu và không dấu như nhau."""
    return remove_diacritics(normalize_text(text))


def has_diacritics(text: str) -> bool:
    return normalize_text(text) != strip_accents(text)


def content_words(text: str) -> str:
    """Văn bản bỏ dấu, đã loại từ đệm, dùng cho TF-IDF."""
    return ' '.join(w for w in strip_accents(text).split() if w not in STOPWORDS)


def add_working_days(start: date, days: int) -> date:
    """Cộng số ngày làm việc (bỏ qua thứ Bảy, Chủ nhật)."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


class ProcedureEngine:
    def __init__(self, kb_path=None, min_similarity=0.28):
        self.kb_path = str(kb_path or PROCEDURE_KB_PATH)
        self.min_similarity = min_similarity
        with open(self.kb_path, encoding='utf-8') as fh:
            data = json.load(fh)
        self.sources = data.get('sources', {})
        self.procedures = data['procedures']

        # Mỗi tên quy trình và mỗi câu hỏi mẫu là một tài liệu riêng; điểm của quy trình = điểm cao nhất
        self.doc_owner = []
        docs = []
        for idx, proc in enumerate(self.procedures):
            for phrase in [proc['name']] + proc.get('aliases', []):
                docs.append(content_words(phrase))
                self.doc_owner.append(idx)
        # Từ khóa neo: quy trình chỉ được ghép khi câu hỏi chứa ít nhất một từ khóa nghiệp vụ của nó
        # Lưu cả bản có dấu (tránh "chuyên ngành" trùng "chuyển ngành") và bản bỏ dấu (cho câu gõ không dấu)
        self.keywords = [[(normalize_text(k), strip_accents(k)) for k in proc.get('keywords', [])]
                         for proc in self.procedures]

        self.vectorizer = FeatureUnion([
            ('word', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)),
        ])
        self.doc_vectors = self.vectorizer.fit_transform(docs)

    def match(self, query_text: str, predicted_topic: str = None, top_k: int = 3) -> list[dict]:
        """Trả về các quy trình phù hợp nhất (đã lọc theo ngưỡng), kèm điểm tương đồng."""
        query = content_words(query_text)
        if not query:
            return []
        accented = has_diacritics(query_text)
        padded = f" {normalize_text(query_text) if accented else strip_accents(query_text)} "
        sims = cosine_similarity(self.vectorizer.transform([query]), self.doc_vectors)[0]
        best = {}
        for doc_idx, score in enumerate(sims):
            owner = self.doc_owner[doc_idx]
            best[owner] = max(best.get(owner, 0.0), float(score))

        ranked = []
        for idx, score in best.items():
            hits = [plain for full, plain in self.keywords[idx] if f" {full if accented else plain} " in padded]
            if score < self.min_similarity or (self.keywords[idx] and not hits):
                continue
            proc = self.procedures[idx]
            # Ngưỡng áp dụng trên điểm gốc; nhãn chủ đề và từ khóa dài (cụ thể hơn) chỉ cộng điểm xếp hạng
            bonus = 0.05 if predicted_topic and proc['topic'] == predicted_topic else 0.0
            bonus += 0.02 * max(len(k.split()) for k in hits) if hits else 0.0
            ranked.append({'procedure': proc, 'score': round(score, 4), 'rank_score': score + bonus,
                           'keyword_hits': hits})
        ranked.sort(key=lambda r: r['rank_score'], reverse=True)
        return ranked[:top_k]

    def build_ticket_plan(self, query_text: str, procedure: dict, score: float, today: date = None) -> dict:
        """Lập phiếu xử lý ticket theo quy trình đã ghép."""
        today = today or date.today()
        missing = []
        if procedure.get('requires_student_id') and '[STUDENT_ID]' not in query_text:
            missing.append('Mã sinh viên')

        # Việc tiếp theo phía nhà trường: bước đầu tiên không do riêng sinh viên tự làm
        next_step = next((s for s in procedure['steps'] if s['unit'].strip().lower() != 'sinh viên'), procedure['steps'][0])
        max_days = procedure.get('max_days')
        return {
            'procedure_id': procedure['id'],
            'procedure_name': procedure['name'],
            'topic': procedure['topic'],
            'receiving_unit': procedure['receiving_unit'],
            'legal_basis': procedure.get('legal_basis', ''),
            'source_doc': self.sources.get(procedure.get('source'), procedure.get('source', '')),
            'match_score': score,
            'conditions': procedure.get('conditions', []),
            'documents': procedure.get('documents', []),
            'submit_window': procedure.get('submit_window', ''),
            'steps': procedure['steps'],
            'result_time': procedure.get('result_time', ''),
            'sla_due_date': add_working_days(today, max_days).isoformat() if max_days else None,
            'missing_info': missing,
            'status': 'Chờ sinh viên bổ sung thông tin' if missing else 'Đã tiếp nhận',
            'next_action': f"{next_step['unit']}: {next_step['action']}",
        }

    def plan_to_article(self, plan: dict) -> dict:
        """Chuyển phiếu xử lý sang dạng tài liệu tham chiếu để giao diện và CSDL hiện có hiển thị được."""
        lines = [f"Căn cứ: {plan['legal_basis']}", f"Đơn vị đầu mối tiếp nhận: {plan['receiving_unit']}"]
        if plan['conditions']:
            lines.append('Điều kiện: ' + '; '.join(plan['conditions']))
        if plan['documents']:
            lines.append('Hồ sơ: ' + '; '.join(plan['documents']))
        if plan['submit_window']:
            lines.append(f"Thời hạn nộp: {plan['submit_window']}")
        for i, step in enumerate(plan['steps'], 1):
            lines.append(f"Bước {i} - {step['unit']}: {step['action']} ({step['time']})")
        lines.append(f"Thời gian giải quyết: {plan['result_time']}")
        if plan['sla_due_date']:
            lines.append(f"Hạn xử lý dự kiến (ngày làm việc): {plan['sla_due_date']}")
        return {
            'kb_id': plan['procedure_id'],
            'type': 'procedure',
            'topic': plan['topic'],
            'question_standard': 'Quy trình: ' + plan['procedure_name'],
            'content_extract': '\n'.join(lines),
            'department': plan['receiving_unit'],
            'source_url': plan['source_doc'],
            'verified': True,
            'similarity_score': plan['match_score'],
            'rank_score': plan['match_score'],
        }


def context_for_llm(plan: dict) -> str:
    """Văn bản ngữ cảnh duy nhất mà mô hình ngôn ngữ được phép dựa vào."""
    parts = [
        f"Quy trình: {plan['procedure_name']} (mã {plan['procedure_id']})",
        f"Căn cứ: {plan['legal_basis']}",
        f"Đơn vị đầu mối tiếp nhận: {plan['receiving_unit']}",
    ]
    if plan['conditions']:
        parts.append('Điều kiện:\n' + '\n'.join('- ' + c for c in plan['conditions']))
    if plan['documents']:
        parts.append('Hồ sơ cần chuẩn bị:\n' + '\n'.join('- ' + d for d in plan['documents']))
    if plan['submit_window']:
        parts.append(f"Thời hạn nộp: {plan['submit_window']}")
    parts.append('Các bước xử lý:\n' + '\n'.join(
        f"{i}. {s['unit']}: {s['action']} ({s['time']})" for i, s in enumerate(plan['steps'], 1)))
    parts.append(f"Thời gian giải quyết: {plan['result_time']}")
    if plan['missing_info']:
        parts.append('Thông tin sinh viên còn thiếu: ' + ', '.join(plan['missing_info']))
    return '\n\n'.join(parts)


def render_template_reply(plan: dict) -> str:
    """Bản nháp theo mẫu, chỉ ghép nội dung có trong quy trình (không sinh nội dung mới)."""
    lines = [
        'Chào bạn,',
        '',
        f"Bộ phận hỗ trợ đã tiếp nhận yêu cầu của bạn về: {plan['procedure_name'].lower()}. "
        f"Theo {plan['legal_basis']}, bạn tham khảo hướng dẫn sau:",
    ]
    if plan['conditions']:
        lines += ['', 'Điều kiện áp dụng:'] + ['- ' + c for c in plan['conditions']]
    if plan['documents']:
        lines += ['', 'Hồ sơ cần chuẩn bị:'] + ['- ' + d for d in plan['documents']]
    lines += ['', f"Nơi tiếp nhận: {plan['receiving_unit']}."]
    if plan['submit_window']:
        lines.append(f"Thời hạn nộp: {plan['submit_window']}.")
    lines.append(f"Thời gian giải quyết dự kiến: {plan['result_time']}.")
    if plan['missing_info']:
        lines += ['', f"Để cán bộ xử lý nhanh hơn, bạn vui lòng bổ sung: {', '.join(plan['missing_info'])}."]
    lines += ['', 'Trân trọng.']
    return '\n'.join(lines)
