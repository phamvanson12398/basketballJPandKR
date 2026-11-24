"""AI xem ảnh / khung hình video (chọn ảnh hợp nội dung, chọn đoạn video, xác nhận đúng người).

Chọn trong Cài đặt → "AI xem ảnh/video":
  • antigravity – Antigravity CLI (agy) trên máy bạn, đăng nhập Google → không tốn lượt Claude
  • gemini      – Gemini API key (Google AI Studio, có gói miễn phí theo ngày)
  • claude      – Claude CLI (như trước)
  • off         – không dùng AI (chỉ thuật toán) → miễn phí hoàn toàn
Viết content / biên tập / kiểm tra sự thật vẫn luôn dùng Claude.
"""
import base64
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import requests

from .claude_cli import extract_json
from .config import load_settings

PROVIDERS = ("antigravity", "gemini", "claude", "off")
DEFAULT_AGY_CMD = "agy -p {prompt}"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class VisionOff(Exception):
    """Đang tắt AI xem ảnh → nơi gọi tự dùng cách chọn không cần AI."""


def provider() -> str:
    p = load_settings().get("vision_provider") or "claude"
    return p if p in PROVIDERS else "claude"


def provider_name(p: str | None = None) -> str:
    return {"antigravity": "Antigravity", "gemini": "Gemini", "claude": "Claude", "off": "—"}[p or provider()]


# ---------------------------------------------------------------- từng nhà cung cấp
def _claude(task: str, images: list[Path], workdir: Path, timeout: int) -> str:
    from .claude_cli import ask
    head = "次の画像ファイルを Read ツールで開いてください:\n" + "\n".join(f"- {p.as_posix()}" for p in images) + "\n\n"
    return ask(head + task, tools=["Read"], add_dirs=[str(workdir)], timeout=timeout)


def _gemini(task: str, images: list[Path], timeout: int) -> str:
    st = load_settings()
    key = (st.get("gemini_api_key") or "").strip()
    if not key:
        raise RuntimeError("chưa nhập Gemini API key trong Cài đặt")
    model = (st.get("gemini_model") or DEFAULT_GEMINI_MODEL).strip()
    parts = [{"text": "画像は添付の順に 画像1, 画像2… です。\n\n" + task}]
    for p in images:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(p.read_bytes()).decode()}})
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                      json={"contents": [{"role": "user", "parts": parts}],
                            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}},
                      timeout=timeout)
    if r.status_code == 429:
        raise RuntimeError("Gemini báo hết lượt miễn phí hôm nay (429)")
    r.raise_for_status()
    data = r.json()
    return "".join(pt.get("text", "") for c in data.get("candidates", [])[:1]
                   for pt in c.get("content", {}).get("parts", []))


def _antigravity(task: str, images: list[Path], workdir: Path, timeout: int) -> str:
    """Gọi Antigravity CLI ở chế độ không giao diện. Lệnh lấy từ Cài đặt (mặc định: agy -p {prompt}).
    Ảnh được chép vào thư mục làm việc và nhắc tên trong prompt (kèm cú pháp @tệp) để agent tự mở xem."""
    tmpl = (load_settings().get("agy_command") or DEFAULT_AGY_CMD).strip()
    names = []
    for i, p in enumerate(images, 1):
        dst = workdir / f"_vis_{i}{p.suffix or '.jpg'}"
        if p.resolve() != dst.resolve():
            shutil.copyfile(p, dst)
        names.append(dst.name)
    prompt = ("次の画像ファイル（このフォルダ内）を開いて中身を見てください。ファイルの作成・変更・削除やコマンドの実行はしないこと。\n"
              + "\n".join(f"- 画像{i}: @{n}" for i, n in enumerate(names, 1))
              + "\n\n" + task + "\n\n回答は JSON だけを出力すること（説明文なし）。")
    if os.name == "nt":   # Windows: giữ nguyên dấu \ trong đường dẫn, chỉ bỏ ngoặc kép bao ngoài
        parts = [x[1:-1] if len(x) > 1 and x[0] == x[-1] == '"' else x for x in shlex.split(tmpl, posix=False)]
    else:
        parts = shlex.split(tmpl, posix=True)
    if "{prompt}" in tmpl:
        cmd, stdin = [prompt if x == "{prompt}" else x.replace("{prompt}", prompt) for x in parts], None
    else:
        cmd, stdin = parts, prompt            # lệnh không có {prompt} → gửi prompt qua stdin
    exe = shutil.which(cmd[0])
    if not exe:
        raise RuntimeError(f"không tìm thấy lệnh “{cmd[0]}” – cài Antigravity CLI rồi đăng nhập Google một lần")
    try:
        r = subprocess.run([exe] + cmd[1:], input=stdin, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=str(workdir))
    finally:
        for n in names:
            (workdir / n).unlink(missing_ok=True)
    out = (r.stdout or "").strip()
    if r.returncode != 0 and not out:
        raise RuntimeError(f"Antigravity lỗi: {(r.stderr or '').strip()[:300]}")
    try:                                      # nếu bản agy trả JSON bọc ngoài (VD --output-format json)
        wrap = json.loads(out)
        if isinstance(wrap, dict):
            for k in ("response", "result", "text", "output"):
                if isinstance(wrap.get(k), str):
                    return wrap[k]
    except ValueError:
        pass
    return out


# ---------------------------------------------------------------- dùng chung
def ask_json(task: str, images: list[Path], workdir: Path, timeout: int = 300, log=None):
    """Hỏi AI xem ảnh, trả về JSON đã đọc. Lỗi nhà cung cấp → ném lỗi (nơi gọi tự dùng cách dự phòng)."""
    p = provider()
    if p == "off":
        raise VisionOff()
    workdir.mkdir(parents=True, exist_ok=True)
    if p == "gemini":
        text = _gemini(task, images, timeout)
    elif p == "antigravity":
        text = _antigravity(task, images, workdir, timeout)
    else:
        text = _claude(task, images, workdir, timeout)
    return extract_json(text)


def self_test(workdir: Path) -> dict:
    """Nút “Kiểm tra” trong Cài đặt: vẽ 1 ảnh (hình tròn đỏ + số 7) và hỏi AI → biết AI xem ảnh có chạy không."""
    from PIL import Image, ImageDraw, ImageFont
    workdir.mkdir(parents=True, exist_ok=True)
    img = workdir / "_vision_test.jpg"
    im = Image.new("RGB", (480, 320), "white")
    d = ImageDraw.Draw(im)
    d.ellipse((40, 60, 240, 260), fill=(220, 20, 30))
    try:
        font = ImageFont.load_default(size=150)
    except TypeError:
        font = ImageFont.load_default()
    d.text((300, 70), "7", fill="black", font=font)
    im.save(img, quality=90)
    p = provider()
    try:
        data = ask_json('画像1を見て答えて。JSONのみ: {"shape_color": "図形の色（英語1語）", "number": 画像の数字}',
                        [img], workdir, timeout=180)
        ok = "red" in str(data.get("shape_color", "")).lower() and str(data.get("number")) == "7"
        return {"ok": ok, "provider": provider_name(p), "answer": data}
    except VisionOff:
        return {"ok": True, "provider": "—", "answer": "Đang tắt AI xem ảnh (chỉ dùng thuật toán)."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "provider": provider_name(p), "error": str(e)[:400]}
    finally:
        img.unlink(missing_ok=True)
