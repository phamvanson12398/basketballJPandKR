"""Gọi Claude CLI (claude -p) — dùng gói Claude bạn đã đăng nhập, không cần API key."""
import json
import re
import shutil
import subprocess

from .config import load_settings


def claude_path() -> str:
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError(
            "Không tìm thấy Claude CLI. Cài Claude Code rồi chạy `claude` một lần để đăng nhập.")
    return exe


def ask(prompt: str, tools: list[str] | None = None, add_dirs: list[str] | None = None,
        timeout: int = 600) -> str:
    """Gửi prompt qua stdin, trả về câu trả lời dạng text."""
    cmd = [claude_path(), "-p", "--output-format", "json"]
    model = load_settings().get("claude_model")
    if model:
        cmd += ["--model", model]
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    else:
        cmd += ["--tools", ""]
    for d in add_dirs or []:
        cmd += ["--add-dir", d]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    out = (r.stdout or "").strip()
    if r.returncode != 0 and not out:
        raise RuntimeError(f"Claude CLI lỗi: {(r.stderr or '').strip()[:500]}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return out
    if data.get("is_error"):
        raise RuntimeError(f"Claude CLI lỗi: {str(data.get('result'))[:500]}")
    return str(data.get("result", ""))


def extract_json(text: str):
    """Lấy khối JSON trong câu trả lời (có hoặc không có ```json)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    raw = m.group(1) if m else None
    if raw is None:
        start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
        if start < 0:
            raise ValueError("Claude không trả về JSON")
        end = max(text.rfind("}"), text.rfind("]"))
        raw = text[start:end + 1]
    return json.loads(raw)
