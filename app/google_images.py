"""Tìm ảnh trên Google Images bằng trình duyệt chạy ẩn (Playwright).

Từ 2025 Google bắt trang tìm kiếm phải chạy JavaScript → không đọc thẳng bằng requests được.
Tool mở Chrome ẩn (không thấy cửa sổ), vào Google Images giống người dùng thật, rồi lấy link ẢNH GỐC
từ dữ liệu trong trang. Không cần khóa API.

Trình duyệt dùng theo thứ tự: Chromium của Playwright (install.bat cài) → Microsoft Edge → Google Chrome
(Windows nào cũng có Edge nên vẫn chạy được kể cả khi chưa cài Chromium).
"""
import json
import re
import threading
import urllib.parse

from .config import ROOT

PROFILE = ROOT / "library" / "google_profile"     # giữ cookie như người dùng thật → ít bị hỏi "robot"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SEARCH_URL = "https://www.google.{tld}/search?q={q}&udm=2&tbm=isch&hl={hl}&gl={gl}&tbs={tbs}"
_lock = threading.Lock()          # 1 hồ sơ trình duyệt → mỗi lúc 1 lượt tìm
EXECUTABLE = None                 # (thử nghiệm) đường dẫn Chromium riêng

_TUPLE = re.compile(r'\["(https?://(?:[^"\\]|\\.)+?)",(\d+),(\d+)\]')
_META = re.compile(r'"2003":\[null,"(?:[^"\\]|\\.)*","((?:[^"\\]|\\.)+)","((?:[^"\\]|\\.)*)"')


def _unescape(s: str) -> str:
    try:
        return json.loads(f'"{s}"')
    except Exception:  # noqa: BLE001
        return s.encode().decode("unicode_escape", errors="ignore")


def parse(html: str) -> list[dict]:
    """Lấy (ảnh gốc, kích thước, trang nguồn, tiêu đề) từ dữ liệu JS trong trang Google Images."""
    hits = [m for m in _TUPLE.finditer(html)
            if not re.search(r"(gstatic\.com|google\.com|googleusercontent\.com/[a-z]+/)", m.group(1))]
    out, seen = [], set()
    for i, m in enumerate(hits):
        url = _unescape(m.group(1))
        if url in seen or not re.match(r"https?://", url):
            continue
        seen.add(url)
        # thông tin trang nguồn nằm ngay sau ảnh, trước kết quả tiếp theo
        end = hits[i + 1].start() if i + 1 < len(hits) else m.end() + 4000
        meta = _META.search(html, m.end(), min(end, m.end() + 4000))
        out.append({"url": url, "h": int(m.group(2)), "w": int(m.group(3)),
                    "page": _unescape(meta.group(1)) if meta else "",
                    "title": _unescape(meta.group(2)) if meta else "", "src": "google"})
    return out


def _launch(p):
    args = ["--disable-blink-features=AutomationControlled", "--lang=ja-JP"]
    PROFILE.mkdir(parents=True, exist_ok=True)
    errors = []
    for opt in ({"executable_path": EXECUTABLE} if EXECUTABLE else {}, {"channel": "msedge"}, {"channel": "chrome"}):
        try:
            return p.chromium.launch_persistent_context(
                str(PROFILE), headless=True, args=args, user_agent=UA, locale="ja-JP",
                viewport={"width": 1366, "height": 900}, **opt)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e).splitlines()[0][:120])
    raise RuntimeError("chưa có trình duyệt cho Google – chạy lại install.bat (" + " | ".join(errors) + ")")


def search(query: str, n: int = 80, recent: str | None = None, korean: bool = False) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("chưa cài Playwright – chạy lại install.bat") from e
    tbs = ",".join(x for x in ("iar:w", {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}.get(recent or "", "")) if x)
    url = SEARCH_URL.format(tld="co.kr" if korean else "co.jp", q=urllib.parse.quote(query),
                            hl="ko" if korean else "ja", gl="kr" if korean else "jp", tbs=urllib.parse.quote(tbs))
    with _lock, sync_playwright() as p:
        ctx = _launch(p)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if "/sorry/" in page.url or "unusual traffic" in page.content() or "通常と異なるトラフィック" in page.content():
                raise RuntimeError("Google đang hỏi “Tôi không phải robot”")
            if "consent.google" in page.url:      # trang đồng ý cookie (hiếm khi gặp ở châu Á)
                for label in ("すべて受け入れる", "Accept all", "모두 수락"):
                    btn = page.get_by_role("button", name=label)
                    if btn.count():
                        btn.first.click()
                        page.wait_for_load_state("domcontentloaded")
                        break
            results = parse(page.content())
            for _ in range(3):                    # cuộn để Google tải thêm ảnh
                if len(results) >= n:
                    break
                page.mouse.wheel(0, 6000)
                page.wait_for_timeout(1200)
                more = parse(page.content())
                if len(more) <= len(results):
                    break
                results = more
            return results[:n]
        finally:
            ctx.close()
