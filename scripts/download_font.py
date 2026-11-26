"""Tải font vào thư mục fonts/:
  • Noto Sans CJK JP Black  – chữ phụ đề đậm (giống video mẫu)
  • Noto Serif CJK JP Black – chữ tiêu đề kiểu Minh triều đậm (thẻ tiêu đề bố cục toàn màn hình, video mẫu 井上尚弥)"""
import socket
import sys
import urllib.request
from pathlib import Path

socket.setdefaulttimeout(90)   # mạng chập chờn → không treo mãi
FONTS = Path(__file__).resolve().parent.parent / "fonts"
FONTS.mkdir(exist_ok=True)
ITEMS = [
    ("NotoSansCJKjp-Black.otf", True, [
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Black.otf",
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansCJKjp-Black.otf"]),
    ("NotoSerifCJKjp-Black.otf", False, [
        "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/Japanese/NotoSerifCJKjp-Black.otf",
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/Japanese/NotoSerifCJKjp-Black.otf"]),
]
failed = False
for name, required, urls in ITEMS:
    dest = FONTS / name
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print("Font đã có:", dest)
        continue
    ok = False
    for u in urls:
        try:
            print("Đang tải font:", u)
            urllib.request.urlretrieve(u, dest)
            if dest.stat().st_size > 1_000_000:
                print("OK:", dest)
                ok = True
                break
        except Exception as e:  # noqa: BLE001
            print("  lỗi:", e)
    if not ok:
        dest.unlink(missing_ok=True)
        print(f"Không tải được {name}." + (" Hãy tự tải và bỏ vào thư mục fonts/" if required
                                           else " (không bắt buộc – tiêu đề sẽ dùng chữ không chân)"))
        failed = failed or required
sys.exit(1 if failed else 0)
