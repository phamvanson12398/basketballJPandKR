"""Viết content (kịch bản) tiếng Nhật bằng Claude CLI."""
import datetime

from . import languages as LG
from . import project as P
from .claude_cli import ask, extract_json
from .config import IMAGE_SEC
from .tts import VOICE_DESIGN_OPTIONS

GENRES = {
    "sports": {
        "role": "{country}のスポーツ系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 1文目で強烈なフック（例:「日ハムから返品不可の刻印を押された男」）。
- 事実ベースのエピソードを、短い文でテンポよく積み上げ、意外な展開やオチで締める。""",
        "action": "ダンク・ゴール・好プレー・歓喜・乱闘など=高、インタビュー・事実説明・数字=低",
        "image": "選手名+チーム名+状況など具体的に（例: 河村勇輝 グリズリーズ ドリブル）",
        "video": "選手名+試合/ハイライト/プレー など（例: 河村勇輝 ハイライト 2025）",
    },
    "biography": {
        "role": "{country}の「有名人の人生ストーリー・生い立ち」系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 1文目で意外な事実や人生の落差を突くフック（例:「年収ゼロから世界の頂点に立った男」）。
- 生い立ち → 挫折・苦労 → 転機 → 成功 → 現在、という流れを基本に（全部でなくてよい）、
  知られざるエピソードを短い文でテンポよく積み上げ、心に残る一言で締める。
- 年・年齢・数字は正確に。噂・ゴシップ・私生活の未確認情報は書かない。""",
        "action": "ライブ・試合・演技・スピーチ・授賞式・会見の盛り上がりなど=高、幼少期・家族・年表・数字の説明=低",
        "image": "人物名+年代/出来事/場所など具体的に（例: 大谷翔平 花巻東 高校時代、宮崎駿 アカデミー賞 授賞式）",
        "video": "人物名+インタビュー/ライブ/会見/ドキュメンタリー/名場面 など",
    },
    "news": {
        "role": "{country}のテレビ局のニュースキャスター兼記者として、{country}の視聴者に向けてニュースを伝えるショート動画（TikTok / YouTube Shorts）",
        "style": "",   # news_context() で動的に作る
        "action": "現場映像・抗議・災害・試合・会見の様子など=高、数字・背景説明・解説・地図=低",
        "image": "出来事+場所+人物など具体的に（例: 能登半島地震 輪島 朝市）",
        "video": "出来事+ニュース/現場/会見 など（例: 〇〇 ニュース 現場映像）",
    },
    "ranking": {
        "role": "{country}のランキング（TOP N）系ショート動画（TikTok / YouTube Shorts）",
        "style": """- テーマに沿った TOP{n} を、第{n}位から第1位へのカウントダウン形式で紹介する。
- 1文目は「〇〇 TOP{n}」と意外性のあるフック。各順位は「第〇位、〇〇。」のように順位から始め、
  根拠となる数字・記録・エピソードを短く添える（{country}の言語での自然な言い方にする）。
- 順位の根拠は WebSearch で確認した記録・統計・報道にもとづく。主観的なランキングの場合は
  「独自に選んだ」ことが分かる言い方にする。
- 第1位の直前で「そして第1位は…」と一拍おいて引っ張る。最後に一言で締める。
- 1つの順位につき1〜2シーン。各シーンの image_query / video_query はその順位の対象専用にする。""",
        "action": "決定的なプレー・パフォーマンス・名場面=高、記録や数字の説明=低",
        "image": "その順位の人物・チーム・対象の名前+具体的な場面（例: 八村塁 レイカーズ ダンク）",
        "video": "その順位の対象の名前+ハイライト/名場面",
    },
    "general": {
        "role": "{country}の雑学・ニュース解説系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 1文目で「えっ？」と思わせるフック。
- 事実ベースの情報を、短い文でテンポよく積み上げ、意外なオチで締める。""",
        "action": "動きのある出来事・現場の様子=高、説明・数字・データ=低",
        "image": "テーマ+具体的な対象・場所・出来事",
        "video": "テーマ+ニュース/現場/解説 など",
    },
}

# ---------------------------------------------------------------- TIN TỨC
NEWS_REGIONS = [
    {"id": "world", "vi": "🌍 Thế giới", "ja": "世界（国際ニュース）", "lang": "英語・日本語"},
    {"id": "jp", "vi": "🇯🇵 Nhật Bản", "ja": "日本", "lang": "日本語"},
    {"id": "kr", "vi": "🇰🇷 Hàn Quốc", "ja": "韓国", "lang": "韓国語"},
    {"id": "vn", "vi": "🇻🇳 Việt Nam", "ja": "ベトナム", "lang": "ベトナム語"},
    {"id": "us", "vi": "🇺🇸 Mỹ", "ja": "アメリカ", "lang": "英語"},
    {"id": "cn", "vi": "🇨🇳 Trung Quốc", "ja": "中国", "lang": "中国語"},
    {"id": "tw", "vi": "🇹🇼 Đài Loan", "ja": "台湾", "lang": "中国語（繁体字）"},
    {"id": "th", "vi": "🇹🇭 Thái Lan", "ja": "タイ", "lang": "タイ語"},
    {"id": "ph", "vi": "🇵🇭 Philippines", "ja": "フィリピン", "lang": "英語・タガログ語"},
    {"id": "in", "vi": "🇮🇳 Ấn Độ", "ja": "インド", "lang": "英語・ヒンディー語"},
    {"id": "gb", "vi": "🇬🇧 Anh", "ja": "イギリス", "lang": "英語"},
    {"id": "fr", "vi": "🇫🇷 Pháp", "ja": "フランス", "lang": "フランス語"},
    {"id": "de", "vi": "🇩🇪 Đức", "ja": "ドイツ", "lang": "ドイツ語"},
    {"id": "ru", "vi": "🇷🇺 Nga", "ja": "ロシア", "lang": "ロシア語"},
    {"id": "ua", "vi": "🇺🇦 Ukraine", "ja": "ウクライナ", "lang": "ウクライナ語・英語"},
    {"id": "au", "vi": "🇦🇺 Úc", "ja": "オーストラリア", "lang": "英語"},
    {"id": "br", "vi": "🇧🇷 Brazil", "ja": "ブラジル", "lang": "ポルトガル語"},
    {"id": "custom", "vi": "✏️ Quốc gia khác (tự nhập)", "ja": "", "lang": "現地語"},
]
NEWS_CATEGORIES = [
    {"id": "all", "vi": "Tất cả", "ja": ""},
    {"id": "politics", "vi": "Chính trị", "ja": "政治"},
    {"id": "economy", "vi": "Kinh tế", "ja": "経済"},
    {"id": "society", "vi": "Xã hội / sự kiện", "ja": "社会・事件・事故"},
    {"id": "disaster", "vi": "Thiên tai / thời tiết", "ja": "災害・気象"},
    {"id": "sports", "vi": "Thể thao", "ja": "スポーツ"},
    {"id": "entertainment", "vi": "Giải trí / showbiz", "ja": "エンタメ・芸能"},
    {"id": "tech", "vi": "Công nghệ / khoa học", "ja": "科学・IT"},
]


def _region(region: str, custom: str = "") -> dict:
    r = next((x for x in NEWS_REGIONS if x["id"] == region), NEWS_REGIONS[0])
    if r["id"] == "custom":
        r = dict(r, ja=custom or "世界", vi=custom or "Khác")
    return r


def _category(cat: str) -> dict:
    return next((x for x in NEWS_CATEGORIES if x["id"] == cat), NEWS_CATEGORIES[0])


def today_ja() -> str:
    d = datetime.date.today()
    return f"{d.year}年{d.month}月{d.day}日"


def news_context(news: dict, lang: str = "ja") -> str:
    L = LG.get(lang)
    r = _region(news.get("region", "world"), news.get("custom_region", ""))
    c = _category(news.get("category", "all"))
    days = int(news.get("days") or 3)
    count = max(1, min(5, int(news.get("count") or 1)))
    cat = f"（ジャンル: {c['ja']}）" if c["ja"] else ""
    digest = "" if count == 1 else f"""
## ダイジェスト形式（{count}本）
- この動画では {count}本のニュースを伝える。テーマ・メモに複数の見出しがあればそれを使い、空なら注目度の高い順に{count}本選ぶ。
- 冒頭で「{{日付}}の主なニュースを{count}本お伝えします」に相当する短い一言、各ニュースの切り替えで
  「続いては」「最後は」に相当するつなぎ言葉を入れる（言語に合わせて自然に）。
- 1本あたり2〜3シーン。各シーンの image_query / video_query は、そのシーンが扱うニュース専用にする。
- 冒頭の「テーマ・メモが空なら1件選ぶ」というルールより、このダイジェスト形式を優先する。
"""
    return f"""- 今日は{today_ja()}。扱うのは「{r['ja']}」の最新ニュース{cat}で、過去{days}日以内に報じられたもの。
- 必ず WebSearch / WebFetch で最新の報道を調べること。{r['lang']}の現地報道と、{L['name']}・英語の報道の両方を確認し、
  日時・場所・人数・金額・固有名詞は複数の信頼できる報道機関で一致するものだけを使う。
- テーマ・メモが空なら、その中で最も注目度が高く、ショート動画向きのニュースを1件選ぶ。

## 語り手（最重要）
{L['anchor']}

## 構成と正確さ
- 1文目で「何が起きたか」を端的に伝える → 経緯 → 背景 → 影響・今後の見通し、の順で伝える。
- 中立・客観的に。推測・未確認情報・断定的な評価は書かない。必要に応じて伝聞の表現を使う。
{digest}"""


def suggest_news(region: str, days: int, category: str, custom_region: str = "",
                 lang: str = "ja") -> list[dict]:
    """Quét tin nóng → danh sách để người dùng chọn."""
    r = _region(region, custom_region)
    c = _category(category)
    L = LG.get(lang)
    cat = f"ジャンルは「{c['ja']}」に限定。" if c["ja"] else ""
    prompt = f"""今日は{today_ja()}です。WebSearch を使って、「{r['ja']}」で過去{days}日以内に報じられた
主要ニュースを調べてください。{cat}{r['lang']}の現地メディアと、{L['name']}・英語メディアの両方を確認してください。
{L['country']}の視聴者向けショート動画にしやすい（話題性が高く、映像・写真が多い）ニュースを8件選び、
次のJSONだけを出力してください（説明文は不要）。

```json
[{{"headline": "{L['name']}の見出し", "headline_vi": "Tiêu đề tiếng Việt",
  "summary_vi": "Tóm tắt 1–2 câu tiếng Việt", "date": "YYYY-MM-DD",
  "source": "報道機関名", "url": "記事URL", "score": 8}}]
```
score は話題性（1〜10）。新しい順ではなく、話題性の高い順に並べてください。"""
    text = ask(prompt, tools=["WebSearch", "WebFetch"], timeout=600)
    data = extract_json(text)
    if isinstance(data, dict):
        data = data.get("news") or data.get("items") or []
    out = []
    for x in data:
        if isinstance(x, dict) and (x.get("headline") or x.get("headline_ja")):
            x["headline"] = x.get("headline") or x.get("headline_ja")
            out.append(x)
    return out


# ---------------------------------------------------------------- MÔN THỂ THAO
SPORTS = {
    "baseball": {"vi": "⚾ Bóng chày", "ja": "野球", "rule": """## 競技: 野球（NPB / MLB / 高校野球 / KBO）
- 用語は正確に（防御率・打率・本塁打・先発・救援・ドラフト・FA など）。成績の数字は公式記録や報道で確認。
- 選手名は tts で読みをかな/ハングルにする（例: 上沢→うわさわ）。
- image_query / video_query は「選手名 + 球団名 + 場面（投球/本塁打/試合後）」で具体的に。"""},
    "basketball": {"vi": "🏀 Bóng rổ", "ja": "バスケットボール", "rule": """## 競技: バスケットボール（Bリーグ / KBL / NBA / 代表戦）
- 用語は正確に（得点・リバウンド・アシスト・3P成功率・ダブルダブル・ドラフト・2ウェイ契約 など）。数字は公式記録で確認。
- image_query / video_query は「選手名 + チーム名 + 場面（ダンク/3P/ハイライト）」で具体的に。"""},
    "sumo": {"vi": "🤼 Sumo", "ja": "大相撲", "rule": """## 競技: 大相撲（相撲）
- 用語を正確に使う: 番付（横綱・大関・関脇・小結・前頭・十両）、本場所（初場所・春場所・夏場所・名古屋場所・秋場所・九州場所）、
  取組・立ち合い・決まり手（寄り切り・押し出し・上手投げ・突き落とし など）、勝ち越し・負け越し・千秋楽・金星・懸賞・優勝・昇進。
- 四股名は読みが難しいので、tts では必ず読みをひらがな（韓国語ならハングル）にする
  （例: 照ノ富士→てるのふじ、大の里→おおのさと、豊昇龍→ほうしょうりゅう、琴櫻→ことざくら、霧島→きりしま）。
- 成績・番付・優勝回数は日本相撲協会の公式情報や報道で確認する。力士の私生活のうわさ・未確認情報は書かない。
- 相撲を知らない視聴者向けに、専門用語は短く補足する（韓国語なら 요코즈나＝最高位 のように）。
- action: 立ち合い・決まり手の瞬間・逆転・優勝の瞬間・懸賞金を受け取る場面=高、番付や成績の説明=低。
- image_query は「四股名 + 場所名/年 + 取組/土俵入り/優勝」、video_query は「四股名 + 取組 + 場所名」や「大相撲 ハイライト 場所名」。"""},
    "soccer": {"vi": "⚽ Bóng đá", "ja": "サッカー", "rule": """## 競技: サッカー（Jリーグ / Kリーグ / 欧州 / 代表戦）
- 用語は正確に（ゴール・アシスト・PK・移籍金・代表キャップ など）。数字は公式記録で確認。
- image_query / video_query は「選手名 + クラブ名 + 場面（ゴール/ハイライト）」で具体的に。"""},
    "other": {"vi": "🏅 Môn khác / không phải thể thao", "ja": "", "rule": ""},
}


# ---------------------------------------------------------------- CHỮ TRÊN MÀN HÌNH (bố cục)
SCREEN_RULES = {
    "news": """## 画面表示用テキスト（JSON の "screen" と各シーンに入れる）
- screen.band: 赤い帯に出す「国名 ・ 日付」（例: 「韓国 ・ 11月19日」）。出力言語で書く。
- screen.breaking: 24時間以内に起きた出来事なら true（「速報」マークを出す）、それ以外は false。
- screen.stories: ニュースごとに1つ。headline（最大14文字の見出し）、subhead（最大16文字の補足）、
  source（報道機関名、例: "SBS / 聯合ニュース"）。ダイジェストでなければ1つだけ。
- 各シーンに "story": そのシーンが扱うニュースの番号（1から）。""",
    "ranking": """## 画面表示用テキスト（JSON の "screen" と各シーンに入れる）
- screen.title1: 上段の小見出し（最大12文字、例: 「日本人NBA選手」）。
- screen.title2: 下段の大見出し（最大10文字、例: 「通算得点 TOP5」）。
- 各シーンに "rank": そのシーンの順位（数字）。オープニング・締めのシーンは null。
- 各シーンに "rank_label": その順位の名前＋決め手の数字（最大14文字、例: 「渡邊雄太 875得点」）。
- 第1位は他の順位より長く、2〜3シーン使う。""",
    "biography": """## 画面表示用テキスト（JSON の "screen" と各シーンに入れる）
- screen.title: 上部に常に出すタイトル（最大10文字、例: 「大谷翔平の人生」）。
- 各シーンに "year": その場面の西暦4桁（例: "2010"）。分からなければ直前のシーンと同じ。
- 各シーンに "chapter": 人生の章（最大12文字、例: 「第2章・高校時代」）。同じ章のシーンは同じ文字列。""",
    "general": """## 画面表示用テキスト（JSON の "screen" に入れる）
- screen.title1: 上段（最大12文字、例: 「韓国人NBA選手は」）。
- screen.title2: 下段の一番気になる部分（最大10文字、例: 「たった1人？」）。""",
}
SCENE_LABELS = ("story", "rank", "rank_label", "year", "chapter")


# ---------------------------------------------------------------- PROMPT
PROMPT = """あなたは{role}の人気ナレーション作家です。
以下の条件で、縦型ショート動画のナレーション台本を書いてください。

## 入力
- タイトル: {title}
- テーマ・メモ: {topic}
- 目標の長さ: 約{duration}秒（ナレーション合計 約{chars}文字）
{feedback}

## スタイル（参考動画の特徴）
{style}
{sport_rule}
{lang_rules}
- テンポよく引きのある語り口にするが、誹謗中傷や事実でないことは書かない。必要ならWeb検索で事実を確認する。
- 字幕は白背景に黒文字で表示され、1チャンク=1〜3行、1行は最大{line_max}文字。

## 構成ルール
- 台本を「シーン」に分ける。1シーン = 画像1枚 または 動画クリップ1本。
- 各シーンのナレーションは約{scene_chars}文字（{scene_sec}秒前後、最大でも{max_chars}文字）。
- 各シーンを字幕チャンクに分ける。チャンクは自然な文節で区切り、行の改行は "\\n" で表す。
  チャンクを全部つなげるとそのシーンのナレーションになること。
- tts: 読み上げ用テキスト。基本は字幕と同じだが、{tts_rule}。
- action: そのシーンの内容が「動き」のある映像向きかを0〜10で評価
  （{action_rule}）。
- image_query: その場面に合う写真を探す検索語（{query_lang}。{image_rule}）。
- video_query: その場面に合う動画（YouTube等）を探す検索語（{query_lang}。{video_rule}）。
- voice: このテーマに合うナレーターの声。次の候補からそれぞれ1つ選ぶ:
  gender {genders} / age {ages} / pitch {pitches}

{screen_rule}
{extra}
## 出力形式（JSONのみ。説明文は不要。下の例は形式の見本で、内容は無関係）
```json
{{
  "title": "動画タイトル（入力タイトルがあればそれを使う）",
  "voice": {{"gender": "male", "age": "middle-aged", "pitch": "low pitch"}},
  "sources": [{{"title": "参考にした記事の見出し", "url": "https://...", "date": "YYYY-MM-DD"}}],
  "scenes": [
    {{
      "chunks": ["日ハムから\\n返品不可の刻印を\\n押された男"],
      "tts": "にちハムから、返品不可の刻印を押された男。",
      "action": 2,
      "image_query": "上沢直之 ソフトバンク 投球",
      "video_query": "上沢直之 オープン戦 日本ハム 2024"
    }}
  ]
}}
```
"""


def generate(pid: str, log, feedback: str = "") -> None:
    p = P.load(pid)
    L = LG.get(p.get("lang"))
    dur = int(p["duration"])
    chars = int(dur * L["cps"])
    scene_chars = int(IMAGE_SEC * L["cps"])
    old = ""
    if feedback and p.get("scenes"):
        old = "\n".join(P.scene_plain_text(s) for s in p["scenes"])
        feedback = f"\n## 前回の台本\n{old}\n\n## 修正リクエスト（ベトナム語の場合あり。内容を理解して反映）\n{feedback}\n"
    gen = GENRES.get(p.get("genre") or "sports", GENRES["sports"])
    if p.get("genre") == "news":
        style = news_context(p.get("news") or {}, p.get("lang"))
    elif p.get("genre") == "ranking":
        style = gen["style"].format(n=int(p.get("ranking_n") or 5), country=L["country"])
    else:
        style = gen["style"]
    extra = ("\n## 出典\n- sources に、事実確認に使った記事（見出し・URL・日付）を3件以上必ず入れる。\n"
             if p.get("genre") == "news" else "")
    prompt = PROMPT.format(
        role=gen["role"].format(country=L["country"]), style=style, extra=extra, action_rule=gen["action"],
        lang_rules=L["rules"], line_max=L["line_max"], tts_rule=L["tts_rule"], query_lang=L["query_lang"],
        screen_rule=SCREEN_RULES.get(p.get("genre"), ""),
        sport_rule=SPORTS.get(p.get("sport") or "other", SPORTS["other"])["rule"],
        image_rule=gen["image"], video_rule=gen["video"],
        title=p.get("title") or "（なし。テーマから魅力的なタイトルを考える）",
        topic=p.get("topic") or "（なし）",
        duration=dur, chars=chars, scene_chars=scene_chars, scene_sec=IMAGE_SEC,
        max_chars=int(scene_chars * 1.6), feedback=feedback,
        genders=VOICE_DESIGN_OPTIONS["gender"], ages=VOICE_DESIGN_OPTIONS["age"],
        pitches=VOICE_DESIGN_OPTIONS["pitch"],
    )
    log("Đang nhờ Claude viết content (có thể tra cứu web, mất 1–3 phút)..."
        + (" Tin tức: đang quét báo mới nhất." if p.get("genre") == "news" else ""), 0.1)
    text = ask(prompt, tools=["WebSearch", "WebFetch"], timeout=900)
    data = extract_json(text)
    scenes = []
    for i, s in enumerate(data.get("scenes", [])):
        chunks = [c.strip() for c in s.get("chunks", []) if str(c).strip()]
        if not chunks:
            continue
        scenes.append({
            "id": f"s{i + 1:02d}",
            "chunks": chunks,
            "tts": s.get("tts", "").strip(),
            "action": int(s.get("action") or 0),
            "image_query": s.get("image_query", ""),
            "video_query": s.get("video_query", ""),
            "kind": "image",
            **{k: s[k] for k in SCENE_LABELS if s.get(k) not in (None, "")},
        })
    if not scenes:
        raise RuntimeError("Claude không trả về cảnh nào, thử lại nhé.")
    P.rebalance(scenes, P.video_ratio(p))

    def apply(pp):
        if not pp.get("title"):
            pp["title"] = data.get("title", "")
        pp["scenes"] = scenes
        pp["script_approved"] = False
        pp["sources"] = [x for x in (data.get("sources") or []) if isinstance(x, dict)]
        pp["screen"] = data.get("screen") if isinstance(data.get("screen"), dict) else {}
        v = data.get("voice") or {}
        pp["voice"]["auto_instruct"] = ", ".join(
            x for x in (v.get("gender"), v.get("age"), v.get("pitch")) if x)
    P.update(pid, apply)
    info = P.ratio_info(scenes)
    log(f"Đã viết {len(scenes)} cảnh, ước tính {info['total']}s "
        f"(ảnh {info['image_pct']}% / video {info['video_pct']}%).", 1.0)


# ---------------------------------------------------------------- TIKTOK
TIKTOK_PROMPT = """あなたは{country}のTikTok運用のプロです。次のショート動画を投稿するための
キャプション（タイトル）とハッシュタグを考えてください。視聴者は{people}です。
キャプションとハッシュタグはすべて{lang_name}で書くこと（例は日本語でも、出力は{lang_name}）。

## 動画情報
- ジャンル: {genre}
- 動画タイトル: {title}
- ナレーション全文:
{script}

## キャプション（タイトル）のルール
- 5案。それぞれ違う切り口にする（例: 疑問形 / 数字 / 意外な事実 / 感情に訴える / ストレートな要約）。
- 1案は全角40文字以内が目安。最初の15文字で続きが気になるようにする。
- 必ず{lang_name}の標準語。誇張しすぎ・嘘・誤解を招く表現・誹謗中傷はNG。
  ニュースの場合は事実に忠実に、落ち着いたトーンで。
- 絵文字は0〜2個まで。
- 各案にベトナム語訳（vi）を付ける。

## ハッシュタグのルール
- 合計10〜12個。# を付けた形で出力。重複なし、スペースなし。
- big: ジャンル全体の大きなタグ（例: #バスケ #NBA #ニュース #偉人）3〜4個
- mid: テーマ・チーム・出来事のタグ 3〜4個
- niche: 人物名・固有名詞などの具体的なタグ 2〜3個
- discover: {country}のTikTokでおすすめに載りやすい定番タグ 1〜2個（例: {discover}）
- 各タグにベトナム語の意味（vi）を付ける。

## 出力（JSONのみ）
```json
{{
  "captions": [{{"ja": "キャプション（{lang_name}）", "vi": "Bản dịch"}}],
  "hashtags": [{{"tag": "#タグ", "group": "big", "vi": "nghĩa"}}]
}}
```
"""

GENRE_NAMES_JA = {"sports": "スポーツ", "biography": "有名人の人生ストーリー", "news": "ニュース",
                  "general": "雑学・解説"}


def gen_tiktok(pid: str, log) -> None:
    p = P.load(pid)
    if not p.get("scenes"):
        raise RuntimeError("Chưa có content.")
    script = "\n".join(P.scene_plain_text(s) for s in p["scenes"])
    log("Đang nhờ Claude viết title và hashtag TikTok...", 0.2)
    L = LG.get(p.get("lang"))
    sport_ja = SPORTS.get(p.get("sport") or "other", SPORTS["other"])["ja"]
    text = ask(TIKTOK_PROMPT.format(genre=GENRE_NAMES_JA.get(p.get("genre"), "スポーツ") + (f"（{sport_ja}）" if sport_ja else ""),
                                    title=p.get("title", ""), script=script, country=L["country"],
                                    people=L["people"], lang_name=L["name"], discover=L["discover"]),
               timeout=300)
    data = extract_json(text)
    caps = [c for c in data.get("captions", []) if isinstance(c, dict) and c.get("ja")]
    tags = []
    for t in data.get("hashtags", []):
        if isinstance(t, dict) and t.get("tag"):
            tag = "#" + str(t["tag"]).strip().lstrip("#").replace(" ", "")
            if tag != "#" and tag not in [x["tag"] for x in tags]:
                tags.append({"tag": tag, "group": t.get("group", ""), "vi": t.get("vi", ""), "on": True})
    if not caps:
        raise RuntimeError("Claude không trả về title, thử lại nhé.")

    def apply(pp):
        pp["tiktok"] = {"captions": caps, "hashtags": tags, "caption": caps[0]["ja"]}
    P.update(pid, apply)
    log(f"Đã có {len(caps)} title và {len(tags)} hashtag.", 1.0)
