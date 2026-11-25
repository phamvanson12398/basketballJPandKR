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
from . import markup as MK
from .config import SWITCH_SEC
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
def smart_offset(im: Image.Image, cw: int, ch: int) -> tuple[int, int]:
    """Chọn vị trí cắt (cw x ch trên ảnh im) giữ được người: ưu tiên vùng có màu da + nhiều chi tiết,
    hơi nghiêng lên nửa trên (mặt thường ở trên). Không cần model nhận diện khuôn mặt."""
    if cw >= im.width and ch >= im.height:
        return 0, 0
    sw = 160
    sc = sw / im.width
    small = im.resize((sw, max(1, round(im.height * sc))))
    a = np.asarray(small.convert("YCbCr"), dtype=np.float32)
    cb, cr = a[..., 1], a[..., 2]
    skin = ((cr > 135) & (cr < 180) & (cb > 85) & (cb < 135)).astype(np.float32)
    gray = a[..., 0]
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    detail = np.clip((gx + gy) / 60, 0, 1)
    hh = small.height
    rows = np.linspace(1.15, 0.75, hh)[:, None]        # nửa trên được ưu tiên hơn
    score = (1.8 * skin + detail) * rows
    integ = np.pad(score, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    w, h = max(1, round(cw * sc)), max(1, round(ch * sc))
    best, bx, by = -1.0, 0, 0
    for y in range(0, max(1, small.height - h + 1), 2):
        for x in range(0, max(1, sw - w + 1), 2):
            v = integ[y + h, x + w] - integ[y, x + w] - integ[y + h, x] + integ[y, x]
            # phạt nhẹ khi lệch xa giữa ảnh, tránh cắt sát mép không cần thiết
            v -= 0.02 * score.sum() * abs((x + w / 2) / sw - 0.5)
            if v > best:
                best, bx, by = v, x, y
    return (min(im.width - cw, max(0, round(bx / sc))), min(im.height - ch, max(0, round(by / sc))))


def prepare_image(src: Path, dst: Path, g: dict) -> Path:
    """Đưa ảnh vào khung (không làm mờ, không viền trắng).
    Mọi tỉ lệ (ngang / vuông / dọc) được phóng cho kín khung rồi cắt vào chỗ có người (smart_offset).
    Muốn giữ vùng khác thì dùng công cụ ✂️ Cắt ảnh."""
    tw, th = g["w"] * ZOOM_SCALE, g["h"] * ZOOM_SCALE
    im = Image.open(src).convert("RGB")
    s = max(tw / im.width, th / im.height)
    r = im.resize((max(tw, round(im.width * s)), max(th, round(im.height * s))), Image.LANCZOS)
    x, y = smart_offset(r, tw, th)     # cắt vào chỗ có người thay vì luôn cắt giữa
    out = r.crop((x, y, x + tw, y + th))
    out.save(dst, "JPEG", quality=93)
    return dst


def prepare_split(src1: Path, src2: Path, dst: Path, g: dict) -> Path:
    """2 ảnh đặt cạnh nhau (so sánh 2 người), mỗi nửa được cắt thông minh vào người."""
    gap = 6
    half = dict(g, w=(g["w"] - gap) // 2)
    a = Image.open(prepare_image(src1, dst.with_name(dst.stem + "_a.jpg"), half))
    b = Image.open(prepare_image(src2, dst.with_name(dst.stem + "_b.jpg"), half))
    out = Image.new("RGB", (g["w"] * ZOOM_SCALE, g["h"] * ZOOM_SCALE), "black")
    out.paste(a, (0, 0))
    out.paste(b, (out.width - b.width, 0))
    out.save(dst, "JPEG", quality=93)
    return dst


def compose(g: dict, n: int) -> str:
    """[m] (khung media) → đặt lên nền màu của bố cục → [v]. Tiểu sử: viền trắng + rơi nhẹ, nghiêng."""
    f = g["frame"]
    pre, lab = "", "m"
    x, y = g["x"] - f, g["y"] - f
    if f:
        pre += f"[{lab}]pad=iw+{2 * f}:ih+{2 * f}:{f}:{f}:{g.get('frame_color', 'white')}[mf];"
        lab = "mf"
    if g["drop"]:
        pre += f"[{lab}]rotate=a='-0.035*max(0,1-t/0.35)':c={g['bg']}:ow=iw:oh=ih[mr];"
        lab = "mr"
        ypos = f"'{y}-28*max(0,1-t/0.35)'"
    else:
        ypos = str(y)
    return (pre + f"color={g['bg']}:s={W}x{H}:r={FPS}:d={n / FPS + 1:.3f}[bg];"
            f"[bg][{lab}]overlay={x}:{ypos}:shortest=1:eval=frame,format=yuv420p[v]")


def _sticker_fc(sticker, src_label: str = "m0") -> tuple[list[str], str]:
    """Phủ sticker (đứng yên, hiện dần sau 0.3s) lên khung media. Trả về (tham số input thêm, đoạn filter → [m])."""
    if not sticker:
        return [], f"[{src_label}]null[m];"
    f, x, y = sticker
    return (["-framerate", str(FPS), "-loop", "1", "-i", str(f)],
            f"[1:v]format=rgba,fade=in:st=0.3:d=0.25:alpha=1[st];[{src_label}][st]overlay={x}:{y}:shortest=1[m];")


def image_part(img: Path, dur: float, out: Path, variant: int, g: dict, sticker=None) -> None:
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
    extra_in, st_fc = _sticker_fc(sticker)
    fc = (f"[0:v]zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={g['w']}x{g['h']}:fps={FPS},setsar=1[m0];"
          + st_fc + compose(g, n))
    run([ffmpeg_bin(), "-v", "error", "-y", "-i", str(img), *extra_in, "-filter_complex", fc, "-map", "[v]",
         "-frames:v", str(n), "-r", str(FPS), *venc(False), "-an", str(out)])


# ------------------------------------------------------------------ video
def video_part(src: Path, start: float, dur: float, out: Path, g: dict, sticker=None,
               crop: dict | None = None) -> None:
    n = max(2, round(dur * FPS))
    from .highlight import video_size
    w, h = video_size(src)
    if not w:
        w, h = 1920, 1080
    box = f"{g['w']}:{g['h']}"
    pre = ""
    if crop:   # ✂️ bạn đã chọn vùng giữ lại (bỏ logo, chữ, viền đen…)
        cw, ch = float(crop.get("w", 1)), float(crop.get("h", 1))
        cx, cy = float(crop.get("x", 0)), float(crop.get("y", 0))
        pre = f"crop=trunc(iw*{cw:.4f}/2)*2:trunc(ih*{ch:.4f}/2)*2:trunc(iw*{cx:.4f}):trunc(ih*{cy:.4f}),"
        w, h = w * cw, h * ch
    if w / max(h, 1) >= (g['w'] / g['h']) * 0.8:
        media = (f"[0:v]{pre}fps={FPS},scale={box}:force_original_aspect_ratio=increase,"
                 f"crop={box},setsar=1,tpad=stop_mode=clone:stop_duration={dur + 1:.2f}[m0];")
    else:  # video dọc (link TikTok bạn dán) → đặt giữa khung, nền trắng, không làm mờ
        media = (f"[0:v]{pre}fps={FPS},scale={box}:force_original_aspect_ratio=decrease,"
                 f"pad={box}:(ow-iw)/2:(oh-ih)/2:{g['bg']},setsar=1,"
                 f"tpad=stop_mode=clone:stop_duration={dur + 1:.2f}[m0];")
    extra_in, st_fc = _sticker_fc(sticker)
    fc = media + st_fc + compose(g, n)
    run([ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", str(src),
         *extra_in, "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n), "-r", str(FPS), *venc(False), "-an",
         str(out)])


def _bgm_track(path: Path, sr: int, n: int) -> np.ndarray:
    """Giải mã nhạc nền → stereo, lặp cho đủ độ dài, fade vào 0.5s / fade ra 2s."""
    raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    b = np.nan_to_num(np.frombuffer(raw, dtype=np.float32).reshape(-1, 2))
    if len(b) < sr // 2:
        raise RuntimeError("file nhạc quá ngắn")
    if len(b) < n:   # nối vòng: đan chéo 1 giây để chỗ nối không bị giật / hở
        xf = min(sr, len(b) // 4)
        ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
        out = b.copy()
        while len(out) < n:
            out = np.concatenate([out[:-xf], out[-xf:] * (1 - ramp) + b[:xf] * ramp, b[xf:]])
        b = out
    b = b[:n].copy()
    fi, fo = min(n, int(sr * 0.5)), min(n, int(sr * 2))
    b[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    b[n - fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
    return b


def _check_gaps(final: Path, mix: np.ndarray, sr: int, log, total: float) -> None:
    """So sánh tiếng trong video xuất ra với bản trộn: báo chỗ nào bị mất tiếng (để dễ tìm lỗi)."""
    try:
        raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(final), "-ac", "1", "-ar", str(sr),
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
    except Exception:  # noqa: BLE001
        return
    out = np.frombuffer(raw, dtype=np.float32)
    ref = mix.mean(axis=1)
    if len(out) < len(ref):          # âm thanh kết thúc sớm hơn hình → coi phần thiếu là mất tiếng
        out = np.concatenate([out, np.zeros(len(ref) - len(out), dtype=np.float32)])
    try:
        adur = float(subprocess.run([ffprobe_bin(), "-v", "error", "-select_streams", "a:0", "-show_entries",
                                     "stream=duration", "-of", "csv=p=0", str(final)],
                                    capture_output=True, text=True).stdout.strip() or 0)
        if adur and adur < total - 0.3:
            log(f"  ⚠️ luồng âm thanh chỉ dài {adur:.1f}s trong khi video {total:.1f}s")
    except Exception:  # noqa: BLE001
        pass
    w = int(sr * 0.25)
    n = len(ref) // w
    if n == 0:
        return
    r_out = np.sqrt((out[: n * w].reshape(n, w) ** 2).mean(1))
    r_ref = np.sqrt((ref[: n * w].reshape(n, w) ** 2).mean(1))
    lost = (r_ref > 0.01) & (r_out < 0.002)
    spans, i = [], 0
    while i < n:
        if lost[i]:
            j = i
            while j < n and lost[j]:
                j += 1
            if j - i >= 2:
                spans.append(f"{i * 0.25:.1f}–{j * 0.25:.1f}s")
            i = j
        else:
            i += 1
    if spans:
        log(f"  ⚠️ video xuất ra bị mất tiếng ở: {', '.join(spans[:10])} (bản trộn có tiếng) – gửi dòng này cho mình nhé")
    else:
        log("  ✓ Đã kiểm tra: âm thanh video xuất ra liền mạch, không bị mất đoạn nào")


def _clean_render_dir(rdir: Path, log) -> None:
    """Xóa file của lần xuất trước. Trên Windows, video đang mở (khung xem trong tool, trình phát…) bị khóa
    → không xóa được thì bỏ qua file đó thay vì báo lỗi dừng cả quá trình."""
    rdir.mkdir(parents=True, exist_ok=True)
    locked = []
    for f in sorted(rdir.rglob("*"), key=lambda x: -len(x.parts)):
        try:
            f.rmdir() if f.is_dir() else f.unlink()
        except OSError:
            if f.is_file():
                locked.append(f.name)
    if locked:
        log(f"  (video cũ đang được mở nên chưa xóa được: {', '.join(locked[:3])} → bản mới sẽ lưu tên khác)")


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
    if "\n" in chunk or len(MK.strip(chunk)) <= maxlen:
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


def build_ass(scenes: list[dict], starts: list[float], out: Path, extra_rows: list | None = None,
              style: dict | None = None) -> None:
    """style (đua ngựa): cỡ chữ / vị trí riêng + chữ ĐỎ / TO theo ký hiệu 〔〕【】《》."""
    st = load_settings()
    font, size = st.get("subtitle_font"), int(st.get("subtitle_size", 124))
    lh = size * SUB_LINE_SPACING
    L = layout()
    big = int(size * 1.3)
    if style:
        size, big = style["size"], style["big"]
        L = {"sub_top": style["sub_top"], "sub_bottom": style["sub_bottom"]}

    def pitch(has_big: bool) -> float:
        if style:
            return (big if has_big else size) * style["pitch"]
        return lh * (big / size if has_big else 1)
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
{LAY.STYLE_D.format(font=font)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for sc, t0 in zip(scenes, starts):
        chunks = [auto_wrap(c.strip(), (style or {}).get("wrap", 11))
                  for c in sc.get("chunks", []) if MK.strip(c).strip()]
        if not chunks:
            continue
        speech = max(0.3, float(sc["duration"]) - 0.18)
        weights = [max(1, len(MK.strip(c).replace("\n", "").replace(" ", ""))) for c in chunks]
        tot = sum(weights)
        bounds, acc = [], t0
        for wgt in weights:
            bounds.append((acc, acc + speech * wgt / tot))
            acc += speech * wgt / tot
        end_scene = t0 + float(sc["duration"])
        if style and style.get("below_only"):
            # lịch sử: mỗi lần 1 cụm, chỉ ở dưới khung, đổi theo từng câu đọc
            for i, chunk in enumerate(chunks):
                a1 = bounds[i][1] if i < len(chunks) - 1 else end_scene
                y = L['sub_bottom']
                for text, has_big in MK.to_ass_lines(chunk, size, big, ass_escape, W):
                    ev.append(f"Dialogue: 0,{ass_time(bounds[i][0])},{ass_time(a1)},Bottom,,0,0,0,,"
                              f"{{\\pos({W // 2},{y:.0f})}}{text}")
                    y += pitch(has_big)
            continue
        # cặp (trên, dưới): chunk lẻ ở trên, chunk chẵn hiện thêm ở dưới
        for i in range(0, len(chunks), 2):
            a0 = bounds[i][0]
            last = min(i + 1, len(chunks) - 1)
            a1 = bounds[last][1] if last < len(chunks) - 1 else end_scene
            # mỗi dòng là 1 sự kiện riêng để tự kiểm soát khoảng cách dòng
            # (dòng trên: canh chân dòng, xếp ngược lên; dòng dưới: canh đỉnh dòng, xếp xuống)
            lines = MK.to_ass_lines(chunks[i], size, big, ass_escape, W)
            y = L['sub_top']
            for k in range(len(lines) - 1, -1, -1):
                text, has_big = lines[k]
                ev.append(f"Dialogue: 0,{ass_time(a0)},{ass_time(a1)},Top,,0,0,0,,"
                          f"{{\\pos({W // 2},{y:.0f})}}{text}")
                y -= pitch(has_big)      # dòng canh chân → dòng trên nằm cách đúng chiều cao dòng này
            if i + 1 < len(chunks):
                y = L['sub_bottom']
                for text, has_big in MK.to_ass_lines(chunks[i + 1], size, big, ass_escape, W):
                    ev.append(f"Dialogue: 0,{ass_time(bounds[i + 1][0])},{ass_time(a1)},Bottom,,0,0,0,,"
                              f"{{\\pos({W // 2},{y:.0f})}}{text}")
                    y += pitch(has_big)
    out.write_text(head + "\n".join((extra_rows or []) + ev) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ main
def render(pid: str, log) -> None:
    import soundfile as sf

    p = P.load(pid)
    base = P.pdir(pid)
    rdir = base / "render"
    _clean_render_dir(rdir, log)
    scenes = p["scenes"]
    missing = [s["id"] for s in scenes if not s.get("audio") or not (base / s["audio"]).exists()]
    if missing:
        raise RuntimeError(f"Các cảnh chưa có giọng đọc: {', '.join(missing)}")
    lay = LAY.resolve(p)
    sport = LAY.sport_variant(p, lay)
    if LAY.is_light(p):
        log("Idol / K-pop → dùng nền trắng")
    g = LAY.geometry(lay, sport, light=LAY.is_light(p))
    log(f"Bộ mã hóa video: {encoder()} · bố cục: {lay}")

    # 1) ghép giọng đọc
    from . import audio_check as AC
    from .languages import est_seconds
    audios, sr, t_at = [], None, 0.0
    for s in scenes:
        a, asr = sf.read(base / s["audio"], dtype="float32")
        sr = sr or asr
        bad = AC.problem(a, asr, est_seconds(P.scene_plain_text(s)), 0.25)
        if bad:
            log(f"  ⚠️ giọng cảnh {s['id']} (giây {t_at:.0f} của video): {bad}"
                f" → nên vào bước Giọng đọc, đọc lại cảnh này")
        t_at += len(a) / asr
        a = AC.resample(AC.level(a, asr), asr, sr)   # mọi cảnh to đều nhau, cùng tần số mẫu
        audios.append(a)
        s["duration"] = len(a) / sr
    narration = np.concatenate(audios + [np.zeros(int(sr * 0.6), dtype=np.float32)])
    sf.write(rdir / "narration.wav", narration, sr)
    total = len(narration) / sr

    # 2) từng phần hình
    parts, starts, t = [], [], 0.0
    topped: dict = {}
    variant = random.randint(0, 3)
    for si, s in enumerate(scenes):
        starts.append(t)
        D = float(s["duration"]) + (0.6 if si == len(scenes) - 1 else 0)
        items = s.get("items") or []
        log(f"Dựng cảnh {s['id']} ({D:.1f}s)", 0.05 + 0.75 * si / len(scenes))
        if not items:
            pieces = [("blank", None, D)]
        elif items[0]["kind"] == "video":
            # cảnh video dài → cắt thành nhiều đoạn hay (~3 giây/đoạn) từ các đoạn ứng viên
            clips = [items[0]] + ([] if s.get("picked") is not False else   # bạn đã chọn đoạn → chỉ dùng đoạn đó
                                  [c for c in (s.get("candidates") or [])
                                   if c.get("kind") == "video" and c is not items[0]
                                   and (c.get("file"), c.get("start")) != (items[0].get("file"), items[0].get("start"))])
            k = max(1, min(len(clips), round(D / SWITCH_SEC)))
            pieces = [("video", clips[i], D / k) for i in range(k)]
        elif lay == "korea" and s.get("split") and len(items) >= 2 and items[1]["kind"] == "image":
            pieces = [("split", (items[0], items[1]), D)]   # so sánh 2 người: chia đôi khung
        else:
            imgs = [it for it in items if it["kind"] == "image"]
            k = n_images_for(D)
            if s.get("picked") is False and len(imgs) < k:
                # tool tự chọn (bạn chưa đụng tới cảnh này): giọng đọc dài hơn dự tính → chọn thêm ảnh khác
                # trong danh sách ứng viên, và LƯU LẠI để giao diện hiện đúng những ảnh có trong video
                seen = {it["file"] for it in imgs}
                for c in s.get("candidates") or []:
                    if len(imgs) >= k:
                        break
                    if (c.get("kind") == "image" and not c.get("rejected") and c["file"] not in seen
                            and (base / c["file"]).exists()):
                        imgs.append(c)
                        seen.add(c["file"])
                topped[s["id"]] = list(imgs)
            elif len(imgs) < k:
                # BẠN ĐÃ CHỌN ẢNH (hoặc dự án cũ) → dùng đúng và chỉ những ảnh đang được chọn.
                log(f"  {s['id']}: dùng {len(imgs)} ảnh đang được chọn → mỗi ảnh {D / len(imgs):.1f}s")
            pieces = [("image", it, D / len(imgs)) for it in imgs]
        # sticker (hình minh họa) của cảnh: hiện ở mảnh đầu tiên của cảnh
        stk = None
        if s.get("sticker"):
            from . import stickers as STK
            stk = STK.overlay(s["sticker"], s.get("sticker_pos", ""), g, seed=si)
            if stk is None:
                log(f"  (không tải được hình minh họa {s['sticker']} cho {s['id']} – bỏ qua)")
        for pi, (kind, it, d) in enumerate(pieces):
            out = rdir / f"part_{len(parts):03d}.mp4"
            sticker = stk if pi == 0 else None
            try:
                if kind == "image":
                    prep = prepare_image(base / it["file"], rdir / f"img_{len(parts):03d}.jpg", g)
                    image_part(prep, d, out, variant, g, sticker)
                    variant += 1
                elif kind == "split":
                    prep = prepare_split(base / it[0]["file"], base / it[1]["file"], rdir / f"img_{len(parts):03d}.jpg", g)
                    image_part(prep, d, out, variant, g)
                    variant += 1
                elif kind == "video":
                    video_part(base / it["file"], float(it.get("start", 0)), d, out, g, sticker, it.get("crop"))
                else:
                    blank_part(d, out, g)
            except Exception as e:  # noqa: BLE001
                log(f"  ⚠️ lỗi dựng {s['id']}: {e} → để trống")
                blank_part(d, out, g)
            parts.append(out)
        t += float(s["duration"])

    if topped:
        def _save_items(pp):
            for sc in pp["scenes"]:
                if sc["id"] in topped:
                    sc["items"] = topped[sc["id"]]
        P.update(pid, _save_items)

    lst = rdir / "parts.txt"
    lst.write_text("".join(f"file '{x.name}'\n" for x in parts), encoding="utf-8")
    run([ffmpeg_bin(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "parts.txt",
         "-c", "copy", "video.mp4"], cwd=rdir)

    # 3) sub + chữ/hiệu ứng của bố cục
    if lay == "sports":
        extra = LAY.sport_rows(sport, p, scenes, starts, total, g) if sport else None
        build_ass(scenes, starts, rdir / "subs.ass", extra, LAY.SUB_STYLES.get(sport))
    else:
        LAY.build_ass(lay, p, scenes, starts, total, rdir / "subs.ass")

    # 4) trộn nhạc nền + chèn sub + xuất
    log("Chèn sub, trộn nhạc nền và xuất video cuối...", 0.85)
    rel = rdir.relative_to(ROOT).as_posix()
    fonts_rel = FONTS.relative_to(ROOT).as_posix()
    cmd = [ffmpeg_bin(), "-v", "error", "-y", "-i", f"{rel}/video.mp4", "-i", f"{rel}/mix.wav"]
    from .bgm_gen import resolve as resolve_bgm
    bgm = p.get("bgm", {})
    bgm_name = resolve_bgm(p)
    bgm_file = BGM / bgm_name if bgm_name else None
    if bgm_name:
        log(f"Nhạc nền: {bgm_name}")
    # Trộn giọng + nhạc nền ngay trong Python (lặp nhạc chính xác từng mẫu, không bị hở khi nối vòng)
    mix = np.repeat(narration[:, None], 2, axis=1)
    if bgm_file and bgm_file.exists():
        vol = float(bgm.get("volume", 0.15))
        try:
            mix = mix + vol * _bgm_track(bgm_file, sr, len(narration))
        except Exception as e:  # noqa: BLE001
            log(f"  ⚠️ không đọc được nhạc nền ({e}) → xuất không nhạc nền")
    # âm lượng chuẩn -14 LUFS như video trên TikTok – tự tính, KHÔNG dùng loudnorm của FFmpeg
    # (một số bản FFmpeg trên Windows làm cụt mấy giây âm thanh cuối khi dùng loudnorm)
    mix = AC.normalize_lufs(mix, sr)
    sf.write(rdir / "mix.wav", mix, sr, subtype="FLOAT")
    fc = f"[0:v]ass={rel}/subs.ass:fontsdir={fonts_rel}[v]"
    safe_title = re.sub(r'[\\/:*?"<>|]+', "_", p.get("title") or p["id"])[:60].strip() or p["id"]
    final_rel = f"{rel}/{safe_title}.mp4"
    k = 2
    while (ROOT / final_rel).exists():     # bản cũ đang mở (Windows khóa file) → lưu tên mới, không ghi đè
        final_rel = f"{rel}/{safe_title} ({k}).mp4"
        k += 1
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "1:a", *venc(True), "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.3f}",
            "-movflags", "+faststart", final_rel]
    run(cmd, cwd=ROOT)
    _check_gaps(ROOT / final_rel, mix, sr, log, total)
    for f in rdir.glob("part_*.mp4"):
        f.unlink()
    for f in rdir.glob("img_*.jpg"):
        f.unlink()
    out_rel = Path(final_rel).relative_to(base.relative_to(ROOT)).as_posix()
    P.update(pid, lambda pp: pp.__setitem__("output", out_rel))
    log(f"Đã xuất: projects/{pid}/{out_rel} ({total:.1f}s)", 1.0)
