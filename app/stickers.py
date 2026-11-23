"""Hình minh họa (sticker) dán lên ảnh – kiểu video đua ngựa mẫu (bông hoa, trái tim, táo, hộp cơm…).
AI chọn 1 emoji cho mỗi cảnh → tải hình emoji màu 512px (Noto Emoji của Google) một lần, lưu ở library/stickers."""
import random

import requests
from PIL import Image

from .config import ROOT

DIR = ROOT / "library" / "stickers"
URLS = ("https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/512/emoji_u{cp}.png",
        "https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/png/512/emoji_u{cp}.png")
POS = ("tl", "tr", "bl", "br")


def codepoints(emoji: str) -> str:
    return "_".join(f"{ord(c):04x}" for c in emoji.strip() if ord(c) not in (0xFE0F, 0xFE0E))


def get(emoji: str) -> Image.Image | None:
    emoji = (emoji or "").strip()
    if not emoji:
        return None
    cp = codepoints(emoji)
    if not cp:
        return None
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / f"{cp}.png"
    if not f.exists():
        for u in URLS:
            try:
                r = requests.get(u.format(cp=cp), timeout=15)
                if r.ok and r.content[:4] == b"\x89PNG":
                    f.write_bytes(r.content)
                    break
            except Exception:  # noqa: BLE001
                continue
    try:
        return Image.open(f).convert("RGBA") if f.exists() else None
    except Exception:  # noqa: BLE001
        return None


def file(emoji: str, size: int) -> "Path | None":
    """PNG sticker đã thu về đúng cỡ (lưu cache)."""
    st = get(emoji)
    if st is None:
        return None
    out = DIR / f"{codepoints(emoji)}_{size}.png"
    if not out.exists():
        st.resize((size, size), Image.LANCZOS).save(out)
    return out


def overlay(emoji: str, pos: str, g: dict, seed: int = 0):
    """Trả về (đường dẫn PNG, x, y) để FFmpeg phủ sticker lên khung ảnh/video; None nếu không có sticker.
    pos: tl / tr / bl / br (trống = tự chọn góc phải)."""
    size = int(g["h"] * 0.34) // 2 * 2
    f = file(emoji, size)
    if f is None:
        return None
    pos = pos if pos in POS else random.Random(seed).choice(("br", "tr", "br"))
    mx, my = int(g["w"] * 0.04), int(g["h"] * 0.06)
    x = mx if pos[1] == "l" else g["w"] - size - mx
    y = my if pos[0] == "t" else g["h"] - size - my
    return f, x, y
