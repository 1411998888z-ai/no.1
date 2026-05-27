"""pending_message.jsonを読んで、LINEに案ごと(text+image)を別プッシュで送信する。"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_TO_USER_ID = os.environ["LINE_TO_USER_ID"]
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "1411998888z-ai/no.1")
GITHUB_REF_NAME = os.environ.get("GITHUB_REF_NAME", "main")

REPO_ROOT = Path(__file__).parent
PENDING_PATH = REPO_ROOT / "pending_message.json"


def raw_url_for(rel_path: str) -> str:
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{GITHUB_REF_NAME}/{rel_path}"


def push_messages(messages: list) -> None:
    body = {"to": LINE_TO_USER_ID, "messages": messages[:5]}
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
    if not PENDING_PATH.exists():
        print("No pending_message.json — nothing to send.", file=sys.stderr)
        sys.exit(1)
    pending = json.loads(PENDING_PATH.read_text(encoding="utf-8"))

    posts = pending.get("posts", [])
    for i, post in enumerate(posts, 1):
        messages = [{"type": "text", "text": post["text"][:4900]}]
        if post.get("image_path"):
            url = raw_url_for(post["image_path"])
            messages.append(
                {
                    "type": "image",
                    "originalContentUrl": url,
                    "previewImageUrl": url,
                }
            )
        push_messages(messages)
        print(f"Sent post {i}/{len(posts)} to LINE.")
        if i < len(posts):
            time.sleep(0.5)  # rate limit margin


if __name__ == "__main__":
    main()
