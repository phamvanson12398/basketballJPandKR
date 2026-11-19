"""Tải font Noto Sans CJK JP Black (chữ đậm giống video mẫu) vào thư mục fonts/."""
import sys
import urllib.request
from pathlib import Path

URLS = [
    "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Black.otf",
    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansCJKjp-Black.otf",
]
dest = Path(__file__).resolve().parent.parent / "fonts" / "NotoSansCJKjp-Black.otf"
dest.parent.mkdir(exist_ok=True)
if dest.exists() and dest.stat().st_size > 1_000_000:
    print("Font đã có:", dest)
    sys.exit(0)
for u in URLS:
    try:
        print("Đang tải font:", u)
        urllib.request.urlretrieve(u, dest)
        if dest.stat().st_size > 1_000_000:
            print("OK:", dest)
            sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print("  lỗi:", e)
print("Không tải được font. Hãy tự tải NotoSansCJKjp-Black.otf và bỏ vào thư mục fonts/")
sys.exit(1)
