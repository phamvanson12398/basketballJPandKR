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
MEDIA_W = 1080   # khung ảnh/video rộng hết màn hình; CHIỀU CAO chỉnh trong Cài đặt (media_height)
IMAGE_RATIO = 16 / 9
IMAGE_RATIO_TOL = 0.04   # chấp nhận lệch ±4% so với 16:9 (co giãn không nhận ra)
SUB_LINE_SPACING = 0.76  # khoảng cách dòng (x cỡ chữ), sát nhau giống mẫu

# Tốc độ đọc tiếng Nhật ước tính (ký tự / giây) để ước lượng thời lượng
JA_CHARS_PER_SEC = 6.5
IMAGE_SEC = 4.5          # độ dài mỗi cảnh thuyết minh (~4.5 giây) – dùng khi AI chia cảnh
SWITCH_SEC = 3.0         # cứ ~3 giây đổi ảnh / đổi đoạn video một lần (giữ chân người xem)
SWITCH_SEC_HISTORY = 2.5 # lịch sử: đổi ảnh nhanh như video mẫu 島流し (đo được ~2,6 giây/ảnh, đổi đúng lúc đổi sub)


def switch_sec(p: dict | None) -> float:
    """Bao nhiêu giây đổi ảnh một lần cho dự án này."""
    if p and (p.get("genre") == "history" or (p.get("sport") == "history" and p.get("genre") not in ("news", "brand"))):
        return SWITCH_SEC_HISTORY
    return SWITCH_SEC
VIDEO_RATIO = 0.30       # 70% ảnh / 30% video

DEFAULT_SETTINGS = {
    "claude_model": "",          # để trống = model mặc định của Claude CLI
    "image_sources": ["google", "duckduckgo", "bing", "yahoo", "naver", "news"],   # nguồn ảnh miễn phí, không cần key
    "sources_v2": False,         # đã lưu cài đặt có Naver / ảnh từ báo chưa
    "video_encoder": "auto",     # auto | libx264 | h264_nvenc
    "tts_num_step": 32,
    "subtitle_font": "Noto Sans CJK JP Black",
    "subtitle_size": 124,
    "media_height": 680,         # chiều cao khung ảnh/video (px). 608 = đúng 16:9; lớn hơn = cao hơn
    "media_height_korea": 1140,  # chiều cao khung ảnh/video của bố cục Hàn Quốc (px), khung luôn nằm giữa màn hình
    "sub_gap": 40,               # khoảng cách giữa chữ và khung ảnh/video (px)
    "use_claude_for_highlight": True,
    "facebook_video": True,
    "verify_person_video": True,
    "smart_image_pick": True,
    "fact_check": True,
    "vision_provider": "claude",   # AI xem ảnh/video: antigravity / gemini / claude / off (viết content luôn là Claude)
    "agy_command": "agy -p {prompt}",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "retention_edit": True,        # biên tập giữ chân người xem sau khi viết (thi 5 hook, sửa cảnh yếu)            # tự kiểm tra sự thật sau khi viết content (thêm ~2–5 phút)      # Claude xem ảnh ứng viên, chọn ảnh hợp nội dung (chậm hơn ~15–30s/cảnh ảnh)   # Claude xem hình xác nhận video có ĐÚNG nhân vật (chậm hơn ~20–40s/cảnh video)     # tìm thêm video công khai trên Facebook (qua công cụ tìm kiếm, không cần đăng nhập)
    "image_zoom": True,          # zoom / lia nhẹ ảnh cho sinh động
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


def layout() -> dict:
    """Vị trí khung ảnh/video và sub — dùng CHUNG cho cả ảnh và video."""
    s = load_settings()
    mh = max(400, min(1400, int(s.get("media_height") or 680))) // 2 * 2
    gap = max(0, min(300, int(s.get("sub_gap") if s.get("sub_gap") is not None else 40)))
    my = (H - mh) // 2 - 80          # mép trên khung (giữa màn hình, hơi lệch lên)
    return {"media_h": mh, "media_y": my,
            "sub_top": my + 4 - gap,          # chân dòng sub phía trên khung
            "sub_bottom": my + mh - 18 + gap}  # đỉnh dòng sub phía dưới khung


def ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"
