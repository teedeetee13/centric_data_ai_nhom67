import os

# Bộ test không phụ thuộc Ollama: luôn dùng bản nháp theo mẫu, trừ khi test tự cấp mô hình giả lập
os.environ.setdefault('EDUSUPPORT_LLM', 'off')
