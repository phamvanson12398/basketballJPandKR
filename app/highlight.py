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


def analyze(video: Path) -> dict:
    cache = video.with_suffix(".analysis.json")
    if cache.exists():
        return json.loads(cache.read_text())
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
    cache.write_text(json.dumps(data))
    return data


def _z(x: np.ndarray) -> np.ndarray:
    s = x.std()
    return np.clip((x - x.mean()) / (s + 1e-6), -3, 3)


def best_windows(an: dict, length: float, k: int = 6, exclude: list | None = None) -> list[dict]:
    sps = an["sps"]
    n = an["n"]
    L = max(1, int(round(length * sps)))
    motion, sharp = np.array(an["motion"]), np.array(an["sharp"])
    audio, cuts, bright = np.array(an["audio"]), np.array(an["cuts"]), np.array(an["bright"])
    m_ = np.where(cuts == 1, np.median(motion), motion)   # đừng tính cú cắt cảnh là chuyển động
    per = 1.0 * _z(m_) + 0.6 * _z(audio) + 0.3 * _z(np.log1p(sharp))
    per = per - 2.0 * (bright < 25) - 2.0 * (bright > 235)        # màn đen / trắng
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
