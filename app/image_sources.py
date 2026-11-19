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

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"}


def duckduckgo(query: str, n: int = 80, recent: str | None = None) -> list[dict]:
    from ddgs import DDGS
    out = []
    tl = {"day": "Day", "week": "Week", "month": "Month"}.get(recent or "")
    for it in DDGS().images(query, region="jp-jp", safesearch="off", layout="Wide", timelimit=tl,
                            max_results=n):
        out.append({"url": it.get("image"), "w": int(it.get("width") or 0), "h": int(it.get("height") or 0),
                    "title": it.get("title", ""), "page": it.get("url", ""), "src": "duckduckgo"})
    return out


def bing(query: str, n: int = 70, recent: str | None = None) -> list[dict]:
    out = []
    age = {"day": "+filterui:age-lt1440", "week": "+filterui:age-lt10080",
           "month": "+filterui:age-lt43200"}.get(recent or "", "")
    for first in (0, 35):
        r = requests.get("https://www.bing.com/images/async", headers=HEADERS, timeout=20, params={
            "q": query, "first": first, "count": 35, "mmasync": 1, "setlang": "ja", "cc": "JP",
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


def search_all(query: str, sources: list[str], log=None, recent: str | None = None) -> list[dict]:
    """Gọi các nguồn rồi trộn xen kẽ để ảnh đa dạng."""
    results = []
    for name in sources:
        fn = SOURCES.get(name)
        if not fn:
            continue
        try:
            res = fn(query, recent=recent)
        except Exception as e:  # noqa: BLE001
            res = []
            if log:
                log(f"    nguồn {name} lỗi: {str(e)[:80]}")
        results.append(res)
    merged, i = [], 0
    while any(i < len(r) for r in results):
        for r in results:
            if i < len(r):
                merged.append(r[i])
        i += 1
    return merged


