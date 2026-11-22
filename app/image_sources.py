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


TITLE_KEYS = ("title", "alt", "caption", "description")
PAGE_KEYS = ("refererUrl", "refererLink", "referer", "pageUrl", "link", "sourceUrl", "host")


def _ctx(*objs) -> tuple[str, str]:
    """Tiêu đề + trang nguồn từ object ảnh và các object cha gần nhất."""
    title = page = ""
    for o in objs:
        if not isinstance(o, dict):
            continue
        for k in TITLE_KEYS:
            if not title and isinstance(o.get(k), str):
                title = o[k]
        for k in PAGE_KEYS:
            if not page and isinstance(o.get(k), str):
                page = o[k]
    return re.sub(r"<[^>]+>", "", title), page


def _find_images(obj, acc: list, parents: tuple = ()):
    """Tìm mọi object có url + width + height trong JSON của trang Yahoo (kèm tiêu đề/trang của object cha)."""
    if isinstance(obj, dict):
        url, w, h = obj.get("url"), obj.get("width"), obj.get("height")
        if isinstance(url, str) and url.startswith("http") and str(w).isdigit() and str(h).isdigit():
            acc.append((url, int(w), int(h), _ctx(obj, *parents[-3:][::-1])))
        for v in obj.values():
            _find_images(v, acc, parents + (obj,))
    elif isinstance(obj, list):
        for v in obj:
            _find_images(v, acc, parents)


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
                found.append((u.encode().decode("unicode_escape"), 0, 0, ("", "")))
        for url, w, h, (title, page) in found:
            if w and w < 640:
                continue   # bỏ ảnh thumbnail
            out.append({"url": url, "w": w, "h": h, "title": title, "page": page, "src": "yahoo.co.jp"})
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- 🇰🇷 NAVER IMAGE
def _hangul(s: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7a3]", s or ""))


def _walk_images(obj, acc: list, url_keys=("originalUrl", "originalImageUrl", "imgUrl", "url"),
                 w_keys=("orgWidth", "width", "imageWidth"), h_keys=("orgHeight", "height", "imageHeight")):
    """Tìm mọi object có link ảnh + kích thước trong JSON (cấu trúc trang có thể thay đổi)."""
    if isinstance(obj, dict):
        url = next((obj[k] for k in url_keys if isinstance(obj.get(k), str) and obj[k].startswith("http")), None)
        w = next((obj[k] for k in w_keys if str(obj.get(k, "")).isdigit()), 0)
        h = next((obj[k] for k in h_keys if str(obj.get(k, "")).isdigit()), 0)
        if url:
            acc.append((url, int(w or 0), int(h or 0), obj.get("title", "") or "", obj.get("link", "") or ""))
        for v in obj.values():
            _walk_images(v, acc, url_keys, w_keys, h_keys)
    elif isinstance(obj, list):
        for v in obj:
            _walk_images(v, acc, url_keys, w_keys, h_keys)


def naver(query: str, n: int = 80, recent: str | None = None) -> list[dict]:
    """Naver 이미지 검색 (máy tìm kiếm số 1 Hàn Quốc) – mạnh với ảnh KBO / KBL / K League / K-pop."""
    out, found = [], []
    period = {"day": "1d", "week": "1w", "month": "1m"}.get(recent or "")
    for start in (1, 51):
        params = {"query": query, "json_type": 6, "display": 50, "start": start, "where": "image"}
        if period:
            params["nso"] = f"so:r,p:{period}"
        try:
            r = requests.get("https://s.search.naver.com/p/c/image/search.naver", params=params,
                             headers=dict(HEADERS, **{"Accept-Language": "ko,en;q=0.8",
                                                      "Referer": "https://search.naver.com/"}), timeout=20)
            data = json.loads(r.text[r.text.find("{"):]) if "{" in r.text else {}
            _walk_images(data, found)
        except ValueError:
            pass
        if not found:   # dự phòng: đọc trang HTML
            r = requests.get("https://search.naver.com/search.naver", headers=HEADERS, timeout=20,
                             params={"where": "image", "query": query})
            for u in re.findall(r'"originalUrl"\s*:\s*"([^"]+)"', r.text):
                found.append((u.encode().decode("unicode_escape"), 0, 0, "", ""))
        if len(found) >= n:
            break
    seen = set()
    for url, w, h, title, link in found:
        if url in seen or "pstatic.net/static" in url:
            continue
        seen.add(url)
        if w and w < 640:
            continue
        out.append({"url": url, "w": w, "h": h, "title": title, "page": link, "src": "naver"})
    return out[:n]


# ---------------------------------------------------------------- 📰 ẢNH TỪ BÁO (Yahoo!ニュース / Naver News)
def _og_images(html_text: str) -> list[str]:
    urls = re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html_text)
    urls += re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html_text)
    return [html.unescape(u) for u in urls]


def _yahoo_news_photos(query: str, n: int, recent: str | None) -> list[dict]:
    r = requests.get("https://news.yahoo.co.jp/search", headers=HEADERS, timeout=20,
                     params={"p": query, "ei": "utf-8"})
    links = []
    for u in re.findall(r'https://news\.yahoo\.co\.jp/articles/[0-9a-f]{20,}', r.text):
        if u not in links:
            links.append(u)
    out = []
    for link in links[:8]:
        try:
            a = requests.get(link, headers=HEADERS, timeout=20).text
        except Exception:
            continue
        imgs = _og_images(a) + re.findall(r'https://newsatcl-pctr\.c\.yimg\.jp/t/amd-img/[^"\'\s]+', a)
        # ảnh Yahoo!ニュース: bỏ tham số cũ, xin bản lớn → mỗi ảnh chỉ còn 1 link
        imgs = [u.split("?")[0] + "?pri=l&w=1280" if "yimg.jp" in u else u for u in imgs]
        title = (re.search(r"<title>([^<]+)</title>", a) or [None, ""])[1]
        for u in dict.fromkeys(imgs):
            out.append({"url": u, "w": 0, "h": 0, "title": html.unescape(title), "page": link, "src": "news-photo"})
        if len(out) >= n:
            break
    return out


def _naver_news_photos(query: str, n: int, recent: str | None) -> list[dict]:
    params = {"where": "news", "query": query, "sort": 0}
    period = {"day": "1d", "week": "1w", "month": "1m"}.get(recent or "")
    if period:
        params["pd"] = {"1d": 4, "1w": 1, "1m": 2}[period]
    r = requests.get("https://search.naver.com/search.naver", headers=dict(HEADERS, **{"Accept-Language": "ko"}),
                     timeout=20, params=params)
    links = []
    for u in re.findall(r'https://n\.news\.naver\.com/(?:mnews/)?article/\d+/\d+|https://m\.sports\.naver\.com/[a-z]+/article/\d+/\d+',
                        r.text):
        if u not in links:
            links.append(u)
    out = []
    for link in links[:8]:
        try:
            a = requests.get(link, headers=dict(HEADERS, **{"Accept-Language": "ko"}), timeout=20).text
        except Exception:
            continue
        imgs = _og_images(a) + re.findall(r'https://imgnews\.pstatic\.net/image/[^"\'\s]+', a)
        # ảnh gốc của bài: imgnews.pstatic.net (bỏ ?type=… để lấy bản lớn nhất) → mỗi ảnh chỉ còn 1 link
        imgs = [u.split("?")[0] if "pstatic.net" in u else u for u in imgs]
        title = (re.search(r"<title>([^<]+)</title>", a) or [None, ""])[1]
        for u in dict.fromkeys(imgs):
            out.append({"url": u, "w": 0, "h": 0, "title": html.unescape(title), "page": link, "src": "news-photo"})
        if len(out) >= n:
            break
    return out


def news_photos(query: str, n: int = 30, recent: str | None = None) -> list[dict]:
    """Ảnh báo chí độ phân giải cao: tiếng Hàn → Naver News, còn lại → Yahoo!ニュース."""
    res = (_naver_news_photos if _hangul(query) else _yahoo_news_photos)(query, n, recent)
    seen, out = set(), []
    for x in res:                      # cùng 1 ảnh xuất hiện ở nhiều bài → chỉ giữ 1
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)
    return out


def google(query: str, n: int = 80, recent: str | None = None) -> list[dict]:
    from .google_images import search
    return search(query, n, recent, korean=_hangul(query))


SOURCES = {"google": google, "duckduckgo": duckduckgo, "bing": bing, "yahoo": yahoo_japan, "naver": naver,
           "news": news_photos}
ALL_SOURCES = list(SOURCES)


def route(sources: list[str], query: str) -> list[str]:
    """Thứ tự nguồn theo ngôn ngữ từ khóa: tiếng Hàn → Naver trước (bỏ Yahoo! JAPAN);
    tiếng Nhật → Yahoo! JAPAN + báo Nhật trước (bỏ Naver Image)."""
    order = (["news", "google", "naver", "bing", "duckduckgo"] if _hangul(query)
             else ["news", "google", "yahoo", "bing", "duckduckgo"])
    return [s for s in order if s in sources]


# Nguồn nào lỗi (bị chặn tạm thời, mất mạng...) thì nghỉ một lúc, không gọi lại ở các cảnh sau
COOLDOWN_SEC = 15 * 60
MIN_GAP_SEC = {"google": 3.0, "duckduckgo": 2.0, "bing": 0.5, "yahoo": 0.5, "naver": 1.0, "news": 1.0}   # giãn cách giữa 2 lượt tìm
_paused_until: dict[str, float] = {}
_last_call: dict[str, float] = {}
_lock = threading.Lock()
NAMES = {"google": "Google", "duckduckgo": "DuckDuckGo", "bing": "Bing", "yahoo": "Yahoo! JAPAN", "naver": "Naver",
         "news": "Ảnh từ báo"}


def _short_error(e: Exception) -> str:
    msg = str(e)
    m = re.search(r"\)\s*>\s*(.+?)(?:\'|\)|$)", msg)   # phần lý do thật sau "error sending request for url (...) >"
    reason = m.group(1).strip() if m else msg
    return reason[:200]


def search_all(query: str, sources: list[str], log=None, recent: str | None = None) -> list[dict]:
    """Gọi các nguồn (theo thứ tự hợp với ngôn ngữ) rồi trộn xen kẽ để ảnh đa dạng."""
    results, counts = [], []
    for name in route(sources, query):
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
        counts.append(f"{NAMES.get(name, name)} {len(res)}")
    if log and counts:
        log(f"    “{query}”: " + " · ".join(counts))
    merged, i = [], 0
    while any(i < len(r) for r in results):
        for r in results:
            if i < len(r):
                merged.append(r[i])
        i += 1
    return merged
