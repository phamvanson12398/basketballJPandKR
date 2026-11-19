"""Viết content (kịch bản) tiếng Nhật bằng Claude CLI."""
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
    "general": {
        "role": "日本の雑学・ニュース解説系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 1文目で「えっ？」と思わせるフック。
- 事実ベースの情報を、短い文でテンポよく積み上げ、意外なオチで締める。""",
        "action": "動きのある出来事・現場の様子=高、説明・数字・データ=低",
        "image": "テーマ+具体的な対象・場所・出来事",
        "video": "テーマ+ニュース/現場/解説 など",
    },
}

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

## 出力形式（JSONのみ。説明文は不要。下の例は形式の見本で、内容は無関係）
```json
{{
  "title": "動画タイトル（入力タイトルがあればそれを使う）",
  "voice": {{"gender": "male", "age": "middle-aged", "pitch": "low pitch"}},
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
    prompt = PROMPT.format(
        role=gen["role"], style=gen["style"], action_rule=gen["action"],
        image_rule=gen["image"], video_rule=gen["video"],
        title=p.get("title") or "（なし。テーマから魅力的なタイトルを考える）",
        topic=p.get("topic") or "（なし）",
        duration=dur, chars=chars, scene_chars=scene_chars, scene_sec=IMAGE_SEC,
        max_chars=int(scene_chars * 1.6), feedback=feedback,
        genders=VOICE_DESIGN_OPTIONS["gender"], ages=VOICE_DESIGN_OPTIONS["age"],
        pitches=VOICE_DESIGN_OPTIONS["pitch"],
    )
    log("Đang nhờ Claude viết content (có thể tra cứu web, mất 1–3 phút)...", 0.1)
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
        v = data.get("voice") or {}
        pp["voice"]["auto_instruct"] = ", ".join(
            x for x in (v.get("gender"), v.get("age"), v.get("pitch")) if x)
    P.update(pid, apply)
    info = P.ratio_info(scenes)
    log(f"Đã viết {len(scenes)} cảnh, ước tính {info['total']}s "
        f"(ảnh {info['image_pct']}% / video {info['video_pct']}%).", 1.0)
