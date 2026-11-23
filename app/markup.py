"""Đánh dấu nhấn mạnh trong phụ đề (dùng cho bố cục đua ngựa, kiểu video mẫu):
  〔chữ〕 → chữ ĐỎ (tên ngựa / tên người)
  【chữ】 → chữ ĐỎ + TO (điểm nhấn chính)
  《chữ》 → chữ đen + TO (nhấn phụ)
Giọng đọc, đếm thời lượng… luôn dùng bản đã bỏ ký hiệu (strip)."""
import re

OPEN = {"〔": "red", "【": "redbig", "《": "big"}
CLOSE = {"〕": "red", "】": "redbig", "》": "big"}
_ALL = re.compile("[〔〕【】《》]")
RED = "&H0A00E6&"          # đỏ (230, 0, 10) như video mẫu
BLACK = "&H000000&"


def strip(s: str) -> str:
    return _ALL.sub("", s or "")


def has_marks(s: str) -> bool:
    return bool(_ALL.search(s or ""))


def line_has_big(line: str, state: set | None = None) -> bool:
    """Dòng có chữ TO không (tính cả đoạn đánh dấu mở từ dòng trước)."""
    if state and state & {"big", "redbig"}:
        return True
    return "【" in line or "《" in line


def to_ass_lines(chunk: str, base: int, big: int, escape, width: int = 0) -> list[tuple[str, bool]]:
    """Chuyển 1 chunk (nhiều dòng, có ký hiệu) → [(dòng ASS có thẻ màu/cỡ, dòng có chữ to?)].
    Đánh dấu kéo qua dấu xuống dòng vẫn đúng (mở lại thẻ ở đầu dòng sau)."""
    out, state = [], set()

    def tags(st):
        red = bool(st & {"red", "redbig"})
        bg = bool(st & {"big", "redbig"})
        return f"{{\\c{RED if red else BLACK}\\fs{big if bg else base}}}"

    for line in chunk.split("\n"):
        has_big = line_has_big(line, state)
        buf = tags(state) if state else ""
        txt = ""
        for ch in line:
            if ch in OPEN:
                buf += escape(txt)
                txt = ""
                state.add(OPEN[ch])
                buf += tags(state)
            elif ch in CLOSE:
                buf += escape(txt)
                txt = ""
                state.discard(CLOSE[ch])
                buf += tags(state)
            else:
                txt += ch
        buf += escape(txt)
        if width:
            # ước lượng bề rộng (đo từ font sub: chữ Nhật/Hàn ≈ 0.68 cỡ chữ, chữ/số Latin ≈ 0.42)
            # → dòng quá dài thì nén ngang cho vừa khung, không tràn mép
            vis = strip(line)
            est = sum((0.42 if ord(c) < 0x2E80 else 0.68) for c in vis) * (big if has_big else base)
            if est > width * 0.94:
                buf = f"{{\\fscx{int(100 * width * 0.94 / est)}}}" + buf
        out.append((buf, has_big))
    return out
