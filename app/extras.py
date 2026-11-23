"""Tính năng thêm:
  • make_twin  – từ 1 video, tạo bản ngôn ngữ khác (VD: Nhật → Hàn) dùng lại y nguyên ảnh/video,
                 Claude viết lại content cho người nước đó (không dịch máy móc).
  • suggest_ideas – Claude gợi ý 10 ý tưởng video theo ngách bạn chọn.
"""
import json
import os
import shutil

from . import languages as LG
from . import project as P
from .claude_cli import ask, extract_json
from .script_gen import GENRES, today_ja


# ---------------------------------------------------------------- BẢN NGÔN NGỮ THỨ HAI
def _link_or_copy(src, dst, *, follow_symlinks=True):
    """Dùng hard link để không tốn thêm dung lượng ổ đĩa (video nguồn có thể nặng)."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst


def create_twin(pid: str, lang: str) -> dict:
    """Tạo dự án mới cùng ảnh/video, ngôn ngữ khác. Content sẽ được viết lại bởi job localize()."""
    src = P.load(pid)
    if lang not in LG.LANGS:
        raise ValueError("Ngôn ngữ không hợp lệ")
    if lang == src.get("lang", "ja"):
        raise ValueError("Video này đã là ngôn ngữ đó rồi")
    if not src.get("scenes"):
        raise ValueError("Video gốc chưa có content")
    new = P.create(src.get("title", ""), src.get("topic", ""), src["duration"], src.get("genre", "sports"),
                   src.get("video_pct", 30), src.get("news"), lang, src.get("ranking_n"), src.get("sport") or "other")
    nd, sd = P.pdir(new["id"]), P.pdir(pid)
    for sub in ("media", "sources"):
        if (sd / sub).exists():
            shutil.rmtree(nd / sub, ignore_errors=True)
            shutil.copytree(sd / sub, nd / sub, copy_function=_link_or_copy)
    keep = ("id", "kind", "locked_kind", "action", "image_query", "video_query", "items", "candidates",
            "video_results", "story", "rank", "rank_label", "year", "chapter",
            "banzuke", "name", "record", "kimarite", "score", "minute", "player", "team",
            "stat", "split", "image_query2", "who", "query_alt", "picked", "uniform", "call", "sticker", "sticker_pos")

    def apply(p):
        p["scenes"] = [{k: s[k] for k in keep if k in s} | {"chunks": s.get("chunks", []), "tts": ""}
                       for s in src["scenes"]]
        p["ranking_n"] = src.get("ranking_n")
        p["sources"] = src.get("sources", [])
        p["screen"] = src.get("screen", {})
        p["layout"] = src.get("layout", "auto")
        p["bgm"] = src.get("bgm", {"file": "", "volume": 0.15})
        p["voice"] = {"mode": "auto", "voice": "", "instruct": "", "speed": src.get("voice", {}).get("speed", 1.0),
                      "auto_instruct": src.get("voice", {}).get("auto_instruct", "")}
        p["twin_of"] = pid
        p["twin_from_lang"] = src.get("lang", "ja")
    return P.update(new["id"], apply)


TWIN_PROMPT = """あなたは{role}です。
次の{src_name}のショート動画台本を、{country}の視聴者向けに{dst_name}で作り直してください。

## 絶対条件
- シーン数は必ず {n} 個、順番も内容も同じにする（映像を使い回すため。シーン i の映像はシーン i の内容と一致している）。
- 各シーンの長さ（読み上げ秒数）は元とほぼ同じに。1シーンあたり元の文字数の±20%以内を目安。
- 直訳ではなく、{country}の人が自然に感じる表現・語順・補足にする（{country}の視聴者が知らない固有名詞は短く補足）。
- 事実（数字・日付・人名）は変えない。
- "screen"（画面に出す見出し類）と、各シーンの rank_label / chapter / banzuke / name / record / kimarite /
  player / team も同じキーのまま{dst_name}にする
  （文字数は元と同じくらいに短く）。story / rank / year の値はそのまま。

## 言語ルール
{lang_rules}
- 字幕チャンク: 1チャンク=1〜3行、1行は最大{line_max}文字、改行は "\\n"。チャンクを全部つなげるとそのシーンのナレーション。
- 元のチャンクに強調記号〔〕【】《》があれば、同じ意味の語に同じ記号を付けて残す（tts には付けない）。
- tts: 読み上げ用テキスト。{tts_rule}。
{anchor}
## 元の台本（JSON）
{src_json}

## 出力（JSONのみ）
```json
{{"title": "{dst_name}のタイトル", "screen": {{...元と同じキー...}},
  "scenes": [{{"chunks": ["..."], "tts": "...", "rank_label": "...", "chapter": "..."}}]}}
```
"""


def localize(pid: str, log) -> None:
    p = P.load(pid)
    L = LG.get(p.get("lang"))
    S = LG.get(p.get("twin_from_lang"))
    gen = GENRES.get(p.get("genre") or "sports", GENRES["sports"])
    n = len(p["scenes"])
    labels = ("story", "rank", "rank_label", "year", "chapter",
              "banzuke", "name", "record", "kimarite", "score", "minute", "player", "team", "stat")
    src_json = json.dumps({"title": p.get("title", ""), "screen": p.get("screen") or {},
                           "scenes": [{"no": i + 1, "chunks": s.get("chunks", []),
                                       **{k: s[k] for k in labels if s.get(k) not in (None, "")}}
                                      for i, s in enumerate(p["scenes"])]},
                          ensure_ascii=False, indent=1)
    anchor = ("\n## 語り手（ニュース）\n" + L["anchor"] + "\n") if p.get("genre") == "news" else ""
    prompt = TWIN_PROMPT.format(role=gen["role"].format(country=L["country"]) + "の人気ナレーション作家",
                                src_name=S["name"], dst_name=L["name"], country=L["country"], n=n,
                                lang_rules=L["rules"], line_max=L["line_max"], tts_rule=L["tts_rule"],
                                anchor=anchor, src_json=src_json)
    data = None
    for attempt in range(2):
        log(f"Đang nhờ Claude viết lại content sang {L['vi']} ({n} cảnh, giữ nguyên ảnh/video)...", 0.2)
        data = extract_json(ask(prompt, timeout=600))
        if len(data.get("scenes", [])) == n:
            break
        log(f"  Claude trả về {len(data.get('scenes', []))} cảnh, cần đúng {n} → thử lại")
    scenes_new = data.get("scenes", [])
    if len(scenes_new) != n:
        raise RuntimeError(f"Không giữ được đúng {n} cảnh, thử lại nhé.")

    def apply(pp):
        pp["title"] = data.get("title") or pp.get("title", "")
        if isinstance(data.get("screen"), dict) and data["screen"]:
            pp["screen"] = data["screen"]
        for s, ns in zip(pp["scenes"], scenes_new):
            s["chunks"] = [c.strip() for c in ns.get("chunks", []) if str(c).strip()] or s["chunks"]
            s["tts"] = (ns.get("tts") or "").strip()
            for k in ("rank_label", "chapter", "banzuke", "name", "record", "kimarite", "player", "team", "stat"):
                if ns.get(k):
                    s[k] = ns[k]
            for k in ("audio", "duration", "audio_text", "audio_stale"):
                s.pop(k, None)
        pp["script_approved"] = False
        pp["tiktok"] = None
        pp["output"] = ""
    P.update(pid, apply)
    log(f"Xong bản {L['vi']}. Ảnh/video đã giữ nguyên. Tiếp theo: duyệt content → đọc giọng → xuất video.", 1.0)


# ---------------------------------------------------------------- GỢI Ý Ý TƯỞNG
IDEA_PROMPT = """今日は{date}です。あなたは{country}のTikTok / YouTube Shorts で伸びる企画を考えるプロデューサーです。
{country}の視聴者（{people}）向けに、次のニッチで「今つくるべき」縦型ショート動画の企画を{count}本考えてください。

- ニッチ: {niche}
- ジャンル: {genre_rule}

## 条件
- WebSearch で最近（ここ1〜2週間）の話題を調べ、旬のネタを半分以上入れる。残りは時期を問わず伸びる定番ネタ。
- 写真・映像が多く手に入るテーマを優先（静止画とYouTube映像で作る動画のため）。
- 事実ベースで作れるものだけ。未確認の噂・ゴシップ、炎上しやすい政治・歴史・領土問題は避ける。
- タイトルは{lang_name}で、最初の15文字で気になるように。
- sports / biography の企画は、再生数の多い「雑学・裏話」型を中心にする:
  誰もが知っている有名人物の「知られていない一面」1つに絞った切り口
  （例:「落合博満が試合中ずっと無表情だった本当の理由」「リベラの魔球カットボールは偶然生まれた」
  「4年で2勝の男が野村再生工場の最高傑作になるまで」）。経歴紹介だけの企画は避ける。
  topic には、その切り口・使えるフックの型（比較 / 「〜した人がいる」 / 実際のセリフ / 衝撃の数字）・
  裏付けになる出典（本人インタビュー・報道）を書く。
- brand（企業・ブランド）の企画は「今の姿と意外な過去のギャップ」1つに絞る
  （例:「任天堂は元々花札の会社だった」「チキンラーメンは裏庭の小屋で生まれた」「삼성의 시작은 대구의 작은 상회」）。
- history（歴史）の企画は「教科書のイメージと意外な素顔・真相のギャップ」1つに絞る
  （例:「織田信長は甘党だった」「伊達政宗は料理好き」「세종대왕은 고기 없이는 밥을 못 먹었다」）。
  日韓の歴史認識問題・戦争責任・領土問題は避ける。
- eスポーツ（LoL / Faker / T1 / 格闘ゲーム）の企画は sports として、伝説のプレーの裏側・引退しない理由・復活劇など1つの切り口に絞る。
- genre は sports / biography / brand / history / news / general / ranking のどれか。ranking の場合は ranking_n（3〜10）も入れる。

## 出力（JSONのみ、話題性の高い順）
```json
[{{"title": "{lang_name}のタイトル", "title_vi": "Tiêu đề tiếng Việt", "genre": "sports",
   "ranking_n": null, "topic": "台本作成AIへのメモ（何を・どの切り口で・重要な事実）",
   "why_vi": "Vì sao nên làm (1 câu tiếng Việt)", "timely": true, "score": 8}}]
```
"""

GENRE_RULE = {"any": "自由（企画に合うものを選ぶ）", "sports": "sports のみ", "biography": "biography のみ",
              "brand": "brand のみ（企業・ブランド・商品の誕生秘話・裏話）",
              "history": "history のみ（歴史上の人物・出来事の意外な裏話）",
              "news": "news のみ（最新ニュース）", "general": "general のみ（雑学・解説）",
              "ranking": "ranking のみ（TOP N 形式）"}


def suggest_ideas(lang: str, niche: str, genre: str = "any", count: int = 10) -> list[dict]:
    L = LG.get(lang)
    prompt = IDEA_PROMPT.format(date=today_ja(), country=L["country"], people=L["people"],
                                lang_name=L["name"], niche=niche or "スポーツ（特にバスケットボール）",
                                genre_rule=GENRE_RULE.get(genre, GENRE_RULE["any"]), count=count)
    data = extract_json(ask(prompt, tools=["WebSearch", "WebFetch"], timeout=600))
    if isinstance(data, dict):
        data = data.get("ideas") or data.get("items") or []
    out = []
    for x in data:
        if isinstance(x, dict) and x.get("title"):
            if x.get("genre") not in GENRES:
                x["genre"] = "general"
            out.append(x)
    return out
