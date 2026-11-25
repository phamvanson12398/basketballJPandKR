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
                   src.get("video_pct", 30), src.get("news"), lang, src.get("ranking_n"), src.get("sport") or "other",
                   src.get("audience") or "all")
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
- 下の「例」は型（切り口の作り方）の説明だけ。例に出てくる人物・会社・題材そのものは企画に使わない。
- {count}本はすべて別の主役（人物・チーム・会社・出来事）にする。同じ人物の別エピソードを2本入れない。
  時代（昔〜最近）・分野・切り口の型（意外な過去 / 誕生秘話 / 逆転劇 / 名言の裏側 / 引き際 / ライバル / 素顔）もばらけさせる。
{variety}
{avoid}
- sports / biography の企画は、再生数の多い「雑学・裏話」型を中心にする:
  誰もが知っている有名人物の「知られていない一面」1つに絞った切り口
  （例:「落合博満が試合中ずっと無表情だった本当の理由」「リベラの魔球カットボールは偶然生まれた」
  「4年で2勝の男が野村再生工場の最高傑作になるまで」）。経歴紹介だけの企画は避ける。
  topic には、その切り口・使えるフックの型（比較 / 「〜した人がいる」 / 実際のセリフ / 衝撃の数字）・
  裏付けになる出典（本人インタビュー・報道）を書く。
- brand（企業・ブランド）の企画は「今の姿と意外な過去のギャップ」1つに絞る
  （例:「任天堂は元々花札の会社だった」「チキンラーメンは裏庭の小屋で生まれた」「삼성의 시작은 대구의 작은 상회」）。
- history（歴史）の企画は「歴史のヤバい雑学」チャンネルの型: 制度・刑罰・風習・暮らしの「エグい実態」を
  時代を追って語れるテーマを優先（例:「島流しの刑の実態」「切腹の本当のルール」「江戸時代の離婚事情」「参勤交代のヤバい出費」
  「戦国時代の首実検」「조선시대 곤장의 실체」「조선 왕의 하루」）。人物なら「教科書のイメージと意外な素顔のギャップ」
  （例:「織田信長は甘党だった」）。タイトルは友達に話すような口調（「実は〇〇ってかなりエグかった」「〇〇のヤバすぎる実態」）。
  topic には、時代ごとのエピソード（人物名・理由・結果）と、冒頭で予告して最後に回収する「一番バカバカしい・おもしろい話」を書く。
  日韓の歴史認識問題・戦争責任・領土問題は避ける。
- eスポーツ（LoL / Faker / T1 / 格闘ゲーム）の企画は sports として、伝説のプレーの裏側・引退しない理由・復活劇など1つの切り口に絞る。
- genre は sports / biography / brand / history / news / general / ranking のどれか。ranking の場合は ranking_n（3〜10）も入れる。

## 出力（JSONのみ、話題性の高い順）
```json
[{{"title": "{lang_name}のタイトル", "title_vi": "Tiêu đề tiếng Việt", "genre": "sports", "subject": "主役の正式名（人物名・会社名など）",
   "ranking_n": null, "topic": "台本作成AIへのメモ（何を・どの切り口で・重要な事実）",
   "why_vi": "Vì sao nên làm (1 câu tiếng Việt)", "timely": true, "score": 8}}]
```
"""

GENRE_RULE = {"any": "自由（企画に合うものを選ぶ）", "sports": "sports のみ", "biography": "biography のみ",
              "brand": "brand のみ（企業・ブランド・商品の誕生秘話・裏話）",
              "history": "history のみ（制度・刑罰・風習・暮らしのヤバい実態、歴史上の人物の意外な素顔）",
              "news": "news のみ（最新ニュース）", "general": "general のみ（雑学・解説）",
              "ranking": "ranking のみ（TOP N 形式）"}


# ---- chống trùng: nhớ các ý tưởng đã gợi ý + các video đã làm
def _hist_file():
    from .config import ROOT
    return ROOT / "library" / "idea_history.json"


def _load_history() -> list[dict]:
    f = _hist_file()
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except Exception:  # noqa: BLE001
        return []


def _save_history(items: list[dict]) -> None:
    f = _hist_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(items[-400:], ensure_ascii=False), encoding="utf-8")


def _norm(s: str) -> str:
    import re as _re
    return _re.sub(r"[\s　・、。,.!！?？「」『』（）()〔〕【】《》\-—:：]+", "", (s or "").lower())


def _grams(s: str) -> set:
    s = _norm(s)
    return {s[i:i + 3] for i in range(max(1, len(s) - 2))}


def _similar(a: str, b: str) -> bool:
    ga, gb = _grams(a), _grams(b)
    return bool(ga and gb) and len(ga & gb) / len(ga | gb) >= 0.45


def used_material() -> tuple[list[str], list[str]]:
    """(tiêu đề / chủ đề đã dùng, nhân vật đã dùng) từ các video đã làm + ý tưởng đã gợi ý gần đây."""
    titles, subjects = [], []
    for p in P.list_all() if hasattr(P, "list_all") else []:
        titles += [p.get("title") or "", p.get("topic") or ""]
        subjects += [s.get("who", "").split("、")[0] for s in (p.get("scenes") or [])[:3] if s.get("who")]
    for h in _load_history()[-200:]:
        titles.append(h.get("title", ""))
        if h.get("subject"):
            subjects.append(h["subject"])
    titles = [t for t in dict.fromkeys(t.strip() for t in titles) if t]
    subjects = [s for s in dict.fromkeys(s.strip() for s in subjects) if s]
    return titles, subjects


def _avoid_block(titles: list[str], subjects: list[str]) -> str:
    if not titles and not subjects:
        return ""
    out = ["\n## 使わないもの（既に動画にした・最近提案した。重複・言い換えもNG）"]
    if subjects:
        out.append("- 主役として使わない人物・会社: " + "、".join(subjects[-80:]))
    if titles:
        out.append("- 既出の企画: " + " / ".join(t[:40] for t in titles[-60:]))
    return "\n".join(out) + "\n"


VARIETY = [
    "1980年代〜90年代の題材を2本以上", "2000年代の題材を2本以上", "ここ5年の題材を2本以上",
    "引退後・晩年の話を1本", "デビュー前・無名時代の話を1本", "ライバル・師弟関係の話を1本",
    "家族・恩人がカギの話を1本", "失敗・挫折から逆転した話を1本", "記録の裏にある意外な数字の話を1本",
    "名言・セリフの裏側の話を1本", "あまり知られていない名脇役・裏方の話を1本", "海外で活躍した人物の話を1本",
]


def dedupe(items: list[dict], titles: list[str], subjects: list[str], key_title="title", key_subject="subject"):
    out, seen_sub = [], {_norm(s) for s in subjects}
    for x in items:
        t, s = x.get(key_title, ""), _norm(x.get(key_subject, ""))
        if s and s in seen_sub:
            continue
        if any(_similar(t, u) for u in titles) or any(_similar(t, o.get(key_title, "")) for o in out):
            continue
        out.append(x)
        if s:
            seen_sub.add(s)
    return out


def suggest_ideas(lang: str, niche: str, genre: str = "any", count: int = 10, audience: str = "all") -> list[dict]:
    import random as _random
    L = LG.get(lang)
    titles, subjects = used_material()
    variety = "- 今回は特に: " + " / ".join(_random.sample(VARIETY, 3))
    if audience == "35plus":
        niche = (niche or "") + ("（視聴者は35歳以上の大人。1980〜2000年代の名選手・名場面・商品・出来事など、"
                                 "この世代が懐かしく感じ、自分の人生と重ねられる企画を中心に。旬の話題も、昔の名選手・出来事と比べる切り口で）")
    prompt = IDEA_PROMPT.format(date=today_ja(), country=L["country"], people=L["people"],
                                lang_name=L["name"], niche=niche or "スポーツ（特にバスケットボール）",
                                genre_rule=GENRE_RULE.get(genre, GENRE_RULE["any"]), count=count + 4,
                                variety=variety, avoid=_avoid_block(titles, subjects))
    data = extract_json(ask(prompt, tools=["WebSearch", "WebFetch"], timeout=600))
    if isinstance(data, dict):
        data = data.get("ideas") or data.get("items") or []
    out = []
    for x in data:
        if isinstance(x, dict) and x.get("title"):
            if x.get("genre") not in GENRES:
                x["genre"] = "general"
            out.append(x)
    out = dedupe(out, titles, subjects)[:count]          # bỏ trùng với video đã làm / ý tưởng cũ / trong cùng lượt
    _save_history(_load_history() + [{"title": x["title"], "subject": x.get("subject", ""),
                                      "at": today_ja()} for x in out])
    return out


# ---------------------------------------------------------------- TÌM CHUYỆN ĐỜI NHÂN VẬT
STORY_PROMPT = """今日は{date}です。あなたは{country}の人気ショート動画チャンネルのリサーチャーです。
「{person}」の人生から、ショート動画（60〜90秒、「雑学・裏話」型）1本になる**面白いエピソード**を{count}個探してください。
視聴者は{people}。{audience}

## 調べ方（必ず WebSearch / WebFetch を何回も使う）
- 本人や関係者のインタビュー記事、自伝・評伝の紹介、大手メディアの特集、公式プロフィール、百科事典（{country}語版と英語版）、
  当時の新聞記事、番組で語ったエピソード、などを複数調べる。記憶だけで書かない。
- 有名すぎて誰でも知っている話より、「えっ、そうだったの？」と言われる話を優先する
  （無名時代・意外な前職・家族や恩人・偶然・失敗・名言の裏側・引退後・意外な趣味や癖・知られざる記録）。

## 条件
- 事実として確認できたものだけ。出典（URL）を必ず付ける。噂・ゴシップ・不祥事・私生活の暴露・誹謗中傷は入れない。
- {count}個はすべて別の出来事・時期にする。同じ話の言い換えはNG。
{avoid}
## 出力（JSONのみ、面白い順）
```json
[{{"title": "{lang_name}の動画タイトル", "title_vi": "Tiêu đề tiếng Việt",
   "hook": "{lang_name}で、動画の最初の一文（意外な事実・数字・セリフで始める）",
   "summary_vi": "Câu chuyện tóm tắt 2–3 câu tiếng Việt (có năm, con số, chi tiết cụ thể)",
   "era": "年代（例: 1995年 / 高校時代）",
   "genre": "sports / biography / history / brand のどれか",
   "sport": "分野（baseball / basketball / soccer / sumo / horse / esports / idol / kpop / owarai / history（歴史上の人物） / other）",
   "topic": "台本作成AIへのメモ（{lang_name}。切り口・重要な事実・年・数字・確認できた発言とその出典）",
   "sources": [{{"title": "資料名", "url": "https://..."}}],
   "known": "あまり知られていない / ファンなら知っている / 有名",
   "score": 8}}]
```
"""


def find_stories(lang: str, person: str, count: int = 8, audience: str = "all") -> list[dict]:
    """Claude tra cứu kỹ 1 nhân vật → các chuyện đời thú vị, ít người biết, có nguồn – mỗi chuyện = 1 video."""
    person = (person or "").strip()
    if not person:
        raise ValueError("Nhập tên nhân vật nhé")
    L = LG.get(lang)
    titles, _ = used_material()
    rel = [t for t in titles if _norm(person) in _norm(t)] + \
          [h.get("title", "") for h in _load_history() if _norm(person) in _norm(h.get("subject", ""))]
    avoid = ("\n- 既に動画にした・提案済みの話（使わない）: " + " / ".join(dict.fromkeys(rel))[:2000] + "\n") if rel else ""
    aud = ("視聴者は35歳以上の大人。その世代が懐かしく感じる時代の話や、人生の重みが伝わる話を優先。"
           if audience == "35plus" else "")
    prompt = STORY_PROMPT.format(date=today_ja(), country=L["country"], people=L["people"], lang_name=L["name"],
                                 person=person, count=count + 2, audience=aud, avoid=avoid)
    data = extract_json(ask(prompt, tools=["WebSearch", "WebFetch"], timeout=900))
    if isinstance(data, dict):
        data = data.get("stories") or data.get("items") or []
    out = []
    for x in data:
        if not (isinstance(x, dict) and x.get("title")):
            continue
        if x.get("genre") not in GENRES:
            x["genre"] = "biography"
        x["subject"] = person
        x["sources"] = [s for s in (x.get("sources") or []) if isinstance(s, dict) and s.get("url")][:3]
        out.append(x)
    out = dedupe(out, rel, [], key_subject="_none")[:count]   # cùng 1 nhân vật → chỉ lọc trùng theo nội dung chuyện
    _save_history(_load_history() + [{"title": x["title"], "subject": person, "at": today_ja()} for x in out])
    return out
