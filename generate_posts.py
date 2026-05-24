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

# 1行目フックで使う職業シーン例(Geminiにはここから1つ選ばせる)
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
]

POST_PATTERNS = """
以下5つの型からランダムに3つを選び、1案ごとに別の型で3案作る。

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
""".strip()

PROMPT = f"""
あなたはX(旧Twitter)で月間1,000万インプを叩き出す日本語コピーライターです。
以下のアカウントの発信として、インプレッションが伸びる投稿案を3つ作ってください。

{ACCOUNT_BRIEF}

# 投稿の型
{POST_PATTERNS}

# 1行目フックの職業シーン候補(毎回ランダムに3つ別の職業を選ぶ)
{json.dumps(PERSONA_HOOKS, ensure_ascii=False, indent=2)}

# 絶対制約
- 各案 140文字以内(全角・改行含む)。X無料アカウント前提。
- 1案ごとに別の型・別の職業フックを使う。
- 1行目は必ず上記の職業シーンから始める(指を止めさせるため)。
- 中身は「全対人サービスに共通する選ばれる人のコミュニケーション術」にする。職業の話で終わらせず、必ず普遍化する。
- 各案に心理学または脳科学の用語を必ず1つ明示する(例: 返報性/自己参照効果/初頭効果/ザイガニック効果/ミラーリング/単純接触効果/ハロー効果/ピークエンドの法則/アンカリング/カクテルパーティー効果/メラビアンの法則 等)。同じ用語を3案で被らせない。

# 文体制約
- 語尾は「です。」「ます。」「ですよね。」など柔らかい断定で統一する。「〜しろ。」「〜だ。」などの強い命令/断定は禁止。
- 半角ダブルクォート(")は絶対に使わない。強調は鉤括弧「」を使う。
- ハッシュタグ・絵文字は使わない。
- 「〜について解説します」「いかがでしたか」など定型句は禁止。
- 一般論ではなく、シーンが目に浮かぶ具体描写で書く。

# 出力フォーマット(厳密にこのJSONのみ、前後に文字を入れない)
{{
  "posts": [
    {{"pattern": "型の名前", "persona_hook": "使った職業シーン", "term": "使った心理学/脳科学の用語", "text": "投稿本文"}},
    {{"pattern": "型の名前", "persona_hook": "...", "term": "...", "text": "..."}},
    {{"pattern": "型の名前", "persona_hook": "...", "term": "...", "text": "..."}}
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
        meta = f"フック: {post.get('persona_hook', '')} / 用語: {post.get('term', '')} / {len(post['text'])}字"
        lines.append(f"({meta})")
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
