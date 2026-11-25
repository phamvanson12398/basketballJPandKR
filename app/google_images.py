"""Tìm ảnh trên Google Images bằng trình duyệt chạy ẩn (Playwright).

Từ 2025 Google bắt trang tìm kiếm phải chạy JavaScript → không đọc thẳng bằng requests được.
Tool mở Chrome ẩn (không thấy cửa sổ), vào Google Images giống người dùng thật, rồi lấy link ẢNH GỐC
từ dữ liệu trong trang. Không cần khóa API.

Trình duyệt dùng theo thứ tự: Chromium của Playwright (install.bat cài) → Microsoft Edge → Google Chrome
(Windows nào cũng có Edge nên vẫn chạy được kể cả khi chưa cài Chromium).
"""
import json
import queue
import re
import threading
import urllib.parse

from .config import ROOT

PROFILE = ROOT / "library" / "google_profile"     # giữ cookie như người dùng thật → ít bị hỏi "robot"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SEARCH_URL = "https://www.google.{tld}/search?q={q}&udm=2&tbm=isch&hl={hl}&gl={gl}&tbs={tbs}"
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
CAPTCHA_WAIT_SEC = 180
IDLE_CLOSE_SEC = 20 * 60          # không tìm gì 20 phút → đóng Chrome (cookie đã lưu lại)
COOKIES = PROFILE.parent / "google_cookies.json"


def _launch(p):
    """Ưu tiên Chrome / Edge THẬT trên máy, chạy cửa sổ bình thường nhưng đặt ngoài màn hình
    (Google ít nghi "robot" hơn nhiều so với headless). Máy không có màn hình (server) → headless."""
    args = ["--disable-blink-features=AutomationControlled", "--lang=ja-JP", "--no-first-run",
            "--no-default-browser-check"] + OFFSCREEN
    PROFILE.mkdir(parents=True, exist_ok=True)
    errors = []
    opts = ([{"executable_path": EXECUTABLE}] if EXECUTABLE else []) + [{"channel": "chrome"}, {"channel": "msedge"}, {}]
    for headless in (False, True):
        for opt in opts:
            try:
                ctx = p.chromium.launch_persistent_context(
                    str(PROFILE), headless=headless, args=args, locale="ja-JP", no_viewport=not headless,
                    ignore_default_args=["--enable-automation"],
                    **({"user_agent": UA} if headless else {}), **opt)
                _load_cookies(ctx)
                return ctx
            except Exception as e:  # noqa: BLE001
                errors.append(str(e).splitlines()[0][:100])
    raise RuntimeError("chưa có trình duyệt cho Google – chạy lại install.bat (" + " | ".join(errors[:3]) + ")")


# ---- giữ "giấy thông hành" của Google (cookie sau khi xác minh) qua các lần mở Chrome
def _save_cookies(ctx) -> None:
    try:
        ck = [c for c in ctx.cookies() if "google" in c.get("domain", "")]
        COOKIES.write_text(json.dumps(ck, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _load_cookies(ctx) -> None:
    try:
        if COOKIES.exists():
            ctx.add_cookies(json.loads(COOKIES.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        pass


def _show(page, visible: bool) -> None:
    """Kéo cửa sổ Chrome vào giữa màn hình (để bạn xác minh) hoặc đẩy ra ngoài màn hình."""
    try:
        cdp = page.context.new_cdp_session(page)
        wid = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": {"windowState": "normal"}})
        b = {"left": 120, "top": 60, "width": 1100, "height": 850} if visible else {"left": -32000, "top": -32000}
        cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": b})
        if visible:
            page.bring_to_front()
    except Exception:  # noqa: BLE001
        pass


def _is_captcha(page) -> bool:
    try:
        html = page.content()
    except Exception:  # noqa: BLE001
        return False
    return ("/sorry/" in page.url or "unusual traffic" in html or "通常と異なるトラフィック" in html
            or "비정상적인 트래픽" in html or 'id="captcha-form"' in html)


def _wait_human(page, log, why: str) -> bool:
    """Hiện cửa sổ cho bạn tích “Tôi không phải robot”, chờ tối đa CAPTCHA_WAIT_SEC. True = đã qua."""
    if log:
        log(f"    🤖 {why} → cửa sổ Chrome đã hiện lên: bạn tích ô xác minh giúp "
            f"(tool chờ tối đa {CAPTCHA_WAIT_SEC // 60} phút rồi tự tìm tiếp)")
    _show(page, True)
    waited = 0
    while _is_captcha(page) and waited < CAPTCHA_WAIT_SEC:
        page.wait_for_timeout(2000)
        waited += 2
    ok = not _is_captcha(page)
    if ok:
        page.wait_for_timeout(1500)
        if log:
            log("    ✅ Đã xác minh Google – tìm tiếp")
    _show(page, False)
    return ok


# ---- đăng nhập tài khoản Google (khi Google bắt đăng nhập mới cho tìm, hoặc để ít bị hỏi "robot" hơn)
LOGIN_WAIT_SEC = 6 * 60
LOGIN_URL = "https://accounts.google.com/ServiceLogin?hl={hl}&continue={cont}"


def _is_login(page) -> bool:
    return "accounts.google.com" in (page.url or "")


def _logged_in(ctx) -> bool:
    try:
        return any(c.get("name") in ("SID", "__Secure-1PSID") and "google" in c.get("domain", "") for c in ctx.cookies())
    except Exception:  # noqa: BLE001
        return False


def logged_in() -> bool:
    """Đã có cookie đăng nhập Google đã lưu chưa (không cần mở Chrome)."""
    try:
        return any(c.get("name") in ("SID", "__Secure-1PSID") for c in json.loads(COOKIES.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return False


def _wait_login(page, log, back_url: str = "") -> bool:
    """Hiện cửa sổ Chrome ở trang đăng nhập, chờ bạn đăng nhập xong (tối đa LOGIN_WAIT_SEC). True = đã đăng nhập."""
    if log:
        log(f"    🔑 Google yêu cầu đăng nhập → cửa sổ Chrome đã hiện lên: bạn đăng nhập tài khoản Google giúp "
            f"(tool chờ tối đa {LOGIN_WAIT_SEC // 60} phút rồi tự tìm tiếp)")
    _show(page, True)
    waited = 0
    while waited < LOGIN_WAIT_SEC:
        if _logged_in(page.context) and not _is_login(page):
            break
        page.wait_for_timeout(2000)
        waited += 2
    ok = _logged_in(page.context)
    _save_cookies(page.context)
    if ok:
        if log:
            log("    ✅ Đã đăng nhập Google – tìm tiếp")
        if back_url:
            page.goto(back_url, wait_until="domcontentloaded", timeout=30000)
        else:
            page.wait_for_timeout(1500)
    _show(page, False)
    return ok


def _login_on(page):
    page.goto(LOGIN_URL.format(hl="ja", cont=urllib.parse.quote("https://www.google.co.jp/imghp?hl=ja")),
              wait_until="domcontentloaded", timeout=30000)
    if _logged_in(page.context) and not _is_login(page):
        _show(page, True)              # đã đăng nhập sẵn → hiện 3 giây cho bạn thấy rồi ẩn
        page.wait_for_timeout(3000)
        _show(page, False)
        return "ok"
    return "ok" if _wait_login(page, None) else "chưa đăng nhập"


def open_for_login() -> str:
    """Nút 🔑 Đăng nhập Google: đăng nhập NGAY TRÊN cửa sổ Chrome mà tool dùng để tìm ảnh (cookie được lưu lại)."""
    try:
        return BROWSER.call(_login_on, timeout=LOGIN_WAIT_SEC + 120)
    except Exception:  # noqa: BLE001
        return "lỗi"


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


# ---- 1 cửa sổ Chrome dùng chung cho mọi lần tìm (chạy trong 1 luồng riêng – Playwright yêu cầu vậy)
class _Browser:
    def __init__(self):
        self.q: queue.Queue = queue.Queue()
        self.thread = None
        self.start_lock = threading.Lock()

    def call(self, fn, *args, timeout: float = LOGIN_WAIT_SEC + 120):
        with self.start_lock:
            if not (self.thread and self.thread.is_alive()):
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()
        box: dict = {}
        done = threading.Event()
        self.q.put((fn, args, box, done))
        if not done.wait(timeout):
            raise RuntimeError("Google không phản hồi")
        if "error" in box:
            raise box["error"]
        return box["result"]

    def _run(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self._fail_all(RuntimeError("chưa cài Playwright – chạy lại install.bat"))
            return
        with sync_playwright() as p:
            ctx = None
            while True:
                try:
                    fn, args, box, done = self.q.get(timeout=IDLE_CLOSE_SEC)
                except queue.Empty:
                    if ctx:
                        _save_cookies(ctx)
                        ctx.close()
                        ctx = None
                    continue
                try:
                    if ctx is None or not ctx.pages and not _alive(ctx):
                        ctx = _launch(p)
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    box["result"] = fn(page, *args)
                    _save_cookies(ctx)
                except Exception as e:  # noqa: BLE001
                    box["error"] = e
                    if ctx is not None and not _alive(ctx):
                        ctx = None          # bạn đã đóng cửa sổ Chrome → lần sau mở lại
                finally:
                    done.set()

    def _fail_all(self, err):
        while True:
            try:
                _, _, box, done = self.q.get_nowait()
            except queue.Empty:
                return
            box["error"] = err
            done.set()


def _alive(ctx) -> bool:
    try:
        ctx.cookies()
        return True
    except Exception:  # noqa: BLE001
        return False


BROWSER = _Browser()


def _search_on(page, url: str, n: int, log, retry: bool = True):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    if _is_login(page) and not _wait_login(page, log, url):   # Google bắt đăng nhập mới cho tìm
        raise RuntimeError("Google yêu cầu đăng nhập (chưa đăng nhập) – bấm 🔑 Đăng nhập Google trong Cài đặt")
    if _is_captcha(page) and not _wait_human(page, log, "Google hỏi “Tôi không phải robot”"):
        raise RuntimeError("Google đang hỏi “Tôi không phải robot” (chưa xác minh)")
    res = _collect(page, n)
    if not res and retry:
        page.wait_for_timeout(1000)
        if _is_login(page):    # trang chuyển sang đăng nhập SAU khi tải (bằng JavaScript) → chờ đăng nhập rồi tìm lại
            if not _wait_login(page, log):
                raise RuntimeError("Google yêu cầu đăng nhập (chưa đăng nhập) – bấm 🔑 Đăng nhập Google trong Cài đặt")
            return _search_on(page, url, n, log, retry=False)
    return res


def search(query: str, n: int = 80, recent: str | None = None, korean: bool = False, log=None) -> list[dict]:
    tbs = ",".join(x for x in ({"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}.get(recent or "", ""),) if x)
    url = SEARCH_URL.format(tld="co.kr" if korean else "co.jp", q=urllib.parse.quote(query),
                            hl="ko" if korean else "ja", gl="kr" if korean else "jp", tbs=urllib.parse.quote(tbs))
    return BROWSER.call(_search_on, url, n, log)


def _verify_on(page):
    page.goto(SEARCH_URL.format(tld="co.jp", q=urllib.parse.quote("大谷翔平"), hl="ja", gl="jp", tbs=""),
              wait_until="domcontentloaded", timeout=30000)
    if not _is_captcha(page):
        _show(page, True)              # không bị hỏi → vẫn hiện để bạn thấy Google đang chạy tốt, rồi ẩn lại
        page.wait_for_timeout(2500)
        _show(page, False)
        return "ok"
    return "ok" if _wait_human(page, None, "") else "chưa xác minh"


def open_for_verify() -> str:
    """Nút trong Cài đặt: dùng CHÍNH cửa sổ Chrome mà tool tìm ảnh → xác minh xong là các lần tìm sau dùng được."""
    try:
        return BROWSER.call(_verify_on)
    except Exception:  # noqa: BLE001
        return "lỗi"
