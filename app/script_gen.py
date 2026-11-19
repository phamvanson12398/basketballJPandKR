"""Viết content (kịch bản) tiếng Nhật bằng Claude CLI."""
import datetime

from . import project as P
from .claude_cli import ask, extract_json
from .config import JA_CHARS_PER_SEC, IMAGE_SEC
from .tts import VOICE_DESIGN_OPTIONS

GENRES = {
    "sports": {
        "role": "日本のスポーツ系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 1文目で強烈なフック（例:「日ハムから返品不可の刻印を押された男」）。
- 事実ベースのエピソードを、短い文でテンポよく積み上げ、意外な展開やオチで締める。""",
        "action": "ダンク・ゴール・好プレー・歓喜・乱闘など=高、インタビュー・事実説明・数字=低",
        "image": "選手名+チーム名+状況など具体的に（例: 河村勇輝 グリズリーズ ドリブル）",
        "video": "選手名+試合/ハイライト/プレー など（例: 河村勇輝 ハイライト 2025）",
    },
    "biography": {
        "role": "日本の「有名人の人生ストーリー・生い立ち」系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 1文目で意外な事実や人生の落差を突くフック（例:「年収ゼロから世界の頂点に立った男」）。
- 生い立ち → 挫折・苦労 → 転機 → 成功 → 現在、という流れを基本に（全部でなくてよい）、
  知られざるエピソードを短い文でテンポよく積み上げ、心に残る一言で締める。
- 年・年齢・数字は正確に。噂・ゴシップ・私生活の未確認情報は書かない。""",
        "action": "ライブ・試合・演技・スピーチ・授賞式・会見の盛り上がりなど=高、幼少期・家族・年表・数字の説明=低",
        "image": "人物名+年代/出来事/場所など具体的に（例: 大谷翔平 花巻東 高校時代、宮崎駿 アカデミー賞 授賞式）",
        "video": "人物名+インタビュー/ライブ/会見/ドキュメンタリー/名場面 など",
    },
    "news": {
        "role": "日本のテレビ局のニュースキャスター兼記者として、日本の視聴者に向けてニュースを伝えるショート動画（TikTok / YouTube Shorts）",
        "style": "",   # news_context() で動的に作る
        "action": "現場映像・抗議・災害・試合・会見の様子など=高、数字・背景説明・解説・地図=低",
        "image": "出来事+場所+人物など具体的に（例: 能登半島地震 輪島 朝市）",
        "video": "出来事+ニュース/現場/会見 など（例: 〇〇 ニュース 現場映像）",
    },
    "general": {
        "role": "日本の雑学・ニュース解説系ショート動画（TikTok / YouTube Shorts）",
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


def news_context(news: dict) -> str:
    r = _region(news.get("region", "world"), news.get("custom_region", ""))
    c = _category(news.get("category", "all"))
    days = int(news.get("days") or 3)
    cat = f"（ジャンル: {c['ja']}）" if c["ja"] else ""
    return f"""- 今日は{today_ja()}。扱うのは「{r['ja']}」の最新ニュース{cat}で、過去{days}日以内に報じられたもの。
- 必ず WebSearch / WebFetch で最新の報道を調べること。{r['lang']}の現地報道と、日本語・英語の報道の両方を確認し、
  日時・場所・人数・金額・固有名詞は複数の信頼できる報道機関で一致するものだけを使う。
- テーマ・メモが空なら、その中で最も注目度が高く、ショート動画向きのニュースを1件選ぶ。

## 語り手（最重要）
- あなたは日本人のニュースキャスター。日本に住む日本人の視聴者に「こんなことが起きています」と伝える立場で書く。
- NHKや民放のニュース番組のような、です・ます調の落ち着いた報道口調（「〜しました」「〜とみられています」）。
  煽り・タメ口・感嘆の多用はしない。ただし1文目は短く印象的に。
- 海外のニュースは、日本人が予備知識なしで分かるように補足する
  （例:「韓国の大学入試にあたる『修学能力試験』」「ベトナムの首相にあたるフン首相」）。
- 外国の人名・地名は日本の報道で一般的なカタカナ/漢字表記にする。
- 金額は現地通貨に加えて日本円の目安を添える（例:「約1兆ドル、日本円でおよそ150兆円」）。
  時刻は必要なら「日本時間の〇日午後〇時」のように日本時間で伝える。
- 可能なら「日本への影響」「日本との関係」「日本人旅行者・在留日本人への注意点」など、日本の視聴者にとっての意味を1シーン入れる
  （無理に結び付けない。関係がなければ入れなくてよい）。
- 最後は「今後の動きが注目されます」のような締めか、日本の視聴者に関係する一言で終える。

## 構成と正確さ
- 1文目で「何が起きたか」を端的に伝える → 経緯 → 背景 → 影響・今後の見通し、の順で伝える。
- 中立・客観的に。推測・未確認情報・断定的な評価は書かない。必要に応じて「〜と報じられています」と表現する。
- 日付は「〇月〇日」と具体的に書く（「昨日」「今日」は使わない）。"""


def suggest_news(region: str, days: int, category: str, custom_region: str = "") -> list[dict]:
    """Quét tin nóng → danh sách để người dùng chọn."""
    r = _region(region, custom_region)
    c = _category(category)
    cat = f"ジャンルは「{c['ja']}」に限定。" if c["ja"] else ""
    prompt = f"""今日は{today_ja()}です。WebSearch を使って、「{r['ja']}」で過去{days}日以内に報じられた
主要ニュースを調べてください。{cat}{r['lang']}の現地メディアと、日本語・英語メディアの両方を確認してください。
日本の視聴者向けショート動画にしやすい（話題性が高く、映像・写真が多い）ニュースを8件選び、
次のJSONだけを出力してください（説明文は不要）。

```json
[{{"headline_ja": "日本語の見出し", "headline_vi": "Tiêu đề tiếng Việt",
  "summary_vi": "Tóm tắt 1–2 câu tiếng Việt", "date": "YYYY-MM-DD",
  "source": "報道機関名", "url": "記事URL", "score": 8}}]
```
score は話題性（1〜10）。新しい順ではなく、話題性の高い順に並べてください。"""
    text = ask(prompt, tools=["WebSearch", "WebFetch"], timeout=600)
    data = extract_json(text)
    if isinstance(data, dict):
        data = data.get("news") or data.get("items") or []
    return [x for x in data if isinstance(x, dict) and x.get("headline_ja")]


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
- 必ず標準語（共通語）で書く。日本全国の誰が聞いても分かる自然な話し言葉にする。
  方言・若者言葉・ネットスラング・過度な俗語（例:「バチクソ」「エグい」「ガチで」）は使わない。
- テンポよく引きのある語り口にするが、誹謗中傷や事実でないことは書かない。必要ならWeb検索で事実を確認する。
- 字幕は白背景に黒文字で表示され、1チャンク=1〜3行、1行は最大10文字。

## 構成ルール
- 台本を「シーン」に分ける。1シーン = 画像1枚 または 動画クリップ1本。
- 各シーンのナレーションは約{scene_chars}文字（{scene_sec}秒前後、最大でも{max_chars}文字）。
- 各シーンを字幕チャンクに分ける。チャンクは自然な文節で区切り、行の改行は "\\n" で表す。
  チャンクを全部つなげるとそのシーンのナレーションになること。
- tts: 読み上げ用テキスト。基本は字幕と同じだが、人名・難読漢字・数字・アルファベットは
  ひらがな/カタカナに直す（例: 上沢→うわさわ、4盗塁→よんとうるい、NBA→エヌビーエー）。
- action: そのシーンの内容が「動き」のある映像向きかを0〜10で評価
  （{action_rule}）。
- image_query: その場面に合う写真を探す検索語（日本語。{image_rule}）。
- video_query: その場面に合う動画（YouTube等）を探す検索語（日本語。{video_rule}）。
- voice: このテーマに合うナレーターの声。次の候補からそれぞれ1つ選ぶ:
  gender {genders} / age {ages} / pitch {pitches}

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
    dur = int(p["duration"])
    chars = int(dur * JA_CHARS_PER_SEC)
    scene_chars = int(IMAGE_SEC * JA_CHARS_PER_SEC)
    old = ""
    if feedback and p.get("scenes"):
        old = "\n".join(P.scene_plain_text(s) for s in p["scenes"])
        feedback = f"\n## 前回の台本\n{old}\n\n## 修正リクエスト（ベトナム語の場合あり。内容を理解して反映）\n{feedback}\n"
    gen = GENRES.get(p.get("genre") or "sports", GENRES["sports"])
    style = news_context(p.get("news") or {}) if p.get("genre") == "news" else gen["style"]
    extra = ("\n## 出典\n- sources に、事実確認に使った記事（見出し・URL・日付）を3件以上必ず入れる。\n"
             if p.get("genre") == "news" else "")
    prompt = PROMPT.format(
        role=gen["role"], style=style, extra=extra, action_rule=gen["action"],
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
        v = data.get("voice") or {}
        pp["voice"]["auto_instruct"] = ", ".join(
            x for x in (v.get("gender"), v.get("age"), v.get("pitch")) if x)
    P.update(pid, apply)
    info = P.ratio_info(scenes)
    log(f"Đã viết {len(scenes)} cảnh, ước tính {info['total']}s "
        f"(ảnh {info['image_pct']}% / video {info['video_pct']}%).", 1.0)
