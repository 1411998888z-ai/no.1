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
【発信軸】業界TOPがなぜ選ばれるのか、その「構造」を体験談 × 心理学 × 脳科学で解説
【トーン】断定的・本質訴求・逆張り・体験談ベース・小手先のテクニックを否定する
【看板フレーズ例】「売りたいなら、技術を磨くな。構造を理解しろ。」
""".strip()

POST_PATTERNS = """
以下5つの型からランダムに3つを選び、それぞれ別の型で3案作る。

1. 逆張り断定型
   形:「〜するな。〜しろ。」で始め、常識を一度否定してから本質を提示。
   例:「売りたいなら、技術を磨くな。構造を理解しろ。」

2. 共感→気づき型
   形:売れない人の行動を具体描写→「実は逆」と裏返す。
   例:「売れない営業ほど、商品説明が上手い。売れる営業は、相手に喋らせている。」

3. 箇条書きノウハウ型
   形:導入1行 → 箇条書き3〜5項目 → 締め1行。
   例:「業界TOPに共通する3つの習慣\n・〜\n・〜\n・〜\n結局、選ばれる人は構造で勝ってる。」

4. 体験談→学び型
   形:「100人コンサルして気づいた」「キャバ嬢No.1に聞いたら〇〇と言った」など具体エピソード→普遍的学び。

5. 脳科学/心理学解説型
   形:「人が買う瞬間、脳では〇〇が起きている」など科学的根拠→実務への落とし込み。
""".strip()

PROMPT = f"""
あなたはX(旧Twitter)で月間1,000万インプを叩き出す日本語コピーライターです。
以下のアカウントの発信として、インプレッションが伸びる投稿案を3つ作ってください。

{ACCOUNT_BRIEF}

# 投稿の型
{POST_PATTERNS}

# 制約
- 各案 140文字以内(全角・改行含む)。X無料アカウント前提。
- 1案ごとに別の型を使う。
- 「〜について解説します」「いかがでしたか」など平凡な表現は禁止。
- 冒頭1行目で必ず指を止めさせる(数字/逆説/断定/問い/具体名のいずれか)。
- ハッシュタグ・絵文字は使わない(発信者のトーンに合わせる)。
- 「対人サービス全般」に効くテーマを選び、営業だけに偏らない。
- 一般論ではなく、固有の言い回し・固有の比喩で書く。

# 出力フォーマット (厳密にこのJSONのみ、前後に文字を入れない)
{{
  "posts": [
    {{"pattern": "型の名前", "text": "投稿本文", "hook_reason": "なぜこの冒頭で指が止まるかを20字以内"}},
    {{"pattern": "型の名前", "text": "投稿本文", "hook_reason": "..."}},
    {{"pattern": "型の名前", "text": "投稿本文", "hook_reason": "..."}}
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
        lines.append(f"(フック狙い: {post.get('hook_reason', '')} / {len(post['text'])}字)")
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
