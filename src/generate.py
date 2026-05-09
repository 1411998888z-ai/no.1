"""Claude APIで投稿候補を3案生成し、pending/ に保存する。"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "business.txt"
PENDING_DIR = ROOT / "pending"

MODEL = "claude-sonnet-4-6"  # コスト重視。質を上げたい場合は claude-opus-4-7 に変更


def load_prompt(time_slot: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{{ time_slot }}", time_slot)


def time_slot_label(now: datetime) -> str:
    hour = now.hour
    if 5 <= hour < 9:
        return "朝（出勤・始業前）"
    if 9 <= hour < 13:
        return "昼前（業務時間中）"
    if 13 <= hour < 18:
        return "夕方（退勤前後）"
    return "夜（リラックスタイム）"


def generate(client: Anthropic, prompt: str) -> dict:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": "今日この時間帯に投稿する案を3つ、JSON形式のみで出力してください。",
            }
        ],
    )
    text = msg.content[0].text.strip()
    # 念のためコードフェンスを剥がす
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def main() -> int:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 1

    now = datetime.now(JST)
    slot = time_slot_label(now)
    prompt = load_prompt(slot)

    client = Anthropic(api_key=api_key)
    data = generate(client, prompt)

    job_id = uuid.uuid4().hex[:12]
    record = {
        "job_id": job_id,
        "created_at": now.isoformat(),
        "slot": slot,
        "candidates": data["candidates"],
        "status": "pending",
    }

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PENDING_DIR / f"{job_id}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    # GitHub Actions の後段ステップ用に出力
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"job_id={job_id}\n")
            f.write(f"file={out_path}\n")

    print(f"Generated {len(record['candidates'])} candidates → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
