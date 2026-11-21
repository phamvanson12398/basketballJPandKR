"""Lưu / đọc dự án (mỗi video là một thư mục trong projects/)."""
import json
import re
import threading
import time
import uuid
from pathlib import Path

from . import languages as LG
from .config import PROJECTS, VIDEO_RATIO

_lock = threading.RLock()


def new_id(title: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:4]}"


def pdir(pid: str) -> Path:
    if not re.fullmatch(r"[\w\-]+", pid):
        raise ValueError("id không hợp lệ")
    return PROJECTS / pid


def create(title: str, topic: str, duration: int, genre: str = "sports", video_pct: int = 30,
           news: dict | None = None, lang: str = "ja", ranking_n: int | None = None,
           sport: str = "other") -> dict:
    pid = new_id(title)
    d = pdir(pid)
    for sub in ("audio", "media", "sources", "render"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    p = {
        "id": pid,
        "title": title.strip(),
        "topic": topic.strip(),
        "duration": int(duration),
        "genre": genre if genre in ("sports", "biography", "general", "news", "ranking") else "sports",
        "ranking_n": max(3, min(10, int(ranking_n))) if genre == "ranking" and ranking_n else None,
        "sport": sport or "other",   # môn thể thao: baseball / basketball / sumo / soccer / other
        "news": news or {},       # tin tức: {region, days, category}
        "lang": lang if lang in LG.LANGS else LG.DEFAULT,   # ngôn ngữ video
        "video_pct": max(0, min(100, int(video_pct))),
        "created": time.time(),
        "script_approved": False,
        "scenes": [],
        "voice": {"mode": "clone", "voice": "", "instruct": "", "speed": 1.0},
        "bgm": {"file": "__auto__", "volume": 0.15},   # nhạc nền tự chọn theo thể loại
        "output": "",
    }
    save(p)
    return p


def load(pid: str) -> dict:
    with _lock:
        return json.loads((pdir(pid) / "project.json").read_text(encoding="utf-8"))


def save(p: dict) -> None:
    with _lock:
        f = pdir(p["id"]) / "project.json"
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(f)


def update(pid: str, fn) -> dict:
    """Đọc – sửa – ghi an toàn giữa các luồng."""
    with _lock:
        p = load(pid)
        fn(p)
        save(p)
        return p


def list_all() -> list[dict]:
    out = []
    for f in sorted(PROJECTS.glob("*/project.json"), reverse=True):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            out.append({"id": p["id"], "title": p.get("title") or p.get("topic", ""),
                        "duration": p.get("duration"), "output": p.get("output", "")})
        except Exception:
            continue
    return out


def scene_plain_text(scene: dict) -> str:
    return "".join(c.replace("\n", "") for c in scene.get("chunks", []))


def scene_est_sec(scene: dict) -> float:
    if scene.get("duration"):
        return float(scene["duration"])
    # đếm theo chữ hiển thị (kanji + kana), không theo câu đọc (hiragana dài hơn nhiều)
    text = scene_plain_text(scene) or scene.get("tts") or ""
    return max(1.0, LG.est_seconds(text))


def video_ratio(p: dict) -> float:
    """Tỉ lệ video mong muốn của dự án (0.0–1.0)."""
    v = p.get("video_pct")
    return VIDEO_RATIO if v is None else max(0, min(100, int(v))) / 100


def rebalance(scenes: list[dict], ratio: float = VIDEO_RATIO) -> None:
    """Chọn cảnh nào dùng video để video chiếm đúng tỉ lệ mong muốn (mặc định 30%).

    Ưu tiên cảnh có điểm hành động (action) cao. Cảnh bị khóa (locked_kind)
    thì giữ nguyên lựa chọn của người dùng.
    """
    total = sum(scene_est_sec(s) for s in scenes) or 1
    target = total * ratio
    locked_video = sum(scene_est_sec(s) for s in scenes
                       if s.get("locked_kind") and s.get("kind") == "video")
    free = [s for s in scenes if not s.get("locked_kind")]
    for s in free:
        s["kind"] = "image"
    acc = locked_video
    # cảnh đầu (hook) ưu tiên VIDEO: 1–2 giây đầu có chuyển động giữ người xem tốt hơn ảnh tĩnh
    if ratio > 0 and scenes and not scenes[0].get("locked_kind"):
        scenes[0]["kind"] = "video"
        acc += scene_est_sec(scenes[0])
    order = sorted((s for s in free if s is not scenes[0]),
                   key=lambda s: (-(s.get("action") or 0), scenes.index(s)))
    for s in order:
        d = scene_est_sec(s)
        if acc >= target:
            break
        # chỉ thêm nếu đưa tổng tới gần mục tiêu hơn
        if abs(acc + d - target) < abs(acc - target):
            s["kind"] = "video"
            acc += d


def ratio_info(scenes: list[dict]) -> dict:
    total = sum(scene_est_sec(s) for s in scenes) or 1
    vid = sum(scene_est_sec(s) for s in scenes if s.get("kind") == "video")
    return {"total": round(total, 1), "video": round(vid, 1),
            "video_pct": round(100 * vid / total), "image_pct": round(100 - 100 * vid / total)}
