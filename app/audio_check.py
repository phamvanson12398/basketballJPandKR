"""Kiểm tra & cân bằng âm lượng giọng đọc từng cảnh.

Vì sao cần: OmniVoice thỉnh thoảng tạo ra 1 tiếng "lách tách" rất to hoặc đọc nhỏ bất thường.
Nếu chuẩn hóa theo đỉnh (peak) thì cả cảnh bị kéo nhỏ theo tiếng lách tách đó → nghe riêng vẫn thấy,
nhưng ghép vào video cạnh các cảnh khác thì gần như im lặng (bộ chuẩn -14 LUFS không kéo lên được).
"""
import numpy as np

TARGET_RMS = 0.10        # độ to giọng nói mong muốn (~ -20 dBFS)
FRAME_SEC = 0.02


def clean(a: np.ndarray) -> np.ndarray:
    """Bỏ mẫu hỏng (NaN/inf), chuyển về mono float32."""
    a = np.asarray(a, dtype=np.float32)
    if a.ndim > 1:
        a = a.mean(axis=1)
    return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)


def resample(a: np.ndarray, sr: int, target: int) -> np.ndarray:
    if sr == target or a.size == 0:
        return a
    n = int(round(len(a) * target / sr))
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)


def _frames(a: np.ndarray, sr: int) -> np.ndarray:
    f = max(1, int(sr * FRAME_SEC))
    n = len(a) // f
    if n == 0:
        return np.sqrt(np.mean(a ** 2, keepdims=True) + 1e-12)
    return np.sqrt(np.mean(a[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)


def stats(a: np.ndarray, sr: int) -> dict:
    """speech_rms: độ to phần có tiếng nói; voiced_sec: số giây có tiếng nói thật."""
    r = _frames(a, sr)
    if r.size == 0 or r.max() < 1e-4:
        return {"speech_rms": 0.0, "voiced_sec": 0.0}
    ref = np.percentile(r, 95)
    voiced = r > max(ref * 0.1, 3e-4)          # khung có tiếng nói (≥ -20 dB so với phần to)
    return {"speech_rms": float(np.sqrt(np.mean(r[voiced] ** 2))) if voiced.any() else 0.0,
            "voiced_sec": float(voiced.sum() * FRAME_SEC)}


def _limit(a: np.ndarray, knee: float = 0.9) -> np.ndarray:
    """Giới hạn đỉnh mềm: tiếng lách tách bị nén lại thay vì kéo nhỏ cả cảnh."""
    m = np.abs(a)
    over = m > knee
    if over.any():
        a = a.copy()
        a[over] = np.sign(a[over]) * (knee + (1 - knee) * np.tanh((m[over] - knee) / (1 - knee)))
    return a


def level(a: np.ndarray, sr: int, max_gain: float = 20.0) -> np.ndarray:
    """Đưa giọng nói về cùng độ to (theo phần có tiếng nói, không theo đỉnh)."""
    a = clean(a)
    st = stats(a, sr)
    if st["speech_rms"] <= 0:
        return a
    gain = min(max_gain, TARGET_RMS / st["speech_rms"])
    return _limit(a * gain).astype(np.float32)


def longest_gap(a: np.ndarray, sr: int) -> tuple[float, float]:
    """Khoảng lặng dài nhất NẰM GIỮA lời đọc → (độ dài giây, bắt đầu ở giây thứ mấy)."""
    r = _frames(clean(a), sr)
    if r.size < 3 or r.max() < 1e-4:
        return 0.0, 0.0
    voiced = r > max(np.percentile(r, 95) * 0.03, 2e-4)
    idx = np.where(voiced)[0]
    if idx.size < 2:
        return 0.0, 0.0
    best, at, run_start = 0, 0, None
    for i in range(idx[0], idx[-1] + 1):
        if not voiced[i]:
            run_start = i if run_start is None else run_start
            if i - run_start + 1 > best:
                best, at = i - run_start + 1, run_start
        else:
            run_start = None
    return best * FRAME_SEC, at * FRAME_SEC


def problem(a: np.ndarray, sr: int, expect_sec: float, min_ratio: float = 0.4) -> str:
    """Trả về mô tả lỗi (tiếng Việt) nếu đoạn đọc có vẻ hỏng, rỗng nếu ổn."""
    raw = np.asarray(a, dtype=np.float32)
    if raw.size and not np.isfinite(raw).all():
        return "có mẫu âm thanh hỏng"
    st = stats(clean(raw), sr)
    if st["voiced_sec"] < 0.3:
        return "gần như không có tiếng"
    gap, at = longest_gap(raw, sr)
    if gap >= 1.2:
        return f"có khoảng lặng {gap:.1f}s giữa câu (từ giây {at:.1f} của cảnh)"
    if expect_sec > 2 and st["voiced_sec"] < expect_sec * min_ratio:
        return f"chỉ có {st['voiced_sec']:.1f}s tiếng nói (dự kiến ~{expect_sec:.0f}s) → có thể bị đọc thiếu"
    return ""


# ---------------------------------------------------------------- CHUẨN HÓA -14 LUFS (thay loudnorm của FFmpeg)
# Một số bản FFmpeg trên Windows: loudnorm làm cụt vài giây âm thanh cuối video → tự tính theo ITU-R BS.1770.
def _biquad_mag(f: np.ndarray, sr: int, kind: str, fc: float, q: float, gain_db: float = 0.0) -> np.ndarray:
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * fc / sr
    c, alpha = np.cos(w0), np.sin(w0) / (2 * q)
    if kind == "shelf":
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * alpha), -2 * A * ((A - 1) + (A + 1) * c),
             A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * alpha)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * alpha, 2 * ((A - 1) - (A + 1) * c),
             (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * alpha]
    else:  # high-pass
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
        a = [1 + alpha, -2 * c, 1 - alpha]
    z = np.exp(-2j * np.pi * f / sr)
    return np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))


def loudness(x: np.ndarray, sr: int) -> float:
    """Độ to tích hợp (LUFS) theo BS.1770: lọc K-weighting + cổng -70 / -10."""
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x          # (n, kênh)
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / sr)
    k = _biquad_mag(f, sr, "shelf", 1681.97, 0.7072, 3.99984) * _biquad_mag(f, sr, "hp", 38.135, 0.5003)
    y = np.fft.irfft(np.fft.rfft(x, axis=0) * k[:, None], n=n, axis=0)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if n < blk:
        return -70.0
    p2 = np.cumsum(np.concatenate([np.zeros((1, y.shape[1])), y ** 2]), axis=0)
    starts = np.arange(0, n - blk + 1, hop)
    z = ((p2[starts + blk] - p2[starts]) / blk).sum(axis=1)
    lk = -0.691 + 10 * np.log10(z + 1e-12)
    g = z[lk > -70]
    if g.size == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = z[(lk > -70) & (lk > rel)]
    return float(-0.691 + 10 * np.log10(g.mean() + 1e-12))


def normalize_lufs(x: np.ndarray, sr: int, target: float = -14.0, ceiling_db: float = -1.5) -> np.ndarray:
    """Đưa cả bản trộn về -14 LUFS (chuẩn TikTok/YouTube), đỉnh không vượt -1.5 dB."""
    gain = min(30.0, 10 ** ((target - loudness(x, sr)) / 20))
    c = 10 ** (ceiling_db / 20)
    return (_limit(x * gain / c) * c).astype(np.float32)
