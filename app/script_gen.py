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
        "style": """- 事実ベースのエピソードを、短い文でテンポよく積み上げる。試合の実況やハイライト解説ではなく、
  1人（または1組）の人間ドラマとして語る。""",
        "action": "ダンク・ゴール・好プレー・歓喜・乱闘など=高、インタビュー・事実説明・数字=低",
        "image": "選手名+チーム名+状況など具体的に（例: 河村勇輝 グリズリーズ ドリブル）",
        "video": "選手名+試合/ハイライト/プレー など（例: 河村勇輝 ハイライト 2025）",
    },
    "biography": {
        "role": "{country}の「有名人の人生ストーリー・生い立ち」系ショート動画（TikTok / YouTube Shorts）",
        "style": """- 人生の落差（どん底 → 転機 → 成功）を軸に、知られざるエピソードを短い文でテンポよく積み上げる。
  生い立ちから順に年表をなぞらない。
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

# ---------------------------------------------------------------- CẤU TRÚC / HOOK
# Thể thao & Tiểu sử: khung "kể chuyện" học từ kênh YouTube có hiệu suất tốt
# (hook bằng câu thoại/con số → thân phận chật vật → đảo chiều mỗi 10–15s → giải thích hook ở giữa
#  → dồn dập thành tích → câu kết so sánh trước–sau).
HOOK_STORY = """## 構成（最重要。人気チャンネルで伸びている「物語型」の型に従う）
視聴者は最初の2〜3秒で離脱するかを決め、続きが気になる限り最後まで見る。次の流れで1本の物語にする:
1. 【フック】物語のいちばんの山場を切り取った一言から始める。
   - 実際に報道・本人インタビューで残っている「セリフ」（例:「お前、横から投げてみろよ。」）か、
     いちばん衝撃的な数字・事実（例:「4年でわずか2勝。」）。主役の名前もすぐ出す。
   - このフックの意味・結末はここでは説明しない（気になる状態のまま本編へ）。
   - 抽象的・詩的な一言（例:「明日より今。」）や、プロフィール（入団年・出身地）から始めない。
2. 【どん底・無名の紹介】主役が置かれていた苦しい状況を、数字入りで2〜3文に圧縮する
   （成績・トレード・ケガ・引退危機など。年表を長々と語らない）。「誰も期待していなかった」まで落とす。
3. 【展開】「ところが」「しかし」「その後」などの言葉で、10〜15秒ごとに流れを反転させる
   （好転 → また壁 → …）。1つの反転には必ず具体的な出来事・数字を1つ入れる。
4. 【フックの回収】動画の中盤〜後半で、冒頭のセリフ・数字の場面に戻り、その意味と背景をここで明かす
   （例: 冒頭のセリフに主役が反発した → 意外な相手の一言で心が変わった）。ここを感情のクライマックスにする。
5. 【逆転の結果】その後の成功を、記録・数字・タイトルをテンポよく畳みかけて見せる。
6. 【締め】冒頭の数字・状況と対比する一文で物語を閉じる
   （例:「4年で2勝の苦労人は、こうして〇〇の最高傑作と呼ばれるようになった。」）。
   問いかけは付けても付けなくてもよい（付けるなら締めの一文のあと短く）。

## 語り口
- 語り手が物語を語る口調。短い文で、過去形でテンポよく（日本語は「〜した。」「〜だった。」の常体。
  韓国語は 합니다체 を保つ）。
- 「」のセリフは、本人・監督・関係者が実際に言ったと報道・インタビューで確認できるものだけ使う。
  WebSearch で確認できないセリフは絶対に作らない（その場合はナレーションで「〜と言われた」と要約する）。
  セリフは字幕でも「」で囲む。
- 1シーン目は映像で見せたい「動き」のある場面にし、action を高く（8以上）する。
"""

# Tin tức / Top / Chung: đưa điều gây sốc lên trước
HOOK_DEFAULT = """## 冒頭と視聴維持（最重要。視聴者の多くは最初の2〜3秒で離脱する）
- 1文目（最初の約2秒）で、いちばん衝撃的な数字・事実と主役の名前を言い切る
  （例:「防御率0.41。中継ぎで史上初のMVP。」）。
  抽象的・詩的な一言（例:「明日より今。」）や、プロフィール（入団年・ドラフト順位・出身地）から始めない。
- 結論・いちばんすごいポイントを先に出し、そのあとで経緯を語る。時系列の年表どおりに語らない。
- 2文目で「なぜ？」「その代償は？」のような続きが気になる問い・予告を置く。
- 動画が長い場合は15〜20秒ごとに「でも本当にすごいのはここから」「その代償は大きかった」のような
  続きが気になる一言（再フック）を入れ、最後まで見る理由を作る。
- 最後は視聴者がコメントしたくなる問いかけで締める（例:「投げすぎだったと思う？」）。
- 1シーン目は映像で見せたい「動き」のある場面にし、action を高く（8以上）する。
"""

HOOK_RULES = {"sports": HOOK_STORY, "biography": HOOK_STORY}


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
- image_query / video_query は「選手名 + 球団名 + 場面（投球/本塁打/試合後）」で具体的に。
- video_query は必ず「試合の映像」が出る言葉にする: 「選手名 + 球団名 + 年 + ハイライト / 投球 / 奪三振 / 本塁打 / 打席」
  （例:「田畑一也 ヤクルト 1997 投球」「千賀滉大 メッツ 奪三振 ハイライト」）。
  インタビュー・トーク・対談・特集・会見・解説・YouTubeチャンネル系の動画を狙う言葉は入れない（試合映像だけを使う）。
  会見・インタビューの話の場面でも、video_query はその選手の試合での投球・打撃シーンにする。"""},
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
    "soccer": {"vi": "⚽ Bóng đá", "ja": "サッカー", "rule": """## 競技: サッカー（Jリーグ / Kリーグ / 欧州5大リーグ / W杯・アジア杯・代表戦）
- 用語を正確に使う: ゴール・アシスト・クリーンシート・PK・FK・ハットトリック・オフサイド・VAR・
  移籍金・契約満了・代表キャップ・得点王・アシスト王・欧州CL・W杯予選・日韓戦。
- 数字（得点・出場数・移籍金・順位）は公式記録や大手報道で確認。移籍の噂は「〜と報じられています」と書き、確定扱いしない。
- 海外選手・海外クラブ名は日本（韓国）の報道で一般的な表記にし、tts では読みをかな（ハングル）にする
  （例: 三笘薫→みとまかおる、久保建英→くぼたけふさ、ソン・フンミン→ソンフンミン、Man City→マンチェスターシティ）。
- 日本・韓国の選手が欧州でどう評価されているか、代表での役割など、{country}の視聴者が誇りや関心を持てる切り口を優先。
- action: ゴールの瞬間・ドリブル突破・スーパーセーブ・逆転・優勝セレブレーション=高、移籍金や順位表の説明=低。
- image_query は「選手名 + クラブ名/代表 + 場面（ゴール/ドリブル/セレブレーション）+ 年」、
  video_query は「選手名 + ゴール/ハイライト + 試合名（例: ブライトン 三笘 ゴール ハイライト）」。
- video_query は必ず試合の映像が出る言葉にする。インタビュー・トーク・対談・特集・会見・解説系は狙わない。"""},
    "idol": {"vi": "🎤 Idol Nhật", "ja": "アイドル", "rule": """## 分野: 日本のアイドル（AKB48・坂道シリーズ・ハロー！プロジェクト・ジャニーズ系/STARTO・地下〜ライブアイドル など）
- グループ名・メンバー名・期・ユニット名・楽曲名を正確に。tts ではメンバー名の読みを必ずひらがな（韓国語ならハングル）にする
  （例: 齋藤飛鳥→さいとうあすか、白石麻衣→しらいしまい、前田敦子→まえだあつこ、指原莉乃→さしはらりの）。
- 順位や「特別扱い」などの根拠は、センター回数・選抜回数・総選挙の順位・ソロ曲の数・公式インタビューや本人/関係者の公式発言など、
  確認できる事実だけを使う。主観的なランキングは「独自に選んだ」と分かる言い方にする。
- 恋愛・私生活のうわさ、スキャンダル、プロデューサーとの私的関係をにおわせる表現、容姿をけなす表現は書かない。
  卒業・脱退の理由も公式発表の範囲で書く。ファンが不快にならない敬意ある語り口にする。
- action: ライブ・MVのダンス・握手会や卒業セレモニーの盛り上がり=高、経歴や数字の説明=低。
- image_query は「メンバー名 + グループ名 + 場面（ライブ/卒業コンサート/選抜発表/写真集発売イベント）」、
  video_query は「グループ名 + 曲名 + MV / ライブ」や「メンバー名 + 卒業コンサート」。"""},
    "kpop": {"vi": "🎶 K-pop", "ja": "K-POP", "rule": """## 分野: K-POP（BTS・BLACKPINK・TWICE・SEVENTEEN・Stray Kids・aespa・IVE・LE SSERAFIM・NewJeans など）
- グループ名・メンバー名・事務所（HYBE・SM・JYP・YG など）・ファンダム名・曲名を正確に。
  韓国語の動画ではハングル表記（例: 블랙핑크, 뉴진스, 아이브）、日本語の動画では日本で一般的なカタカナ表記（例: ブラックピンク, ニュージーンズ）。
- tts では英字のグループ名・曲名・メンバー名を読みのハングル/カタカナにする
  （例: BLACKPINK→블랙핑크 / ブラックピンク、IVE→아이브 / アイヴ、aespa→에스파 / エスパ、LISA→리사 / リサ）。
- 実績の数字は確認できる事実だけ: 音楽番組1位の回数、Circle（旧ガオン）チャート・ハントチャート・MelOn の記録、
  Billboard・Spotify の記録、アルバム初動枚数、ワールドツアー動員、授賞式（MAMA・ゴールデンディスク など）の受賞。
- 恋愛・熱愛のうわさ、メンバー間の不仲説、整形・容姿の話、事務所との紛争の憶測は書かない。
  紛争・活動休止・脱退は公式発表や判決など確定した事実の範囲だけを、中立的に書く。
- 日本語の動画では、日本での活動（日本デビュー・オリコン・紅白・東京ドーム公演 など）や日本人メンバーに触れると日本の視聴者に響く。
  韓国語の動画では、韓国の視聴者が誇りや関心を持てる切り口（世界記録・ビルボード・海外の反応 など）を優先。
- action: ステージ・パフォーマンス・ダンス・受賞の瞬間・コンサートの歓声=高、記録や経歴の説明=低。
- image_query はメンバー名/グループ名 + 場面（ステージ・コンサート・授賞式・空港・ジャケット写真）、
  video_query はグループ名 + 曲名 + MV / 퍼포먼스 / 음악방송 / ライブ。"""},
    "owarai": {"vi": "😂 Hài / M-1", "ja": "お笑い", "rule": """## 分野: お笑い芸人（M-1グランプリ・キングオブコント・R-1・THE SECOND など）
- コンビ名・芸人名・事務所（吉本興業・松竹芸能・人力舎・ワタナベ・太田プロ など）・大会名・審査員名を正確に。
  tts ではコンビ名・芸名の読みを必ずかな（韓国語ならハングル）にする
  （例: 霜降り明星→しもふりみょうじょう、錦鯉→にしきごい、令和ロマン→れいわロマン、千鳥→ちどり、ミルクボーイ→ミルクボーイ）。
- 事実だけを使う: 優勝年、決勝の点数・順位、審査員の採点、結成年、芸歴、敗者復活からの勝ち上がり、
  M-1の「結成15年以内」ルールと「ラストイヤー」。数字は大会公式・報道で確認する。
- 人気の切り口: 下積み・アルバイト生活・解散危機・ラストイヤー・敗者復活・遅咲き・審査員の名言・優勝後の人生の変化。
- ネタの台本を長く書き写さない（著作物）。ネタは内容を短く説明し、引用はキーフレーズ1つまで。
- スキャンダル・不祥事・訴訟はうわさを書かない。触れる場合は公式発表・判決など確定した事実だけを中立に。
  容姿いじりや差別的な表現をそのまま使わない。
- 韓国語の動画では、漫才（만자이）やM-1（일본 최대 개그 대회）を韓国の視聴者向けに短く補足する。
- action: 優勝の瞬間・ネタ中の大爆笑・審査員の高得点発表・涙の会見=高、経歴や数字の説明=低。
- image_query は「コンビ名 + M-1 + 優勝/決勝/会見」、video_query は「コンビ名 + M-1 + 漫才 / 優勝の瞬間 / 敗者復活」。"""},
    "other": {"vi": "🏅 Khác", "ja": "", "rule": ""},
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
SPORT_SCREEN_RULES = {
    "sumo": """## 画面表示用テキスト（JSON の "screen" と各シーン。ストーリー形式の動画なので、該当するシーンにだけ入れる）
- screen.basho: 話の中心となる場所名（例: 「九州場所 13日目」）。特定の場所の話でなければ空文字。
- 各シーンの "banzuke": そのシーンで主役の力士の番付（例: 「横綱」「大関」「前頭7枚目」）。主役が映らない場面は入れない。
- 各シーンの "name": その力士の四股名、"record": その場所の成績（例: 「11勝1敗」）。不明なら record は空。
- 各シーンの "kimarite": ナレーションで勝負が決まった瞬間を語るシーンにだけ決まり手（例: 「寄り切り」）。それ以外は入れない。
- 生い立ち・エピソード・背景を語るシーンにはこれらを無理に入れない（入れなければ普通の写真＋字幕になる）。""",
    "soccer": """## 画面表示用テキスト（JSON の "screen" と各シーン。ストーリー形式の動画なので、該当するシーンにだけ入れる）
- screen.league: 話の中心となる大会・節（例: 「プレミアリーグ 第10節」）。特定の試合の話でなければ空文字。
- screen.home / screen.away: その試合のチーム略称（3文字程度、例: 「COV」「SUN」）。試合の話でなければ空。
- 各シーンの "score": そのシーンの時点のスコア（例: 「1-0」）と "minute": 時間（例: 「17'」）。
  試合の経過を語るシーンにだけ入れ、生い立ち・移籍・背景などのシーンには入れない。
- 各シーンの "player": そのシーンの主役の選手名、"team": 所属と背番号（例: 「コヴェントリー #7」）。主役が映らない場面は入れない。""",
}
KOREA_SCREEN_RULE = """## 画面表示用テキスト（韓国式ショート: 黒背景・上部に2行の固定タイトル・大きな写真）
- screen.title1: 上段の黄色タイトル（最大12文字。例: 「롯데가 정철원 먼저」）、screen.title2: 下段の赤タイトル（最大12文字。例: 「팔아넘긴 진짜 이유」）。
  2行で1つの強いフックになるようにする。
- 字幕チャンクは短いフレーズ: 1チャンク=1〜2行、1行は最大10文字（2〜4語）。テンポよく切り替わるように細かく区切る。
- 各シーンの "stat": ナレーションで成績・数字を語るシーンにだけ、要点の数字（最大16文字。例: 「타율 2할 8리 / 1홈런」「평균자책점 6.75」）。
- 2人の選手を比べる・トレードで交換するなど「2人」が主題のシーンは "split": true にし、
  image_query に1人目、"image_query2" に2人目の検索語を入れる（画面を左右に分けて2人を並べる）。"""
SCENE_LABELS = ("stat", "split", "image_query2",
                "story", "rank", "rank_label", "year", "chapter",
                "banzuke", "name", "record", "kimarite", "score", "minute", "player", "team")


# ---------------------------------------------------------------- PROMPT
PROMPT = """あなたは{role}の人気ナレーション作家です。
以下の条件で、縦型ショート動画のナレーション台本を書いてください。

## 入力
- タイトル: {title}
- テーマ・メモ: {topic}
- 目標の長さ: 約{duration}秒（ナレーション合計 約{chars}文字）
{feedback}

{hook_rule}

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
- who: そのシーンの画面に映すべき人物・チーム・対象の正式名（フルネーム。複数なら「・」区切り）。
  検索結果がその人物かどうかの判定に使う。人物がいない場面は空文字。
- image_query: その場面に合う写真を探す検索語（{query_lang}。{image_rule}）。
- video_query: その場面に合う動画（YouTube / Facebook 等）を探す検索語（{query_lang}。{video_rule}）。
- query_alt: image_query で見つからない時の、もっと広い予備の検索語（例:「人物名 + 当時のチーム名」だけ）。

## 検索語のルール（重要。検索結果が別人・無関係にならないように）
- 人物が映る場面は、検索語の先頭に必ずその人物のフルネーム（{query_lang}の一般的な表記）を入れる。
  名字だけ・あだ名だけ・「監督」「彼」などの代名詞は使わない。
- 2〜4語に絞る。「名前 + 当時の所属 + 年 or 具体的な場面」（例:「田畑一也 ヤクルト 1997」「野村克也 ヤクルト 監督」）。
- その場面の時代に合わせる（現役当時の話なら当時のチーム名・年。現在の話なら現在の所属）。
- 「苦悩」「転機」「努力」「感動」「名言」のような抽象語・感情語は検索語に入れない（写真に写らないため）。
- 実在の写真・映像が見つかりそうな、報道で使われる言葉にする（試合/会見/入団会見/優勝/引退会見/トレード など）。
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
      "who": "上沢直之",
      "image_query": "上沢直之 ソフトバンク 投球",
      "video_query": "上沢直之 オープン戦 日本ハム 2024",
      "query_alt": "上沢直之 日本ハム"
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
    from .layouts import resolve as resolve_layout
    korea_layout = resolve_layout(p) == "korea"
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
        hook_rule=HOOK_RULES.get(p.get("genre") or "sports", HOOK_DEFAULT),
        lang_rules=L["rules"], line_max=10 if korea_layout else L["line_max"], tts_rule=L["tts_rule"],
        query_lang=L["query_lang"],
        screen_rule=(KOREA_SCREEN_RULE if korea_layout else SCREEN_RULES.get(p.get("genre"), "") or
                     (SPORT_SCREEN_RULES.get(p.get("sport"), "") if (p.get("genre") or "sports") == "sports" else "")),
        sport_rule=SPORTS.get(p.get("sport") or "other", SPORTS["other"])["rule"].replace("{country}", L["country"]),
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
            "who": str(s.get("who") or "").strip(),
            "query_alt": str(s.get("query_alt") or "").strip(),
            "kind": "image",
            **{k: s[k] for k in SCENE_LABELS if s.get(k) not in (None, "", False)},
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
