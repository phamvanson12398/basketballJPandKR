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


OFFSCREEN = ["--window-position=-32000,-32000", "--window-size=1366,900"]
ONSCREEN = ["--window-position=120,80", "--window-size=1100,850"]
CAPTCHA_WAIT_SEC = 180


def _launch(p, visible: bool = False):
    """Ưu tiên Chrome / Edge THẬT trên máy, chạy cửa sổ bình thường nhưng đặt ngoài màn hình
    (Google ít nghi "robot" hơn nhiều so với chế độ headless). visible=True → hiện giữa màn hình để bạn xác minh.
    Máy không có màn hình (server) → tự chuyển sang headless."""
    args = ["--disable-blink-features=AutomationControlled", "--lang=ja-JP", "--no-first-run",
            "--no-default-browser-check"] + (ONSCREEN if visible else OFFSCREEN)
    PROFILE.mkdir(parents=True, exist_ok=True)
    errors = []
    opts = ([{"executable_path": EXECUTABLE}] if EXECUTABLE else []) + [{"channel": "chrome"}, {"channel": "msedge"}, {}]
    for headless in (False, True):
        if headless and visible:
            break
        for opt in opts:
            try:
                return p.chromium.launch_persistent_context(
                    str(PROFILE), headless=headless, args=args, locale="ja-JP", no_viewport=not headless,
                    ignore_default_args=["--enable-automation"],
                    **({"user_agent": UA} if headless else {}), **opt)
            except Exception as e:  # noqa: BLE001
                errors.append(str(e).splitlines()[0][:100])
    raise RuntimeError("chưa có trình duyệt cho Google – chạy lại install.bat (" + " | ".join(errors[:3]) + ")")


def _is_captcha(page) -> bool:
    try:
        html = page.content()
    except Exception:  # noqa: BLE001
        return False
    return ("/sorry/" in page.url or "unusual traffic" in html or "通常と異なるトラフィック" in html
            or "비정상적인 트래픽" in html or 'id="captcha-form"' in html)


def _solve_captcha(p, url: str, log) -> list[dict] | None:
    """Mở cửa sổ Chrome giữa màn hình để BẠN tích "Tôi không phải robot", chờ tối đa 3 phút.
    Google nhớ việc xác minh trong hồ sơ riêng của tool → các lần sau chạy ẩn bình thường."""
    if log:
        log("    🤖 Google hỏi “Tôi không phải robot” → đã mở cửa sổ Chrome: bạn tích ô xác minh giúp "
            f"(tool chờ tối đa {CAPTCHA_WAIT_SEC // 60} phút rồi tự tìm tiếp)")
    try:
        ctx = _launch(p, visible=True)
    except Exception:  # noqa: BLE001
        return None
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.bring_to_front()
        waited = 0
        while _is_captcha(page) and waited < CAPTCHA_WAIT_SEC:
            page.wait_for_timeout(2000)
            waited += 2
        if _is_captcha(page):
            return None
        page.wait_for_timeout(1500)
        if log:
            log("    ✅ Đã xác minh Google – tìm tiếp")
        return _collect(page, 80)
    except Exception:  # noqa: BLE001
        return None
    finally:
        ctx.close()


def _collect(page, n: int) -> list[dict]:
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


def search(query: str, n: int = 80, recent: str | None = None, korean: bool = False, log=None) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("chưa cài Playwright – chạy lại install.bat") from e
    tbs = ",".join(x for x in ({"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}.get(recent or "", ""),) if x)
    url = SEARCH_URL.format(tld="co.kr" if korean else "co.jp", q=urllib.parse.quote(query),
                            hl="ko" if korean else "ja", gl="kr" if korean else "jp", tbs=urllib.parse.quote(tbs))
    with _lock, sync_playwright() as p:
        ctx = _launch(p)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            captcha = _is_captcha(page)
            if not captcha:
                return _collect(page, n)
        finally:
            ctx.close()
        res = _solve_captcha(p, url, log)    # hồ sơ trình duyệt chỉ mở được 1 cửa sổ → đóng bản ẩn trước
        if res is None:
            raise RuntimeError("Google đang hỏi “Tôi không phải robot” (chưa xác minh)")
        return res[:n]


def open_for_verify() -> str:
    """Nút trong Cài đặt: mở Google (cửa sổ thật) để bạn xác minh trước. Đóng cửa sổ là xong."""
    from playwright.sync_api import sync_playwright
    with _lock, sync_playwright() as p:
        ctx = _launch(p, visible=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(SEARCH_URL.format(tld="co.jp", q=urllib.parse.quote("大谷翔平"), hl="ja", gl="jp", tbs=""),
                      wait_until="domcontentloaded", timeout=30000)
            page.bring_to_front()
            waited = 0
            while waited < 300 and ctx.pages:
                try:
                    page.wait_for_timeout(1000)
                except Exception:  # noqa: BLE001
                    break        # bạn đã đóng cửa sổ
                waited += 1
                if not _is_captcha(page) and waited > 5:
                    page.wait_for_timeout(3000)
                    break
            return "ok" if not _is_captcha(page) else "chưa xác minh"
        except Exception:  # noqa: BLE001
            return "đã đóng"
        finally:
            try:
                ctx.close()
            except Exception:  # noqa: BLE001
                pass
