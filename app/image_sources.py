"""Các nguồn tìm ảnh MIỄN PHÍ, không cần API key.

  • DuckDuckGo Images   (thư viện ddgs)
  • Bing Images          (lọc sẵn: ảnh ngang + cỡ lớn)
  • Yahoo! JAPAN 画像検索 (nhiều ảnh báo thể thao Nhật)

Mỗi nguồn trả về list {url, w, h, title, page, src}. Nguồn nào lỗi thì bỏ qua, không làm hỏng
các nguồn khác. Kích thước (w, h) có thể = 0 nếu nguồn không cho biết; khi tải về tool sẽ
kiểm tra lại tỉ lệ 16:9 thật.
"""
import html
import json
import re
import threading
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"}


def _duckduckgo_direct(query: str, n: int, recent: str | None, region: str) -> list[dict]:
    """Gọi thẳng API ảnh của DuckDuckGo bằng requests (HTTP/1.1).
    B1: lấy mã vqd từ trang tìm kiếm.  B2: gọi i.js lấy kết quả (có lọc ảnh ngang + thời gian)."""
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,ko;q=0.9,en;q=0.8"})
    r = sess.get("https://duckduckgo.com/", params={"q": query, "iax": "images", "ia": "images"}, timeout=20)
    r.raise_for_status()
    m = re.search(r"vqd=[\"']?([\d-]+)", r.text)
    if not m:
        raise RuntimeError("không lấy được mã vqd")
    tl = {"day": "time:Day", "week": "time:Week", "month": "time:Month"}.get(recent or "", "")
    params = {"l": region, "o": "json", "q": query, "vqd": m.group(1), "f": f"{tl},,,,layout:Wide,", "p": "-1"}
    headers = {"Referer": "https://duckduckgo.com/", "Accept": "application/json, text/javascript, */*; q=0.01",
               "X-Requested-With": "XMLHttpRequest"}
    out, url = [], "https://duckduckgo.com/i.js"
    for _ in range(4):
        r = sess.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        for it in data.get("results", []):
            out.append({"url": it.get("image"), "w": int(it.get("width") or 0), "h": int(it.get("height") or 0),
                        "title": it.get("title", ""), "page": it.get("url", ""), "src": "duckduckgo"})
        nxt = data.get("next")
        if len(out) >= n or not nxt:
            break
        url, params = "https://duckduckgo.com/" + nxt.lstrip("/"), {"vqd": m.group(1)}
    return out[:n]


def _duckduckgo_ddgs(query: str, n: int, recent: str | None, region: str) -> list[dict]:
    """Dự phòng: thư viện ddgs. backend="duckduckgo" vì chế độ "auto" gọi kèm engine Bing nội bộ
    cần mã thời gian khác ("week" thay vì "w") → luôn lỗi."""
    from ddgs import DDGS
    tl = {"day": "d", "week": "w", "month": "m"}.get(recent or "")
    return [{"url": it.get("image"), "w": int(it.get("width") or 0), "h": int(it.get("height") or 0),
             "title": it.get("title", ""), "page": it.get("url", ""), "src": "duckduckgo"}
            for it in DDGS().images(query, region=region, safesearch="off", layout="Wide", timelimit=tl,
                                    backend="duckduckgo", max_results=n)]


def duckduckgo(query: str, n: int = 80, recent: str | None = None) -> list[dict]:
    # Gọi trực tiếp trước. Thư viện ddgs có lỗi "malformed headers": nó luôn gửi header
    # "Connection: keep-alive", mà khi giả lập ngẫu nhiên trúng trình duyệt dùng HTTP/2 thì header này
    # bị cấm → lỗi. requests dùng HTTP/1.1 nên không gặp.
    region = "kr-kr" if re.search(r"[\uac00-\ud7a3]", query) else "jp-jp"
    try:
        return _duckduckgo_direct(query, n, recent, region)
    except Exception as first:  # noqa: BLE001
        try:
            return _duckduckgo_ddgs(query, n, recent, region)
        except Exception as second:  # noqa: BLE001
            raise RuntimeError(f"{first} | ddgs: {second}") from second


def bing(query: str, n: int = 70, recent: str | None = None) -> list[dict]:
    out = []
    age = {"day": "+filterui:age-lt1440", "week": "+filterui:age-lt10080",
           "month": "+filterui:age-lt43200"}.get(recent or "", "")
    for first in (0, 35):
        r = requests.get("https://www.bing.com/images/async", headers=HEADERS, timeout=20, params={
            "q": query, "first": first, "count": 35, "mmasync": 1,
            **({"setlang": "ko", "cc": "KR"} if re.search(r"[\uac00-\ud7a3]", query) else {"setlang": "ja", "cc": "JP"}),
            "qft": "+filterui:aspect-wide+filterui:imagesize-large" + age})
        for m in re.findall(r'\sm="([^"]+)"', r.text):
            try:
                d = json.loads(html.unescape(m))
            except ValueError:
                continue
            if d.get("murl"):
                out.append({"url": d["murl"], "w": 0, "h": 0, "title": d.get("t", ""),
                            "page": d.get("purl", ""), "src": "bing"})
        if len(out) >= n:
            break
    return out


def _find_images(obj, acc: list):
    """Tìm mọi object có url + width + height trong JSON của trang Yahoo."""
    if isinstance(obj, dict):
        url, w, h = obj.get("url"), obj.get("width"), obj.get("height")
        if isinstance(url, str) and url.startswith("http") and str(w).isdigit() and str(h).isdigit():
            acc.append((url, int(w), int(h), obj))
        for v in obj.values():
            _find_images(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _find_images(v, acc)


def yahoo_japan(query: str, n: int = 60, recent: str | None = None) -> list[dict]:
    out = []
    for b in (1, 21, 41):
        r = requests.get("https://search.yahoo.co.jp/image/search", headers=HEADERS, timeout=20,
                         params={"p": query, "ei": "UTF-8", "b": b, "dim": "large"})
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        found = []
        if m:
            try:
                _find_images(json.loads(m.group(1)), found)
            except ValueError:
                pass
        if not found:   # dự phòng nếu Yahoo đổi cấu trúc trang
            for u in re.findall(r'"original"\s*:\s*\{\s*"url"\s*:\s*"([^"]+)"', r.text):
                found.append((u.encode().decode("unicode_escape"), 0, 0, {}))
        for url, w, h, _ in found:
            if w and w < 640:
                continue   # bỏ ảnh thumbnail
            out.append({"url": url, "w": w, "h": h, "title": "", "page": "", "src": "yahoo.co.jp"})
        if len(out) >= n:
            break
    return out


SOURCES = {"duckduckgo": duckduckgo, "bing": bing, "yahoo": yahoo_japan}


# Nguồn nào lỗi (bị chặn tạm thời, mất mạng...) thì nghỉ một lúc, không gọi lại ở các cảnh sau
COOLDOWN_SEC = 15 * 60
MIN_GAP_SEC = {"duckduckgo": 2.0, "bing": 0.5, "yahoo": 0.5}   # giãn cách giữa 2 lượt tìm
_paused_until: dict[str, float] = {}
_last_call: dict[str, float] = {}
_lock = threading.Lock()
NAMES = {"duckduckgo": "DuckDuckGo", "bing": "Bing", "yahoo": "Yahoo! JAPAN"}


def _short_error(e: Exception) -> str:
    msg = str(e)
    m = re.search(r"\)\s*>\s*(.+?)(?:\'|\)|$)", msg)   # phần lý do thật sau "error sending request for url (...) >"
    reason = m.group(1).strip() if m else msg
    return reason[:200]


def search_all(query: str, sources: list[str], log=None, recent: str | None = None) -> list[dict]:
    """Gọi các nguồn rồi trộn xen kẽ để ảnh đa dạng."""
    results = []
    for name in sources:
        fn = SOURCES.get(name)
        if not fn:
            continue
        with _lock:
            if time.time() < _paused_until.get(name, 0):
                continue   # đang tạm nghỉ
            wait = _last_call.get(name, 0) + MIN_GAP_SEC.get(name, 0) - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            res = fn(query, recent=recent)
        except Exception as e:  # noqa: BLE001
            res = []
            with _lock:
                _paused_until[name] = time.time() + COOLDOWN_SEC
            if log:
                log(f"    ⚠️ {NAMES.get(name, name)} đang lỗi ({_short_error(e)}) → tạm bỏ qua "
                    f"{COOLDOWN_SEC // 60} phút, các nguồn khác vẫn tìm bình thường.")
        finally:
            with _lock:
                _last_call[name] = time.time()
        results.append(res)
    merged, i = [], 0
    while any(i < len(r) for r in results):
        for r in results:
            if i < len(r):
                merged.append(r[i])
        i += 1
    return merged
