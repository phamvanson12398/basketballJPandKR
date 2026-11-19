"""Đường dẫn và cài đặt chung."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
LIBRARY = ROOT / "library"
VOICES = LIBRARY / "voices"
BGM = LIBRARY / "bgm"
FONTS = ROOT / "fonts"
STATIC = Path(__file__).resolve().parent / "static"
SETTINGS_FILE = ROOT / "settings.json"

for d in (PROJECTS, VOICES, BGM, FONTS):
    d.mkdir(parents=True, exist_ok=True)

# Khung hình giống video mẫu
W, H = 1080, 1920
FPS = 30
MEDIA_W, MEDIA_H = 1080, 608   # khung 16:9 – ảnh hiện nguyên vẹn, không cắt, không làm mờ
MEDIA_Y = (H - MEDIA_H) // 2 - 80   # mép trên của khung (giữa màn hình, hơi lệch lên)
SUB_TOP_BOTTOM_Y = MEDIA_Y + 4            # chân của dòng sub phía trên khung
SUB_BOTTOM_TOP_Y = MEDIA_Y + MEDIA_H - 18  # đỉnh của dòng sub phía dưới khung
IMAGE_RATIO = 16 / 9
IMAGE_RATIO_TOL = 0.04   # chấp nhận lệch ±4% so với 16:9 (co giãn không nhận ra)
SUB_LINE_SPACING = 0.76  # khoảng cách dòng (x cỡ chữ), sát nhau giống mẫu

# Tốc độ đọc tiếng Nhật ước tính (ký tự / giây) để ước lượng thời lượng
JA_CHARS_PER_SEC = 6.5
IMAGE_SEC = 4.5          # mỗi ảnh 4–5 giây
VIDEO_RATIO = 0.30       # 70% ảnh / 30% video

DEFAULT_SETTINGS = {
    "claude_model": "",          # để trống = model mặc định của Claude CLI
    "image_sources": ["duckduckgo", "bing", "yahoo"],   # nguồn ảnh miễn phí, không cần key
    "video_encoder": "auto",     # auto | libx264 | h264_nvenc
    "tts_num_step": 32,
    "subtitle_font": "Noto Sans CJK JP Black",
    "subtitle_size": 124,
    "use_claude_for_highlight": True,
    "image_zoom": False,         # zoom nhẹ ảnh (sẽ che mất một chút mép ảnh) – mặc định tắt
}


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return s


def save_settings(data: dict) -> dict:
    s = load_settings()
    s.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s


def ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"
