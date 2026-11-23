"""Tự tìm "đoạn hay" trong một video dài.

Chấm điểm từng khoảng thời gian theo:
  • chuyển động (pha bóng, chạy, ăn mừng)  • độ to của tiếng khán giả
  • độ nét  • có bị cắt cảnh giữa chừng không
Sau đó (tùy chọn) đưa ảnh của các đoạn tốt nhất cho Claude chọn đoạn hợp nội dung nhất.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import ffmpeg_bin, ffprobe_bin

SPS = 4          # số mẫu mỗi giây khi phân tích
FW, FH = 192, 108


def probe_duration(path: Path) -> float:
    r = subprocess.run([ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


FIELD_MIN = 0.12   # khung hình có ≥12% điểm ảnh màu cỏ → coi là cảnh trên sân


def field_ratio(video: Path) -> list[float]:
    """Tỉ lệ điểm ảnh "màu cỏ sân" của từng khung (SPS khung/giây).
    Video trận đấu bóng chày / bóng đá: phần lớn khung có sân cỏ. Talkshow, phỏng vấn, phòng thu: gần như không."""
    cmd = [ffmpeg_bin(), "-v", "error", "-i", str(video), "-vf", f"fps={SPS},scale={FW // 2}:{FH // 2}",
           "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    sz = (FW // 2) * (FH // 2) * 3
    n = len(raw) // sz
    if n == 0:
        return []
    fr = np.frombuffer(raw[: n * sz], dtype=np.uint8).reshape(n, FH // 2, FW // 2, 3).astype(np.int16)
    r, g, b = fr[..., 0], fr[..., 1], fr[..., 2]
    # cỏ tự nhiên / cỏ nhân tạo, cả trận đêm: xanh lá trội rõ hơn đỏ và xanh dương
    green = (g >= 45) & (g - r >= 18) & (g - b >= 12)
    return green.mean(axis=(1, 2)).round(3).tolist()


def game_share(an: dict) -> float:
    """Tỉ lệ thời lượng video là cảnh trên sân."""
    f = np.array(an.get("field") or [])
    return float((f >= FIELD_MIN).mean()) if f.size else 1.0


def analyze(video: Path, need_field: bool = False) -> dict:
    cache = video.with_suffix(".analysis.json")
    if cache.exists():
        data = json.loads(cache.read_text())
        if need_field and "field" not in data:
            data["field"] = field_ratio(video)
            cache.write_text(json.dumps(data))
        return data
    # khung hình xám nhỏ
    cmd = [ffmpeg_bin(), "-v", "error", "-i", str(video), "-vf",
           f"fps={SPS},scale={FW}:{FH},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (FW * FH)
    frames = np.frombuffer(raw[: n * FW * FH], dtype=np.uint8).reshape(n, FH, FW).astype(np.float32)
    if n < 2:
        raise RuntimeError("Không đọc được khung hình video")
    motion = np.zeros(n, dtype=np.float32)
    motion[1:] = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    lap = (frames[:, 1:-1, 1:-1] * 4 - frames[:, :-2, 1:-1] - frames[:, 2:, 1:-1]
           - frames[:, 1:-1, :-2] - frames[:, 1:-1, 2:])
    sharp = lap.var(axis=(1, 2))
    bright = frames.mean(axis=(1, 2))
    med = float(np.median(motion[1:]) + 1e-6)
    cuts = (motion > max(25.0, med * 4)).astype(np.int8)
    # âm thanh
    a = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(video), "-ac", "1", "-ar", "8000",
                        "-f", "s16le", "-"], capture_output=True).stdout
    pcm = np.frombuffer(a[: len(a) // 2 * 2], dtype=np.int16).astype(np.float32)
    hop = 8000 // SPS
    m = len(pcm) // hop
    audio = (np.sqrt((pcm[: m * hop].reshape(m, hop) ** 2).mean(axis=1)) if m else np.zeros(n))
    audio = np.resize(audio, n) if len(audio) else np.zeros(n)
    data = {"sps": SPS, "n": int(n), "motion": motion.round(2).tolist(), "sharp": sharp.round(1).tolist(),
            "bright": bright.round(1).tolist(), "cuts": cuts.tolist(), "audio": audio.round(1).tolist()}
    if need_field:
        data["field"] = field_ratio(video)
    cache.write_text(json.dumps(data))
    return data


def _z(x: np.ndarray) -> np.ndarray:
    s = x.std()
    return np.clip((x - x.mean()) / (s + 1e-6), -3, 3)


def best_windows(an: dict, length: float, k: int = 6, exclude: list | None = None,
                 need_field: bool = False, focus: list[float] | None = None) -> list[dict]:
    """focus = các thời điểm (giây) bình luận viên gọi tên nhân vật → ưu tiên mạnh các đoạn quanh đó."""
    sps = an["sps"]
    n = an["n"]
    L = max(1, int(round(length * sps)))
    motion, sharp = np.array(an["motion"]), np.array(an["sharp"])
    audio, cuts, bright = np.array(an["audio"]), np.array(an["cuts"]), np.array(an["bright"])
    m_ = np.where(cuts == 1, np.median(motion), motion)   # đừng tính cú cắt cảnh là chuyển động
    per = 1.0 * _z(m_) + 0.6 * _z(audio) + 0.3 * _z(np.log1p(sharp))
    per = per - 2.0 * (bright < 25) - 2.0 * (bright > 235)        # màn đen / trắng
    if focus:
        near = np.zeros(n, dtype=np.float32)
        for t in focus:
            a, b = max(0, int((t - 1.0) * sps)), min(n, int((t + 6.0) * sps))
            near[a:b] = 1.0
        per = per + 2.5 * near
    fld = None
    if need_field and an.get("field"):
        # chỉ lấy cảnh trên sân: phạt nặng khung phòng thu / bình luận viên / khán đài
        fld = np.resize(np.array(an["field"]), n)
        per = per - 4.0 * (fld < FIELD_MIN)
    cs = np.concatenate([[0], np.cumsum(per)])
    cc = np.concatenate([[0], np.cumsum(cuts)])
    head = int(min(8 * sps, n * 0.05))       # bỏ phần mở đầu (logo, intro)
    tail = int(min(15 * sps, n * 0.08))      # bỏ phần kết (end screen)
    lo, hi = head, n - tail - L
    if hi <= lo:
        lo, hi = 0, max(0, n - L)
    cands = []
    for s in range(lo, hi + 1, max(1, sps // 2)):
        score = (cs[s + L] - cs[s]) / L
        inner_cuts = cc[s + L - 1] - cc[s + 1] if L > 2 else 0
        score -= 0.7 * inner_cuts
        if cuts[s] or (s > 0 and cuts[s - 1]):
            score += 0.4   # bắt đầu ngay sau cú chuyển cảnh → mở đầu gọn
        cands.append((score, s))
    cands.sort(reverse=True)
    ex = [(a * sps, b * sps) for a, b in (exclude or [])]
    chosen = []
    for score, s in cands:
        if any(not (s + L <= a or s >= b) for a, b in ex):
            continue
        if any(abs(s - c["_s"]) < L for c in chosen):
            continue
        if fld is not None and (fld[s:s + L] >= FIELD_MIN).mean() < 0.6:
            continue
        chosen.append({"_s": s, "start": round(s / sps, 2), "dur": round(length, 2),
                       "score": round(float(score), 3)})
        if len(chosen) >= k:
            break
    for c in chosen:
        c.pop("_s")
    return chosen


def video_size(path: Path) -> tuple[int, int]:
    r = subprocess.run([ffprobe_bin(), "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


def best_stills(an: dict, count: int, min_gap: float = 6.0) -> list[float]:
    """Chọn các thời điểm có khung hình NÉT và ĐỨNG YÊN (không nhòe) để làm ảnh."""
    sps, n = an["sps"], an["n"]
    motion, sharp = np.array(an["motion"]), np.array(an["sharp"])
    cuts, bright = np.array(an["cuts"]), np.array(an["bright"])
    score = _z(np.log1p(sharp)) - 0.8 * _z(motion)
    near_cut = np.convolve(cuts, np.ones(2 * sps + 1), mode="same") > 0   # tránh ±1s quanh cú chuyển cảnh
    score[near_cut] -= 5
    score[(bright < 30) | (bright > 230)] -= 5
    head, tail = int(min(8 * sps, n * 0.05)), int(min(15 * sps, n * 0.08))
    score[:head] -= 10
    if tail:
        score[-tail:] -= 10
    picks: list[int] = []
    for i in np.argsort(-score):
        if score[i] < -4:
            break
        if all(abs(i - j) >= min_gap * sps for j in picks):
            picks.append(int(i))
        if len(picks) >= count:
            break
    return [round(i / sps, 2) for i in sorted(picks)]


def frame_at(video: Path, t: float, out: Path, width: int = 480) -> Path:
    subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                    "-frames:v", "1", "-vf", f"scale={width}:-2", str(out)], check=False)
    return out


def contact_sheet(video: Path, windows: list[dict], out: Path) -> Path:
    """Mỗi hàng = 1 đoạn ứng viên (3 khung: đầu, giữa, cuối), có đánh số."""
    rows = []
    tmp = out.parent
    for i, w in enumerate(windows):
        ims = []
        for j, f in enumerate((0.1, 0.5, 0.9)):
            p = frame_at(video, w["start"] + w["dur"] * f, tmp / f"_cs_{i}_{j}.jpg", 320)
            try:
                ims.append(Image.open(p).convert("RGB").resize((320, 180)))
            except Exception:
                ims.append(Image.new("RGB", (320, 180), "gray"))
            p.unlink(missing_ok=True)
        rows.append(ims)
    sheet = Image.new("RGB", (60 + 3 * 330, len(rows) * 190 + 10), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=40)
    except TypeError:
        font = ImageFont.load_default()
    for i, ims in enumerate(rows):
        y = 10 + i * 190
        d.text((10, y + 60), str(i + 1), fill="red", font=font)
        for j, im in enumerate(ims):
            sheet.paste(im, (60 + j * 330, y))
    sheet.save(out, quality=85)
    return out


def ask_claude_pick(video: Path, windows: list[dict], scene_text: str, workdir: Path) -> int:
    from .claude_cli import ask
    sheet = contact_sheet(video, windows, workdir / "_highlight_sheet.jpg")
    prompt = (f"画像ファイル {sheet.as_posix()} を Read ツールで開いてください。\n"
              f"各行(番号1〜{len(windows)})は動画クリップ候補の 始め/中間/終わり のフレームです。\n"
              f"このクリップは次のナレーションの間に流れます:\n「{scene_text}」\n"
              "ナレーションの内容に最も合い、見ていて盛り上がる(プレーが見える・鮮明・"
              "テロップや広告・解説者の顔だけではない)候補を1つ選び、番号だけを答えてください。")
    try:
        ans = ask(prompt, tools=["Read"], add_dirs=[str(workdir)], timeout=300)
        m = re.search(r"\d+", ans)
        if m and 1 <= int(m.group()) <= len(windows):
            return int(m.group()) - 1
    except Exception:
        pass
    finally:
        sheet.unlink(missing_ok=True)
    return 0


def verify_person(video: Path, windows: list[dict], scene_text: str, who: str, uniform: str,
                  ref: Path | None, workdir: Path) -> dict:
    """Claude xem khung hình các đoạn ứng viên (+ ảnh chân dung tham chiếu) và xác nhận đoạn nào có ĐÚNG nhân vật.
    Trả về {"ok": [chỉ số đoạn đúng người], "best": chỉ số đoạn hợp nhất hoặc None}."""
    from .claude_cli import ask, extract_json
    sheet = contact_sheet(video, windows, workdir / "_verify_sheet.jpg")
    refline = ""
    if ref and ref.exists():
        rp = workdir / "_verify_ref.jpg"
        rp.write_bytes(ref.read_bytes())
        refline = f"- 参考写真（この人物本人）: {rp.as_posix()}\n"
    prompt = (
        "次の画像ファイルを Read ツールで開いてください。\n"
        f"- 候補シート: {sheet.as_posix()}（各行 1〜{len(windows)} が動画クリップ候補の 始め/中間/終わり のフレーム）\n"
        + refline +
        f"\n探している人物・馬・会社/商品: {who}\n"
        + (f"見分ける特徴（ユニフォーム・背番号 / 馬の毛色・勝負服など）: {uniform}\n" if uniform else "")
        + f"このクリップが流れる時のナレーション:「{scene_text}」\n\n"
        "各候補について、この人物・馬（会社なら、その会社のロゴ・商品・店舗・創業者）がはっきり映っているか判定してください"
        "（人なら背番号・ユニフォームの色やチーム名・顔・体格、馬なら毛色・顔の白斑・ゼッケンや馬名・騎手の勝負服で判断。"
        "別の選手・別の馬、観客、解説者、スタジオだけなら false）。\n"
        "そのうえで、人物が映っていてナレーションの内容に最も合う候補を best に。\n"
        'JSONのみで答える: {"windows": [{"no": 1, "person": true, "why": "背番号23が投球"}], "best": 1}\n'
        "人物が映っている候補が1つもなければ best は null。")
    try:
        data = extract_json(ask(prompt, tools=["Read"], add_dirs=[str(workdir)], timeout=300))
        ok = [int(w["no"]) - 1 for w in data.get("windows", [])
              if w.get("person") and 1 <= int(w.get("no", 0)) <= len(windows)]
        best = data.get("best")
        best = int(best) - 1 if isinstance(best, (int, float)) and 1 <= int(best) <= len(windows) else None
        if best is not None and best not in ok:
            ok.append(best)
        return {"ok": ok, "best": best, "checked": True,
                "why": {int(w["no"]) - 1: str(w.get("why", ""))[:60] for w in data.get("windows", []) if "no" in w}}
    except Exception as e:  # noqa: BLE001
        return {"ok": list(range(len(windows))), "best": None, "checked": False, "error": str(e)[:120]}
    finally:
        sheet.unlink(missing_ok=True)
        (workdir / "_verify_ref.jpg").unlink(missing_ok=True)


def image_sheet(paths: list[Path], out: Path, cols: int = 4) -> Path:
    """Lưới ảnh ứng viên có đánh số (1, 2, 3…) để Claude xem một lần."""
    tw, th = 360, 240
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 10) + 10), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=44)
    except TypeError:
        font = ImageFont.load_default()
    for i, p in enumerate(paths):
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 10)
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        except Exception:  # noqa: BLE001
            pass
        d.rectangle((x, y, x + 58, y + 52), fill="red")
        d.text((x + 10, y + 2), str(i + 1), fill="white", font=font)
    sheet.save(out, quality=85)
    return out


def pick_images(paths: list[Path], scene_text: str, who: str, uniform: str, workdir: Path) -> dict | None:
    """Claude xem lưới ảnh ứng viên → {"good": [chỉ số, tốt nhất trước], "bad": [chỉ số loại], "why": {...}}.
    None nếu không hỏi được (khi đó giữ thứ tự cũ)."""
    from .claude_cli import ask, extract_json
    if len(paths) < 2:
        return None
    sheet = image_sheet(paths, workdir / "_pick_sheet.jpg")
    prompt = (
        f"画像ファイル {sheet.as_posix()} を Read ツールで開いてください。赤い番号 1〜{len(paths)} が候補の写真です。\n"
        f"この写真はショート動画で次のナレーションの間に映します:\n「{scene_text}」\n"
        + (f"写すべき人物・馬: {who}\n" if who else "")
        + (f"見分ける特徴: {uniform}\n" if uniform else "")
        + "\n各写真を判定してください:\n"
        "- good: ナレーションの内容（出来事・物・場面）に合い、写すべき人物・馬が写っている（またはその話の物そのもの）。"
        "合っている順に並べる。\n"
        "- bad: 別の人物・別の馬・無関係（グッズ、ゲーム・アニメの絵、文字だけの画像、ロゴ、地図、別の話題）、"
        "または画質が悪すぎる・大きな文字や透かしで見えない。\n"
        'JSONのみ: {"good": [3, 1, 5], "bad": [2, 4], "why": {"3": "モーリスが花束を食べている"}}')
    try:
        data = extract_json(ask(prompt, tools=["Read"], add_dirs=[str(workdir)], timeout=300))
        n = len(paths)
        good = [int(i) - 1 for i in data.get("good", []) if str(i).isdigit() and 1 <= int(i) <= n]
        bad = [int(i) - 1 for i in data.get("bad", []) if str(i).isdigit() and 1 <= int(i) <= n and int(i) - 1 not in good]
        return {"good": list(dict.fromkeys(good)), "bad": list(dict.fromkeys(bad)),
                "why": {int(k) - 1: str(v)[:40] for k, v in (data.get("why") or {}).items() if str(k).isdigit()}}
    except Exception:  # noqa: BLE001
        return None
    finally:
        sheet.unlink(missing_ok=True)
