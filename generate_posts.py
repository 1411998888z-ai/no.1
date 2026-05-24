import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_TO_USER_ID = os.environ["LINE_TO_USER_ID"]

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

ACCOUNT_BRIEF = """
【発信者】サク @「戦略的に選ばれる」セールス設計士 (@_x_saku_)
【ターゲット】対人サービスで稼ぐ人(営業マン/セラピスト/コーチ/占い師/飲食店/エステ/整体/キャバ嬢/ホスト)
【発信軸】全対人サービスに共通する「選ばれる人のコミュニケーション術」を、心理学・脳科学の用語で裏打ちして解説する。
【トーン】柔らかい断定。語尾は「です。」「ます。」「ですよね。」を基本とする。
""".strip()

# 1行目フックで使う職業シーン候補
PERSONA_HOOKS = [
    "指名が止まらないキャバ嬢",
    "指名が取れないホスト",
    "リピート率8割超えの整体師",
    "予約の取れないセラピスト",
    "鑑定後に必ず予約を入れさせる占い師",
    "全国TOPセールス",
    "潰れないスナックのママ",
    "口コミだけで埋まるエステティシャン",
    "リピートだけで満席の飲食店オーナー",
    "クライアントが3年続くコーチ",
    "紹介だけで指名が回る美容師",
    "1ヶ月先まで予約が埋まるネイリスト",
    "相談が途切れないカウンセラー",
    "売上トップの不動産営業",
    "解約率が低い保険外交員",
    "生徒が辞めないヨガインストラクター",
    "成婚率の高い結婚相談所カウンセラー",
    "リピート率の高いパーソナルトレーナー",
    "月商7桁の個人サロンオーナー",
    "常連で埋まるバーのマスター",
    "法人契約が切れないコンサルタント",
    "紹介が止まらない税理士",
    "クチコミだけで生徒が集まる塾講師",
    "売れ続けるアパレル販売員",
    "二次会まで指名されるキャバ嬢",
]

# 心理学/脳科学の用語候補
PSYCH_TERMS = [
    "返報性",
    "自己開示の返報性",
    "好意の返報性",
    "自己参照効果",
    "初頭効果",
    "親近効果",
    "ザイガニック効果",
    "ミラーリング",
    "バックトラッキング",
    "単純接触効果",
    "ハロー効果",
    "ピークエンドの法則",
    "アンカリング",
    "カクテルパーティー効果",
    "メラビアンの法則",
    "バーナム効果",
    "ベン・フランクリン効果",
    "認知的不協和",
    "コミットメントと一貫性の法則",
    "社会的証明",
    "希少性の原理",
    "権威への服従",
    "フット・イン・ザ・ドア",
    "ドア・イン・ザ・フェイス",
    "ローボール・テクニック",
    "プロスペクト理論",
    "損失回避",
    "フレーミング効果",
    "確証バイアス",
    "認知的流暢性",
    "リフレーミング",
    "ラベリング効果",
    "ピグマリオン効果",
    "ゴーレム効果",
    "エンハンシング効果",
    "両面提示の法則",
    "スリーパー効果",
    "つり橋効果",
    "ハード・トゥ・ゲット",
    "YESセット",
    "Iメッセージ",
]

# シーン軸(投稿のフォーカスする瞬間)
SCENE_AXES = [
    "初回接客の最初の30秒",
    "リピーターになるかどうかの分かれ目",
    "クロージング・価格提示の瞬間",
    "クレーム対応中",
    "紹介が発生する瞬間",
    "別れ際・見送りの30秒",
    "アフターフォローの連絡",
    "リピート2回目以降の関係深化",
    "売り込み前の関係構築",
    "高単価を提示する瞬間",
    "断られた直後の振る舞い",
    "雑談から本題に入る間",
]

# 対比軸(誰と誰を比べるか)
CONTRAST_AXES = [
    "売れる人 vs 売れない人",
    "リピートされる人 vs されない人",
    "指名が取れる人 vs 取れない人",
    "紹介が発生する人 vs しない人",
    "高単価で売れる人 vs 値引きしないと売れない人",
    "選ばれ続ける人 vs 一回で終わる人",
]

POST_PATTERNS = """
以下8つの型からランダムに3つを選び、1案ごとに別の型で3案作る。

1. 逆張り断定型
   構成: 1行目で職業の固有シーン→常識を否定→心理学/脳科学の用語で根拠提示→普遍化した一言で締め。

2. 共感→気づき型
   構成: 1行目で「選ばれる側」の具体行動→2行目で「選ばれない側」の対比行動→心理学/脳科学の用語で根拠→普遍化。

3. 箇条書きノウハウ型
   構成: 1行目に職業の固有シーンを置いた導入→箇条書き3項目(各項目に心理現象を絡める)→普遍化した締め。

4. 体験談→学び型
   構成: 「100人見てきて気づいた」など固有数字のエピソード→具体行動の発見→心理学/脳科学の用語で根拠→普遍化。

5. 脳科学/心理学解説型
   構成: 職業の具体行動を1行目に→脳/心理の仕組みを解説→現象名を明示→普遍化した一言で締め。

6. 失敗エピソード型
   構成: 1行目で職業の固有シーン→「昔は〜してた」と過去の失敗→気づき→心理学/脳科学の用語→普遍化。

7. 比喩で説明型
   構成: 1行目で職業の固有シーン→「これは〇〇と同じ」と異領域の比喩で説明→心理学/脳科学の用語→普遍化。

8. Q&A自問自答型
   構成: 1行目で職業の固有シーン→読み手が抱きそうな疑問を提示→答え→心理学/脳科学の用語→普遍化。
""".strip()

PROMPT = f"""
あなたはX(旧Twitter)で月間1,000万インプを叩き出す日本語コピーライターです。
以下のアカウントの発信として、インプレッションが伸びる投稿案を3つ作ってください。

{ACCOUNT_BRIEF}

# 投稿の型
{POST_PATTERNS}

# 1行目フックの職業シーン候補
{json.dumps(PERSONA_HOOKS, ensure_ascii=False, indent=2)}

# 心理学/脳科学の用語候補
{json.dumps(PSYCH_TERMS, ensure_ascii=False, indent=2)}

# シーン軸候補(投稿のフォーカスする瞬間。任意で1つ選び、行動描写を寄せる)
{json.dumps(SCENE_AXES, ensure_ascii=False, indent=2)}

# 対比軸候補(共感→気づき型などで使う)
{json.dumps(CONTRAST_AXES, ensure_ascii=False, indent=2)}

# 絶対制約
- 各案 140文字以内(全角・改行含む)。X無料アカウント前提。
- 1案ごとに「別の型・別の職業フック・別の心理学用語」を使う(3案で全て被らせない)。
- 1行目は必ず職業シーン候補から1つ選んで始める(指を止めさせるため)。
- 中身は「全対人サービスに共通する選ばれる人のコミュニケーション術」にする。職業の話で終わらせず、必ず普遍化する。
- 各案に心理学/脳科学の用語を必ず1つ明示する(候補リストから選ぶか、同レベルの著名な用語を使う)。
- シーン軸/対比軸は必須ではないが、ネタが似てきたら積極的に使い分けて多様性を出す。

# 文体制約
- 語尾は「です。」「ます。」「ですよね。」など柔らかい断定で統一する。「〜しろ。」「〜だ。」などの強い命令/断定は禁止。
- 半角ダブルクォート(")は絶対に使わない。強調は鉤括弧「」を使う。
- ハッシュタグ・絵文字は使わない。
- 「〜について解説します」「いかがでしたか」など定型句は禁止。
- 一般論ではなく、シーンが目に浮かぶ具体描写で書く。

# 出力フォーマット(厳密にこのJSONのみ、前後に文字を入れない)
{{
  "posts": [
    {{"pattern": "型の名前", "persona_hook": "使った職業シーン", "term": "使った心理学/脳科学の用語", "scene_axis": "使ったシーン軸(なければ空文字)", "text": "投稿本文"}},
    {{"pattern": "型の名前", "persona_hook": "...", "term": "...", "scene_axis": "...", "text": "..."}},
    {{"pattern": "型の名前", "persona_hook": "...", "term": "...", "scene_axis": "...", "text": "..."}}
  ]
}}
""".strip()


def call_gemini() -> dict:
    body = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {
            "temperature": 1.1,
            "topP": 0.95,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        payload = json.loads(res.read().decode("utf-8"))
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def format_line_message(result: dict) -> str:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d")
    lines = [f"☀ {today} の投稿候補 3案", ""]
    for i, post in enumerate(result["posts"], 1):
        lines.append(f"━━━ 案{i}【{post.get('pattern', '')}】━━━")
        lines.append(post["text"])
        meta_parts = [
            f"フック: {post.get('persona_hook', '')}",
            f"用語: {post.get('term', '')}",
        ]
        if post.get("scene_axis"):
            meta_parts.append(f"シーン: {post['scene_axis']}")
        meta_parts.append(f"{len(post['text'])}字")
        lines.append("(" + " / ".join(meta_parts) + ")")
        lines.append("")
    lines.append("精査して良ければXへ。")
    return "\n".join(lines).strip()


def push_to_line(message: str) -> None:
    body = {
        "to": LINE_TO_USER_ID,
        "messages": [{"type": "text", "text": message[:4900]}],
    }
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            res.read()
    except urllib.error.HTTPError as e:
        print(f"LINE push failed: {e.code} {e.read().decode('utf-8')}", file=sys.stderr)
        raise


def main() -> None:
    result = call_gemini()
    message = format_line_message(result)
    print(message)
    push_to_line(message)


if __name__ == "__main__":
    main()
