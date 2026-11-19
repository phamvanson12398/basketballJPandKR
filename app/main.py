"""Server web: chạy `python -m app.main` rồi mở http://127.0.0.1:7860"""
import re
import shutil
import webbrowser
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import jobs
from . import media as M
from . import project as P
from .config import BGM, FONTS, PROJECTS, STATIC, VOICES, load_settings, save_settings

app = FastAPI(title="Shorts Maker")


def _safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("._")
    return name[:60] or "file"


def _err(e: Exception):
    raise HTTPException(400, str(e))


# ---------------------------------------------------------------- dự án
@app.get("/api/projects")
def projects():
    return P.list_all()


@app.post("/api/projects")
def create_project(data: dict = Body(...)):
    title, topic = data.get("title", ""), data.get("topic", "")
    genre = data.get("genre") or "sports"
    if genre != "news" and not title.strip() and not topic.strip():
        _err(ValueError("Nhập title hoặc chủ đề nhé"))
    return P.create(title, topic, int(data.get("duration") or 60), genre,
                    int(data.get("video_pct") if data.get("video_pct") is not None else 30),
                    data.get("news") if genre == "news" else None)


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = P.load(pid)
    p["ratio"] = P.ratio_info(p["scenes"]) if p["scenes"] else None
    p["job"] = jobs.get(pid)
    return p


@app.put("/api/projects/{pid}")
def put_project(pid: str, data: dict = Body(...)):
    """Lưu chỉnh sửa content / giọng / nhạc nền từ giao diện."""
    def apply(p):
        for k in ("title", "topic", "duration", "voice", "bgm", "script_approved", "genre", "video_pct", "news"):
            if k in data:
                p[k] = data[k]
        if "scenes" in data:
            old = {s["id"]: s for s in p["scenes"]}
            new = []
            for i, s in enumerate(data["scenes"]):
                sid = s.get("id") or f"n{i}"
                base = dict(old.get(sid, {}))
                text_changed = (base.get("chunks") != s.get("chunks") or base.get("tts") != s.get("tts"))
                base.update({k: s[k] for k in ("chunks", "tts", "kind", "image_query", "video_query",
                                               "action", "locked_kind") if k in s})
                base["id"] = sid
                if text_changed and base.get("audio"):
                    base["audio_stale"] = True  # cần đọc lại
                new.append(base)
            ids = {s["id"] for s in new}
            for i, s in enumerate(new):  # id mới cho cảnh thêm
                if s["id"].startswith("n"):
                    k = 1
                    while f"s{k:02d}" in ids:
                        k += 1
                    s["id"] = f"s{k:02d}"
                    ids.add(s["id"])
            p["scenes"] = new
    return P.update(pid, apply)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    shutil.rmtree(P.pdir(pid), ignore_errors=True)
    return {"ok": True}


@app.post("/api/projects/{pid}/rebalance")
def rebalance(pid: str):
    return P.update(pid, lambda p: P.rebalance(p["scenes"], P.video_ratio(p)))


@app.get("/api/projects/{pid}/job")
def job(pid: str):
    return jobs.get(pid)


# ---------------------------------------------------------------- các bước
@app.post("/api/projects/{pid}/script")
def gen_script(pid: str, data: dict = Body(default={})):
    from .script_gen import generate
    try:
        return jobs.start(pid, "script", generate, feedback=data.get("feedback", ""))
    except RuntimeError as e:
        _err(e)


@app.get("/api/news/regions")
def news_regions():
    from .script_gen import NEWS_REGIONS, NEWS_CATEGORIES
    return {"regions": NEWS_REGIONS, "categories": NEWS_CATEGORIES}


@app.post("/api/news/suggest")
def news_suggest(data: dict = Body(...)):
    """Quét tin mới nhất của quốc gia / thế giới (mất khoảng 1–2 phút)."""
    from .script_gen import suggest_news
    try:
        return suggest_news(data.get("region") or "world", int(data.get("days") or 3),
                            data.get("category") or "all", data.get("custom_region") or "")
    except Exception as e:  # noqa: BLE001
        _err(e)


@app.post("/api/projects/{pid}/tts")
def gen_tts(pid: str, data: dict = Body(default={})):
    from .tts import synth
    try:
        return jobs.start(pid, "tts", synth, only=data.get("only"))
    except RuntimeError as e:
        _err(e)


@app.post("/api/projects/{pid}/media")
def gen_media(pid: str, data: dict = Body(default={})):
    try:
        return jobs.start(pid, "media", M.fill_all, only=data.get("only"),
                          query=data.get("query") or None, url=data.get("url") or None)
    except RuntimeError as e:
        _err(e)


@app.post("/api/projects/{pid}/render")
def gen_render(pid: str):
    from .render import render
    try:
        return jobs.start(pid, "render", render)
    except RuntimeError as e:
        _err(e)


@app.post("/api/projects/{pid}/scenes/{sid}/pick")
def pick(pid: str, sid: str, data: dict = Body(...)):
    """Chọn ảnh/đoạn video ứng viên. data = {index, mode: 'replace'|'toggle'}"""
    def apply(p):
        s = next(x for x in p["scenes"] if x["id"] == sid)
        items = s.get("items") or []
        cands = list(s.get("candidates") or [])
        for it in items:  # giống giao diện: mục đã chọn mà không có trong ứng viên thì đưa lên đầu
            if not any(c["file"] == it["file"] and c.get("start") == it.get("start") for c in cands):
                cands.insert(0, it)
        s["candidates"] = cands
        c = cands[int(data["index"])]
        if c["kind"] == "video" or not items or items[0]["kind"] == "video" or data.get("mode") == "replace":
            s["items"] = [c]
        else:
            files = [i["file"] for i in items]
            if c["file"] in files:
                if len(items) > 1:
                    s["items"] = [i for i in items if i["file"] != c["file"]]
            else:
                s["items"] = items + [c]
    return P.update(pid, apply)


@app.post("/api/projects/{pid}/scenes/{sid}/upload")
async def upload_scene(pid: str, sid: str, file: UploadFile = File(...)):
    data = await file.read()
    res = M.save_upload(pid, sid, file.filename or "x.jpg", data)
    if res["kind"] == "video_source":
        def job_fn(pid_, log):
            p = P.load(pid_)
            s = next(x for x in p["scenes"] if x["id"] == sid)
            s["kind"] = "video"
            s["locked_kind"] = True
            M.choose_clip(pid_, s, res["path"], "upload", {}, log)
            P.update(pid_, lambda pp: [pp["scenes"].__setitem__(i, s) for i, x in enumerate(pp["scenes"])
                                       if x["id"] == sid])
        return jobs.start(pid, "media", job_fn)

    def apply(p):
        s = next(x for x in p["scenes"] if x["id"] == sid)
        s.setdefault("candidates", []).insert(0, res)
        if s.get("kind") == "video":
            s["kind"] = "image"
            s["locked_kind"] = True
        s["items"] = [res]
    return P.update(pid, apply)


# ---------------------------------------------------------------- thư viện giọng & nhạc
@app.get("/api/voices")
def voices():
    from .tts import list_voices, VOICE_DESIGN_OPTIONS
    return {"voices": list_voices(), "design": VOICE_DESIGN_OPTIONS}


@app.post("/api/voices")
async def add_voice(name: str = Form(...), ref_text: str = Form(""), file: UploadFile = File(...)):
    n = _safe_name(name)
    ext = Path(file.filename or "a.wav").suffix.lower() or ".wav"
    for old in VOICES.glob(f"{n}.*"):
        old.unlink()
    (VOICES / f"{n}{ext}").write_bytes(await file.read())
    if ref_text.strip():
        (VOICES / f"{n}.txt").write_text(ref_text.strip(), encoding="utf-8")
    return {"name": n}


@app.delete("/api/voices/{name}")
def del_voice(name: str):
    for f in VOICES.glob(f"{_safe_name(name)}.*"):
        f.unlink()
    return {"ok": True}


@app.get("/api/bgm")
def bgm_list():
    return [f.name for f in sorted(BGM.iterdir()) if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac")]


@app.post("/api/bgm")
async def add_bgm(file: UploadFile = File(...)):
    p = Path(file.filename or "bgm.mp3")
    name = _safe_name(p.stem) + p.suffix.lower()
    (BGM / name).write_bytes(await file.read())
    return {"name": name}


@app.get("/library/{kind}/{name}")
def library_file(kind: str, name: str):
    base = {"voices": VOICES, "bgm": BGM}.get(kind)
    f = (base / name).resolve() if base else None
    if not f or base.resolve() not in f.parents or not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


# ---------------------------------------------------------------- cài đặt & kiểm tra
@app.get("/api/settings")
def settings():
    return load_settings()


@app.put("/api/settings")
def put_settings(data: dict = Body(...)):
    from . import render
    render.encoder.cache_clear()
    return save_settings(data)


@app.get("/api/check")
def check():
    out = {"ffmpeg": bool(shutil.which("ffmpeg")), "claude": bool(shutil.which("claude")),
           "font": any(FONTS.glob("*.otf")) or any(FONTS.glob("*.ttf"))}
    try:
        import torch
        out["cuda"] = torch.cuda.is_available()
        out["gpu"] = torch.cuda.get_device_name(0) if out["cuda"] else ""
    except Exception:
        out["cuda"], out["gpu"] = False, ""
    try:
        import omnivoice  # noqa: F401
        out["omnivoice"] = True
    except Exception:
        out["omnivoice"] = False
    return out


app.mount("/files", StaticFiles(directory=PROJECTS), name="files")
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


def main():
    import argparse
    import threading
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    url = f"http://127.0.0.1:{a.port}"
    print(f"\n  Mở trình duyệt: {url}\n")
    if not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
