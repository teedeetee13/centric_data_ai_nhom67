# -*- coding: utf-8 -*-
"""
Module: src.trace_logger
Bộ ghi nhận và truy vết minh bạch (Explainability & Execution Trace Logger)
thể hiện rõ từng bước làm việc của toàn bộ sản phẩm và Local Learning Machine / LLM:
- Bước 1: Tiếp nhận, chuẩn hóa Unicode NFC, che giấu PII, kiểm toán chất lượng dữ liệu
- Bước 2: Máy học cục bộ trích xuất đặc trưng TF-IDF kép, dự đoán chủ đề, độ tự tin & ưu tiên nghiệp vụ
- Bước 3: Tra cứu đối chiếu quy trình nghiệp vụ tương đồng từ kho tài liệu data-doc
- Bước 4: Lập luận từng bước (Chain-of-Thought Reasoning) & Tổng hợp câu trả lời theo quy chuẩn
- Bước 5: Kiểm định rào chắn an toàn (Guardrails) & Ra quyết định phân luồng (Tự động / Bàn duyệt)
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any

def current_time_str() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

class TraceStep:
    def __init__(self, step_number: int, name: str, description: str):
        self.step_number = step_number
        self.name = name
        self.description = description
        self.status = "PENDING"
        self.duration_ms = 0.0
        self.details: Dict[str, Any] = {}
        self.logs: List[str] = []
        self._start_time = time.perf_counter()

    def add_log(self, message: str):
        timestamp = current_time_str()
        self.logs.append(f"[{timestamp}] {message}")

    def finish(self, status: str = "SUCCESS", **details):
        self.duration_ms = round((time.perf_counter() - self._start_time) * 1000, 2)
        self.status = status
        self.details.update(details)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "details": self.details,
            "logs": self.logs
        }

class ExecutionTrace:
    def __init__(self, trace_id: str, record_id: str = ""):
        self.trace_id = trace_id
        self.record_id = record_id
        self.start_time_iso = current_time_str()
        self.steps: List[TraceStep] = []
        self._start_perf = time.perf_counter()
        self.total_duration_ms = 0.0

    def new_step(self, step_number: int, name: str, description: str) -> TraceStep:
        step = TraceStep(step_number, name, description)
        self.steps.append(step)
        return step

    def finalize(self):
        self.total_duration_ms = round((time.perf_counter() - self._start_perf) * 1000, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "record_id": self.record_id,
            "start_time": self.start_time_iso,
            "total_duration_ms": self.total_duration_ms,
            "steps": [s.to_dict() for s in self.steps]
        }

    def format_terminal_log(self) -> str:
        """Định dạng log kiểu terminal / console chi tiết, rõ ràng, không bị cắt xén chuỗi."""
        sep_double = "=" * 80
        sep_single = "-" * 80
        lines = [
            sep_double,
            "EDUSUPPORT-AI :: LOCAL LEARNING MACHINE EXECUTION TRACE LOG",
            f"Trace ID  : {self.trace_id} | Record ID: {self.record_id or 'N/A'}",
            f"Timestamp : {self.start_time_iso} | Total Latency: {self.total_duration_ms:.2f} ms",
            sep_double,
        ]

        for s in self.steps:
            status_icon = "[OK]" if s.status in ("SUCCESS", "AUTO_APPROVED") else ("[WAIT]" if s.status in ("REVIEW_QUEUE", "WARNING") else "[ERR]")
            lines.append(f"{status_icon} BƯỚC {s.step_number}: {s.name} ({s.duration_ms:.2f} ms)")
            lines.append(f"     Mục tiêu: {s.description}")
            for log in s.logs:
                lines.append(f"     > {log}")
            for k, v in s.details.items():
                if isinstance(v, (dict, list)):
                    v_str = json.dumps(v, ensure_ascii=False)
                else:
                    v_str = str(v)
                lines.append(f"     * {k}: {v_str}")
            lines.append(sep_single)

        lines.append(f"HOÀN TẤT CHUỖI XỬ LÝ (5 BƯỚC) TRONG {self.total_duration_ms:.2f} MS")
        lines.append(sep_double)
        return "\n".join(lines)

    def format_markdown(self) -> str:
        """Định dạng markdown trực quan cho giao diện người dùng."""
        md = []
        md.append(f"#### Chi Tiết Luồng Hoạt Động Của Máy Học & LLM Trace (`{self.trace_id}`)")
        md.append(f"**Thời điểm tiếp nhận:** `{self.start_time_iso}` | **Tổng thời gian xử lý:** `{self.total_duration_ms:.2f} ms`\n")

        for s in self.steps:
            badge = "🟢 Thành công" if s.status in ("SUCCESS", "AUTO_APPROVED") else ("🟡 Cần rà soát" if s.status in ("REVIEW_QUEUE", "WARNING") else "🔴 Cảnh báo")
            md.append(f"**Bước {s.step_number}: {s.name}** — *{badge}* (`{s.duration_ms:.2f} ms`)")
            md.append(f"> *{s.description}*")
            if s.details:
                md.append("```json")
                md.append(json.dumps(s.details, ensure_ascii=False, indent=2))
                md.append("```")
            md.append("")
        return "\n".join(md)
