"""Tìm và tải ảnh / video cho từng cảnh.

Ảnh : DuckDuckGo + Bing + Yahoo! JAPAN (miễn phí, không cần key). Nếu vẫn thiếu ảnh 16:9,
       tool chụp khung hình nét nhất từ video YouTube liên quan (luôn đúng 16:9).
Video: YouTube (yt-dlp tìm kiếm). Bạn cũng có thể dán link YouTube / X / TikTok /
       Instagram / Facebook... cho từng cảnh, yt-dlp tải được hầu hết các nền tảng.
"""
import hashlib
import secrets
import io
import re
from pathlib import Path

import requests
from PIL import Image

from . import highlight as HL
from . import project as P
from .config import IMAGE_RATIO, IMAGE_RATIO_TOL, SWITCH_SEC, load_settings

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
N_CANDIDATES = 8


# ---------------------------------------------------------------- ẢNH
def is_16_9(w: int, h: int) -> bool:
    return h > 0 and abs((w / h) / IMAGE_RATIO - 1) <= IMAGE_RATIO_TOL


def search_images(query: str, log=None, recent: str | None = None) -> list[dict]:
    from .image_sources import search_all
    from .image_sources import ALL_SOURCES
    st = load_settings()
    sources = st.get("image_sources") or ALL_SOURCES
    if not st.get("sources_v2"):      # cài đặt cũ (chưa có Naver / ảnh từ báo) → tự bật nguồn mới
        sources = list(dict.fromkeys(list(sources) + ["naver", "news"]))
    if not st.get("sources_v3"):      # cài đặt cũ (chưa có Google) → tự bật Google
        sources = list(dict.fromkeys(list(sources) + ["google"]))
    out = search_all(query, sources, log, recent)
    if recent and len(out) < 15:   # tin mới mà ít ảnh → lấy thêm ảnh không lọc thời gian
        out += search_all(query, sources, log)

    seen, uniq = set(), []
    for x in out:
        # nhận MỌI tỉ lệ ảnh (ngang, vuông, dọc) – khi dựng video tự cắt vào chỗ có người cho kín khung
        if x["url"] and x["url"] not in seen:
            seen.add(x["url"])
            uniq.append(x)
    # ưu tiên ảnh ngang (ít bị cắt nhất) → ảnh chưa rõ kích thước → ảnh vuông/dọc; giữ thứ tự xen kẽ giữa các nguồn
    def order(x):
        if not x["w"]:
            return 1
        return 0 if x["w"] / max(1, x["h"]) >= 1.3 else 2
    return sorted(uniq, key=order)


# ---------------------------------------------------------------- ĐÚNG NGƯỜI / ĐÚNG CHỦ ĐỀ
def _norm(s: str) -> str:
    import urllib.parse
    s = urllib.parse.unquote(s or "").lower()
    return re.sub(r"[\s　・･·\-_/.,()（）「」\[\]'\"]+", "", s)


KATAKANA = re.compile(r"^[\u30a0-\u30ffー]+$")


def split_people(who: str) -> list[str]:
    """Tách nhiều người trong "who". Ngăn cách chuẩn: 「、」.
    「・」 chỉ dùng để tách khi KHÔNG phải tên nước ngoài viết katakana (マリアノ・リベラ là 1 người)."""
    who = (who or "").strip()
    if not who:
        return []
    if re.search(r"[、,/|／]", who):
        parts = re.split(r"[、,/|／]+", who)
    else:
        bits = who.split("・")
        parts = [who] if all(KATAKANA.match(b) for b in bits if b) else bits
    return [x.strip() for x in parts if x.strip()]


def names_of(scene: dict) -> list[str]:
    """Tên người/đối tượng của cảnh (field "who" do AI ghi, bạn sửa được ở bước Content)."""
    out = []
    for person in split_people(scene.get("who") or ""):
        out.append(_norm(person))
        bits = person.split("・")
        if len(bits) > 1 and len(bits[-1]) >= 3:     # マリアノ・リベラ → cũng nhận "リベラ"
            out.append(_norm(bits[-1]))
    return [n for n in dict.fromkeys(out) if len(n) >= 2]


def relevance(res: dict, names: list[str]) -> int:
    """2 = tiêu đề/link có tên → chắc đúng người · 1 = không có tiêu đề để biết · 0 = có tiêu đề mà không nhắc tên."""
    if not names:
        return 1
    text = _norm(" ".join(str(res.get(k) or "") for k in ("title", "page", "url", "channel")))
    if any(n in text for n in names):
        return 2
    return 1 if not (res.get("title") or "").strip() else 0


POLITICS_WORDS = ("首相", "総理", "政府", "内閣", "国会", "議員", "選挙", "自民党", "立憲", "大臣", "知事", "外交", "政権",
                  "政治", "大統領", "대통령", "국회", "의원", "선거", "정부", "장관", "정당", "정치", "총리")
SPORT_WORDS = {
    "baseball": ("野球", "投手", "打者", "本塁打", "ホームラン", "プロ野球", "NPB", "MLB", "甲子園", "야구", "투수", "타자", "홈런", "KBO"),
    "sumo": ("大相撲", "相撲", "横綱", "大関", "関脇", "力士", "土俵", "씨름", "스모"),
    "soccer": ("サッカー", "Jリーグ", "W杯", "ワールドカップ", "축구", "K리그", "월드컵"),
    "basketball": ("バスケ", "NBA", "Bリーグ", "농구", "KBL"),
    "horse": ("競馬", "JRA", "騎手", "厩舎", "ダービー", "有馬記念", "天皇賞", "ジャパンカップ", "G1", "GI", "牝馬", "牡馬",
              "경마"),
}


def off_topic(res: dict, p: dict, names: list[str]) -> str:
    """Kết quả lạc đề (thể loại thể thao): tiêu đề nói về chính trị / môn thể thao khác mà không nhắc tên người
    của cảnh → trả về lý do, rỗng nếu ổn."""
    if (p.get("genre") or "sports") != "sports":
        return ""
    t = f"{res.get('title') or ''} {res.get('page') or ''}"
    if not t.strip() or relevance(res, names) == 2:
        return ""
    if any(w in t for w in POLITICS_WORDS):
        return "chính trị"
    sport = p.get("sport") or ""
    if sport in SPORT_WORDS:
        for other, words in SPORT_WORDS.items():
            if other != sport and any(w in t for w in words) and not any(w in t for w in SPORT_WORDS[sport]):
                return "môn khác"
    return ""


SRC_NAMES = {"google": "Google", "yahoo.co.jp": "Yahoo", "bing": "Bing", "duckduckgo": "DuckDuckGo",
             "naver": "Naver", "news-photo": "Ảnh báo", "video-frame": "Khung hình video"}
SRC_RANK = {"news-photo": 0, "google": 0, "naver": 1, "yahoo.co.jp": 1, "bing": 1, "duckduckgo": 2}


def rank_by_names(results: list[dict], names: list[str]) -> list[dict]:
    """Kết quả nhắc đúng tên lên trước; cùng mức thì Google / ảnh báo trước các nguồn khác
    (giữ thứ tự xen kẽ gốc trong cùng nhóm)."""
    return sorted(results, key=lambda r: (-relevance(r, names), SRC_RANK.get(r.get("src"), 1)))


# ---------------------------------------------------------------- CHỈ LẤY VIDEO THI ĐẤU (thể thao)
# Video talkshow / phỏng vấn / kênh bình luận của cựu cầu thủ… → bỏ qua; ưu tiên highlight, cảnh trận đấu.
TALK_WORDS = ("トーク", "対談", "鼎談", "ラジオ", "雑談", "語る", "語った", "激白", "告白", "本音", "暴露", "切り抜き",
              "反応", "ゆっくり", "考察", "予想", "インタビュー", "会見", "密着", "ドキュメント", "チャンネル", "ちゃんねる",
              "OB", "YouTuber", "ライブ配信", "生配信", "podcast", "ポッドキャスト", "番組", "スタジオ", "ワイドショー",
              "토크", "인터뷰", "라디오", "썰", "반응", "예능", "기자회견", "분석", "예측", "다큐", "방송", "채널",
              "talk", "interview", "podcast", "reaction")
GAME_WORDS = ("ハイライト", "試合", "vs", "対", "投球", "奪三振", "本塁打", "ホームラン", "全球", "打席", "名場面",
              "好プレー", "サヨナラ", "完封", "ノーヒット", "ゴール", "得点", "取組", "優勝決定",
              "하이라이트", "경기", "홈런", "삼진", "골", "득점", "결승", "highlights", "game", "match",
              "レース", "競馬", "ダービー", "有馬記念", "天皇賞", "ジャパンカップ", "引退式", "G1", "GI")
TITLE_FILTER_SPORTS = ("baseball", "soccer", "basketball", "sumo", "horse")
FIELD_SPORTS = ("baseball", "soccer")      # sân cỏ → kiểm tra bằng màu sân trong hình


def video_mode(p: dict) -> tuple[bool, bool]:
    """(lọc tiêu đề talkshow?, kiểm tra hình có sân cỏ?) theo môn thể thao của dự án."""
    if (p.get("genre") or "sports") != "sports":
        return False, False
    sport = p.get("sport") or "other"
    return sport in TITLE_FILTER_SPORTS, sport in FIELD_SPORTS


def game_score(res: dict, query: str = "") -> int:
    """-1 = video nói chuyện (bỏ) · 1 = có dấu hiệu video trận đấu · 0 = không rõ."""
    t = (res.get("title") or "").lower()
    q = (query or "").lower()
    if any(w.lower() in t and w.lower() not in q for w in TALK_WORDS):
        return -1
    return 1 if any(w.lower() in t for w in GAME_WORDS) else 0


def scene_queries(scene: dict, kind: str, query: str | None = None) -> list[str]:
    """Danh sách từ khóa thử lần lượt: từ khóa chính → dự phòng → tên người."""
    if query:
        return [query]
    main = [scene.get("video_query"), scene.get("image_query")] if kind == "video" \
        else [scene.get("image_query")]
    qs = main + [scene.get("query_alt"), (split_people(scene.get("who") or "") or [""])[0]]
    out = []
    for q in qs:
        q = (q or "").strip()
        if q and q not in out:
            out.append(q)
    return out or [P.scene_plain_text(scene)[:30]]


def download_image(url: str, dest: Path, loose: bool = False) -> bool:
    """loose=True (ảnh báo chí): nhận cả ảnh ngang 3:2, 4:3… vì khung video tự cắt vừa (ưu tiên giữ người)."""
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": url}, timeout=20)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im = im.convert("RGB")
        if im.width < 640 or im.height < 360:
            return False   # ảnh quá nhỏ → mờ khi phóng to
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=92)
        return True
    except Exception:
        return False


def n_images_for(dur: float) -> int:
    """Số ảnh cho 1 cảnh: cứ ~3 giây đổi ảnh một lần."""
    return max(1, round(dur / SWITCH_SEC))


def fill_images(pid: str, scene: dict, used: set, log, query: str | None = None,
                recent: str | None = None) -> None:
    queries = scene_queries(scene, "image", query)
    q = queries[0]
    names = names_of(scene)
    proj = P.load(pid)
    dropped = {"chính trị": 0, "môn khác": 0, "báo không nhắc tên": 0}
    d = P.pdir(pid) / "media" / scene["id"]
    if d.exists():
        for pat in ("c*.jpg", "f*.jpg"):   # c*.jpg gồm cả c2_*.jpg
            for f in d.glob(pat):
                f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    # tên file mới mỗi lần tìm (không dùng lại c1.jpg…) → trình duyệt không hiện nhầm ảnh cũ còn trong bộ nhớ đệm
    tok = secrets.token_hex(3)
    cands = []
    k = n_images_for(P.scene_est_sec(scene))
    want = max(N_CANDIDATES, k + 2)
    weak = []     # ảnh có tiêu đề nhưng KHÔNG nhắc tên người → chỉ dùng khi thiếu
    for qi, qq in enumerate(queries):
        if len(cands) >= want:
            break
        if qi:
            log(f"    ít ảnh đúng → thử từ khóa dự phòng “{qq}”")
        tried = 0
        for res in rank_by_names(search_images(qq, log, recent), names):
            if res["url"] in used or len(cands) >= want:
                continue
            why = off_topic(res, proj, names)
            if not why and names and res.get("src") == "news-photo" and relevance(res, names) < 2:
                why = "báo không nhắc tên"    # ảnh đại diện bài báo không nhắc tên người → hay lạc đề
            if why:
                dropped[why] += 1
                continue
            if relevance(res, names) == 0:
                weak.append(res)
                continue
            tried += 1
            if tried > 40:
                break
            f = d / f"c{len(cands) + 1}_{tok}.jpg"
            if download_image(res["url"], f, loose=True):
                cands.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}", "url": res["url"],
                              "page": res.get("page", ""), "src": res.get("src", "")})
                used.add(res["url"])
    if names and weak:
        log(f"    bỏ {len(weak)} ảnh không nhắc tới “{scene.get('who')}” (dễ sai người)")
    if any(dropped.values()):
        log("    bỏ ảnh lạc đề: " + ", ".join(f"{k} {v}" for k, v in dropped.items() if v))
    if len(cands) < k:
        for res in weak[:20]:      # vẫn thiếu → dùng tạm ảnh “không chắc”, xếp sau cùng
            if len(cands) >= k + 1 or res["url"] in used:
                continue
            f = d / f"c{len(cands) + 1}_{tok}.jpg"
            if download_image(res["url"], f, loose=True):
                cands.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}", "url": res["url"],
                              "page": res.get("page", ""), "src": res.get("src", ""), "unsure": True})
                used.add(res["url"])
    if len(cands) < k + 2:
        # Thiếu ảnh 16:9 → chụp khung hình nét từ video liên quan (luôn đúng 16:9)
        try:
            cands += stills_from_video(pid, scene, k + 2 - len(cands) + 2, log, recent)
        except Exception as e:  # noqa: BLE001
            log(f"    không lấy được ảnh từ video: {str(e)[:100]}")
    if not cands:
        raise RuntimeError(f"Không tìm được ảnh 16:9 cho “{q}” – thử từ khóa khác")
    scene["candidates"] = cands
    scene["items"] = cands[:k]
    scene["picked"] = False     # tool tự chọn
    # cảnh so sánh 2 người (bố cục Hàn): tìm thêm ảnh người thứ hai
    if scene.get("split") and scene.get("image_query2"):
        q2 = scene["image_query2"]
        c2 = []
        for res in search_images(q2, log, recent):
            if res["url"] in used:
                continue
            f = d / f"c2_{len(c2) + 1}_{tok}.jpg"
            if download_image(res["url"], f, loose=True):
                c2.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}", "url": res["url"],
                           "page": res.get("page", ""), "src": res.get("src", "")})
                used.add(res["url"])
            if len(c2) >= 4:
                break
        if c2:
            scene["candidates"] = cands[:4] + c2 + cands[4:]
            scene["items"] = [cands[0], c2[0]]
            log(f"    chia đôi khung: {q} | {q2}")
    from collections import Counter
    srcs = Counter(SRC_NAMES.get(c.get("src"), c.get("src") or "?") for c in cands)
    log(f"  {scene['id']}: {len(cands)} ảnh ứng viên, dùng {len(scene['items'])} ảnh · nguồn: "
        + " · ".join(f"{k} {v}" for k, v in srcs.most_common()))


def stills_from_video(pid: str, scene: dict, count: int, log, recent: str | None = None) -> list[dict]:
    q = scene_queries(scene, "video")[0]
    sources = P.pdir(pid) / "sources"
    sources.mkdir(exist_ok=True)
    d = P.pdir(pid) / "media" / scene["id"]
    log(f"    ảnh 16:9 chưa đủ → chụp khung hình từ video YouTube “{q}”")
    talk_filter, field_check = video_mode(P.load(pid))
    vids = search_videos(q, 5, recent)
    if talk_filter:
        vids = [r for r in vids if game_score(r, q) >= 0]
    for r in rank_by_names(vids, names_of(scene))[:2]:
        try:
            v = download_video(r["url"], sources, log)
        except Exception:
            continue
        if field_check and HL.game_share(HL.analyze(v, need_field=True)) < 0.3:
            continue
        w, h = HL.video_size(v)
        if not is_16_9(w, h):
            continue
        out = []
        for i, t in enumerate(HL.best_stills(HL.analyze(v), count)):
            f = HL.frame_at(v, t, d / f"f{len(out) + 1}_{int(t)}_{secrets.token_hex(3)}.jpg", width=1920)
            if f.exists():
                out.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}",
                            "url": f"{r['url']}&t={int(t)}", "page": r["url"], "src": "video-frame"})
        if out:
            return out
    return []


# ---------------------------------------------------------------- VIDEO
def search_videos(query: str, n: int = 8, recent: str | None = None) -> list[dict]:
    """recent != None (tin tức) → tìm theo video MỚI NHẤT."""
    import urllib.parse
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "extract_flat": True, "noplaylist": True,
            "playlistend": n}
    # yt-dlp đã bỏ "ytsearchdate" → dùng link tìm kiếm YouTube có bộ lọc "ngày tải lên" + "chỉ video"
    sp = {"day": "EgQIAhAB", "week": "EgQIAxAB", "month": "EgQIBBAB"}.get(recent or "")
    target = (f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}&sp={sp}"
              if sp else f"ytsearch{n}:{query}")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(target, download=False)
    if sp and not (info or {}).get("entries"):
        return search_videos(query, n)   # lọc thời gian quá chặt → tìm bình thường
    out = []
    for e in list(info.get("entries", []) or [])[:n]:
        dur = e.get("duration") or 0
        if e.get("live_status") in ("is_live", "is_upcoming"):
            continue
        if dur and not (15 <= dur <= 1800):
            continue
        if "/shorts/" in (e.get("url") or ""):
            continue   # bỏ YouTube Shorts (video dọc)
        ch = e.get("channel") or e.get("uploader") or ""
        out.append({"id": e.get("id"), "title": e.get("title", ""), "duration": dur, "channel": ch,
                    "official": is_official(ch),
                    "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"})
    # kênh chính thức (giải đấu, đội bóng, đài truyền hình) lên trước – video nét, đúng trận
    out.sort(key=lambda r: not r["official"])
    if re.search(r"[\uac00-\ud7a3]", query):
        try:
            out = naver_tv_search(query) + out   # clip KBO / KBL… chủ yếu nằm trên Naver
        except Exception:
            pass
    if load_settings().get("facebook_video", True):
        try:
            out += facebook_video_search(query, recent=recent)
        except Exception:
            pass
    return out


# ---------------------------------------------------------------- FACEBOOK
FB_VIDEO = re.compile(r"https?://(?:www\.|m\.|web\.)?(?:facebook\.com/(?:[^/?#]+/videos/|watch/?\?v=|video\.php\?v=)"
                      r"[^\s\"'<>&]*(?:&[^\s\"'<>]*)?|fb\.watch/[\w-]+)")


def _fb_clean(u: str) -> str:
    import html as _html
    import urllib.parse
    u = urllib.parse.unquote(_html.unescape(u))
    u = u.replace("://m.", "://www.").replace("://web.", "://www.")
    if "watch" in u or "video.php" in u:
        v = re.search(r"[?&]v=(\d+)", u)
        return f"https://www.facebook.com/watch/?v={v.group(1)}" if v else u
    return u.split("?")[0].rstrip("/")


def facebook_video_search(query: str, n: int = 4, recent: str | None = None) -> list[dict]:
    """Facebook không cho tìm khi chưa đăng nhập → tìm qua DuckDuckGo / Bing với "site:facebook.com".
    Chỉ lấy video công khai (trang báo, đội bóng, đài TV); bỏ Reels (video dọc)."""
    q = f"site:facebook.com {query} video"
    found: list[tuple[str, str]] = []
    pages = []
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": q, "df": {"week": "w", "month": "m"}.get(recent or "", "")},
                          headers={"User-Agent": UA, "Accept-Language": "ja,ko;q=0.9,en;q=0.8"}, timeout=15)
        pages.append(r.text)
    except Exception:
        pass
    try:
        r = requests.get("https://www.bing.com/search", params={"q": q, "count": 20},
                         headers={"User-Agent": UA, "Accept-Language": "ja,ko;q=0.9,en;q=0.8"}, timeout=15)
        pages.append(r.text)
    except Exception:
        pass
    seen = set()
    for page in pages:
        import html as _html
        import urllib.parse
        # DuckDuckGo bọc link thật trong uddg=...
        text = page + " " + " ".join(urllib.parse.unquote(m) for m in re.findall(r"uddg=([^&\"']+)", page))
        for m in FB_VIDEO.finditer(text):
            u = _fb_clean(m.group(0))
            if "/reel" in u or u in seen:
                continue
            seen.add(u)
            # tiêu đề: đoạn chữ gần link nhất (để lọc đúng tên người)
            i = page.find(m.group(0)[:60])
            title = re.sub(r"<[^>]+>", " ", page[i:i + 600]) if i >= 0 else ""
            found.append((u, _html.unescape(re.sub(r"\s+", " ", title))[:200]))
            if len(found) >= n:
                break
    return [{"id": u, "title": t, "duration": 0, "channel": "Facebook", "official": False, "url": u, "src": "facebook"}
            for u, t in found[:n]]


OFFICIAL_HINTS = ("公式", "official", "공식", "jra", "グリーンチャンネル", "netkeiba", "パ・リーグ", "パーソル", "npb", "dazn", "nhk", "日本相撲協会",
                  "jリーグ", "j.league", "b.league", "bリーグ", "kbo", "kbl", "k리그", "k league", "spotv", "tving",
                  "쿠팡플레이", "sbs", "kbs", "mbc", "jtbc", "ytn", "tbs", "日テレ", "テレ朝", "フジテレビ", "テレビ東京")


def is_official(channel: str) -> bool:
    c = (channel or "").lower()
    return any(h.lower() in c for h in OFFICIAL_HINTS)


def naver_tv_search(query: str, n: int = 5) -> list[dict]:
    """Tìm clip trên Naver TV (네이버 동영상). yt-dlp tải được link dạng tv.naver.com/v/…"""
    r = requests.get("https://search.naver.com/search.naver", timeout=20,
                     headers={"User-Agent": UA, "Accept-Language": "ko"}, params={"where": "video", "query": query})
    ids = []
    for vid in re.findall(r'tv\.naver\.com/v/(\d+)', r.text):
        if vid not in ids:
            ids.append(vid)
    return [{"id": v, "title": f"Naver TV {v}", "duration": 0, "channel": "Naver TV", "official": True,
             "url": f"https://tv.naver.com/v/{v}"} for v in ids[:n]]


def download_video(url: str, sources: Path, log) -> Path:
    import yt_dlp
    key = hashlib.md5(url.encode()).hexdigest()[:12]
    existing = list(sources.glob(f"{key}.mp4"))
    if existing:
        return existing[0]
    opts = {
        "quiet": True, "noplaylist": True, "outtmpl": str(sources / f"{key}.%(ext)s"),
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4", "max_filesize": 800 * 1024 * 1024,
    }
    log(f"  tải video: {url}")
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    files = list(sources.glob(f"{key}.mp4")) or list(sources.glob(f"{key}.*"))
    files = [f for f in files if f.suffix not in (".json", ".part")]
    if not files:
        raise RuntimeError("Tải video thất bại")
    return files[0]


# ---------------------------------------------------------------- PHỤ ĐỀ: lúc bình luận viên gọi tên
def _parse_vtt(text: str) -> list[tuple[float, float, str]]:
    def ts(s):
        p = s.strip().replace(",", ".").split(":")
        p = [0.0] * (3 - len(p)) + [float(x) for x in p]
        return p[0] * 3600 + p[1] * 60 + p[2]
    cues, cur = [], None
    for line in text.splitlines():
        m = re.match(r"\s*([\d:.,]+)\s+-->\s+([\d:.,]+)", line)
        if m:
            cur = [ts(m.group(1)), ts(m.group(2)), ""]
            cues.append(cur)
        elif cur is not None and line.strip():
            cur[2] += re.sub(r"<[^>]+>", "", line).strip()
    out, last = [], ""
    for a, b, t in cues:          # phụ đề tự động hay lặp lại dòng trước → bỏ trùng
        if t and t != last:
            out.append((a, b, t))
        last = t
    return out


def fetch_subs(url: str, sources: Path, log=None) -> list[tuple[float, float, str]]:
    """Tải phụ đề (tự động) tiếng Nhật/Hàn của video YouTube – không tải lại video."""
    if not re.search(r"youtube\.com|youtu\.be", url or ""):
        return []
    import yt_dlp
    key = hashlib.md5(url.encode()).hexdigest()[:12]
    found = list(sources.glob(f"{key}*.vtt"))
    if not found and not (sources / f"{key}.nosubs").exists():
        opts = {"quiet": True, "skip_download": True, "writesubtitles": True, "writeautomaticsub": True,
                "subtitleslangs": ["ja", "ko", "ja-orig", "ko-orig"], "subtitlesformat": "vtt",
                "outtmpl": str(sources / f"{key}.%(ext)s"), "noplaylist": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception:  # noqa: BLE001
            pass
        found = list(sources.glob(f"{key}*.vtt"))
        if not found:
            (sources / f"{key}.nosubs").write_text("", encoding="utf-8")
    cues = []
    for f in found:
        cues += _parse_vtt(f.read_text(encoding="utf-8", errors="ignore"))
    return sorted(cues)


def call_names(scene: dict) -> list[str]:
    """Tên bình luận viên hay gọi: field "call" (AI ghi, VD 田畑・タバタ) + họ trong "who"."""
    out = [x.strip() for x in re.split(r"[・,、/|]+", scene.get("call") or "") if len(x.strip()) >= 2]
    for n in split_people(scene.get("who") or ""):
        if len(n) >= 2:
            out.append(n)
            if "・" in n:
                out.append(n.split("・")[-1])           # マリアノ・リベラ → リベラ
            if re.fullmatch(r"[\u4e00-\u9fff]{3,4}", n):      # 田畑一也 → 田畑 (họ 2 chữ Hán)
                out.append(n[:2])
            if re.fullmatch(r"[\uac00-\ud7a3]{3}", n):        # 이승엽 → 승엽 (gọi tên) / 이승엽
                out.append(n[1:])
    return list(dict.fromkeys(out))


def name_hits(cues: list[tuple[float, float, str]], names: list[str]) -> list[float]:
    names = [re.sub(r"\s+", "", n) for n in names if n]
    return [a for a, b, t in cues if any(n in re.sub(r"\s+", "", t) for n in names)]


# ---------------------------------------------------------------- ẢNH CHÂN DUNG THAM CHIẾU (để AI so người)
def reference_photo(pid: str, scene: dict, log) -> Path | None:
    who = (split_people(scene.get("who") or "") or [""])[0]
    if not who:
        return None
    d = P.pdir(pid) / "refs"
    d.mkdir(exist_ok=True)
    f = d / f"{hashlib.md5(who.encode()).hexdigest()[:10]}.jpg"
    if f.exists():
        return f
    try:
        names = names_of({"who": who})
        for r in search_images(who, None):
            if relevance(r, names) == 2 and download_image(r["url"], f, loose=True):
                return f
    except Exception:  # noqa: BLE001
        pass
    return None


def choose_clip(pid: str, scene: dict, video: Path, url: str, used_windows: dict, log,
                need_field: bool = False, strict: bool = True) -> None:
    """strict=False (link bạn tự dán): không loại video vì không thấy người, chỉ ưu tiên đoạn đúng người."""
    d = P.pdir(pid) / "media" / scene["id"]
    d.mkdir(parents=True, exist_ok=True)
    dur = P.scene_est_sec(scene)
    an = HL.analyze(video, need_field=need_field)
    # (1) phụ đề: lúc bình luận viên gọi tên nhân vật → ưu tiên các đoạn quanh đó
    focus = []
    if url and url != "upload" and (scene.get("who") or scene.get("call")):
        try:
            hits = name_hits(fetch_subs(url, video.parent, log), call_names(scene))
            if hits:
                focus = hits
                log(f"    phụ đề: bình luận viên nhắc tên {len(hits)} lần → ưu tiên các đoạn quanh "
                    + ", ".join(f"{t:.0f}s" for t in hits[:6]))
        except Exception:  # noqa: BLE001
            pass
    wins = HL.best_windows(an, dur, k=6, exclude=used_windows.get(str(video), []), need_field=need_field,
                           focus=focus)
    if not wins and need_field:
        raise RuntimeError("Video không có đoạn nào là cảnh trên sân")
    if not wins:
        raise RuntimeError("Video quá ngắn")
    pick = 0
    verified = False
    # (2) Claude xem hình + ảnh chân dung → chỉ giữ đoạn có ĐÚNG nhân vật
    if load_settings().get("verify_person_video", True) and scene.get("who") and url != "upload":
        log(f"  {scene['id']}: nhờ Claude xem {len(wins)} đoạn để xác nhận đúng “{scene.get('who')}”...")
        v = HL.verify_person(video, wins, P.scene_plain_text(scene), scene.get("who", ""),
                             scene.get("uniform", ""), reference_photo(pid, scene, log), d)
        if v.get("checked"):
            if not v["ok"]:
                if strict:
                    raise RuntimeError(f"không thấy “{scene.get('who')}” trong video này")
                log(f"    ⚠️ Claude không thấy “{scene.get('who')}” trong link bạn dán – vẫn dùng theo ý bạn")
                v["ok"] = list(range(len(wins)))
            log(f"    đúng người ở {len(v['ok'])}/{len(wins)} đoạn"
                + (f" – chọn đoạn {v['best'] + 1}: {v['why'].get(v['best'], '')}" if v.get("best") is not None else ""))
            keep = sorted(v["ok"], key=lambda i: (i != v.get("best"), i))
            wins = [wins[i] for i in keep]
            verified = True
        else:
            log(f"    (không xác nhận được bằng Claude: {v.get('error', '')} → chọn như bình thường)")
    if not verified and load_settings().get("use_claude_for_highlight") and len(wins) > 1:
        log(f"  {scene['id']}: nhờ Claude xem {len(wins)} đoạn hay nhất để chọn đoạn hợp nội dung...")
        pick = HL.ask_claude_pick(video, wins, P.scene_plain_text(scene), d)
    rel = video.relative_to(P.pdir(pid)).as_posix()
    cands = []
    for f in d.glob("v*.jpg"):
        f.unlink()
    tok = secrets.token_hex(3)
    for i, w in enumerate(wins):
        th = HL.frame_at(video, w["start"] + w["dur"] / 2, d / f"v{i + 1}_{tok}.jpg", 480)
        cands.append({"kind": "video", "file": rel, "start": w["start"], "url": url,
                      "thumb": f"media/{scene['id']}/{th.name}", "score": w["score"]})
    scene["candidates"] = cands
    scene["items"] = [cands[pick]]
    scene["picked"] = url in ("upload",)
    used_windows.setdefault(str(video), []).append((wins[pick]["start"], wins[pick]["start"] + dur))
    log(f"  {scene['id']}: dùng đoạn {wins[pick]['start']:.1f}s–{wins[pick]['start'] + dur:.1f}s")


def fill_video(pid: str, scene: dict, used_urls: set, used_windows: dict, log,
               query: str | None = None, url: str | None = None, recent: str | None = None) -> None:
    sources = P.pdir(pid) / "sources"
    sources.mkdir(exist_ok=True)
    if url:
        results = [{"url": url, "title": url}]
    else:
        names = names_of(scene)
        results = []
        talk_filter, _ = video_mode(P.load(pid))
        for qi, q in enumerate(scene_queries(scene, "video", query)):
            if qi:
                log(f"    chưa có video nhắc đúng tên → thử “{q}”")
            got = search_videos(q, recent=recent)
            proj = P.load(pid)
            got = [r for r in got if not off_topic(r, proj, names)]
            if talk_filter:
                drop = [r for r in got if game_score(r, q) < 0]
                if drop:
                    log(f"    bỏ {len(drop)} video kiểu talkshow/phỏng vấn: " +
                        " · ".join(r["title"][:25] for r in drop[:3]))
                got = [r for r in got if game_score(r, q) >= 0]
            results += [r for r in got if r["url"] not in {x["url"] for x in results}]
            if any(relevance(r, names) == 2 for r in results):
                break
        # đúng tên lên trước → kênh chính thức → video chưa dùng
        results.sort(key=lambda r: (-relevance(r, names), -(game_score(r) if talk_filter else 0),
                                    not r.get("official"), r["url"] in used_urls))
        scene["video_results"] = results
    last_err = None
    _, field_check = video_mode(P.load(pid))
    for r in results[:5 if field_check else 3]:
        try:
            v = download_video(r["url"], sources, log)
            if HL.probe_duration(v) < P.scene_est_sec(scene) + 1:
                continue
            if field_check and not url:
                share = HL.game_share(HL.analyze(v, need_field=True))
                if share < 0.3:
                    log(f"    bỏ “{r.get('title', '')[:30]}”: chỉ {share:.0%} là cảnh trên sân (talkshow / phòng thu?)")
                    continue
            choose_clip(pid, scene, v, r["url"], used_windows, log, need_field=field_check and not url,
                        strict=not url)
            scene["picked"] = bool(url)     # link bạn tự dán → coi như bạn đã chọn
            used_urls.add(r["url"])
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            log(f"  bỏ qua {r['url']}: {e}")
    raise RuntimeError(f"Không lấy được video: {last_err}")


# ---------------------------------------------------------------- JOB
def news_recency(p: dict) -> str | None:
    """Với tin tức: chỉ ưu tiên ảnh/video mới theo khoảng thời gian của tin."""
    if p.get("genre") != "news":
        return None
    days = int((p.get("news") or {}).get("days") or 3)
    return "week" if days <= 7 else "month"

def fill_all(pid: str, log, only: list[str] | None = None, query: str | None = None,
             url: str | None = None) -> None:
    p = P.load(pid)
    scenes = p["scenes"]
    recent = news_recency(p)
    used = {it.get("url") for s in scenes for it in s.get("items", []) if it.get("kind") == "image"}
    used_urls: set = set()
    used_windows: dict = {}
    for s in scenes:
        for it in s.get("items", []):
            if it.get("kind") == "video" and (not only or s["id"] not in only):
                f = str(P.pdir(pid) / it["file"])
                used_windows.setdefault(f, []).append((it["start"], it["start"] + P.scene_est_sec(s)))
    todo = [s for s in scenes if not only or s["id"] in only]
    for i, s in enumerate(todo):
        log(f"Cảnh {s['id']} ({'video' if s['kind'] == 'video' else 'ảnh'}) {i + 1}/{len(todo)}",
            i / len(todo))
        try:
            if s["kind"] == "video":
                try:
                    fill_video(pid, s, used_urls, used_windows, log, query=query, url=url, recent=recent)
                except Exception as e:  # noqa: BLE001
                    if url:
                        raise
                    log(f"  ⚠️ {e} → dùng ảnh thay thế")
                    fill_images(pid, s, used, log, recent=recent)
            else:
                fill_images(pid, s, used, log, query=query, recent=recent)
        except Exception as e:  # noqa: BLE001
            log(f"  ⚠️ {s['id']}: {e}")
        # lưu sau mỗi cảnh để giao diện thấy tiến độ
        P.update(pid, lambda pp, s=s: _replace_scene(pp, s))


def _replace_scene(pp: dict, s: dict) -> None:
    for i, sc in enumerate(pp["scenes"]):
        if sc["id"] == s["id"]:
            sc["candidates"] = s.get("candidates", [])
            sc["items"] = s.get("items", [])
            sc["picked"] = bool(s.get("picked"))
            if "video_results" in s:
                sc["video_results"] = s["video_results"]


def save_upload(pid: str, sid: str, filename: str, data: bytes) -> dict:
    ext = Path(filename).suffix.lower()
    d = P.pdir(pid) / "media" / sid
    d.mkdir(parents=True, exist_ok=True)
    if ext in (".mp4", ".mov", ".webm", ".mkv", ".m4v"):
        f = P.pdir(pid) / "sources" / f"upload_{hashlib.md5(data).hexdigest()[:10]}{ext}"
        f.write_bytes(data)
        return {"kind": "video_source", "path": f}
    im = Image.open(io.BytesIO(data)).convert("RGB")
    f = d / f"u{hashlib.md5(data).hexdigest()[:8]}.jpg"
    im.save(f, "JPEG", quality=92)
    return {"kind": "image", "file": f"media/{sid}/{f.name}", "url": "upload"}
