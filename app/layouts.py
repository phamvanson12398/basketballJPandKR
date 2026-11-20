"""Bố cục (layout) theo thể loại — phần chữ, khối màu và hiệu ứng chuyển động đều vẽ bằng ASS.

  sports    – bố cục gốc (nền trắng, sub đen trên/dưới khung) — GIỮ NGUYÊN, vẽ trong render.build_ass
  news      – nền navy, dải đỏ NEWS + 速報, ô tiêu đề trắng, hộp phụ đề trắng, thanh tiến độ điểm tin
  ranking   – nền đen, tiêu đề TOP vàng, màn "第N位" nảy ra → huy hiệu vàng/bạc/đồng, dải tên vàng
  biography – nền kem, ảnh viền trắng rơi vào khung, năm chạy số, chương gõ chữ, dòng thời gian
  general   – nền trắng, câu hỏi có vệt bút dạ vàng quét, hộp phụ đề tối

Kích thước chữ: ASS size ≈ 1.45 × cỡ chữ thật (px) với font Noto CJK.
"""
import re
from pathlib import Path

from .config import H, W, layout as frame_layout, load_settings

LAYOUTS = ["sports", "news", "ranking", "biography", "general"]
K = 1.45          # đổi cỡ chữ px → cỡ ASS
FPS_FLASH = 0.12  # chớp chuyển cảnh (giây)

# màu ASS (&HBBGGRR&)
WHITE, BLACK = "&HFFFFFF&", "&H000000&"
NAVY, RED = "&H3A1F0B&", "&H3D26D7&"
YELLOW, SILVER, BRONZE, STEEL = "&H15CCFA&", "&HC0C0C0&", "&H327FCD&", "&HB8A394&"
CREAM, BROWN, BROWN2, TAN, INK, FADED = "&HDFECF4&", "&H2A2F3B&", "&H345E8B&", "&H6889B0&", "&H171A1F&", "&H7C93A8&"
HL_RED, MARKER, DARKBOX = "&H2626DC&", "&H47E0FD&", "&H271811&"


def resolve(p: dict) -> str:
    lay = p.get("layout") or "auto"
    if lay in LAYOUTS:
        return lay
    g = p.get("genre") or "sports"
    return g if g in LAYOUTS else "sports"


def geometry(name: str) -> dict:
    """Màu nền + vị trí khung ảnh/video cho từng bố cục (dùng chung chiều cao khung trong Cài đặt)."""
    L = frame_layout()
    my, mh = L["media_y"], L["media_h"]
    g = {"bg": "white", "x": 0, "y": my, "w": W, "h": mh, "frame": 0, "drop": False}
    if name == "news":
        g["bg"] = "0x0b1f3a"
    elif name == "ranking":
        g["bg"] = "0x0f0f12"
    elif name == "biography":
        # ảnh nhỏ lại, viền trắng 20px như ảnh in, rơi nhẹ + nghiêng khi vào cảnh
        g.update(bg="0xf4ecdf", x=60, y=my + 20, w=960, h=mh - 40, frame=20, drop=True)
    return g


# ------------------------------------------------------------------ tiện ích ASS
def t(sec: float) -> str:
    cs = int(round(max(0.0, sec) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def esc(s: str) -> str:
    return str(s).replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ")


def rect(w, h):
    return f"m 0 0 l {w:.0f} 0 l {w:.0f} {h:.0f} l 0 {h:.0f}"


def rrect(w, h, r):
    k = r * 0.55
    return (f"m {r} 0 l {w - r} 0 b {w - r + k} 0 {w} {r - k} {w} {r} l {w} {h - r} "
            f"b {w} {h - r + k} {w - r + k} {h} {w - r} {h} l {r} {h} b {r - k} {h} 0 {h - r + k} 0 {h - r} "
            f"l 0 {r} b 0 {r - k} {r - k} 0 {r} 0")


def circle(d):
    r, k = d / 2, d / 2 * 0.55
    return (f"m {r} 0 b {r + k} 0 {d} {r - k} {d} {r} b {d} {r + k} {r + k} {d} {r} {d} "
            f"b {r - k} {d} 0 {r + k} 0 {r} b 0 {r - k} {r - k} 0 {r} 0")


def text_width(s: str, px: float) -> float:
    w = 0.0
    for ch in str(s):
        w += px * (0.32 if ch == " " else 0.58 if ord(ch) < 0x2E80 else 1.0)
    return w


def fit(s: str, px: float, maxw: float = 1000) -> str:
    """Thu hẹp chữ theo chiều ngang nếu dòng quá dài (không tràn màn hình)."""
    w = text_width(s, px)
    return f"\\fscx{max(55, int(100 * maxw / w))}" if w > maxw else ""


class Ev:
    def __init__(self):
        self.rows = []

    def add(self, a, b, tags, text="", layer=0):
        if b - a > 0.01:
            self.rows.append(f"Dialogue: {layer},{t(a)},{t(b)},D,,0,0,0,,{{{tags}}}{text}")

    def text(self, a, b, x, y, s, px, color, an=8, layer=5, extra="", maxw=1000):
        self.add(a, b, f"\\an{an}\\pos({x:.0f},{y:.0f})\\fs{px * K:.0f}\\c{color}{fit(s, px, maxw)}{extra}", esc(s), layer)

    def shape(self, a, b, x, y, path, color, layer=1, extra="", an=7):
        self.add(a, b, f"\\an{an}\\pos({x:.0f},{y:.0f})\\p1\\c{color}{extra}", path, layer)

    def pop_text(self, a, b, x, y, s, px, color, layer=6, maxw=1000):
        """Chữ bật ra: 70% → 108% → 100%."""
        self.text(a, b, x, y, s, px, color, layer=layer, maxw=maxw,
                  extra="\\fscy70\\alpha&HFF&\\t(0,120,\\fscy108\\alpha&H00&)\\t(120,200,\\fscy100)")


HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,{font},80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ------------------------------------------------------------------ phụ đề (chung cho bố cục mới)
def fit_lines(chunk: str, korean: bool, maxlen: int) -> list[str]:
    """Gộp các dòng ngắn lại cho vừa chiều ngang (phụ đề bố cục mới rộng hơn bố cục gốc)."""
    sep = " " if korean else ""
    parts = [x.strip() for x in chunk.split("\n") if x.strip()] or [chunk]
    out = []
    for ln in parts:
        if out and len(out[-1]) + len(sep) + len(ln) <= maxlen:
            out[-1] = out[-1] + sep + ln
        else:
            out.append(ln)
    if len(out) > 2:
        # tối đa 2 dòng: chia đôi tại chỗ ngắt dòng gần giữa nhất (dòng dài sẽ được thu hẹp chữ)
        best = min(range(1, len(parts)),
                   key=lambda i: max(len(sep.join(parts[:i])), len(sep.join(parts[i:]))))
        out = [sep.join(parts[:best]), sep.join(parts[best:])]
    return out


def chunk_timing(scene: dict, t0: float):
    chunks = [c.strip() for c in scene.get("chunks", []) if c.strip()]
    speech = max(0.3, float(scene["duration"]) - 0.18)
    weights = [max(1, len(c.replace("\n", "").replace(" ", ""))) for c in chunks]
    tot = sum(weights) or 1
    acc, out = t0, []
    for i, (c, wgt) in enumerate(zip(chunks, weights)):
        d = speech * wgt / tot
        end = acc + d if i < len(chunks) - 1 else t0 + float(scene["duration"])
        out.append((c, acc, end))
        acc += d
    return out


def captions(e: Ev, scenes, starts, y0, color, box=None, px=72):
    """Mỗi lần hiện 1 chunk dưới khung, chữ bật ra. box = màu hộp nền (None = không hộp)."""
    lh = px * 1.18
    for sc, st in zip(scenes, starts):
        korean = bool(re.search(r"[가-힣]", "".join(sc.get("chunks", []))))
        for chunk, a, b in chunk_timing(sc, st):
            lines = fit_lines(chunk, korean, 15 if korean else 12)
            if box:
                hgt = len(lines) * lh + 44
                e.shape(a, b, 60, y0, rrect(960, hgt, 22), box, layer=3, extra="\\fad(80,0)")
            for k, ln in enumerate(lines):
                e.pop_text(a, b, W // 2, y0 + (22 if box else 0) + k * lh, ln, px, color, maxw=900)


def scene_flash(e: Ev, starts, g):
    """Chớp trắng ngắn trên khung ảnh khi chuyển cảnh."""
    for st in starts[1:]:
        e.shape(st, st + FPS_FLASH, g["x"], g["y"], rect(g["w"], g["h"]), WHITE, layer=4,
                extra="\\alpha&H40&\\t(0,120,\\alpha&HFF&)")


def segments(scenes, starts, total, key):
    """Gom các cảnh liên tiếp có cùng giá trị key → [(giá trị, bắt đầu, kết thúc, cảnh đầu)]."""
    segs = []
    for i, (sc, st) in enumerate(zip(scenes, starts)):
        v = sc.get(key)
        end = starts[i + 1] if i + 1 < len(starts) else total
        if segs and segs[-1][0] == v:
            segs[-1][2] = end
        else:
            segs.append([v, st, end, sc])
    return segs


# ------------------------------------------------------------------ 📰 TIN TỨC
def news(e: Ev, p, scenes, starts, total, g):
    scr = p.get("screen") or {}
    stories = scr.get("stories") or [{}]
    my, mb = g["y"], g["y"] + g["h"]
    yb, ybox = my - 310, my - 240
    segs = segments(scenes, starts, total, "story")
    n_st = max(1, len(stories))
    for idx, (sv, a, b, _) in enumerate(segs):
        try:
            si = max(1, min(n_st, int(sv or 1)))
        except (TypeError, ValueError):
            si = 1
        story = stories[si - 1] if si - 1 < len(stories) else {}
        slide = "\\move(-1080,{y},0,{y},0,280)"
        e.shape(a, b, 0, yb, rect(1080, 70), RED, layer=1, extra=slide.format(y=yb))
        e.add(a, b, f"\\an4\\fs{44 * K:.0f}\\c{WHITE}\\move(-1000,{yb + 35},60,{yb + 35},0,280){fit(scr.get('band', 'NEWS'), 44, 700)}",
              esc("NEWS ・ " + str(scr.get("band", ""))), 2)
        if scr.get("breaking") and idx == 0:
            blink = "\\t(300,450,\\alpha&HFF&)\\t(450,600,\\alpha&H00&)\\t(600,750,\\alpha&HFF&)\\t(750,900,\\alpha&H00&)"
            e.shape(a + 0.3, total, 850, yb + 12, rrect(180, 48, 8), WHITE, layer=2, extra=blink)
            e.add(a + 0.3, total, f"\\an5\\pos(940,{yb + 36})\\fs{38 * K:.0f}\\c{RED}{blink}",
                  "速報" if (p.get("lang") or "ja") == "ja" else "속보", 3)
        # ô tiêu đề trắng mở xuống, chữ trồi lên
        e.shape(a, b, 0, ybox, rect(1080, 220), WHITE, layer=1, extra="\\fscy0\\t(0,250,\\fscy100)" if idx == 0 else "")
        e.add(a + 0.2, b, f"\\an8\\fs{74 * K:.0f}\\c{NAVY}{fit(story.get('headline', ''), 74)}\\fad(150,0)"
                          f"\\move(540,{ybox + 40},540,{ybox + 16},0,220)", esc(story.get("headline", p.get("title", ""))), 2)
        if story.get("subhead"):
            e.text(a + 0.35, b, 540, ybox + 118, story["subhead"], 60, "&H55413A&", layer=2, extra="\\fad(150,0)")
        if story.get("source"):
            e.add(a + 0.6, b, f"\\an3\\pos(1060,{mb - 12})\\fs{28 * K:.0f}\\c{WHITE}\\bord8\\3c{BLACK}\\3a&H60&\\fad(200,0)",
                  esc(("出典: " if (p.get("lang") or "ja") == "ja" else "출처: ") + story["source"]), 3)
        if n_st > 1:   # thanh tiến độ điểm tin
            bw, gap = 130, 20
            x0 = (W - (n_st * bw + (n_st - 1) * gap)) // 2
            for k in range(n_st):
                x = x0 + k * (bw + gap)
                done = k < si - 1
                e.shape(a, b, x, mb + 290, rrect(bw, 14, 7), WHITE if done else "&H69554A&", layer=1)
            e.shape(a, b, x0 + (si - 1) * (bw + gap), mb + 290, rrect(bw, 14, 7), WHITE, layer=2,
                    extra=f"\\fscx0\\t(0,{int((b - a) * 1000)},\\fscx100)")
            e.text(a, b, 540, mb + 312, f"{si} / {n_st}", 34, "&HE1D5CB&", layer=2)
    captions(e, scenes, starts, mb + 40, BLACK, box=WHITE)


# ------------------------------------------------------------------ 🏆 TOP
def rank_word(n, lang):
    return f"{n}위" if lang == "ko" else f"第{n}位"


def rank_badge(n, lang):
    return f"{n}위" if lang == "ko" else f"{n}位"


def ranking(e: Ev, p, scenes, starts, total, g):
    scr = p.get("screen") or {}
    lang = p.get("lang") or "ja"
    my, mb = g["y"], g["y"] + g["h"]
    e.text(0, total, 540, my - 290, scr.get("title1", ""), 70, WHITE, layer=2, extra="\\fad(250,0)")
    e.add(0, total, f"\\an8\\fs{96 * K:.0f}\\c{YELLOW}\\bord4\\3c{BLACK}{fit(scr.get('title2', ''), 96)}"
                    f"\\fscx40\\fscy40\\t(100,280,\\fscx108\\fscy108)\\t(280,380,\\fscx100\\fscy100)"
                    f"\\pos(540,{my - 205})", esc(scr.get("title2", p.get("title", ""))), 2)
    for rv, a, b, sc in segments(scenes, starts, total, "rank"):
        try:
            n = int(rv)
        except (TypeError, ValueError):
            continue
        medal = {1: YELLOW, 2: SILVER, 3: BRONZE}.get(n, STEEL)
        if n == 1:   # hạng 1: chớp vàng toàn màn hình
            e.shape(a, a + 0.6, 0, 0, rect(W, H), YELLOW, layer=7, extra="\\alpha&H50&\\t(0,600,\\alpha&HFF&)")
        # màn "第N位" to giữa khung rồi biến mất
        e.shape(a, a + 0.75, g["x"], g["y"], rect(g["w"], g["h"]), BLACK, layer=4,
                extra="\\alpha&H20&\\t(550,750,\\alpha&HFF&)")
        e.add(a, a + 0.75, f"\\an5\\pos(540,{my + g['h'] // 2})\\fs{180 * K:.0f}\\c{medal}\\bord6\\3c{BLACK}"
                           f"\\fscx40\\fscy40\\t(0,180,\\fscx115\\fscy115)\\t(180,300,\\fscx100\\fscy100)"
                           f"\\t(550,750,\\alpha&HFF&)", rank_word(n, lang), 8)
        # huy hiệu ở góc khung
        e.shape(a + 0.6, b, 30, my + 20, rrect(270, 160, 24), medal, layer=5,
                extra="\\fscx0\\fscy0\\t(0,180,\\fscx110\\fscy110)\\t(180,260,\\fscx100\\fscy100)")
        e.text(a + 0.65, b, 165, my + 100, rank_badge(n, lang), 120, "&H111111&", an=5, layer=6,
               extra="\\fad(100,0)", maxw=240)
        # dải vàng tên + số liệu
        label = sc.get("rank_label", "")
        if label:
            e.shape(a + 0.75, b, 0, mb, rect(1080, 90), YELLOW, layer=4, extra=f"\\move(-1080,{mb},0,{mb},0,250)")
            e.add(a + 0.85, b, f"\\an8\\fs{64 * K:.0f}\\c&H111111&{fit(label, 64)}\\move(-500,{mb + 6},540,{mb + 6},0,250)",
                  esc(label), 5)
    captions(e, scenes, starts, mb + 120, WHITE)


# ------------------------------------------------------------------ 👤 TIỂU SỬ
def biography(e: Ev, p, scenes, starts, total, g):
    scr = p.get("screen") or {}
    my = g["y"] - 20
    mb = g["y"] + g["h"] + 20
    e.text(0, total, 540, my - 295, scr.get("title", p.get("title", "")), 92, BROWN, layer=2,
           extra="\\fad(300,0)")
    e.shape(0, total, 540, my - 160, rect(480, 4), TAN, layer=1, an=8, extra="\\fscx0\\t(0,400,\\fscx100)")
    # chương: hiện từng chữ như đang gõ
    for cv, a, b, _ in segments(scenes, starts, total, "chapter"):
        if not cv:
            continue
        s = str(cv)
        step = 0.05
        for k in range(1, len(s) + 1):
            e.text(a + (k - 1) * step, (a + k * step) if k < len(s) else b, 540, my - 140, s[:k], 52, BROWN2, layer=2)
    # năm: chạy số + dòng thời gian
    years = []
    for sc in scenes:
        y = str(sc.get("year") or "").strip()
        if y and y not in years:
            years.append(y)
    if years and all(re.fullmatch(r"\d{4}", y) for y in years):
        years.sort()            # dòng thời gian luôn theo thứ tự năm (cảnh mở đầu có thể nhảy cóc)
    if len(years) > 7:          # quá nhiều mốc → giữ đầu, cuối và các mốc cách đều
        idx = sorted({round(i * (len(years) - 1) / 6) for i in range(7)})
        years = [years[i] for i in idx]
    ytl = mb + 285
    if years:
        x0, x1 = 140, 940
        xs = {y: (x0 + (x1 - x0) * i / max(1, len(years) - 1)) if len(years) > 1 else 540 for i, y in enumerate(years)}
        e.shape(0, total, x0, ytl - 3, rect(x1 - x0, 6), TAN, layer=1, extra="\\fscx0\\t(0,500,\\fscx100)")
        for y in years:
            e.shape(0, total, xs[y] - 18, ytl - 18, circle(36), CREAM, layer=2, extra=f"\\bord5\\3c{BROWN2}")
    prev_year, prev_x = None, None
    for yv, a, b, _ in segments(scenes, starts, total, "year"):
        if not yv:
            continue
        yv = str(yv)
        # huy hiệu năm
        e.shape(a, b, 70, my - 70, rrect(260, 110, 18), BROWN, layer=6)
        if prev_year and re.fullmatch(r"\d{4}", prev_year) and re.fullmatch(r"\d{4}", yv) and prev_year != yv:
            y0, y1 = int(prev_year), int(yv)
            steps = 8
            for k in range(steps):
                val = round(y0 + (y1 - y0) * (k + 1) / steps)
                e.text(a + k * 0.06, (a + (k + 1) * 0.06) if k < steps - 1 else b, 200, my - 15, str(val), 82,
                       CREAM, an=5, layer=7, maxw=230)
        else:
            e.text(a, b, 200, my - 15, yv, 82, CREAM, an=5, layer=7, maxw=230, extra="\\fad(120,0)")
        if years and yv not in xs:   # năm bị lược khỏi dòng thời gian → dùng mốc gần nhất
            near = min(xs, key=lambda y: abs(int(y) - int(yv)) if y.isdigit() and yv.isdigit() else 0)
        else:
            near = yv
        if years and near in xs:
            yv_tl = near
            x = xs[yv_tl]
            mv = f"\\move({prev_x - 18:.0f},{ytl - 18},{x - 18:.0f},{ytl - 18},0,300)" if prev_x is not None else ""
            e.shape(a, b, x - 18, ytl - 18, circle(36), BROWN2, layer=3, extra=mv)
            for yy in years:
                e.text(a, b, xs[yy], ytl + 30, yy, 34, BROWN if yy == yv_tl else FADED, layer=3, maxw=180)
            prev_x = x
        prev_year = yv
    captions(e, scenes, starts, mb + 50, INK)


# ------------------------------------------------------------------ 💡 CHỦ ĐỀ CHUNG
def general(e: Ev, p, scenes, starts, total, g):
    scr = p.get("screen") or {}
    my, mb = g["y"], g["y"] + g["h"]
    t1, t2 = scr.get("title1", ""), scr.get("title2", p.get("title", ""))
    w2 = min(1000, text_width(t2, 100) + 80)
    e.shape(0.15, total, 540 - w2 / 2, my - 170, rect(w2, 95), MARKER, layer=1,
            extra="\\fscx0\\t(0,450,\\fscx100)")
    e.text(0, total, 540, my - 290, t1, 80, BLACK, layer=2, extra="\\fad(200,0)")
    e.text(0, total, 540, my - 205, t2, 100, HL_RED, layer=2,
           extra="\\fscx60\\fscy60\\t(0,200,\\fscx105\\fscy105)\\t(200,300,\\fscx100\\fscy100)")
    captions(e, scenes, starts, mb + 40, WHITE, box=DARKBOX)


BUILDERS = {"news": news, "ranking": ranking, "biography": biography, "general": general}


def build_ass(name: str, p: dict, scenes: list, starts: list, total: float, out: Path) -> None:
    g = geometry(name)
    e = Ev()
    scene_flash(e, starts, g)
    BUILDERS[name](e, p, scenes, starts, total, g)
    font = load_settings().get("subtitle_font") or "Noto Sans CJK JP Black"
    out.write_text(HEAD.format(W=W, H=H, font=font) + "\n".join(e.rows) + "\n", encoding="utf-8")
