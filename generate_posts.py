"""投稿候補と画像を生成し、ローカルに保存する。
LINE送信は send_to_line.py が担当(画像をGitHubに先にpushしてraw URLを有効化するため)。"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

REPO_ROOT = Path(__file__).parent
STATE_PATH = REPO_ROOT / "state.json"
PENDING_PATH = REPO_ROOT / "pending_message.json"

ACCOUNT_BRIEF = """
【発信者】サク @「戦略的に選ばれる」セールス設計士 (@_x_saku_)
【ターゲット】対人サービスで稼ぐ人(営業マン/セラピスト/コーチ/占い師/飲食店/エステ/整体/キャバ嬢/ホスト 等)
【発信軸】全対人サービスに共通する「選ばれる人のコミュニケーション術」を、心理学・脳科学の用語で裏打ちして解説する。
【トーン】柔らかい断定。語尾は「です。」「ます。」「ですよね。」を基本とする。
""".strip()

# ティア定義: S=フォロワー獲得期の鉄板、A=2nd弾、B=応用編
PERSONA_TIERS = {
    "S": [
        "指名が止まらないキャバ嬢",
        "指名が取れないホスト",
        "鑑定後に必ず予約を入れさせる占い師",
        "全国TOPセールス",
        "潰れないスナックのママ",
    ],
    "A": [
        "リピート率8割超えの整体師",
        "予約の取れないセラピスト",
        "口コミだけで埋まるエステティシャン",
        "リピートだけで満席の飲食店オーナー",
        "クライアントが3年続くコーチ",
        "紹介だけで指名が回る美容師",
        "二次会まで指名されるキャバ嬢",
        "常連で埋まるバーのマスター",
    ],
    "B": [
        "1ヶ月先まで予約が埋まるネイリスト",
        "相談が途切れないカウンセラー",
        "売上トップの不動産営業",
        "解約率が低い保険外交員",
        "生徒が辞めないヨガインストラクター",
        "成婚率の高い結婚相談所カウンセラー",
        "リピート率の高いパーソナルトレーナー",
        "月商7桁の個人サロンオーナー",
        "法人契約が切れないコンサルタント",
        "紹介が止まらない税理士",
        "クチコミだけで生徒が集まる塾講師",
        "売れ続けるアパレル販売員",
    ],
}

TERM_TIERS = {
    "S": [
        "返報性",
        "ミラーリング",
        "単純接触効果",
        "初頭効果",
        "ハロー効果",
        "メラビアンの法則",
        "アンカリング",
        "ピークエンドの法則",
        "認知的不協和",
        "社会的証明",
    ],
    "A": [
        "自己参照効果",
        "ザイガニック効果",
        "カクテルパーティー効果",
        "バーナム効果",
        "希少性の原理",
        "ピグマリオン効果",
        "つり橋効果",
        "プロスペクト理論",
        "損失回避",
        "確証バイアス",
        "ラベリング効果",
        "フット・イン・ザ・ドア",
        "ドア・イン・ザ・フェイス",
    ],
    "B": [
        "自己開示の返報性",
        "好意の返報性",
        "親近効果",
        "バックトラッキング",
        "ベン・フランクリン効果",
        "コミットメントと一貫性の法則",
        "権威への服従",
        "ローボール・テクニック",
        "フレーミング効果",
        "認知的流暢性",
        "リフレーミング",
        "ゴーレム効果",
        "エンハンシング効果",
        "両面提示の法則",
        "スリーパー効果",
        "ハード・トゥ・ゲット",
        "YESセット",
        "Iメッセージ",
    ],
}

PATTERN_TIERS = {
    "S": ["共感→気づき型", "逆張り断定型", "脳科学/心理学解説型"],
    "A": ["体験談→学び型", "箇条書きノウハウ型"],
    "B": ["失敗エピソード型", "比喩で説明型", "Q&A自問自答型"],
}

PATTERN_DESCRIPTIONS = {
    "逆張り断定型": "1行目で職業の固有シーン→常識を否定→心理学/脳科学の用語で根拠提示→普遍化した一言で締め。",
    "共感→気づき型": "1行目で「選ばれる側」の具体行動→2行目で「選ばれない側」の対比行動→心理学/脳科学の用語で根拠→普遍化。",
    "箇条書きノウハウ型": "1行目に職業の固有シーンを置いた導入→箇条書き3項目→普遍化した締め。",
    "体験談→学び型": "「100人見てきて気づいた」など固有数字のエピソード→具体行動の発見→心理学/脳科学の用語で根拠→普遍化。",
    "脳科学/心理学解説型": "職業の具体行動を1行目に→脳/心理の仕組みを解説→現象名を明示→普遍化した一言で締め。",
    "失敗エピソード型": "1行目で職業の固有シーン→「昔は〜してた」と過去の失敗→気づき→心理学/脳科学の用語→普遍化。",
    "比喩で説明型": "1行目で職業の固有シーン→「これは〇〇と同じ」と異領域の比喩で説明→心理学/脳科学の用語→普遍化。",
    "Q&A自問自答型": "1行目で職業の固有シーン→読み手が抱きそうな疑問を提示→答え→心理学/脳科学の用語→普遍化。",
}

def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"used_triples": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def items_up_to_tier(tiered: dict, max_tier: str) -> list:
    order = ["S", "A", "B"]
    cutoff = order.index(max_tier)
    items = []
    for t in order[: cutoff + 1]:
        items.extend(tiered.get(t, []))
    return items


def select_triples(state: dict, count: int = 3) -> tuple:
    """Phase S→A→Bの順で、未使用の(persona, term, pattern)を3つ選ぶ。
    3案は職業・用語・型が全て被らないようにする。"""
    used = {tuple(t) for t in state["used_triples"]}

    for phase in ("S", "A", "B"):
        personas = items_up_to_tier(PERSONA_TIERS, phase)
        terms = items_up_to_tier(TERM_TIERS, phase)
        patterns = items_up_to_tier(PATTERN_TIERS, phase)

        candidates = [
            (p, t, pat)
            for p in personas
            for t in terms
            for pat in patterns
            if (p, t, pat) not in used
        ]
        if len(candidates) < count:
            continue

        random.shuffle(candidates)
        selected = []
        used_p, used_t, used_pat = set(), set(), set()
        for triple in candidates:
            p, t, pat = triple
            if p in used_p or t in used_t or pat in used_pat:
                continue
            selected.append(triple)
            used_p.add(p)
            used_t.add(t)
            used_pat.add(pat)
            if len(selected) == count:
                return selected, phase

        if selected:
            return selected, phase

    # 全phase使い切ったらリセット
    print("All triples exhausted — resetting state.", file=sys.stderr)
    state["used_triples"] = []
    return select_triples(state, count)


def build_prompt(triples: list) -> str:
    assignments = "\n".join(
        f"- 案{i + 1}: 職業フック=「{p}」 / 心理学用語=「{t}」 / 投稿型=「{pat}」"
        for i, (p, t, pat) in enumerate(triples)
    )
    pattern_explanations = "\n".join(
        f"- {pat}: {PATTERN_DESCRIPTIONS[pat]}" for (_, _, pat) in triples
    )
    return f"""
あなたはX(旧Twitter)で月間1,000万インプを叩き出す日本語コピーライターです。
以下のアカウントの発信として、インプレッションが伸びる投稿案を3つ作ってください。

{ACCOUNT_BRIEF}

# 今回の割当て(必ずこの組み合わせで生成する)
{assignments}

# 各型の構成
{pattern_explanations}

# 投稿本文の絶対制約
- 各案 140文字以内(全角・改行含む)。X無料アカウント前提。
- 1行目は必ず割当てられた職業フックの文字列から始める(指を止めさせるため)。
- 中身は「全対人サービスに共通する選ばれる人のコミュニケーション術」にする。職業の話で終わらせず、必ず普遍化する。
- 割当てられた心理学/脳科学の用語を本文中に明示する(例: 「心理学で〇〇と言います」)。

# 文体制約
- 語尾は「です。」「ます。」「ですよね。」など柔らかい断定で統一する。「〜しろ。」「〜だ。」などの強い命令/断定は禁止。
- 半角ダブルクォート(")は絶対に使わない。強調は鉤括弧「」を使う。
- ハッシュタグ・絵文字は使わない。
- 「〜について解説します」「いかがでしたか」など定型句は禁止。
- 一般論ではなく、シーンが目に浮かぶ具体描写で書く。

# 出力フォーマット(厳密にこのJSONのみ、前後に文字を入れない)
{{
  "posts": [
    {{"pattern": "型の名前", "persona_hook": "...", "term": "...", "text": "投稿本文"}},
    {{"pattern": "...", "persona_hook": "...", "term": "...", "text": "..."}},
    {{"pattern": "...", "persona_hook": "...", "term": "...", "text": "..."}}
  ]
}}
""".strip()


def call_gemini(prompt: str, max_retries: int = 4) -> dict:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.1,
            "topP": 0.95,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(body).encode("utf-8")

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                payload = json.loads(res.read().decode("utf-8"))
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            print(
                f"Gemini text HTTP {e.code} (attempt {attempt}/{max_retries}): {err_body}",
                file=sys.stderr,
            )
            last_err = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except Exception as e:
            print(
                f"Gemini text call failed (attempt {attempt}/{max_retries}): {e}",
                file=sys.stderr,
            )
            last_err = e

        if attempt < max_retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Gemini text generation failed after {max_retries} attempts: {last_err}")


def main() -> None:
    state = load_state()
    triples, phase = select_triples(state, count=3)
    print(f"Selected phase: {phase}")
    for t in triples:
        print(f"  - {t}")

    prompt = build_prompt(triples)
    result = call_gemini(prompt)

    state.setdefault("used_triples", []).extend(list(t) for t in triples)
    save_state(state)

    posts_payload = [{"text": post["text"].strip()} for post in result["posts"]]

    PENDING_PATH.write_text(
        json.dumps({"posts": posts_payload}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for p in posts_payload:
        print("\n---\n" + p["text"])


if __name__ == "__main__":
    main()
