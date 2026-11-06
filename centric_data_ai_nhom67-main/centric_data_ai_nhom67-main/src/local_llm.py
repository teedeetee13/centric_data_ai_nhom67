# -*- coding: utf-8 -*-
"""
Module: src.local_llm
Mô hình ngôn ngữ chạy cục bộ (Ollama, mặc định qwen2.5:3b) dùng để soạn bản nháp phản hồi:
- Chỉ được dựa trên ngữ cảnh quy trình đã truy xuất (RAG), không gọi dịch vụ ngoài, không cần API key
- Kiểm tra bám nguồn (grounding check): mọi con số, mã biểu mẫu, số quyết định trong bản nháp
  phải xuất hiện trong ngữ cảnh hoặc câu hỏi; vi phạm thì loại bản nháp và dùng bản theo mẫu
- Không có Ollama hoặc lỗi kết nối thì trả None để tầng service tự dùng bản nháp theo mẫu
"""

import json
import re
import urllib.error
import urllib.request

from src.config import LOCAL_LLM_MODE, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT, OLLAMA_HOST

# Giữ model trong bộ nhớ suốt buổi demo
KEEP_ALIVE = '30m'

SYSTEM_PROMPT = (
    "Bạn là trợ lý soạn bản nháp trả lời sinh viên cho cán bộ Phòng Công tác sinh viên và cố vấn học tập "
    "Trường Đại học Công nghệ Đông Á. Quy tắc bắt buộc:\n"
    "1. Chỉ dùng thông tin trong phần TÀI LIỆU QUY TRÌNH. Không thêm số ngày, mức tiền, mã biểu mẫu, "
    "số quyết định, địa chỉ hay đơn vị nào không có trong tài liệu.\n"
    "2. Nếu tài liệu không đủ để trả lời câu hỏi, nói rõ cán bộ sẽ xác minh thêm.\n"
    "3. Viết tiếng Việt, gọi sinh viên là 'bạn', tự xưng 'Bộ phận hỗ trợ' (không xưng 'tôi'), "
    "giọng hành chính lịch sự, không emoji, không markdown in đậm.\n"
    "4. Chép nguyên văn tên đơn vị và từ viết tắt như trong tài liệu (ví dụ 'P.HC-NS' giữ nguyên), "
    "không tự diễn giải tên đơn vị.\n"
    "5. Mở đầu đúng bằng dòng 'Chào bạn,'. Sau đó: trả lời trực tiếp câu hỏi; hồ sơ cần chuẩn bị; "
    "nơi nộp và thời hạn; thời gian giải quyết; yêu cầu bổ sung thông tin còn thiếu (nếu có). "
    "Kết thúc đúng bằng dòng 'Trân trọng.'\n"
    "6. Không lặp lại thông tin cá nhân; giữ nguyên các ký hiệu [PHONE], [EMAIL], [STUDENT_ID] nếu cần nhắc.\n"
    "7. Tối đa khoảng 180 từ."
)

# Những chuỗi "dữ kiện" cần đối chiếu nguồn: số (kể cả 4.000.000, 2,0, 0.5%), mã biểu mẫu, số văn bản
FACT_PATTERN = re.compile(
    r"\b(?:BM[\w\-/]*\d[\w\-/]*|\d+/(?:QĐ|TB|GUQ|NĐ)[\w\-/]*|\d+(?:[.,]\d+)*%?)",
    re.IGNORECASE,
)


def _normalize_fact(token: str) -> str:
    token = token.lower().replace(',', '.').rstrip('.')
    # "02" và "2" là cùng một dữ kiện
    if token[:1].isdigit():
        return token.lstrip('0') or '0'
    return token


def ungrounded_facts(answer: str, context: str, question: str = '') -> list[str]:
    """Liệt kê các dữ kiện trong bản nháp không có trong ngữ cảnh hoặc câu hỏi."""
    allowed = {_normalize_fact(t) for t in FACT_PATTERN.findall(context + '\n' + question)}
    # Số thứ tự đầu dòng ("1.", "2)", "- 3.") là định dạng danh sách, không phải dữ kiện
    body = re.sub(r'(?m)^\s*(?:[-•]\s*)?\d+[.)]\s+', '', answer)
    return sorted({t for t in FACT_PATTERN.findall(body) if _normalize_fact(t) not in allowed})


class LocalLLM:
    def __init__(self, host=None, model=None, timeout=None, mode=None):
        self.host = (host or OLLAMA_HOST).rstrip('/')
        self.model = model or LOCAL_LLM_MODEL
        self.timeout = timeout or LOCAL_LLM_TIMEOUT
        self.mode = (mode or LOCAL_LLM_MODE).lower()
        self._available = None

    def _request(self, path, payload=None, timeout=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(self.host + path, data=data,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def is_available(self, refresh=False) -> bool:
        """Ollama đang chạy và đã tải model cấu hình."""
        if self.mode == 'off':
            return False
        if self._available is None or refresh:
            try:
                tags = self._request('/api/tags', timeout=2)
                names = {m.get('name', '') for m in tags.get('models', [])}
                self._available = self.model in names or f"{self.model}:latest" in names
            except (urllib.error.URLError, OSError, ValueError):
                self._available = False
        return self._available

    def warm_up(self) -> bool:
        """Nạp sẵn model lên GPU/RAM để bản nháp đầu tiên không phải chờ (Ollama mặc định gỡ model sau 5 phút)."""
        if not self.is_available():
            return False
        try:
            self._request('/api/generate', {'model': self.model, 'prompt': '', 'keep_alive': KEEP_ALIVE}, timeout=180)
            return True
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            return False

    def status(self) -> str:
        if self.mode == 'off':
            return 'Đã tắt mô hình ngôn ngữ cục bộ (EDUSUPPORT_LLM=off); dùng bản nháp theo mẫu.'
        if self.is_available():
            return f'Mô hình ngôn ngữ cục bộ sẵn sàng: {self.model} (Ollama {self.host}).'
        return f'Chưa kết nối được Ollama hoặc chưa tải model {self.model}; dùng bản nháp theo mẫu.'

    def generate_reply(self, question: str, context: str) -> dict | None:
        """Soạn bản nháp dựa trên ngữ cảnh. Trả về None nếu không dùng được mô hình."""
        if not self.is_available():
            return None
        user_msg = f"CÂU HỎI CỦA SINH VIÊN (đã che thông tin cá nhân):\n{question}\n\nTÀI LIỆU QUY TRÌNH:\n{context}"
        try:
            resp = self._request('/api/chat', {
                'model': self.model,
                'stream': False,
                'keep_alive': KEEP_ALIVE,
                'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                             {'role': 'user', 'content': user_msg}],
                'options': {'temperature': 0.1, 'top_p': 0.9, 'num_ctx': 4096, 'num_predict': 512},
            })
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            self._available = None
            return None

        text = (resp.get('message') or {}).get('content', '').strip()
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        if not text:
            return None
        bad = ungrounded_facts(text, context, question)
        return {
            'text': text,
            'model': self.model,
            'grounded': not bad,
            'ungrounded_facts': bad,
            'duration_s': round(resp.get('total_duration', 0) / 1e9, 2),
        }
