"""LINE Messaging APIで承認用メッセージを送信する。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


def build_candidate_bubble(job_id: str, candidate: dict) -> dict:
    text = candidate["text"]
    structure = candidate.get("structure", "")
    cid = candidate["id"]
    preview = text if len(text) <= 380 else text[:377] + "…"
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"案 {cid}｜{structure}",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#888888",
                }
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": preview,
                    "wrap": True,
                    "size": "sm",
                }
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1DB446",
                    "action": {
                        "type": "postback",
                        "label": f"案{cid}を採用して投稿",
                        "data": f"action=approve&job={job_id}&id={cid}",
                        "displayText": f"案{cid}を採用しました",
                    },
                }
            ],
        },
    }


def build_control_bubble(job_id: str) -> dict:
    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "全部イマイチ？",
                    "weight": "bold",
                    "size": "md",
                },
                {
                    "type": "text",
                    "text": "再生成 or 却下を選んでください。",
                    "size": "xs",
                    "color": "#888888",
                    "margin": "sm",
                    "wrap": True,
                },
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "再生成",
                        "data": f"action=regenerate&job={job_id}",
                        "displayText": "再生成します",
                    },
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "今回は投稿しない",
                        "data": f"action=reject&job={job_id}",
                        "displayText": "今回はスキップ",
                    },
                },
            ],
        },
    }


def build_flex(job_id: str, slot: str, candidates: list[dict]) -> dict:
    bubbles = [build_candidate_bubble(job_id, c) for c in candidates]
    bubbles.append(build_control_bubble(job_id))
    return {
        "type": "flex",
        "altText": f"[Threads承認] {slot} の投稿候補が届きました",
        "contents": {"type": "carousel", "contents": bubbles},
    }


def push(record: dict) -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user_id = os.environ["LINE_USER_ID"]

    flex = build_flex(record["job_id"], record["slot"], record["candidates"])
    payload = {"to": user_id, "messages": [flex]}

    res = requests.post(
        LINE_PUSH_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=15,
    )
    if res.status_code >= 300:
        raise RuntimeError(f"LINE push failed: {res.status_code} {res.text}")


def main() -> int:
    load_dotenv()
    if len(sys.argv) < 2:
        print("usage: notify.py <pending-json-path>", file=sys.stderr)
        return 1
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    push(record)
    print(f"Notified job_id={record['job_id']} via LINE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
