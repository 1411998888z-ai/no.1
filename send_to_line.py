"""pending_message.jsonを読んで、LINEに本文+画像3枚を送信する。
画像は事前にgit pushされてGitHubのraw URLで参照できる前提。"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_TO_USER_ID = os.environ["LINE_TO_USER_ID"]
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "1411998888z-ai/no.1")
GITHUB_REF_NAME = os.environ.get("GITHUB_REF_NAME", "claude/dazzling-newton-mHn8p")

REPO_ROOT = Path(__file__).parent
PENDING_PATH = REPO_ROOT / "pending_message.json"


def raw_url_for(rel_path: str) -> str:
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{GITHUB_REF_NAME}/{rel_path}"


def push_to_line(text: str, image_urls: list) -> None:
    messages = [{"type": "text", "text": text[:4900]}]
    for url in image_urls:
        if url:
            messages.append(
                {
                    "type": "image",
                    "originalContentUrl": url,
                    "previewImageUrl": url,
                }
            )
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
    image_urls = [raw_url_for(p) if p else None for p in pending.get("image_paths", [])]
    push_to_line(pending["text"], image_urls)
    print("Sent to LINE.")


if __name__ == "__main__":
    main()
