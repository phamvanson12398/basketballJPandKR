"""Ghép video cuối cùng bằng FFmpeg.

Bố cục "sports" (giống video mẫu): nền trắng, khung ảnh/video ở giữa, sub chữ đen đậm
TRÊN/DƯỚI khung. Các thể loại khác dùng bố cục chuyển động trong layouts.py.
Mọi phần dựng (ảnh, video, khung trống) nhận "g" = vị trí/màu nền của bố cục.
"""
import functools
import random
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from . import project as P
from .config import (FONTS, FPS, H, ROOT, SUB_LINE_SPACING, W, ffmpeg_bin, ffprobe_bin,
                     layout, load_settings, BGM)
from . import layouts as LAY
from .media import n_images_for

ZOOM_SCALE = 3  # ảnh chuẩn bị ở 3x để zoom mượt, không giật


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("FFmpeg lỗi:\n" + (r.stderr or "")[-1500:])


@functools.lru_cache(maxsize=1)
def encoder() -> str:
    pref = load_settings().get("video_encoder", "auto")
    if pref in ("libx264", "h264_nvenc"):
        return pref
    r = subprocess.run([ffmpeg_bin(), "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.2",
                        "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True)
    return "h264_nvenc" if r.returncode == 0 else "libx264"


def venc(final: bool) -> list[str]:
    if encoder() == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19" if final else "17",
                "-b:v", "0", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "medium" if final else "veryfast", "-crf", "19" if final else "16",
            "-pix_fmt", "yuv420p"]


# ------------------------------------------------------------------ ảnh
def prepare_image(src: Path, dst: Path, g: dict) -> Path:
    """Đưa ảnh vào khung (không làm mờ).
    Ảnh ngang (16:9...) được phóng cho kín khung, chỉ hụt chút ít ở mép trái/phải.
    Ảnh dọc/vuông (do bạn tự upload) được đặt giữa, phần thừa để nền trắng."""
    tw, th = g["w"] * ZOOM_SCALE, g["h"] * ZOOM_SCALE
    im = Image.open(src).convert("RGB")
    ar = im.width / im.height
    if ar >= (tw / th) * 0.97:
        s = max(tw / im.width, th / im.height)
        r = im.resize((max(tw, round(im.width * s)), max(th, round(im.height * s))), Image.LANCZOS)
        x, y = (r.width - tw) // 2, (r.height - th) // 2
        out = r.crop((x, y, x + tw, y + th))
    else:
        s = min(tw / im.width, th / im.height)
        fg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        out = Image.new("RGB", (tw, th), "white")
        out.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2))
    out.save(dst, "JPEG", quality=93)
    return dst


def compose(g: dict, n: int) -> str:
    """[m] (khung media) → đặt lên nền màu của bố cục → [v]. Tiểu sử: viền trắng + rơi nhẹ, nghiêng."""
    f = g["frame"]
    pre, lab = "", "m"
    x, y = g["x"] - f, g["y"] - f
    if f:
        pre += f"[{lab}]pad=iw+{2 * f}:ih+{2 * f}:{f}:{f}:white[mf];"
        lab = "mf"
    if g["drop"]:
        pre += f"[{lab}]rotate=a='-0.035*max(0,1-t/0.35)':c={g['bg']}:ow=iw:oh=ih[mr];"
        lab = "mr"
        ypos = f"'{y}-28*max(0,1-t/0.35)'"
    else:
        ypos = str(y)
    return (pre + f"color={g['bg']}:s={W}x{H}:r={FPS}:d={n / FPS + 1:.3f}[bg];"
            f"[bg][{lab}]overlay={x}:{ypos}:shortest=1:eval=frame,format=yuv420p[v]")


def image_part(img: Path, dur: float, out: Path, variant: int, g: dict) -> None:
    n = max(2, round(dur * FPS))
    N = n - 1
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z, x, y = [
        (f"1+0.08*on/{N}", cx, cy),                 # zoom vào
        (f"1.08-0.08*on/{N}", cx, cy),              # zoom ra
        ("1.06", f"(iw-iw/zoom)*on/{N}", cy),       # lia trái → phải
        (f"1+0.08*on/{N}", cx, cy),                 # zoom vào
        ("1.06", f"(iw-iw/zoom)*(1-on/{N})", cy),   # lia phải → trái
        (f"1.08-0.08*on/{N}", cx, cy),              # zoom ra
    ][variant % 6]
    if not load_settings().get("image_zoom"):
        z, x, y = "1", "0", "0"   # ảnh đứng yên, hiện trọn vẹn (giống video mẫu)
    fc = (f"[0:v]zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={g['w']}x{g['h']}:fps={FPS},setsar=1[m];"
          + compose(g, n))
    run([ffmpeg_bin(), "-v", "error", "-y", "-i", str(img), "-filter_complex", fc, "-map", "[v]",
         "-frames:v", str(n), "-r", str(FPS), *venc(False), "-an", str(out)])


# ------------------------------------------------------------------ video
def video_part(src: Path, start: float, dur: float, out: Path, g: dict) -> None:
    n = max(2, round(dur * FPS))
    from .highlight import video_size
    w, h = video_size(src)
    if not w:
        w, h = 1920, 1080
    box = f"{g['w']}:{g['h']}"
    if w / max(h, 1) >= (g['w'] / g['h']) * 0.8:
        media = (f"[0:v]fps={FPS},scale={box}:force_original_aspect_ratio=increase,"
                 f"crop={box},setsar=1,tpad=stop_mode=clone:stop_duration={dur + 1:.2f}[m];")
    else:  # video dọc (link TikTok bạn dán) → đặt giữa khung, nền trắng, không làm mờ
        media = (f"[0:v]fps={FPS},scale={box}:force_original_aspect_ratio=decrease,"
                 f"pad={box}:(ow-iw)/2:(oh-ih)/2:{g['bg']},setsar=1,"
                 f"tpad=stop_mode=clone:stop_duration={dur + 1:.2f}[m];")
    fc = media + compose(g, n)
    run([ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", str(src),
         "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n), "-r", str(FPS), *venc(False), "-an",
         str(out)])


def blank_part(dur: float, out: Path, g: dict | None = None) -> None:
    n = max(2, round(dur * FPS))
    bg = (g or {}).get("bg", "white")
    run([ffmpeg_bin(), "-v", "error", "-y", "-f", "lavfi", "-i", f"color={bg}:s={W}x{H}:r={FPS}",
         "-frames:v", str(n), *venc(False), str(out)])


# ------------------------------------------------------------------ sub
def ass_time(t: float) -> str:
    cs = int(round(max(0, t) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_escape(s: str) -> str:
    return s.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", "\\N")


def auto_wrap(chunk: str, maxlen: int = 11) -> str:
    """Tự xuống dòng nếu chunk chưa có dấu xuống dòng.
    Tiếng Hàn (có dấu cách): ngắt giữa các từ. Tiếng Nhật: ngắt theo số ký tự."""
    if "\n" in chunk or len(chunk) <= maxlen:
        return chunk
    if " " in chunk.strip():
        maxlen = 12
        lines, cur = [], ""
        for word in chunk.split():
            if cur and len(cur) + 1 + len(word) > maxlen:
                lines.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}".strip()
        if cur:
            lines.append(cur)
        return "\n".join(lines)
    lines, cur = [], ""
    for ch in chunk:
        cur += ch
        if len(cur) >= maxlen and ch not in "」』）、。！？":
            lines.append(cur)
            cur = ""
    if cur:
        if len(cur) <= 2 and lines:
            lines[-1] += cur
        else:
            lines.append(cur)
    return "\n".join(lines)


def build_ass(scenes: list[dict], starts: list[float], out: Path) -> None:
    st = load_settings()
    font, size = st.get("subtitle_font"), int(st.get("subtitle_size", 124))
    lh = size * SUB_LINE_SPACING
    L = layout()
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Top,{font},{size},&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,2,0,1,0,0,2,20,20,0,1
Style: Bottom,{font},{size},&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,2,0,1,0,0,8,20,20,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for sc, t0 in zip(scenes, starts):
        chunks = [auto_wrap(c.strip()) for c in sc.get("chunks", []) if c.strip()]
        if not chunks:
            continue
        speech = max(0.3, float(sc["duration"]) - 0.18)
        weights = [max(1, len(c.replace("\n", "").replace(" ", ""))) for c in chunks]
        tot = sum(weights)
        bounds, acc = [], t0
        for wgt in weights:
            bounds.append((acc, acc + speech * wgt / tot))
            acc += speech * wgt / tot
        end_scene = t0 + float(sc["duration"])
        # cặp (trên, dưới): chunk lẻ ở trên, chunk chẵn hiện thêm ở dưới
        for i in range(0, len(chunks), 2):
            a0 = bounds[i][0]
            last = min(i + 1, len(chunks) - 1)
            a1 = bounds[last][1] if last < len(chunks) - 1 else end_scene
            # mỗi dòng là 1 sự kiện riêng để tự kiểm soát khoảng cách dòng
            lines = chunks[i].split("\n")
            for k, line in enumerate(lines):
                y = L['sub_top'] - (len(lines) - 1 - k) * lh
                ev.append(f"Dialogue: 0,{ass_time(a0)},{ass_time(a1)},Top,,0,0,0,,"
                          f"{{\\pos({W // 2},{y:.0f})}}{ass_escape(line)}")
            if i + 1 < len(chunks):
                for k, line in enumerate(chunks[i + 1].split("\n")):
                    y = L['sub_bottom'] + k * lh
                    ev.append(f"Dialogue: 0,{ass_time(bounds[i + 1][0])},{ass_time(a1)},Bottom,,0,0,0,,"
                              f"{{\\pos({W // 2},{y:.0f})}}{ass_escape(line)}")
    out.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ main
def render(pid: str, log) -> None:
    import soundfile as sf

    p = P.load(pid)
    base = P.pdir(pid)
    rdir = base / "render"
    if rdir.exists():
        shutil.rmtree(rdir)
    rdir.mkdir()
    scenes = p["scenes"]
    missing = [s["id"] for s in scenes if not s.get("audio") or not (base / s["audio"]).exists()]
    if missing:
        raise RuntimeError(f"Các cảnh chưa có giọng đọc: {', '.join(missing)}")
    lay = LAY.resolve(p)
    g = LAY.geometry(lay)
    log(f"Bộ mã hóa video: {encoder()} · bố cục: {lay}")

    # 1) ghép giọng đọc
    audios = []
    for s in scenes:
        a, sr = sf.read(base / s["audio"], dtype="float32")
        if a.ndim > 1:
            a = a.mean(axis=1)
        audios.append(a)
        s["duration"] = len(a) / sr
    narration = np.concatenate(audios + [np.zeros(int(sr * 0.6), dtype=np.float32)])
    sf.write(rdir / "narration.wav", narration, sr)
    total = len(narration) / sr

    # 2) từng phần hình
    parts, starts, t = [], [], 0.0
    variant = random.randint(0, 3)
    for si, s in enumerate(scenes):
        starts.append(t)
        D = float(s["duration"]) + (0.6 if si == len(scenes) - 1 else 0)
        items = s.get("items") or []
        log(f"Dựng cảnh {s['id']} ({D:.1f}s)", 0.05 + 0.75 * si / len(scenes))
        if not items:
            pieces = [("blank", None, D)]
        elif items[0]["kind"] == "video":
            pieces = [("video", items[0], D)]
        else:
            k = n_images_for(D)
            imgs = [items[i % len(items)] for i in range(k)]
            pieces = [("image", it, D / k) for it in imgs]
        for kind, it, d in pieces:
            out = rdir / f"part_{len(parts):03d}.mp4"
            try:
                if kind == "image":
                    prep = prepare_image(base / it["file"], rdir / f"img_{len(parts):03d}.jpg", g)
                    image_part(prep, d, out, variant, g)
                    variant += 1
                elif kind == "video":
                    video_part(base / it["file"], float(it.get("start", 0)), d, out, g)
                else:
                    blank_part(d, out, g)
            except Exception as e:  # noqa: BLE001
                log(f"  ⚠️ lỗi dựng {s['id']}: {e} → để trống")
                blank_part(d, out, g)
            parts.append(out)
        t += float(s["duration"])

    lst = rdir / "parts.txt"
    lst.write_text("".join(f"file '{x.name}'\n" for x in parts), encoding="utf-8")
    run([ffmpeg_bin(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "parts.txt",
         "-c", "copy", "video.mp4"], cwd=rdir)

    # 3) sub + chữ/hiệu ứng của bố cục
    if lay == "sports":
        build_ass(scenes, starts, rdir / "subs.ass")
    else:
        LAY.build_ass(lay, p, scenes, starts, total, rdir / "subs.ass")

    # 4) trộn nhạc nền + chèn sub + xuất
    log("Chèn sub, trộn nhạc nền và xuất video cuối...", 0.85)
    rel = rdir.relative_to(ROOT).as_posix()
    fonts_rel = FONTS.relative_to(ROOT).as_posix()
    cmd = [ffmpeg_bin(), "-v", "error", "-y", "-i", f"{rel}/video.mp4", "-i", f"{rel}/narration.wav"]
    bgm = p.get("bgm", {})
    bgm_file = BGM / bgm["file"] if bgm.get("file") else None
    if bgm_file and bgm_file.exists():
        vol = float(bgm.get("volume", 0.15))
        cmd += ["-stream_loop", "-1", "-i", str(bgm_file)]
        afc = (f"[2:a]volume={vol:.3f},afade=t=in:d=0.5,afade=t=out:st={max(0, total - 2):.2f}:d=2[b];"
               f"[1:a][b]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        afc = "[1:a]anull[a]"
    fc = f"[0:v]ass={rel}/subs.ass:fontsdir={fonts_rel}[v];{afc}"
    safe_title = re.sub(r'[\\/:*?"<>|]+', "_", p.get("title") or p["id"])[:60].strip() or p["id"]
    final_rel = f"{rel}/{safe_title}.mp4"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", *venc(True), "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.3f}",
            "-movflags", "+faststart", final_rel]
    run(cmd, cwd=ROOT)
    for f in rdir.glob("part_*.mp4"):
        f.unlink()
    for f in rdir.glob("img_*.jpg"):
        f.unlink()
    out_rel = Path(final_rel).relative_to(base.relative_to(ROOT)).as_posix()
    P.update(pid, lambda pp: pp.__setitem__("output", out_rel))
    log(f"Đã xuất: projects/{pid}/{out_rel} ({total:.1f}s)", 1.0)
