"""投稿候補を3案生成し、pending/ に保存する。

LLM_PROVIDER 環境変数でプロバイダを切替：
  - "claude"  : Anthropic Claude (Sonnet 4.6) ※有料、日本語品質◎
  - "gemini"  : Google Gemini 2.0 Flash       ※無料、日本語品質○
未指定時は "gemini"（無料）をデフォルトとする。
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "business.txt"
PENDING_DIR = ROOT / "pending"

CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.0-flash"


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


def parse_json_loose(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def generate_with_claude(prompt: str) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=CLAUDE_MODEL,
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
    return parse_json_loose(msg.content[0].text)


def generate_with_gemini(prompt: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    res = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="今日この時間帯に投稿する案を3つ、JSON形式のみで出力してください。",
        config=types.GenerateContentConfig(
            system_instruction=prompt,
            response_mime_type="application/json",
            max_output_tokens=4000,
            temperature=0.9,
        ),
    )
    return parse_json_loose(res.text)


def main() -> int:
    load_dotenv()

    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    now = datetime.now(JST)
    slot = time_slot_label(now)
    prompt = load_prompt(slot)

    if provider == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
            return 1
        data = generate_with_claude(prompt)
    elif provider == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            print("GEMINI_API_KEY is not set", file=sys.stderr)
            return 1
        data = generate_with_gemini(prompt)
    else:
        print(f"unknown LLM_PROVIDER: {provider}", file=sys.stderr)
        return 1

    job_id = uuid.uuid4().hex[:12]
    record = {
        "job_id": job_id,
        "created_at": now.isoformat(),
        "slot": slot,
        "provider": provider,
        "candidates": data["candidates"],
        "status": "pending",
    }

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PENDING_DIR / f"{job_id}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"job_id={job_id}\n")
            f.write(f"file={out_path}\n")

    print(f"Generated {len(record['candidates'])} candidates with {provider} → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
