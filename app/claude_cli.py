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


def _repair(raw: str) -> str:
    """Vá lỗi JSON hay gặp khi AI viết tiếng Nhật/Hàn:
    - dấu " nằm TRONG chuỗi chưa được escape (VD: "cover": "あの"背中"") → \"
    - dấu phẩy thừa trước } hoặc ]
    - xuống dòng thật nằm trong chuỗi → \n"""
    out, i, n, in_str = [], 0, len(raw), False
    while i < n:
        c = raw[i]
        if not in_str:
            if c == '"':
                in_str = True
            out.append(c)
        else:
            if c == "\\" and i + 1 < n:
                out.append(raw[i:i + 2])
                i += 2
                continue
            if c == '"':
                j = i + 1
                while j < n and raw[j] in " \t\r\n":
                    j += 1
                if j >= n or raw[j] in ",:}]":
                    in_str = False          # dấu " đóng chuỗi thật
                    out.append(c)
                else:
                    out.append('\\"')     # dấu " nằm giữa chữ → escape
            elif c == "\n":
                out.append("\\n")
            elif c == "\r":
                pass
            else:
                out.append(c)
        i += 1
    fixed = "".join(out)
    return re.sub(r",\s*([}\]])", r"\1", fixed)


def _raw_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    if m:
        return m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("Claude không trả về JSON")
    end = max(text.rfind("}"), text.rfind("]"))
    return text[start:end + 1]


def extract_json(text: str, retry: bool = True):
    """Lấy khối JSON trong câu trả lời (có hoặc không có ```json).
    JSON hỏng → tự vá; vẫn hỏng → nhờ Claude sửa lại đúng định dạng 1 lần (không báo lỗi ngay)."""
    raw = _raw_json(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        err = e
    try:
        return json.loads(_repair(raw))
    except json.JSONDecodeError:
        pass
    if not retry:
        raise ValueError(f"Claude trả về JSON hỏng ({err})")
    fixed = ask("次のJSONは文法エラーで読み込めません。内容は一切変えずに、正しいJSONだけを出力してください"
                "（文字列の中の \" は \\\" にエスケープする、余計なカンマを消す、説明文は不要）。\n\n"
                f"エラー: {err}\n\n{raw}", timeout=300)
    return extract_json(fixed, retry=False)
