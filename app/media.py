"""Tìm và tải ảnh / video cho từng cảnh.

Ảnh : DuckDuckGo + Bing + Yahoo! JAPAN (miễn phí, không cần key). Nếu vẫn thiếu ảnh 16:9,
       tool chụp khung hình nét nhất từ video YouTube liên quan (luôn đúng 16:9).
Video: YouTube (yt-dlp tìm kiếm). Bạn cũng có thể dán link YouTube / X / TikTok /
       Instagram / Facebook... cho từng cảnh, yt-dlp tải được hầu hết các nền tảng.
"""
import hashlib
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
    out = search_all(query, sources, log, recent)
    if recent and len(out) < 15:   # tin mới mà ít ảnh → lấy thêm ảnh không lọc thời gian
        out += search_all(query, sources, log)

    seen, uniq = set(), []
    for x in out:
        # chỉ giữ ảnh 16:9 (theo thông tin kích thước của kết quả tìm kiếm; tải về sẽ kiểm tra lại)
        ok_ratio = (not x["w"] or is_16_9(x["w"], x["h"]) or
                    (x.get("src") == "news-photo" and 1.3 <= x["w"] / max(1, x["h"]) <= 2.0))
        if x["url"] and x["url"] not in seen and ok_ratio:
            seen.add(x["url"])
            uniq.append(x)
    # ưu tiên ảnh đã biết chắc là 16:9 (giữ thứ tự xen kẽ giữa các nguồn)
    return sorted(uniq, key=lambda x: not x["w"])


def download_image(url: str, dest: Path, loose: bool = False) -> bool:
    """loose=True (ảnh báo chí): nhận cả ảnh ngang 3:2, 4:3… vì khung video tự cắt vừa (ưu tiên giữ người)."""
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": url}, timeout=20)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im = im.convert("RGB")
        if im.width < 640:
            return False
        ar = im.width / max(1, im.height)
        if not (is_16_9(*im.size) or (loose and 1.3 <= ar <= 2.0)):
            return False   # ảnh thường: chỉ 16:9 · ảnh báo: ảnh ngang
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
    q = query or scene.get("image_query") or P.scene_plain_text(scene)
    d = P.pdir(pid) / "media" / scene["id"]
    if d.exists():
        for pat in ("c*.jpg", "f*.jpg"):   # c*.jpg gồm cả c2_*.jpg
            for f in d.glob(pat):
                f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    cands = []
    k = n_images_for(P.scene_est_sec(scene))
    want = max(N_CANDIDATES, k + 2)
    tried = 0
    for res in search_images(q, log, recent):
        if res["url"] in used:
            continue
        tried += 1
        if tried > 40:
            break
        f = d / f"c{len(cands) + 1}.jpg"
        if download_image(res["url"], f, loose=res.get("src") == "news-photo"):
            cands.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}", "url": res["url"],
                          "page": res.get("page", ""), "src": res.get("src", "")})
            used.add(res["url"])
        if len(cands) >= want:
            break
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
    # cảnh so sánh 2 người (bố cục Hàn): tìm thêm ảnh người thứ hai
    if scene.get("split") and scene.get("image_query2"):
        q2 = scene["image_query2"]
        c2 = []
        for res in search_images(q2, log, recent):
            if res["url"] in used:
                continue
            f = d / f"c2_{len(c2) + 1}.jpg"
            if download_image(res["url"], f, loose=res.get("src") == "news-photo"):
                c2.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}", "url": res["url"],
                           "page": res.get("page", ""), "src": res.get("src", "")})
                used.add(res["url"])
            if len(c2) >= 4:
                break
        if c2:
            scene["candidates"] = cands[:4] + c2 + cands[4:]
            scene["items"] = [cands[0], c2[0]]
            log(f"    chia đôi khung: {q} | {q2}")
    log(f"  {scene['id']}: {len(cands)} ảnh ứng viên, dùng {len(scene['items'])} ảnh")


def stills_from_video(pid: str, scene: dict, count: int, log, recent: str | None = None) -> list[dict]:
    q = scene.get("image_query") or scene.get("video_query") or P.scene_plain_text(scene)
    sources = P.pdir(pid) / "sources"
    sources.mkdir(exist_ok=True)
    d = P.pdir(pid) / "media" / scene["id"]
    log(f"    ảnh 16:9 chưa đủ → chụp khung hình từ video YouTube “{q}”")
    for r in search_videos(q, 5, recent)[:2]:
        try:
            v = download_video(r["url"], sources, log)
        except Exception:
            continue
        w, h = HL.video_size(v)
        if not is_16_9(w, h):
            continue
        out = []
        for i, t in enumerate(HL.best_stills(HL.analyze(v), count)):
            f = HL.frame_at(v, t, d / f"f{len(out) + 1}_{int(t)}.jpg", width=1920)
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
    return out


OFFICIAL_HINTS = ("公式", "official", "공식", "パ・リーグ", "パーソル", "npb", "dazn", "nhk", "日本相撲協会",
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


def choose_clip(pid: str, scene: dict, video: Path, url: str, used_windows: dict, log) -> None:
    d = P.pdir(pid) / "media" / scene["id"]
    d.mkdir(parents=True, exist_ok=True)
    dur = P.scene_est_sec(scene)
    an = HL.analyze(video)
    wins = HL.best_windows(an, dur, k=6, exclude=used_windows.get(str(video), []))
    if not wins:
        raise RuntimeError("Video quá ngắn")
    pick = 0
    if load_settings().get("use_claude_for_highlight") and len(wins) > 1:
        log(f"  {scene['id']}: nhờ Claude xem {len(wins)} đoạn hay nhất để chọn đoạn hợp nội dung...")
        pick = HL.ask_claude_pick(video, wins, P.scene_plain_text(scene), d)
    rel = video.relative_to(P.pdir(pid)).as_posix()
    cands = []
    for f in d.glob("v*.jpg"):
        f.unlink()
    for i, w in enumerate(wins):
        th = HL.frame_at(video, w["start"] + w["dur"] / 2, d / f"v{i + 1}.jpg", 480)
        cands.append({"kind": "video", "file": rel, "start": w["start"], "url": url,
                      "thumb": f"media/{scene['id']}/{th.name}", "score": w["score"]})
    scene["candidates"] = cands
    scene["items"] = [cands[pick]]
    used_windows.setdefault(str(video), []).append((wins[pick]["start"], wins[pick]["start"] + dur))
    log(f"  {scene['id']}: dùng đoạn {wins[pick]['start']:.1f}s–{wins[pick]['start'] + dur:.1f}s")


def fill_video(pid: str, scene: dict, used_urls: set, used_windows: dict, log,
               query: str | None = None, url: str | None = None, recent: str | None = None) -> None:
    sources = P.pdir(pid) / "sources"
    sources.mkdir(exist_ok=True)
    if url:
        results = [{"url": url, "title": url}]
    else:
        q = query or scene.get("video_query") or scene.get("image_query")
        results = search_videos(q, recent=recent)
        scene["video_results"] = results
        # tránh dùng lại cùng một video quá nhiều lần
        results = sorted(results, key=lambda r: r["url"] in used_urls)
    last_err = None
    for r in results[:3]:
        try:
            v = download_video(r["url"], sources, log)
            if HL.probe_duration(v) < P.scene_est_sec(scene) + 1:
                continue
            choose_clip(pid, scene, v, r["url"], used_windows, log)
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
