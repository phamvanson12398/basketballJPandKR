"""Viết content (kịch bản) tiếng Nhật bằng Claude CLI."""
from . import project as P
from .claude_cli import ask, extract_json
from .config import JA_CHARS_PER_SEC, IMAGE_SEC
from .tts import VOICE_DESIGN_OPTIONS

PROMPT = """あなたは日本のスポーツ系ショート動画（TikTok / YouTube Shorts）の人気ナレーション作家です。
以下の条件で、縦型ショート動画のナレーション台本を書いてください。

## 入力
- タイトル: {title}
- テーマ・メモ: {topic}
- 目標の長さ: 約{duration}秒（ナレーション合計 約{chars}文字）
{feedback}

## スタイル（参考動画の特徴）
- 1文目で強烈なフック（例:「日ハムから返品不可の刻印を押された男」）。
- 事実ベースのエピソードを、短い文でテンポよく積み上げ、意外な展開やオチで締める。
- 口語的で煽り気味だが、誹謗中傷や事実でないことは書かない。必要ならWeb検索で事実を確認する。
- 字幕は白背景に黒文字で表示され、1チャンク=1〜3行、1行は最大10文字。

## 構成ルール
- 台本を「シーン」に分ける。1シーン = 画像1枚 または 動画クリップ1本。
- 各シーンのナレーションは約{scene_chars}文字（{scene_sec}秒前後、最大でも{max_chars}文字）。
- 各シーンを字幕チャンクに分ける。チャンクは自然な文節で区切り、行の改行は "\\n" で表す。
  チャンクを全部つなげるとそのシーンのナレーションになること。
- tts: 読み上げ用テキスト。基本は字幕と同じだが、選手名・難読漢字・数字・アルファベットは
  ひらがな/カタカナに直す（例: 上沢→うわさわ、4盗塁→よんとうるい、NBA→エヌビーエー）。
- action: そのシーンの内容が「動き」のある映像向きかを0〜10で評価
  （ダンク・プレー・歓喜・乱闘など=高、インタビュー・事実説明・数字=低）。
- image_query: その場面に合う写真を探す検索語（日本語、選手名+チーム名+状況など具体的に）。
- video_query: その場面に合う動画（YouTubeハイライト等）を探す検索語（日本語）。
- voice: このテーマに合うナレーターの声。次の候補からそれぞれ1つ選ぶ:
  gender {genders} / age {ages} / pitch {pitches}

## 出力形式（JSONのみ。説明文は不要）
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
    prompt = PROMPT.format(
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
    P.rebalance(scenes)

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
