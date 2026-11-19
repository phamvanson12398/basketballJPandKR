"""Tìm và tải ảnh / video cho từng cảnh.

Ảnh : DuckDuckGo Images (không cần key) hoặc Google Custom Search (nếu có key)
Video: YouTube (yt-dlp tìm kiếm). Bạn cũng có thể dán link YouTube / X / TikTok /
       Instagram / Facebook... cho từng cảnh, yt-dlp tải được hầu hết các nền tảng.
"""
import hashlib
import io
from pathlib import Path

import requests
from PIL import Image

from . import highlight as HL
from . import project as P
from .config import IMAGE_RATIO, IMAGE_RATIO_TOL, IMAGE_SEC, load_settings

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
N_CANDIDATES = 8


# ---------------------------------------------------------------- ẢNH
def is_16_9(w: int, h: int) -> bool:
    return h > 0 and abs((w / h) / IMAGE_RATIO - 1) <= IMAGE_RATIO_TOL


def search_images(query: str, n: int = 80) -> list[dict]:
    s = load_settings()
    out: list[dict] = []
    if s.get("google_api_key") and s.get("google_cx"):
        try:
            for start in (1, 11):
                r = requests.get("https://www.googleapis.com/customsearch/v1", timeout=20, params={
                    "key": s["google_api_key"], "cx": s["google_cx"], "q": query,
                    "searchType": "image", "num": 10, "start": start, "gl": "jp", "hl": "ja",
                    "imgSize": "xlarge"})
                for it in r.json().get("items", []):
                    im = it.get("image", {})
                    out.append({"url": it["link"], "w": im.get("width", 0), "h": im.get("height", 0),
                                "title": it.get("title", ""), "page": im.get("contextLink", "")})
        except Exception:
            pass
    if sum(is_16_9(x["w"], x["h"]) for x in out) < 6:
        from ddgs import DDGS
        try:
            for it in DDGS().images(query, region="jp-jp", safesearch="off", layout="Wide",
                                    max_results=n):
                out.append({"url": it.get("image"), "w": int(it.get("width") or 0),
                            "h": int(it.get("height") or 0), "title": it.get("title", ""),
                            "page": it.get("url", "")})
        except Exception:
            pass

    seen, uniq = set(), []
    for x in out:
        # chỉ giữ ảnh 16:9 (theo thông tin kích thước của kết quả tìm kiếm; tải về sẽ kiểm tra lại)
        if x["url"] and x["url"] not in seen and (not x["w"] or is_16_9(x["w"], x["h"])):
            seen.add(x["url"])
            uniq.append(x)
    # ưu tiên ảnh có kích thước rõ ràng và lớn
    return sorted(uniq, key=lambda x: (not x["w"], -min(x["w"] or 0, 2560)))


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": url}, timeout=20)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im = im.convert("RGB")
        if im.width < 640 or not is_16_9(*im.size):
            return False   # chỉ nhận ảnh 16:9, đủ nét
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=92)
        return True
    except Exception:
        return False


def n_images_for(dur: float) -> int:
    return max(1, round(dur / IMAGE_SEC))


def fill_images(pid: str, scene: dict, used: set, log, query: str | None = None) -> None:
    q = query or scene.get("image_query") or P.scene_plain_text(scene)
    d = P.pdir(pid) / "media" / scene["id"]
    if d.exists():
        for f in d.glob("c*.jpg"):
            f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    cands = []
    for res in search_images(q):
        if res["url"] in used:
            continue
        f = d / f"c{len(cands) + 1}.jpg"
        if download_image(res["url"], f):
            cands.append({"kind": "image", "file": f"media/{scene['id']}/{f.name}", "url": res["url"],
                          "page": res.get("page", "")})
            used.add(res["url"])
        if len(cands) >= N_CANDIDATES:
            break
    if not cands:
        raise RuntimeError(f"Không tìm được ảnh 16:9 cho “{q}” – thử từ khóa khác")
    k = n_images_for(P.scene_est_sec(scene))
    scene["candidates"] = cands
    scene["items"] = cands[:k]
    log(f"  {scene['id']}: {len(cands)} ảnh ứng viên, dùng {len(scene['items'])} ảnh")


# ---------------------------------------------------------------- VIDEO
def search_videos(query: str, n: int = 8) -> list[dict]:
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "extract_flat": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    out = []
    for e in info.get("entries", []) or []:
        dur = e.get("duration") or 0
        if e.get("live_status") in ("is_live", "is_upcoming"):
            continue
        if dur and not (15 <= dur <= 1800):
            continue
        if "/shorts/" in (e.get("url") or ""):
            continue   # bỏ YouTube Shorts (video dọc)
        out.append({"id": e.get("id"), "title": e.get("title", ""), "duration": dur,
                    "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"})
    return out


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
               query: str | None = None, url: str | None = None) -> None:
    sources = P.pdir(pid) / "sources"
    sources.mkdir(exist_ok=True)
    if url:
        results = [{"url": url, "title": url}]
    else:
        q = query or scene.get("video_query") or scene.get("image_query")
        results = search_videos(q)
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
def fill_all(pid: str, log, only: list[str] | None = None, query: str | None = None,
             url: str | None = None) -> None:
    p = P.load(pid)
    scenes = p["scenes"]
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
                    fill_video(pid, s, used_urls, used_windows, log, query=query, url=url)
                except Exception as e:  # noqa: BLE001
                    if url:
                        raise
                    log(f"  ⚠️ {e} → dùng ảnh thay thế")
                    fill_images(pid, s, used, log)
            else:
                fill_images(pid, s, used, log, query=query)
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
