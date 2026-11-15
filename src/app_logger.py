# -*- coding: utf-8 -*-
"""
Module: src.app_logger
Hệ thống ghi nhật ký hoạt động chuẩn ứng dụng Web & Server (Application Runtime Logger):
Theo dõi và hiển thị trực quan toàn bộ vòng đời thực thi:
- Gọi gì (Hàm, API, Mô hình AI, CSDL, Mail, Bộ lọc, Cán bộ duyệt)
- Làm những gì (Chuẩn hóa dữ liệu, dự đoán phân loại, tra cứu quy chế, kiểm định rào chắn, lưu trữ)
- Kết quả ra sao (Mã trạng thái, độ tự tin, thời gian thực thi ms)
Đồng bộ hiển thị tức thì trên cả 2 kênh:
1. Console Terminal (stdout) khi chạy `streamlit run app/main.py`
2. Giao diện Web (Live Terminal Console Widget) trong Sidebar và Tab Lịch sử.
"""

import sys
import threading
from datetime import datetime
from collections import deque
from pathlib import Path
from typing import List, Dict, Any, Optional

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app_activity.log"

_LOCK = threading.Lock()
_LOG_BUFFER: deque = deque(maxlen=500)

COMPONENT_COLORS = {
    "WEB": "#38bdf8",          # Cyan
    "INTAKE": "#60a5fa",       # Light Blue
    "CLEANER": "#a78bfa",      # Lavender
    "AI-MODEL": "#c084fc",     # Purple
    "RAG-DOCX": "#34d399",     # Emerald
    "SYNTHESIS": "#fbbf24",    # Amber
    "GUARDRAILS": "#f97316",   # Orange
    "DATABASE": "#3b82f6",     # Blue
    "EMAIL": "#f472b6",        # Pink
    "WORKBENCH": "#2dd4bf",    # Teal
    "KNOWLEDGE": "#818cf8"     # Indigo
}

LEVEL_COLORS = {
    "INFO": "#22c55e",         # Green
    "SUCCESS": "#10b981",      # Emerald
    "WARN": "#f59e0b",         # Amber
    "ERROR": "#ef4444"         # Red
}

def _get_timestamp() -> str:
    """Lấy thời điểm chuẩn Việt Nam (UTC+7)."""
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

def app_log(component: str, action: str, details: str = "", level: str = "INFO"):
    """
    Ghi nhận một sự kiện hoạt động của ứng dụng web.
    In trực tiếp ra Terminal (stdout) và đẩy vào hàng đợi Live Logs của giao diện.
    """
    ts = _get_timestamp()
    component = component.upper()
    level = level.upper()

    log_entry = {
        "timestamp": ts,
        "level": level,
        "component": component,
        "action": action,
        "details": details,
        "raw_text": f"[{ts}] [{level}] [{component}] {action}{(': ' + details) if details else ''}"
    }

    with _LOCK:
        _LOG_BUFFER.append(log_entry)
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry["raw_text"] + "\n")
        except Exception:
            pass

    # In ra Terminal (stdout) như một Web Server bình thường
    ansi_reset = "\033[0m"
    ansi_level = "\033[32m" if level in ("INFO", "SUCCESS") else ("\033[33m" if level == "WARN" else "\033[31m")
    ansi_comp = "\033[36m"
    ansi_bold = "\033[1m"

    sys.stdout.write(
        f"[{ts}] {ansi_level}[{level}]{ansi_reset} {ansi_comp}[{component}]{ansi_reset} {ansi_bold}{action}{ansi_reset}"
        f"{(': ' + details) if details else ''}\n"
    )
    sys.stdout.flush()

def get_recent_logs(limit: int = 100, component_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách các dòng nhật ký gần nhất."""
    with _LOCK:
        logs = list(_LOG_BUFFER)
    if component_filter and component_filter != "TẤT CẢ":
        logs = [entry for entry in logs if entry["component"] == component_filter]
    return logs[-limit:]

def clear_logs():
    """Xóa bộ đệm nhật ký trong phiên."""
    with _LOCK:
        _LOG_BUFFER.clear()

def export_logs_text() -> str:
    """Xuất toàn bộ nhật ký thành chuỗi văn bản."""
    with _LOCK:
        return "\n".join(entry["raw_text"] for entry in _LOG_BUFFER)

def render_log_terminal_html(logs: List[Dict[str, Any]], height_px: int = 240) -> str:
    """Sinh mã HTML giả lập giao diện Terminal Console chuyên nghiệp."""
    if not logs:
        return f"""
        <div style="background: #0f172a; color: #64748b; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.78rem; padding: 12px; border-radius: 6px; height: {height_px}px; display: flex; align-items: center; justify-content: center; border: 1px solid #1e293b;">
            [Chưa có dữ liệu sự kiện mới — Mọi thao tác trên web sẽ xuất hiện tại đây]
        </div>
        """

    lines_html = []
    for entry in logs:
        comp = entry.get("component", "SYS")
        lvl = entry.get("level", "INFO")
        comp_color = COMPONENT_COLORS.get(comp, "#94a3b8")
        lvl_color = LEVEL_COLORS.get(lvl, "#22c55e")
        ts = entry.get("timestamp", "")
        action = entry.get("action", "")
        details = entry.get("details", "")

        line = (
            f'<div style="margin-bottom: 4px; line-height: 1.45;">'
            f'<span style="color: #64748b;">[{ts}]</span> '
            f'<span style="color: {lvl_color}; font-weight: 600;">[{lvl}]</span> '
            f'<span style="color: {comp_color}; font-weight: 600;">[{comp}]</span> '
            f'<span style="color: #f1f5f9; font-weight: 600;">{action}</span>'
            f'{"<span style=\"color: #cbd5e1;\">: " + details + "</span>" if details else ""}'
            f'</div>'
        )
        lines_html.append(line)

    content = "".join(lines_html)
    return f"""
    <div style="background: #090d16; color: #e2e8f0; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.76rem; padding: 12px 14px; border-radius: 6px; height: {height_px}px; overflow-y: auto; border: 1px solid #1e293b; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
        {content}
    </div>
    """
