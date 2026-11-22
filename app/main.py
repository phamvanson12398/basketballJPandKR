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
                    data.get("news") if genre == "news" else None, data.get("lang") or "ja",
                    data.get("ranking_n"), data.get("sport") or "other")


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = P.load(pid)
    p["ratio"] = P.ratio_info(p["scenes"]) if p["scenes"] else None
    p["job"] = jobs.get(pid)
    from .bgm_gen import resolve as resolve_bgm
    p["bgm_resolved"] = resolve_bgm(p)
    return p


@app.put("/api/projects/{pid}")
def put_project(pid: str, data: dict = Body(...)):
    """Lưu chỉnh sửa content / giọng / nhạc nền từ giao diện."""
    def apply(p):
        for k in ("title", "topic", "duration", "voice", "bgm", "script_approved", "genre", "video_pct", "news", "tiktok", "lang", "ranking_n",
                  "screen", "layout", "sport"):
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
                                               "action", "locked_kind", "story", "rank", "rank_label",
                                               "year", "chapter", "banzuke", "name", "record",
                                               "kimarite", "score", "minute", "player", "team",
                                               "stat", "split", "image_query2", "who", "query_alt", "uniform", "call") if k in s})
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
    from .languages import LANGS
    from .script_gen import NEWS_REGIONS, NEWS_CATEGORIES, SPORTS
    return {"regions": NEWS_REGIONS, "categories": NEWS_CATEGORIES,
            "sports": [{"id": k, "vi": v["vi"]} for k, v in SPORTS.items()],
            "langs": [{"id": k, "vi": v["vi"]} for k, v in LANGS.items()]}


@app.post("/api/news/suggest")
def news_suggest(data: dict = Body(...)):
    """Quét tin mới nhất của quốc gia / thế giới (mất khoảng 1–2 phút)."""
    from .script_gen import suggest_news
    try:
        return suggest_news(data.get("region") or "world", int(data.get("days") or 3),
                            data.get("category") or "all", data.get("custom_region") or "",
                            data.get("lang") or "ja")
    except Exception as e:  # noqa: BLE001
        _err(e)


@app.post("/api/projects/{pid}/twin")
def make_twin(pid: str, data: dict = Body(...)):
    """Tạo bản ngôn ngữ khác của video này, dùng lại ảnh/video."""
    from .extras import create_twin, localize
    try:
        p = create_twin(pid, data.get("lang") or "ko")
    except Exception as e:  # noqa: BLE001
        _err(e)
    jobs.start(p["id"], "script", localize)
    return {"id": p["id"]}


@app.post("/api/ideas")
def ideas(data: dict = Body(...)):
    """Claude gợi ý ý tưởng video (mất khoảng 1–2 phút)."""
    from .extras import suggest_ideas
    try:
        return suggest_ideas(data.get("lang") or "ja", data.get("niche") or "", data.get("genre") or "any",
                             int(data.get("count") or 10))
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


@app.post("/api/projects/{pid}/tiktok")
def gen_tiktok(pid: str):
    from .script_gen import gen_tiktok as fn
    try:
        return jobs.start(pid, "tiktok", fn)
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
        s["picked"] = True          # bạn đã tự chọn → khi xuất video chỉ dùng đúng những gì đã chọn
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


@app.post("/api/projects/{pid}/scenes/{sid}/crop")
def crop_image(pid: str, sid: str, data: dict = Body(...)):
    """Cắt ảnh: data = {file, x, y, w, h} (tỉ lệ 0–1 theo ảnh gốc). Ảnh gốc được giữ lại."""
    import hashlib
    from PIL import Image
    base = P.pdir(pid)
    p = P.load(pid)
    sc = next((x for x in p["scenes"] if x["id"] == sid), None)
    if not sc:
        _err(ValueError("Không thấy cảnh"))
    old = data.get("file", "")
    cand = next((c for c in (sc.get("candidates") or []) + (sc.get("items") or [])
                 if c.get("file") == old and c.get("kind") == "image"), None)
    if not cand:
        _err(ValueError("Không thấy ảnh này trong cảnh"))
    # luôn cắt từ ảnh GỐC (cắt lại nhiều lần không bị mờ dần)
    src_rel = cand.get("cropped_from") or old
    src = (base / src_rel).resolve()
    if base.resolve() not in src.parents or not src.exists():
        _err(ValueError("Không thấy file ảnh gốc"))
    im = Image.open(src).convert("RGB")
    fx = max(0.0, min(1.0, float(data.get("x", 0))))
    fy = max(0.0, min(1.0, float(data.get("y", 0))))
    fw = max(0.02, min(1.0 - fx, float(data.get("w", 1))))
    fh = max(0.02, min(1.0 - fy, float(data.get("h", 1))))
    box = (round(fx * im.width), round(fy * im.height), round((fx + fw) * im.width), round((fy + fh) * im.height))
    out = im.crop(box)
    if out.width < 200 or out.height < 120:
        _err(ValueError("Vùng cắt quá nhỏ, kéo rộng ra một chút nhé"))
    tag = hashlib.md5(f"{src_rel}{box}".encode()).hexdigest()[:8]
    new_rel = f"media/{sid}/crop_{tag}.jpg"
    (base / "media" / sid).mkdir(parents=True, exist_ok=True)
    out.save(base / new_rel, "JPEG", quality=93)

    def apply(pp):
        s = next(x for x in pp["scenes"] if x["id"] == sid)
        for lst in ("candidates", "items"):
            s[lst] = [dict(c, file=new_rel, cropped_from=src_rel) if c.get("file") == old else c
                      for c in (s.get(lst) or [])]
    return P.update(pid, apply)


@app.post("/api/projects/{pid}/scenes/{sid}/uncrop")
def uncrop_image(pid: str, sid: str, data: dict = Body(...)):
    """Trả ảnh đã cắt về ảnh gốc."""
    old = data.get("file", "")

    def apply(pp):
        s = next(x for x in pp["scenes"] if x["id"] == sid)
        for lst in ("candidates", "items"):
            s[lst] = [({k: v for k, v in c.items() if k != "cropped_from"} | {"file": c["cropped_from"]})
                      if c.get("file") == old and c.get("cropped_from") else c for c in (s.get(lst) or [])]
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
            s["picked"] = True
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
        s["picked"] = True
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
    files = [f.name for f in sorted(BGM.iterdir()) if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac")]
    # nhạc của tool lên đầu, nhạc bạn upload ở sau
    return sorted(files, key=lambda x: (not x.endswith("(tool).m4a"), x))


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
@app.post("/api/google/verify")
def google_verify():
    """Mở Google trong cửa sổ Chrome thật để bạn tích "Tôi không phải robot" (chạy nền)."""
    import threading
    from . import google_images as GI
    from . import image_sources as S

    def run():
        if GI.open_for_verify() == "ok":
            S._paused_until.pop("google", None)     # xác minh xong → bỏ tạm nghỉ Google
    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


# ---------------------------------------------------------------- thư viện kịch bản mẫu
@app.get("/api/refs")
def refs_list():
    from . import refs as REFS
    return REFS.load()


@app.post("/api/refs")
def refs_add(data: dict = Body(...)):
    from . import refs as REFS
    try:
        return REFS.add(data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/refs/{rid}")
def refs_delete(rid: str):
    from . import refs as REFS
    REFS.delete(rid)
    return {"ok": True}


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


class NoCacheFiles(StaticFiles):
    """Ảnh/video của dự án hay bị thay (tìm lại, cắt ảnh…) → bắt trình duyệt hỏi lại mỗi lần,
    không hiện nhầm bản cũ trong bộ nhớ đệm (file không đổi thì trả 304, vẫn nhanh)."""
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


app.mount("/files", NoCacheFiles(directory=PROJECTS), name="files")
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
    def make_bgm():
        try:
            from .bgm_gen import ensure_all
            n = ensure_all(log=lambda msg: print(msg, flush=True))
            if n:
                print(f"  Đã soạn xong {n} bài nhạc nền.", flush=True)
        except Exception as e:  # noqa: BLE001
            print("  Không tạo được nhạc nền:", e, flush=True)
    threading.Thread(target=make_bgm, daemon=True).start()   # lần đầu mất ~2 phút, chạy nền
    if not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
