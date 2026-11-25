"""Tự soạn nhạc nền cho từng thể loại bằng code (không bản quyền, không cần tải gì).

Mỗi bài dài ~1 phút rưỡi, kết thúc tròn ô nhịp nên lặp lại liền mạch khi video dài hơn.
Chạy tay:  python -m app.bgm_gen   (tạo lại toàn bộ: thêm --force)
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

from .config import BGM, ffmpeg_bin

SR = 44100
RNG = np.random.default_rng(7)

# ---------------------------------------------------------------- danh sách bài (genre → bài)
TRACKS = [
    # file,                                   thể loại,    hàm soạn,      mô tả
    ("Thể thao - Sôi động (tool).m4a",        "sports",    "sports_hype"),
    ("Thể thao - Kịch tính (tool).m4a",       "sports",    "sports_tense"),
    ("Tin tức - Bản tin (tool).m4a",          "news",      "news_pulse"),
    ("Tin tức - Trầm tĩnh (tool).m4a",        "news",      "news_calm"),
    ("Top - Đếm ngược (tool).m4a",            "ranking",   "rank_countdown"),
    ("Top - Vui nhộn (tool).m4a",             "ranking",   "rank_fun"),
    ("Tiểu sử - Cảm động (tool).m4a",         "biography", "bio_emotional"),
    ("Tiểu sử - Truyền cảm hứng (tool).m4a",  "biography", "bio_inspire"),
    ("Chủ đề chung - Lo-fi (tool).m4a",       "general",   "gen_lofi"),
    ("Chủ đề chung - Tò mò (tool).m4a",       "general",   "gen_curious"),
    ("Sumo - Trống Taiko (tool).m4a",         "sumo",      "sumo_taiko"),
    ("Sumo - Truyền thống (tool).m4a",        "sumo",      "sumo_traditional"),
    ("Bóng đá - Sân vận động (tool).m4a",     "soccer",    "soccer_stadium"),
    ("Bóng đá - Hào hùng (tool).m4a",         "soccer",    "soccer_anthem"),
    ("Idol - J-pop sôi động (tool).m4a",      "idol",      "idol_pop"),
    ("Idol - Ballad (tool).m4a",              "idol",      "idol_ballad"),
    ("K-pop - Dance (tool).m4a",              "kpop",      "kpop_dance"),
    ("K-pop - Hip-hop (tool).m4a",            "kpop",      "kpop_hiphop"),
    ("Hài - Vui nhộn (tool).m4a",             "owarai",    "owarai_fun"),
    ("Hài - Hồi hộp M-1 (tool).m4a",          "owarai",    "owarai_tension"),
    ("Đua ngựa - Fanfare phi nước đại (tool).m4a", "horse", "horse_fanfare"),
    ("Đua ngựa - Chuyện vui (tool).m4a",      "horse",     "horse_cozy"),
    ("Thương hiệu - Khởi nghiệp (tool).m4a",  "brand",     "brand_startup"),
    ("Thương hiệu - Hoài niệm (tool).m4a",    "brand",     "brand_retro"),
    ("Lịch sử Nhật - Chiến quốc (tool).m4a",  "history_ja", "history_sengoku"),
    ("Lịch sử Nhật - Edo (tool).m4a",         "history_ja", "history_edo"),
    ("Lịch sử Hàn - Cung đình (tool).m4a",    "history_ko", "history_joseon"),
    ("Lịch sử Hàn - Chiến trận (tool).m4a",   "history_ko", "history_battle_ko"),
    ("eSports - EDM sôi động (tool).m4a",     "esports",   "esports_hype"),
    ("eSports - Hùng tráng kiểu Worlds (tool).m4a", "esports", "esports_epic"),
]


AUTO = "__auto__"   # giá trị "Tự chọn theo thể loại"


def tracks_for(genre: str) -> list[str]:
    return [f for f, g, _ in TRACKS if g == genre and (BGM / f).exists()]


def resolve(p: dict) -> str:
    """Tên file nhạc nền thật sẽ dùng cho dự án ("" = không nhạc).
    "Tự chọn theo thể loại": chọn 1 bài của thể loại, cố định theo từng video (xuất lại vẫn cùng bài)."""
    f = (p.get("bgm") or {}).get("file", "")
    if f != AUTO:
        return f
    lay = p.get("layout") if p.get("layout") not in (None, "", "auto") else (p.get("genre") or "sports")
    if p.get("genre") == "history" or p.get("sport") == "history":
        lay = "history_ko" if p.get("lang") == "ko" else "history_ja"   # nhạc cổ truyền theo nước
    elif p.get("sport") in ("sumo", "soccer", "idol", "kpop", "owarai", "horse", "esports") and tracks_for(p["sport"]):
        lay = p["sport"]   # sumo: taiko / shamisen · bóng đá: sân vận động · idol: J-pop
    if p.get("audience") == "35plus" and lay in ("sports", "general", "ranking", "brand", "esports", "kpop", "idol", "soccer"):
        calm = [f for f in ("Tiểu sử - Truyền cảm hứng (tool).m4a", "Thương hiệu - Hoài niệm (tool).m4a",
                            "Tiểu sử - Cảm động (tool).m4a") if (BGM / f).exists()]
        if calm:
            return calm[sum(p.get("id", "").encode()) % len(calm)]   # 35+: piano / hoài niệm thay cho EDM, nhạc sôi động
    files = tracks_for(lay if lay in ("sports", "news", "ranking", "biography", "general", "sumo", "soccer", "idol",
                                      "kpop", "owarai", "horse", "brand", "history_ja", "history_ko", "esports")
                       else "sports")
    if not files:
        return ""
    return files[sum(p.get("id", "").encode()) % len(files)]


# ---------------------------------------------------------------- nhạc cụ
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def chord(name: str, octave: int = 4) -> list[int]:
    """'Am', 'F', 'Cmaj7', 'Dm9', 'Bsus4', 'G13'... → danh sách nốt MIDI."""
    root = name[:2] if len(name) > 1 and name[1] == "#" else name[:1]
    q = name[len(root):]
    r = 12 * (octave + 1) + NOTE[root]
    iv = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10],
          "sus4": [0, 5, 7], "m9": [0, 3, 7, 10, 14], "maj9": [0, 4, 7, 11, 14], "13": [0, 4, 10, 14, 21],
          "add9": [0, 4, 7, 14], "5": [0, 7, 12]}[q]
    return [r + i for i in iv]


def env(n, a=0.005, d=0.3, s=0.0, r=0.05, dur=None):
    """ADSR đơn giản (giây) cho n mẫu."""
    t = np.arange(n) / SR
    dur = dur if dur is not None else n / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((t - dur) / max(r, 1e-4), 0, 1)
    return e * (1 - rel)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    # vòng lặp đơn giản; đủ nhanh cho vài chục giây âm thanh
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lp_fast(x, cutoff):
    """Lọc thông thấp nhanh bằng FFT (dùng cho cả bài)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def hp_fast(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (f / cutoff) ** 2 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def kick(punch=1.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30) * punch
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * 1.0


def snare():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    noise = hp_fast(RNG.standard_normal(n), 1500) * np.exp(-t * 22)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30)
    return 0.45 * noise + 0.35 * tone


def clap():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    noise = hp_fast(RNG.standard_normal(n), 1200)
    e = sum(np.exp(-np.clip(t - k * 0.011, 0, None) * 60) * (t >= k * 0.011) for k in range(3))
    return 0.4 * noise * e / 2


def hat(open_=False):
    n = int((0.25 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return 0.22 * hp_fast(RNG.standard_normal(n), 7000) * np.exp(-t * (9 if open_ else 70))


def tom(m=45):
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    f = hz(m) * (1 + 0.6 * np.exp(-t * 25))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * 0.7


def saw(f, n, harm=12, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, harm + 1):
        if f * k > 16000:
            break
        out += np.sin(2 * np.pi * f * k * (1 + detune) * t + k) / k
    return out


def square(f, n, harm=9):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harm + 1, 2))


def piano(m, dur, vel=0.8):
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    out = np.zeros(n)
    for k, amp in enumerate([1, 0.5, 0.3, 0.2, 0.12, 0.08], start=1):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        out += amp * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.2 + 0.9 * k) * (f / 400) ** 0.3)
    out *= np.minimum(1, t / 0.004)
    out *= np.where(t < dur, 1, np.exp(-(t - dur) * 6))
    return vel * out * 0.35


def epiano(m, dur, vel=0.7):
    n = int((dur + 0.8) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    mod = np.sin(2 * np.pi * f * 2 * t) * 1.2 * np.exp(-t * 3)
    out = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 1.6)
    out *= np.minimum(1, t / 0.003) * np.where(t < dur, 1, np.exp(-(t - dur) * 8))
    return vel * out * 0.3


def pluck(m, dur, vel=0.7, bright=0.5):
    """Karplus–Strong: tiếng đàn gảy / pizzicato."""
    f = hz(m)
    n = int((dur + 0.6) * SR)
    p = max(2, int(SR / f))
    buf = RNG.uniform(-1, 1, p)
    out = np.empty(n)
    damp = 0.496 + 0.003 * bright
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = damp * (buf[i % p] + buf[(i + 1) % p])
    t = np.arange(n) / SR
    out *= np.where(t < dur, 1, np.exp(-(t - dur) * 10))
    return vel * out * 0.5


def pad(notes, dur, bright=1800, vol=0.12):
    n = int((dur + 0.5) * SR)
    out = np.zeros(n)
    for m in notes:
        for d in (-0.004, 0.0, 0.004):
            out += saw(hz(m), n, harm=8, detune=d)
    out = lp_fast(out, bright)
    t = np.arange(n) / SR
    e = np.minimum(1, t / 0.4) * np.where(t < dur, 1, np.exp(-(t - dur) * 5))
    return vol * out * e / (len(notes) * 3)


def bass(m, dur, kind="saw", vol=0.35, cutoff=600):
    n = int((dur + 0.05) * SR)
    x = saw(hz(m), n, harm=10) if kind == "saw" else np.sin(2 * np.pi * hz(m) * np.arange(n) / SR)
    x = lp_fast(x, cutoff) if kind == "saw" else x
    return vol * x * env(n, a=0.004, d=0.25, s=0.6, r=0.04, dur=dur)


def lead(m, dur, vol=0.12, kind="square"):
    n = int((dur + 0.1) * SR)
    x = square(hz(m), n) if kind == "square" else saw(hz(m), n, harm=8)
    x = lp_fast(x, 3500)
    return vol * x * env(n, a=0.005, d=0.12, s=0.3, r=0.05, dur=dur)


# ---------------------------------------------------------------- dựng bài
class Song:
    def __init__(self, bpm, bars, beats_per_bar=4):
        self.bpm, self.bars, self.bpb = bpm, bars, beats_per_bar
        self.beat = 60 / bpm
        self.n = int(bars * beats_per_bar * self.beat * SR)
        self.tracks = {}

    def put(self, bus, sound, beat_pos, gain=1.0, swing=0.0):
        x = self.tracks.setdefault(bus, np.zeros(self.n + SR * 3))
        b = beat_pos + (swing * self.beat / 3 if (beat_pos * 2) % 2 == 1 else 0)
        i = int(b * self.beat * SR)
        if i >= self.n:
            return
        j = min(len(x), i + len(sound))
        x[i:j] += gain * sound[: j - i]

    def mix(self, gains=None, reverb=0.25, master=0.9):
        gains = gains or {}
        out = np.zeros(self.n + SR * 3)
        for bus, x in self.tracks.items():
            out += gains.get(bus, 1.0) * x
        # vang (reverb) đơn giản: vài đường trễ phản hồi
        if reverb:
            wet = np.zeros_like(out)
            for d, g in ((0.031, 0.5), (0.047, 0.45), (0.071, 0.4), (0.113, 0.35)):
                k = int(d * SR)
                y = out.copy()
                for _ in range(6):
                    y = np.concatenate([np.zeros(k), y[:-k]]) * g
                    wet += y
            out = out + reverb * lp_fast(wet, 4000) * 0.5
        # phần đuôi tràn qua cuối bài → cộng vào đầu bài để lặp lại liền mạch
        tail = out[self.n:]
        out = out[: self.n]
        out[: len(tail)] += tail
        out = np.tanh(out * 1.2) / np.tanh(1.2)
        rms = np.sqrt(np.mean(out ** 2)) + 1e-9
        out = out * (0.16 / rms)
        peak = np.max(np.abs(out))
        if peak > 0.95:
            out *= 0.95 / peak
        fade = int(0.02 * SR)
        out[:fade] *= np.linspace(0, 1, fade)
        out[-fade:] *= np.linspace(1, 0, fade)
        return out * master


def four_floor(s, bar, hats=True, clap_=True, open_hat=True):
    b0 = bar * s.bpb
    for k in range(4):
        s.put("drums", kick(), b0 + k)
        if hats:
            s.put("hats", hat(), b0 + k + 0.5)
            if open_hat and k % 2 == 1:
                s.put("hats", hat(True), b0 + k + 0.5, 0.6)
    if clap_:
        s.put("drums", clap(), b0 + 1)
        s.put("drums", clap(), b0 + 3)


def backbeat(s, bar, hat_div=2, swing=0.0, kick_pat=(0, 2.5)):
    b0 = bar * s.bpb
    for k in kick_pat:
        s.put("drums", kick(0.8), b0 + k)
    s.put("drums", snare(), b0 + 1)
    s.put("drums", snare(), b0 + 3)
    for k in range(4 * hat_div):
        s.put("hats", hat(), b0 + k / hat_div, 0.7 if k % 2 else 1.0, swing=swing)


# ---------------------------------------------------------------- 10 bài
def sports_hype():
    s = Song(128, 48)
    prog = ["Am", "F", "C", "G"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        sec = bar // 8
        if sec >= 1:
            four_floor(s, bar, open_hat=sec >= 2)
        for k in range(8):   # bass 8 nốt / ô nhịp
            s.put("bass", bass(c[0] - 12, s.beat / 2 * 0.9, cutoff=700), bar * 4 + k / 2)
        if sec >= 2 and sec != 4:
            for k in range(4):
                s.put("synth", sum(lead(m + 12, s.beat * 0.3, 0.05, "saw") for m in c), bar * 4 + k + 0.5)
        s.put("pad", pad(chord(prog[bar % 4], 4), s.beat * 4, 2200, 0.10), bar * 4)
    return s.mix({"drums": 1.0, "hats": 0.6, "bass": 0.9, "synth": 0.8, "pad": 0.7}, reverb=0.2)


def sports_tense():
    s = Song(100, 32)
    prog = ["Dm", "A#", "Gm", "A"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        for k in (0, 0.75, 1.5, 2.5, 3):
            s.put("drums", tom(38 if k < 2 else 43), b0 + k, 0.8)
        if bar >= 8:
            s.put("drums", kick(), b0)
            s.put("drums", kick(), b0 + 2)
            s.put("drums", snare(), b0 + 3, 0.8)
        for k in range(16):
            s.put("bass", bass(c[0] - 12, s.beat / 4 * 0.8, cutoff=500, vol=0.3), b0 + k / 4)
        if bar >= 16:
            for k, m in enumerate([c[0] + 12, c[2] + 12, c[1] + 12, c[2] + 12] * 2):
                s.put("synth", lead(m, s.beat / 2 * 0.8, 0.06), b0 + k / 2)
        s.put("pad", pad(c, s.beat * 4, 1200, 0.12), b0)
    return s.mix({"drums": 0.9, "bass": 0.9, "synth": 0.7, "pad": 0.9}, reverb=0.3)


def news_pulse():
    s = Song(112, 40)
    prog = ["Em", "Cmaj7", "Am7", "Bsus4"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        for k in range(16):   # nhịp đập 16 nốt kiểu bản tin
            s.put("bass", bass(c[0] - 12, s.beat / 4 * 0.6, cutoff=900, vol=0.22), b0 + k / 4, 1.0 if k % 4 == 0 else 0.6)
        s.put("drums", kick(0.7), b0)
        s.put("drums", kick(0.7), b0 + 2)
        for k in range(8):
            s.put("hats", hat(), b0 + k / 2, 0.5)
        if bar >= 8:
            s.put("drums", snare(), b0 + 3, 0.5)
        if bar % 2 == 0:
            for k, m in enumerate([c[0] + 24, c[2] + 12, c[1] + 24, c[2] + 12]):
                s.put("synth", pluck(m, s.beat * 0.4, 0.5, 0.8), b0 + k)
        s.put("pad", pad(chord(prog[bar % 4], 4), s.beat * 4, 1500, 0.10), b0)
    return s.mix({"bass": 1.0, "drums": 0.8, "hats": 0.6, "synth": 0.8, "pad": 0.8}, reverb=0.25)


def news_calm():
    s = Song(90, 28)
    prog = ["Fmaj7", "G", "Em", "Am"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        s.put("pad", pad(c, s.beat * 4, 1400, 0.14), b0)
        for k, m in enumerate([c[0], c[1], c[2], c[1], c[0] + 12, c[2], c[1], c[2]]):
            s.put("synth", pluck(m, s.beat * 0.45, 0.4, 0.4), b0 + k / 2)
        s.put("bass", bass(c[0] - 24, s.beat * 3.5, kind="sine", vol=0.3), b0)
        if bar >= 4:
            s.put("drums", kick(0.6), b0)
            s.put("hats", hat(), b0 + 1, 0.4)
            s.put("hats", hat(), b0 + 3, 0.4)
    return s.mix({"pad": 1.0, "synth": 0.9, "bass": 0.8, "drums": 0.6, "hats": 0.5}, reverb=0.35)


def rank_countdown():
    s = Song(120, 48)
    prog = ["C", "G", "Am", "F"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        sec = bar // 8
        if sec in (1, 2, 4, 5):
            four_floor(s, bar)
        elif sec == 3:   # đoạn "dồn" trước cao trào
            for k in range(4 * (1 + bar % 8 // 2)):
                s.put("drums", snare(), b0 + k * 4 / (4 * (1 + bar % 8 // 2)), 0.6)
        for k in range(8):
            s.put("bass", bass(c[0] - 12, s.beat / 2 * 0.8, cutoff=800), b0 + k / 2)
        mel = [c[2] + 12, c[1] + 12, c[0] + 12, c[1] + 12]
        if sec >= 2:
            for k, m in enumerate(mel * 2):
                s.put("synth", lead(m, s.beat / 2 * 0.7, 0.07), b0 + k / 2)
        s.put("pad", pad(chord(prog[bar % 4], 4), s.beat * 4, 2500, 0.09), b0)
    return s.mix({"drums": 1.0, "hats": 0.6, "bass": 0.9, "synth": 0.8, "pad": 0.7}, reverb=0.2)


def rank_fun():
    s = Song(116, 40)
    prog = ["F", "Dm", "Gm", "C"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        backbeat(s, bar, hat_div=2, kick_pat=(0, 1.5, 2.5))
        for k in (0, 1.5, 2, 3.5):
            s.put("bass", bass(c[0] - 24, s.beat * 0.4, cutoff=900), b0 + k)
        for k in range(4):
            s.put("synth", sum(pluck(m, s.beat * 0.25, 0.35, 0.9) for m in c), b0 + k + 0.5)
        if bar % 4 == 3:
            for k, m in enumerate([c[2] + 12, c[1] + 12, c[0] + 12, c[2]]):
                s.put("lead", lead(m, s.beat * 0.4, 0.07), b0 + k)
    return s.mix({"drums": 0.9, "hats": 0.6, "bass": 0.9, "synth": 0.8, "lead": 0.8}, reverb=0.15)


def bio_emotional():
    s = Song(72, 24)
    prog = [("C", "C"), ("G", "B"), ("Am", "A"), ("F", "F")]
    for bar in range(s.bars):
        name, b = prog[bar % 4]
        c = chord(name, 4)
        b0 = bar * 4
        s.put("bass", piano(12 * 3 + NOTE[b], s.beat * 3.8, 0.7), b0)
        arp = [c[0], c[1], c[2], c[1] + 12 if len(c) > 1 else c[0], c[2], c[1]]
        for k, m in enumerate(arp):
            s.put("piano", piano(m, s.beat * 0.9, 0.55), b0 + k * 4 / 6)
        if bar >= 8:
            s.put("pad", pad(chord(name, 4), s.beat * 4, 1000, 0.10), b0)
        if bar >= 12 and bar % 2 == 0:
            s.put("melody", piano(c[2] + 12, s.beat * 1.8, 0.45), b0 + 0.0)
            s.put("melody", piano(c[1] + 12, s.beat * 1.8, 0.4), b0 + 2.0)
    return s.mix({"piano": 1.0, "bass": 0.8, "pad": 0.8, "melody": 0.9}, reverb=0.45)


def bio_inspire():
    s = Song(84, 32)
    prog = ["F", "C", "G", "Am"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        for k in range(8):
            s.put("piano", piano(c[k % 3] + (12 if k >= 4 else 0), s.beat * 0.6, 0.45), b0 + k / 2)
        s.put("bass", piano(c[0] - 24, s.beat * 3.8, 0.6), b0)
        if bar >= 8:
            s.put("pad", pad(c, s.beat * 4, 1600, 0.10), b0)
        if bar >= 16:
            backbeat(s, bar, hat_div=2, kick_pat=(0, 2))
    return s.mix({"piano": 1.0, "bass": 0.8, "pad": 0.8, "drums": 0.6, "hats": 0.4}, reverb=0.35)


def gen_lofi():
    s = Song(82, 32)
    prog = ["Dm9", "G13", "Cmaj9", "Am7"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        backbeat(s, bar, hat_div=2, swing=0.6, kick_pat=(0, 2.5))
        for k in (0, 2.5):
            s.put("keys", sum(epiano(m + 12, s.beat * 1.6, 0.5) for m in c[:4]), b0 + k)
        s.put("bass", bass(c[0] - 12, s.beat * 1.8, kind="sine", vol=0.32), b0)
        s.put("bass", bass(c[0] - 12, s.beat * 1.2, kind="sine", vol=0.28), b0 + 2.5)
    out = s.mix({"drums": 0.7, "hats": 0.45, "keys": 1.0, "bass": 0.9}, reverb=0.3)
    vinyl = hp_fast(RNG.standard_normal(len(out)), 3000) * 0.004   # tiếng sột soạt đĩa than nhẹ
    return lp_fast(out, 6000) + vinyl


def gen_curious():
    s = Song(104, 32)
    prog = ["G", "Em", "C", "D"]
    mel = [0, 4, 7, 4, 2, 4, 0, -1]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        for k in range(8):   # pizzicato nhảy nhót
            s.put("pizz", pluck(c[0] + mel[k] + (12 if bar % 2 else 0), s.beat * 0.2, 0.55, 0.2), b0 + k / 2)
        s.put("bass", pluck(c[0] - 12, s.beat * 0.5, 0.7, 0.1), b0)
        s.put("bass", pluck(c[2] - 24, s.beat * 0.5, 0.6, 0.1), b0 + 2)
        if bar >= 8:
            s.put("drums", kick(0.5), b0)
            s.put("drums", kick(0.5), b0 + 2)
            for k in range(4):
                s.put("hats", hat(), b0 + k + 0.5, 0.5)
    return s.mix({"pizz": 1.0, "bass": 0.9, "drums": 0.6, "hats": 0.4}, reverb=0.2)


def taiko(big=True):
    """Trống taiko: thân trống trầm, ngân dài + tiếng dùi gõ."""
    n = int((1.2 if big else 0.5) * SR)
    t = np.arange(n) / SR
    f0 = 62 if big else 140
    f = f0 * (1 + 0.35 * np.exp(-t * 18))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (3.2 if big else 9))
    hit = hp_fast(RNG.standard_normal(n), 900) * np.exp(-t * 60) * 0.25
    return (body + hit) * (1.0 if big else 0.6)


def kane():
    """Chuông kim loại nhỏ (kane) – tiếng leng keng giữ nhịp."""
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * fr * t) * a for fr, a in ((2100, 0.5), (3350, 0.3), (5200, 0.2))) * np.exp(-t * 14) * 0.12


def shamisen(m, dur, vel=0.6):
    """Shamisen: đàn gảy sáng, tắt nhanh + tiếng 'sawari' rè nhẹ."""
    x = pluck(m, dur, vel, bright=1.0)
    n = len(x)
    t = np.arange(n) / SR
    return x + 0.15 * vel * np.sign(np.sin(2 * np.pi * hz(m) * t)) * np.exp(-t * 25) * 0.3


def shakuhachi(m, dur, vol=0.12):
    """Sáo shakuhachi: âm sine có hơi thở và rung nhẹ."""
    n = int((dur + 0.3) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5 * t) * np.minimum(1, t / 0.4)
    tone = np.sin(2 * np.pi * np.cumsum(hz(m) * vib) / SR)
    breath = lp_fast(RNG.standard_normal(n), 2500) * 0.25
    e = np.minimum(1, t / 0.15) * np.where(t < dur, 1, np.exp(-(t - dur) * 6))
    return vol * (tone + breath) * e


# thang âm Nhật (miyako-bushi): Mi Fa La Si Đô
MIYAKO = [0, 1, 5, 7, 8]


def sumo_taiko():
    s = Song(132, 40)
    pat = [(0, True), (1, False), (1.5, False), (2, True), (3, True), (3.5, False)]
    for bar in range(s.bars):
        b0 = bar * 4
        sec = bar // 8
        for k, big in pat:
            s.put("taiko", taiko(big), b0 + k, 1.0 if big else 0.7)
        if sec >= 1:
            for k in range(4):
                s.put("kane", kane(), b0 + k + 0.5)
        if sec in (2, 3):   # dàn trống đuổi nhau
            for k in range(8):
                s.put("taiko", taiko(False), b0 + k / 2 + 0.25, 0.4)
        if sec >= 1:
            root = 52   # Mi
            phrase = [0, 1, 3, 4, 3, 1, 0, 2]
            for k, idx in enumerate(phrase):
                m = root + MIYAKO[idx] + (12 if sec == 3 else 0)
                s.put("shamisen", shamisen(m, s.beat * 0.4, 0.6), b0 + k / 2)
        if bar % 8 == 7:   # tiếng hô dồn trước đoạn mới
            for k in range(4):
                s.put("taiko", taiko(True), b0 + 2 + k / 2, 0.9)
    return s.mix({"taiko": 1.0, "kane": 0.5, "shamisen": 0.8}, reverb=0.3)


def sumo_traditional():
    s = Song(76, 24)
    for bar in range(s.bars):
        b0 = bar * 4
        s.put("taiko", taiko(True), b0, 0.9)
        if bar % 2 == 1:
            s.put("taiko", taiko(True), b0 + 2.5, 0.6)
        root = 52
        if bar % 4 in (0, 2):
            for k, idx in enumerate([4, 3, 1, 0]):
                s.put("shamisen", shamisen(root + MIYAKO[idx] + 12, s.beat * 0.8, 0.5), b0 + k)
        if bar >= 4:
            line = [(0, 3, 2.0), (2, 4, 2.0)] if bar % 2 == 0 else [(0, 1, 3.0)]
            for pos, idx, d in line:
                s.put("flute", shakuhachi(root + MIYAKO[idx] + 12, s.beat * d), b0 + pos)
        s.put("drone", pad([40, 47], s.beat * 4, 700, 0.08), b0)
    return s.mix({"taiko": 0.9, "shamisen": 0.8, "flute": 0.9, "drone": 0.7}, reverb=0.45)


def crowd(n_sec):
    """Tiếng khán đài: nhiễu lọc dải giữa, lên xuống chậm như hàng vạn người reo."""
    n = int(n_sec * SR)
    x = RNG.standard_normal(n)
    x = lp_fast(hp_fast(x, 300), 2500)
    t = np.arange(n) / SR
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 7.3) * np.sin(2 * np.pi * t / 3.1 + 1)
    return 0.05 * x * swell


def brass(notes, dur, vol=0.10):
    """Kèn đồng tổng hợp (saw sáng, mở dần) cho đoạn điệp khúc hào hùng."""
    n = int((dur + 0.15) * SR)
    out = sum(saw(hz(m), n, harm=14) for m in notes)
    out = lp_fast(out, 2800)
    t = np.arange(n) / SR
    e = np.minimum(1, t / 0.06) * np.where(t < dur, 1, np.exp(-(t - dur) * 12))
    return vol * out * e / len(notes)


def soccer_stadium():
    """Nhịp vỗ tay 'tán tán – tán tán tán' của khán đài + trống lớn + tiếng reo."""
    s = Song(124, 40)
    prog = ["Em", "C", "G", "D"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        sec = bar // 8
        for k in (0, 1, 2.5, 3, 3.5):          # vỗ tay kiểu cổ động viên
            s.put("claps", clap(), b0 + k, 1.0)
        for k in (0, 2):
            s.put("drums", tom(36), b0 + k, 1.0)   # trống cổ động
        if sec >= 1:
            four_floor(s, bar, clap_=False, open_hat=sec >= 3)
            for k in range(8):
                s.put("bass", bass(c[0] - 12, s.beat / 2 * 0.85, cutoff=750), b0 + k / 2)
        if sec in (2, 4):
            s.put("brass", brass(chord(prog[bar % 4], 4), s.beat * 1.8), b0)
            s.put("brass", brass(chord(prog[bar % 4], 4), s.beat * 1.6), b0 + 2)
        s.put("pad", pad(chord(prog[bar % 4], 4), s.beat * 4, 1800, 0.08), b0)
    s.put("crowd", crowd(s.n / SR + 1), 0)
    return s.mix({"claps": 0.8, "drums": 0.9, "hats": 0.5, "bass": 0.9, "brass": 0.9, "pad": 0.6, "crowd": 1.0},
                 reverb=0.3)


def soccer_anthem():
    """Hào hùng kiểu nhạc vào sân: kèn đồng, trống tom dồn, piano giữ nhịp."""
    s = Song(96, 32)
    prog = ["C", "G", "Am", "F"]
    for bar in range(s.bars):
        name = prog[bar % 4]
        c = chord(name, 4)
        b0 = bar * 4
        for k in range(8):
            s.put("piano", piano(c[k % 3] + (12 if k % 4 == 3 else 0), s.beat * 0.5, 0.4), b0 + k / 2)
        s.put("bass", bass(c[0] - 24, s.beat * 3.8, kind="sine", vol=0.32), b0)
        if bar >= 8:
            s.put("drums", kick(), b0)
            s.put("drums", snare(), b0 + 1)
            s.put("drums", kick(), b0 + 2)
            s.put("drums", snare(), b0 + 3)
            for k in (3.5, 3.75):
                s.put("drums", tom(41), b0 + k, 0.7)
        if bar >= 16:
            s.put("brass", brass(chord(name, 3), s.beat * 3.6, 0.12), b0)
            s.put("lead", brass([c[2] + 12], s.beat * 0.9, 0.08), b0 + 2)
            s.put("lead", brass([c[1] + 12], s.beat * 0.9, 0.08), b0 + 3)
        s.put("pad", pad(c, s.beat * 4, 1600, 0.09), b0)
    s.put("crowd", crowd(s.n / SR + 1), 0, 0.6)
    return s.mix({"piano": 0.9, "bass": 0.8, "drums": 0.9, "brass": 1.0, "lead": 0.9, "pad": 0.7, "crowd": 1.0},
                 reverb=0.35)


def idol_pop():
    """J-pop idol: nhịp nhanh, vỗ tay, synth sáng, bass nhảy quãng tám, giai điệu bắt tai."""
    s = Song(150, 48)
    prog = ["F", "G", "Em", "Am"]          # tiến trình "royal road" rất hay gặp trong J-pop
    mel = [12, 14, 16, 19, 16, 14, 12, 11]
    for bar in range(s.bars):
        name = prog[bar % 4]
        c = chord(name, 4)
        b0 = bar * 4
        sec = bar // 8
        if sec >= 1:
            four_floor(s, bar, clap_=True, open_hat=True)
        for k in range(8):                  # bass nhảy quãng tám
            s.put("bass", bass(c[0] - 24 + (12 if k % 2 else 0), s.beat / 2 * 0.7, cutoff=900), b0 + k / 2)
        for k in range(4):                  # hợp âm synth nhịp phách
            s.put("synth", sum(lead(m, s.beat * 0.35, 0.03, "saw") for m in c), b0 + k + 0.5)
        if sec in (2, 3, 5):                # giai điệu điệp khúc
            for k, iv in enumerate(mel):
                s.put("lead", lead(48 + 12 + iv + (2 if bar % 4 == 1 else 0), s.beat / 2 * 0.85, 0.07), b0 + k / 2)
        if bar % 8 == 7:                    # dồn trống trước đoạn mới
            for k in range(8):
                s.put("drums", snare(), b0 + 2 + k / 4, 0.5 + k * 0.05)
        s.put("pad", pad(c, s.beat * 4, 2600, 0.07), b0)
    return s.mix({"drums": 0.9, "hats": 0.6, "bass": 0.9, "synth": 0.7, "lead": 0.9, "pad": 0.6}, reverb=0.25)


def idol_ballad():
    """Ballad idol (kiểu nhạc tốt nghiệp / cảm động): piano + dây đàn tổng hợp, trống nhẹ ở nửa sau."""
    s = Song(76, 28)
    prog = [("C", "C"), ("G", "B"), ("Am", "A"), ("Em", "G"), ("F", "F"), ("C", "E"), ("Dm", "D"), ("G", "G")]
    for bar in range(s.bars):
        name, bnote = prog[bar % 8]
        c = chord(name, 4)
        b0 = bar * 4
        s.put("bass", piano(12 * 3 + NOTE[bnote], s.beat * 3.8, 0.6), b0)
        for k, m in enumerate([c[0], c[1], c[2], c[1] + 12, c[2], c[1]]):
            s.put("piano", piano(m, s.beat * 0.9, 0.45), b0 + k * 4 / 6)
        if bar >= 8:
            s.put("strings", pad(chord(name, 4), s.beat * 4, 1300, 0.12), b0)
        if bar >= 16:
            s.put("drums", kick(0.6), b0)
            s.put("drums", snare(), b0 + 2, 0.5)
            for k in range(4):
                s.put("hats", hat(), b0 + k, 0.35)
            s.put("melody", piano(c[2] + 12, s.beat * 1.8, 0.4), b0)
            s.put("melody", piano(c[1] + 12, s.beat * 1.8, 0.35), b0 + 2)
    return s.mix({"piano": 1.0, "bass": 0.8, "strings": 0.9, "drums": 0.6, "hats": 0.4, "melody": 0.9}, reverb=0.45)


def sub808(m, dur, vol=0.5):
    """Bass 808: sine trầm trượt cao độ nhẹ, ngân dài."""
    n = int((dur + 0.1) * SR)
    t = np.arange(n) / SR
    f = hz(m) * (1 + 0.5 * np.exp(-t * 40))
    x = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR))
    return vol * x * np.exp(-t * 1.2) * np.where(t < dur, 1, np.exp(-(t - dur) * 20))


def kpop_dance():
    """Dance-pop kiểu K-pop: kick 4/4, synth bass móc, stab hợp âm, đoạn "drop" giữa bài."""
    s = Song(124, 48)
    prog = ["Am", "F", "C", "G"]
    hook = [0, 0, 3, 0, 5, 3, 0, -2]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        sec = bar // 8
        if sec != 3:
            four_floor(s, bar, clap_=sec >= 1, open_hat=True)
        for k in range(8):                       # synth bass nảy theo nốt móc
            s.put("bass", bass(c[0] - 12 + (12 if k in (3, 6) else 0), s.beat / 2 * 0.6, cutoff=1100), b0 + k / 2)
        if sec >= 2 and sec != 3:                # stab hợp âm
            for k in (0.5, 1.5, 2.25, 3.5):
                s.put("stab", sum(lead(m + 12, s.beat * 0.2, 0.035, "saw") for m in c), b0 + k)
        if sec in (2, 4, 5):                     # giai điệu móc (hook)
            for k, iv in enumerate(hook):
                s.put("lead", lead(69 + iv, s.beat / 2 * 0.7, 0.07), b0 + k / 2)
        if sec == 3:                             # break: chỉ còn pad + tiếng snare dồn
            s.put("pad", pad(chord(prog[bar % 4], 4), s.beat * 4, 1200, 0.12), b0)
            for k in range(4 * (1 + bar % 8 // 2)):
                s.put("drums", snare(), b0 + k * 4 / (4 * (1 + bar % 8 // 2)), 0.5)
    return s.mix({"drums": 1.0, "hats": 0.6, "bass": 1.0, "stab": 0.8, "lead": 0.9, "pad": 0.7}, reverb=0.2)


def kpop_hiphop():
    """Nhịp trap / hip-hop (girl-crush, boy group): 808, hi-hat rải 1/16 – 1/32, snare nửa nhịp."""
    s = Song(140, 40)
    prog = ["Dm", "A#", "Gm", "A"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        sec = bar // 8
        if sec >= 1:
            for k in (0, 1.75, 2.5):
                s.put("drums", kick(1.1), b0 + k)
            s.put("drums", clap(), b0 + 2, 1.0)
            s.put("drums", snare(), b0 + 2, 0.6)
            for k in range(16):                  # hi-hat 1/16, cuối ô nhịp rải 1/32
                s.put("hats", hat(), b0 + k / 4, 0.8 if k % 2 == 0 else 0.5)
            if bar % 2 == 1:
                for k in range(8):
                    s.put("hats", hat(), b0 + 3 + k / 8, 0.4)
        s.put("bass", sub808(c[0] - 24, s.beat * 1.6), b0)
        s.put("bass", sub808(c[0] - 24, s.beat * 1.2), b0 + 2.5)
        if sec >= 2:                             # giai điệu tối, nốt kéo dài
            for k, m in enumerate([c[2] + 12, c[1] + 12, c[0] + 12, c[1] + 12]):
                s.put("lead", lead(m, s.beat * 0.8, 0.05, "saw"), b0 + k)
        s.put("pad", pad(chord(prog[bar % 4], 4), s.beat * 4, 1000, 0.09), b0)
    return s.mix({"drums": 1.0, "hats": 0.6, "bass": 1.0, "lead": 0.8, "pad": 0.7}, reverb=0.2)


def owarai_fun():
    """Vui nhộn kiểu nhạc lên sân khấu (出囃子): nhịp swing, bass đi bộ, pizzicato, vỗ tay, kèn ngắn."""
    s = Song(132, 40)
    prog = ["C", "A7", "Dm7", "G7"]
    walk = {"C": [0, 4, 7, 9], "A7": [0, 4, 7, 6], "Dm7": [0, 3, 7, 8], "G7": [0, 4, 7, 11]}
    for bar in range(s.bars):
        name = prog[bar % 4]
        c = chord(name, 4)
        root = c[0] - 24
        b0 = bar * 4
        sec = bar // 8
        for k, iv in enumerate(walk[name]):                         # bass đi bộ
            s.put("bass", pluck(root + iv, s.beat * 0.8, 0.8, 0.2), b0 + k)
        for k in range(4):                                          # hi-hat swing
            s.put("hats", hat(), b0 + k, 0.6)
            s.put("hats", hat(), b0 + k + 0.5, 0.4, swing=0.7)
        if sec >= 1:
            s.put("drums", kick(0.7), b0)
            s.put("drums", kick(0.7), b0 + 2)
            s.put("drums", clap(), b0 + 1)
            s.put("drums", clap(), b0 + 3)
        for k in (0.5, 1.5, 2.5, 3.5):                              # hợp âm pizzicato nhảy nhót
            s.put("pizz", sum(pluck(m, s.beat * 0.2, 0.3, 0.6) for m in c[:3]), b0 + k, swing=0.7)
        if sec in (2, 4) and bar % 2 == 1:                          # kèn "ta-đa!" cuối câu
            s.put("brass", brass([c[0] + 12, c[2] + 12], s.beat * 0.3, 0.10), b0 + 3)
            s.put("brass", brass([c[0] + 12, c[2] + 12], s.beat * 0.8, 0.10), b0 + 3.5)
        if sec == 3:                                                # đoạn giữa: piano rải vui
            for k, m in enumerate([c[0] + 12, c[1] + 12, c[2] + 12, c[1] + 12]):
                s.put("piano", piano(m, s.beat * 0.4, 0.45), b0 + k)
    return s.mix({"bass": 1.0, "hats": 0.5, "drums": 0.7, "pizz": 0.8, "brass": 0.9, "piano": 0.8}, reverb=0.2)


def owarai_tension():
    """Hồi hộp kiểu chờ công bố điểm M-1: nhịp đập đều, dây trầm, trống cuộn dâng lên rồi 'bùm'."""
    s = Song(100, 32)
    prog = ["Am", "F", "Dm", "E"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 3)
        b0 = bar * 4
        for k in range(8):                                          # nhịp tim
            s.put("bass", bass(c[0] - 12, s.beat * 0.3, cutoff=500, vol=0.3), b0 + k / 2, 1.0 if k % 2 == 0 else 0.6)
        s.put("pad", pad(c, s.beat * 4, 900 + 60 * (bar % 8), 0.12), b0)
        if bar % 8 >= 4:                                            # trống cuộn dâng dần
            n = 4 * (1 + (bar % 8) - 4)
            for k in range(n):
                s.put("drums", snare(), b0 + k * 4 / n, 0.25 + 0.1 * (bar % 8 - 4))
        if bar % 8 == 0 and bar > 0:                                # "bùm" mở đoạn mới
            s.put("drums", kick(1.3), b0)
            s.put("drums", tom(33), b0, 1.0)
            s.put("brass", brass(chord(prog[bar % 4], 3), s.beat * 2, 0.12), b0)
        if bar >= 16:
            for k in range(4):
                s.put("hats", hat(), b0 + k + 0.5, 0.5)
    return s.mix({"bass": 1.0, "pad": 0.9, "drums": 0.8, "brass": 0.9, "hats": 0.5}, reverb=0.35)


# ---------------------------------------------------------------- xuất file
def write_track(name: str, fn: str, dest: Path) -> Path:
    import soundfile as sf
    audio = globals()[fn]()
    peak = np.max(np.abs(audio)) + 1e-9
    audio = audio * min(1.0, 0.6 / peak)    # chừa ~4.4 dB để nén AAC không bị vỡ tiếng
    st = np.stack([audio, np.roll(audio, int(0.004 * SR))], axis=1)   # stereo nhẹ
    wav = dest / (name + ".tmp.wav")
    sf.write(wav, st.astype(np.float32), SR)
    out = dest / name
    subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "160k", str(out)],
                   check=True)
    wav.unlink()
    return out


def glock(m, dur=0.6, vel=0.5):
    """Chuông glockenspiel trong trẻo."""
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2.76 * f * t) + 0.15 * np.sin(2 * np.pi * 5.4 * f * t)
    return vel * 0.3 * x * np.exp(-t * 5.5)


def horse_fanfare():
    """Kèn fanfare kiểu trường đua + nhịp vó ngựa phi (3 tiếng/phách) – hào hứng, trong sáng."""
    s = Song(150, 32)
    prog = ["C", "F", "G", "C", "Am", "F", "G", "G"]
    fan = [(0, 67), (0.5, 72), (1, 76), (1.5, 79), (2, 84)]           # G C E G C – lên dần
    for bar in range(s.bars):
        name = prog[bar % 8]
        c = chord(name, 4)
        b0 = bar * 4
        if bar % 8 == 0:                                              # fanfare mở mỗi 8 ô nhịp
            for pos, m in fan:
                s.put("brass", brass([m, m - 12], s.beat * (1.8 if m == 84 else 0.45), 0.11), b0 + pos)
        elif bar % 2 == 1:
            s.put("brass", brass([c[0] + 12, c[1] + 12, c[2] + 12], s.beat * 1.6, 0.09), b0 + 2)
        if bar >= 1:                                                  # vó ngựa: ta-ta-TÁ mỗi phách
            for k in range(4):
                s.put("drums", tom(52), b0 + k, 0.35)
                s.put("drums", tom(55), b0 + k + 0.33, 0.35)
                s.put("drums", kick(0.8), b0 + k + 0.67)
            s.put("drums", snare(), b0 + 3.67, 0.5)
        for k in range(8):                                            # bass nảy
            s.put("bass", bass(c[0] - 24 + (7 if k % 2 else 0), s.beat * 0.4, vol=0.3, cutoff=500), b0 + k / 2)
        s.put("pad", pad([m for m in c], s.beat * 4, bright=2200, vol=0.08), b0)
    return s.mix({"brass": 1.0, "drums": 0.55, "bass": 0.8, "pad": 0.7}, reverb=0.3)


def horse_cozy():
    """Vui tươi, dễ thương (kiểu kể chuyện vui về ngựa): ukulele gảy, chuông glockenspiel, lắc nhẹ."""
    s = Song(104, 32)
    prog = ["F", "C", "Dm", "A#"]
    mel = [12, 9, 7, 9, 12, 14, 12, 7]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        for k in (0, 1, 1.5, 2.5, 3, 3.5):                            # ukulele gảy
            s.put("uke", sum(pluck(m, s.beat * 0.3, 0.35, 0.7) for m in c), b0 + k, swing=0.4)
        s.put("bass", pluck(c[0] - 12, s.beat * 0.8, 0.7, 0.15), b0)
        s.put("bass", pluck(c[2] - 12, s.beat * 0.8, 0.6, 0.15), b0 + 2)
        if bar >= 4:
            for k in range(8):                                        # lắc (shaker)
                s.put("hats", hat(), b0 + k / 2, 0.35 if k % 2 else 0.2)
            s.put("drums", kick(0.45), b0)
            s.put("drums", clap(), b0 + 2, 0.4)
        if bar >= 8 and bar % 2 == 0:                                 # giai điệu chuông
            for k, iv in enumerate(mel):
                if k % 2 == 0 or bar % 4 == 0:
                    s.put("glock", glock(c[0] + iv, s.beat * 0.4), b0 + k / 2)
    return s.mix({"uke": 0.9, "bass": 0.8, "hats": 0.5, "drums": 0.6, "glock": 0.8}, reverb=0.22)


def brand_startup():
    """Nhạc doanh nghiệp tươi sáng (kiểu video khởi nghiệp): piano nảy, pluck, kick nhẹ, vỗ tay."""
    s = Song(112, 32)
    prog = ["C", "G", "Am", "F"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        for k in range(8):                                            # piano móc 8 nốt
            s.put("piano", piano(c[(0, 2, 1, 2)[k % 4]] + 12, s.beat * 0.4, 0.4), b0 + k / 2)
        s.put("bass", bass(c[0] - 24, s.beat * 1.8, vol=0.28, cutoff=450), b0)
        s.put("bass", bass(c[0] - 24, s.beat * 1.8, vol=0.25, cutoff=450), b0 + 2)
        if bar >= 4:
            for k in range(4):
                s.put("drums", kick(0.55), b0 + k)
                s.put("hats", hat(), b0 + k + 0.5, 0.45)
            s.put("drums", clap(), b0 + 1, 0.5)
            s.put("drums", clap(), b0 + 3, 0.5)
        if bar >= 8:
            s.put("pad", pad(c, s.beat * 4, 2000, 0.07), b0)
            if bar % 2 == 0:
                for k, iv in enumerate((12, 16, 19, 24)):
                    s.put("pluck", pluck(c[0] + iv, s.beat * 0.3, 0.35, 0.6), b0 + 2 + k / 2)
    return s.mix({"piano": 0.9, "bass": 0.8, "drums": 0.55, "hats": 0.4, "pad": 0.7, "pluck": 0.7}, reverb=0.25)


def brand_retro():
    """Hoài niệm kiểu phim tài liệu Showa / ngày xưa: piano điện, nhịp chậm swing, bass gảy."""
    s = Song(88, 32)
    prog = ["Dm7", "G7", "C", "A7"]
    for bar in range(s.bars):
        name = prog[bar % 4]
        c = chord(name, 4)
        b0 = bar * 4
        s.put("ep", sum(epiano(m, s.beat * 1.6, 0.4) for m in c), b0)
        s.put("ep", sum(epiano(m + 12, s.beat * 0.8, 0.25) for m in c[1:3]), b0 + 2.5, swing=0.5)
        s.put("bass", pluck(c[0] - 24, s.beat * 0.9, 0.7, 0.1), b0)
        s.put("bass", pluck(c[2] - 24, s.beat * 0.9, 0.6, 0.1), b0 + 2)
        if bar >= 8:
            s.put("drums", kick(0.4), b0)
            s.put("drums", snare(), b0 + 2, 0.3)
            for k in range(4):
                s.put("hats", hat(), b0 + k + 0.5, 0.3, swing=0.6)
        if bar >= 16 and bar % 4 == 3:
            s.put("glock", glock(c[0] + 24, s.beat * 1.5, 0.4), b0 + 3)
    return s.mix({"ep": 1.0, "bass": 0.8, "drums": 0.5, "hats": 0.35, "glock": 0.6}, reverb=0.3)


KOREAN_PENTA = [0, 2, 5, 7, 9]     # ngũ cung kiểu Hàn (평조)


def gayageum(m, dur, vel=0.6):
    """Đàn gayageum: gảy mềm + rung (농현) ở cuối nốt."""
    x = pluck(m, dur, vel, bright=0.45)
    t = np.arange(len(x)) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) * 4, 0, 1)
    idx = np.clip(np.cumsum(vib).astype(int), 0, len(x) - 1)
    return x[idx]


def janggu(strong=True):
    """Trống janggu: mặt trầm (궁편) + tiếng roi tre (채편)."""
    a, b = taiko(False) * (0.7 if strong else 0.35), clap() * (0.5 if strong else 0.25)
    out = np.zeros(max(len(a), len(b)))
    out[:len(a)] += a
    out[:len(b)] += b
    return out


def history_sengoku():
    """Chiến Quốc Nhật: taiko dồn dập, sáo shakuhachi hùng tráng, shamisen, pad trầm."""
    s = Song(100, 32)
    root = 50
    for bar in range(s.bars):
        b0 = bar * 4
        s.put("taiko", taiko(True), b0, 1.0)
        s.put("taiko", taiko(True), b0 + 2, 0.8)
        if bar >= 4:
            for k in (1, 1.5, 3, 3.5):
                s.put("taiko", taiko(False), b0 + k, 0.6)
        if bar >= 8 and bar % 4 == 3:
            for k in range(8):
                s.put("taiko", taiko(False), b0 + k / 2, 0.4 + k * 0.06)
        if bar % 2 == 0:
            for k, idx in enumerate([0, 1, 3, 4, 3, 1]):
                s.put("shamisen", shamisen(root + MIYAKO[idx] + 12, s.beat * 0.5, 0.5), b0 + k * 0.5)
        if bar >= 8:
            line = [(0, 4, 1.5), (2, 3, 1.8)] if bar % 2 == 0 else [(0, 1, 3.5)]
            for pos, idx, d in line:
                s.put("flute", shakuhachi(root + MIYAKO[idx] + 24, s.beat * d, 0.13), b0 + pos)
        s.put("drone", pad([root - 12, root - 5], s.beat * 4, 600, 0.09), b0)
    return s.mix({"taiko": 0.9, "shamisen": 0.7, "flute": 0.9, "drone": 0.8}, reverb=0.4)


def history_edo():
    """Thời Edo: koto/shamisen thong thả, sáo, trống nhỏ – kể chuyện nhẹ nhàng."""
    s = Song(84, 32)
    root = 52
    for bar in range(s.bars):
        b0 = bar * 4
        for k, idx in enumerate((0, 2, 4, 2) if bar % 2 == 0 else (1, 3, 4, 3)):
            s.put("koto", pluck(root + MIYAKO[idx] + 12, s.beat * 0.9, 0.45, 0.35), b0 + k)
        if bar >= 4:
            s.put("taiko", taiko(False), b0, 0.4)
            s.put("taiko", taiko(False), b0 + 2.5, 0.3)
        if bar >= 8 and bar % 2 == 1:
            s.put("flute", shakuhachi(root + MIYAKO[(bar // 2) % 5] + 24, s.beat * 3, 0.10), b0)
        s.put("drone", pad([root - 12], s.beat * 4, 500, 0.06), b0)
    return s.mix({"koto": 1.0, "taiko": 0.6, "flute": 0.8, "drone": 0.7}, reverb=0.45)


def history_joseon():
    """Cung đình Joseon: gayageum ngũ cung, janggu nhịp 3 (세마치), pad như đàn haegeum."""
    s = Song(90, 36, beats_per_bar=3)
    root = 50
    for bar in range(s.bars):
        b0 = bar * 3
        s.put("janggu", janggu(True), b0)
        s.put("janggu", janggu(False), b0 + 1.5)
        s.put("janggu", janggu(False), b0 + 2)
        for k, idx in enumerate((0, 2, 4) if bar % 2 == 0 else (3, 2, 1)):
            s.put("gaya", gayageum(root + KOREAN_PENTA[idx] + 12, s.beat * 1.2, 0.55), b0 + k)
        if bar >= 6:
            s.put("haegeum", shakuhachi(root + KOREAN_PENTA[(bar // 2) % 5] + 24, s.beat * 2.6, 0.09), b0)
        s.put("drone", pad([root - 12, root - 5], s.beat * 3, 500, 0.07), b0)
    return s.mix({"janggu": 0.8, "gaya": 1.0, "haegeum": 0.8, "drone": 0.7}, reverb=0.4)


def history_battle_ko():
    """Chiến trận (Imjin, Goguryeo…): trống lớn dồn dập, gayageum nhanh, kèn nabal (brass)."""
    s = Song(116, 32)
    root = 50
    for bar in range(s.bars):
        b0 = bar * 4
        for k in (0, 1.5, 2, 3):
            s.put("drum", taiko(True), b0 + k, 0.8 if k in (0, 2) else 0.55)
        if bar >= 4:
            for k in range(8):
                s.put("gaya", gayageum(root + KOREAN_PENTA[(k + bar) % 5] + 12, s.beat * 0.4, 0.45), b0 + k / 2)
        if bar >= 8 and bar % 4 == 0:
            s.put("nabal", brass([root + 12, root + 19], s.beat * 3, 0.10), b0)
        s.put("drone", pad([root - 12, root - 5], s.beat * 4, 650, 0.08), b0)
    return s.mix({"drum": 0.9, "gaya": 0.8, "nabal": 0.8, "drone": 0.8}, reverb=0.35)


def esports_hype():
    """EDM kiểu giải eSports: 4/4 dồn, bass "nhún" theo kick, lead saw, đoạn build-up."""
    s = Song(128, 32)
    prog = ["Am", "F", "C", "G"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        sec = bar // 8
        if sec != 1:                                                  # đoạn 8–15: build-up không kick
            four_floor(s, bar, hats=True, clap_=sec >= 2, open_hat=sec >= 2)
        else:
            for k in range(bar % 8 + 2):                              # snare dồn dần
                s.put("drums", snare(), b0 + k * 4 / (bar % 8 + 2), 0.3 + 0.05 * (bar % 8))
        for k in range(8):                                            # bass "nhún" (offbeat)
            if k % 2 == 1:
                s.put("bass", bass(c[0] - 24, s.beat * 0.45, vol=0.32, cutoff=700), b0 + k / 2)
        s.put("pad", pad(c, s.beat * 4, 2600 if sec >= 2 else 1400, 0.08), b0)
        if sec >= 2:
            for k, iv in enumerate((0, 7, 12, 7, 15, 12, 7, 3)):
                s.put("lead", lead(c[0] + 12 + iv, s.beat * 0.4, vol=0.09, kind="saw"), b0 + k / 2)
    return s.mix({"drums": 0.75, "hats": 0.5, "bass": 0.9, "pad": 0.7, "lead": 0.8}, reverb=0.25)


def esports_epic():
    """Hùng tráng kiểu nhạc mở màn chung kết: trống lớn, kèn, pad dày, arpeggio synth."""
    s = Song(100, 32)
    prog = ["Dm", "A#", "F", "C"]
    for bar in range(s.bars):
        c = chord(prog[bar % 4], 4)
        b0 = bar * 4
        s.put("drums", taiko(True), b0, 0.8)
        s.put("drums", taiko(True), b0 + 2.5, 0.6)
        if bar >= 8:
            s.put("drums", snare(), b0 + 1, 0.5)
            s.put("drums", snare(), b0 + 3, 0.5)
        for k in range(8):                                            # arpeggio synth
            s.put("arp", pluck(c[k % 3] + 12, s.beat * 0.3, 0.35, 0.8), b0 + k / 2)
        s.put("pad", pad(c, s.beat * 4, 1800, 0.10), b0)
        s.put("bass", bass(c[0] - 24, s.beat * 3.8, vol=0.3, cutoff=400), b0)
        if bar >= 16 and bar % 2 == 0:
            s.put("brass", brass([c[0] + 12, c[2] + 12], s.beat * 3.5, 0.10), b0)
    return s.mix({"drums": 0.85, "arp": 0.6, "pad": 0.8, "bass": 0.8, "brass": 0.9}, reverb=0.35)


def ensure_all(log=print, force: bool = False) -> int:
    """Tạo các bài còn thiếu. Trả về số bài vừa tạo."""
    BGM.mkdir(parents=True, exist_ok=True)
    made = 0
    for name, _, fn in TRACKS:
        if force or not (BGM / name).exists():
            log(f"  🎵 đang soạn nhạc nền: {name}")
            write_track(name, fn, BGM)
            made += 1
    return made


if __name__ == "__main__":
    n = ensure_all(force="--force" in sys.argv)
    print(f"Xong, đã tạo {n} bài trong {BGM}")
