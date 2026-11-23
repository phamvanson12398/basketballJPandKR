"""Thư viện kịch bản mẫu: kịch bản của các video nhiều view (đối thủ) để AI học BỐ CỤC & GIỌNG VĂN.
AI chỉ tham khảo cách viết, không chép nội dung/câu chữ. Bạn thêm/xóa trong Cài đặt.
Lưu ở library/reference_scripts.json."""
import json
import threading
import time
import uuid

from .config import ROOT

FILE = ROOT / "library" / "reference_scripts.json"
_lock = threading.Lock()

# 3 kịch bản đã phân tích (phụ đề đã sửa lỗi nhận dạng giọng nói)
DEFAULTS = [
    {"id": "tabata", "title": "田畑一也と野村克也（野村再生工場）", "lang": "ja", "genre": "sports", "sport": "baseball",
     "views": "", "note": "Hook bằng câu thoại → khổ luyện → đảo chiều → quay lại câu thoại → kết trước–sau",
     "text": "「お前、横から投げてみろよ。」ノムさんの言葉にブチギレた田畑一也は、ダイエー時代、4年間でわずか2勝しかできず、"
             "ヤクルトへのトレードを告げられた。社会人で右肩を手術し、一度は野球を諦めて大工をしていたが、"
             "12球団最後の指名で入団した苦労人。監督のノムさんから、自身への期待は少しも感じなかった。"
             "ところがキャンプが始まると、ノムさんはやたらと田畑を褒め続けた。紅白戦でも2回を無安打に抑えると、"
             "「このキャンプの一番の収穫は田畑や」とまで語り、開幕から先発ローテに入ると、田畑は3年ぶりの先発で"
             "移籍後初勝利を挙げ、最高のスタートを切った。しかしその後は先発で3連敗。ついにはリリーフに回された田畑に、"
             "ノムさんはこう告げた。「お前、広島の山崎みたいに横から投げてみろよ。」この言葉に腹を立てた田畑は、"
             "ブルペンでわざと真上から投げ込んだ。その姿を見ていたノムさんは、何も言わずそのままマウンドへ送り出し、"
             "田畑はいつも通りのフォームで2者連続三振を奪った。試合後に呼び出され、怒られると覚悟した田畑に、"
             "ノムさんは静かにこう言った。「お前に足りなかったのは、今日みたいな闘争心だぞ。それを忘れるな。」"
             "ここから先発に定着すると、前半戦だけで2度の完封を含む7勝。監督推薦でオールスターにも出場し、"
             "移籍1年目はチームトップの12勝、翌年は15勝を挙げ、防御率2.96。チームの優勝に貢献し、古田敦也とともに"
             "最優秀バッテリー賞にも輝いた。4年で2勝の苦労人は、こうして野村再生工場の最高傑作と呼ばれるようになったのだった。"},
    {"id": "rivera", "title": "マリアノ・リベラのカットボール誕生秘話", "lang": "ja", "genre": "sports", "sport": "baseball",
     "views": "", "note": "Hook so sánh với mốc Nhật (岩瀬407) → hình ảnh quen thuộc → しかし実は偶然 → lời chính chủ → số liệu → のだった",
     "text": "岩瀬のセーブ数407ですら少なく見えるバグ。652セーブをメジャーで記録したマリアノ・リベラは、"
             "ほぼ一球種で伝説の守護神として活躍。その武器となったカットボールは、リベラの全投球の約8割を占めていたが、"
             "攻略は困難を極め、メジャーの強打者たちを次々とねじ伏せていった。しかし実はこの高速カットボールは偶然誕生。"
             "1995年のデビュー当時、先発だったリベラは結果を残せず救援へと転向。そして97年6月、ブルペンで何気なく投げた速球が"
             "スライダー回転で急激に変化。後にリベラ自身が「神から与えられたもの。自然に起こった」と振り返るように、"
             "偶然に誕生した。これを武器にその年からクローザーを任されると、不動の守護神へと君臨。"
             "引退した2013年にも44セーブを記録し、通算セーブ数652は歴代1位の大記録で、通算防御率も2.21と安定感抜群の成績。"
             "特にポストシーズンにめっぽう強く、96試合141イニングを投げ、8勝1敗42セーブ、防御率0.70と圧倒的な成績で、"
             "リベラはヤンキース一筋で、常に勝利が求められる名門チームを支え続けたのだった。"},
    {"id": "ochiai", "title": "落合博満が無表情だった本当の理由", "lang": "ja", "genre": "sports", "sport": "baseball",
     "views": "", "note": "Hook 'có một HLV…' giấu tên → hình ảnh quen → しかし実は → nguồn phỏng vấn + câu thoại → なぜ → so sánh Hoshino → định nghĩa lại hook",
     "text": "試合中どんなミスが起きても表情を変えなかった監督がいる。落合博満。中日監督時代、落合はベンチでほとんど感情を見せなかった。"
             "選手がチャンスで凡退しても、投手が打たれても、顔色ひとつ変えない。しかし実はあの無表情、感情がなかったわけではない。"
             "2011年、監督退任後のインタビューで、落合はその裏側を明かした。イニングの合間にベンチ裏へ戻ると、"
             "監督室でお茶や水を飲みながら、独り言で不満を吐き出していたという。「あんなところで、あの球打ちやがって。」"
             "そんな言葉が口をついて出るほど、内心では怒っていた。それでもベンチに戻ると、表情を切り替えた。"
             "なぜそこまで感情を隠したのか。落合は理由をこう説明している。選手は監督の顔を見ている。怒っている姿を見せれば、"
             "選手の体が動かなくなるからだ。ミスをして監督の顔色をうかがうようになれば、選手は思い切ったプレーができない。"
             "だから落合は選手にこう伝えていた。勝ち負けの責任は監督である自分が取る。選手はグラウンドで戦ってこいと。"
             "かつての中日には、星野仙一監督のように、怒りを前面に出して選手を鼓舞する指導者もいた。"
             "落合はあえてその逆を選んだ。選手を怒らないために、監督自身が怒りを飲み込む。あの無表情は、冷酷さではなかった。"
             "選手がベンチではなく目の前の勝負に集中できるようにするための、落合なりの覚悟だった。"},
    {"id": "horse_food", "title": "名馬たちの食べ物エピソード（競馬）", "lang": "ja", "genre": "sports", "sport": "horse",
     "views": "", "note": "Tuyển tập 9 con ngựa, mỗi con 2–3 câu + câu bình luận vui; kết bằng Gold Ship 'それに対して'. "
                          "〔〕 = chữ đỏ (tên ngựa) · 【】 = đỏ + to · 《》 = to",
     "text": "〔グラスワンダー〕は放牧先に生えていた《タンポポ》を食べ過ぎて《太った》。"
             "〔グラスワンダー〕の孫の〔モーリス〕は、引退式で【花束を食い漁った】。"
             "〔コントレイル〕は人参を《すりおろさないと》食べれなかった。《赤ちゃん》のようだ。"
             "アメリカ最強馬の〔ゼニヤッタ〕は【ギネスビール】が大好きでよく酔っぱらってた。なぜかギネスビール以外は飲まなかったらしい。"
             "〔トウカイテイオー〕は高級種のふじりんごが大好きで、それ以外の《品種》は食べなかった。"
             "〔ドウデュース〕は【なんでも食べる】。その辺の草も、【手紙】も食べようとしたらしい。《やぎさんか》。"
             "〔ディープ〕はインタビュー中《可愛く》していると、おやつをもらえることを知っていたから、"
             "厩務員さんと【イチャイチャ】し、愛想を振りまいていたようだ。《あざとい！》"
             "〔スーパークリーク〕は、ご飯を綺麗に《4等分》にして食べやすくしないと食べなかった。"
             "〔シンザン〕は、幕の内弁当のようにきれいに配置しないと食べなかった。"
             "それに対して、〔ゴルシ〕はご飯を水に浸して《ぐちゃぐちゃ》にして、《お茶漬け》のように食べるのが【大好きだった！！！】"},
]
DELETED = ROOT / "library" / "reference_scripts_deleted.json"


def load() -> list[dict]:
    with _lock:
        if not FILE.exists():
            FILE.parent.mkdir(parents=True, exist_ok=True)
            FILE.write_text(json.dumps(DEFAULTS, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            items = json.loads(FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return list(DEFAULTS)
        # bản cập nhật có mẫu mới → tự thêm vào thư viện (trừ mẫu bạn đã xóa)
        deleted = set(json.loads(DELETED.read_text(encoding="utf-8"))) if DELETED.exists() else set()
        have = {x.get("id") for x in items}
        new = [d for d in DEFAULTS if d["id"] not in have and d["id"] not in deleted]
        if new:
            items += new
            FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        return items


def _save(items: list[dict]) -> None:
    with _lock:
        FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def add(data: dict) -> dict:
    text = (data.get("text") or "").strip()
    if len(text) < 40:
        raise ValueError("Kịch bản quá ngắn")
    item = {"id": uuid.uuid4().hex[:8], "title": (data.get("title") or text[:20]).strip(),
            "lang": data.get("lang") or "ja", "genre": data.get("genre") or "sports",
            "sport": data.get("sport") or "", "views": str(data.get("views") or "").strip(),
            "note": (data.get("note") or "").strip(), "text": text, "added": int(time.time())}
    items = load()
    items.insert(0, item)
    _save(items)
    return item


def delete(rid: str) -> None:
    _save([x for x in load() if x["id"] != rid])
    if any(d["id"] == rid for d in DEFAULTS):        # nhớ mẫu có sẵn đã xóa → không tự thêm lại
        deleted = set(json.loads(DELETED.read_text(encoding="utf-8"))) if DELETED.exists() else set()
        DELETED.write_text(json.dumps(sorted(deleted | {rid})), encoding="utf-8")


STORY_GENRES = ("sports", "biography", "brand", "history")
FORMAT_SPORTS = ("horse",)


def pick(lang: str, genre: str, sport: str | None = None, n: int = 3) -> list[dict]:
    """Chọn kịch bản mẫu gần nhất: cùng thể loại (thể thao ≈ tiểu sử) → cùng môn → cùng ngôn ngữ → mới thêm trước."""
    def close(g):
        return g == genre or (g in STORY_GENRES and genre in STORY_GENRES)
    items = [x for x in load() if close(x.get("genre"))]
    # môn có kiểu viết riêng (đua ngựa = tuyển tập chuyện vui): chỉ dùng mẫu cùng môn, môn khác không dùng mẫu này
    if sport in FORMAT_SPORTS and any(x.get("sport") == sport for x in items):
        items = [x for x in items if x.get("sport") == sport]
    else:
        items = [x for x in items if x.get("sport") not in FORMAT_SPORTS or x.get("sport") == sport]
    items.sort(key=lambda x: (x.get("genre") != genre, bool(sport) and x.get("sport") != sport,
                              x.get("lang") != lang, -int(x.get("added") or 0)))
    return items[:n]


def prompt_block(lang: str, genre: str, sport: str | None = None) -> str:
    refs = pick(lang, genre, sport)
    if not refs:
        return ""
    parts = ["## 参考台本（再生数の多い人気チャンネルの実例）",
             "- 構成・フックの作り方・反転のタイミング・語り口・締め方だけを学ぶこと。",
             "- 内容・言い回し・独特な表現をコピーしない（題材が違うので、学んだ型を今回の題材で作り直す）。"]
    if any(r.get("lang") != lang for r in refs):
        parts.append("- 参考台本の言語が出力言語と違う場合も、型だけを学び、出力は指定の言語で自然に書く。")
    for i, r in enumerate(refs, 1):
        parts.append(f"\n### 参考{i}: {r.get('title', '')}" + (f"（{r['views']}回再生）" if r.get("views") else ""))
        parts.append(r["text"][:2500])
    return "\n".join(parts) + "\n"
