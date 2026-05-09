"""Threads Graph APIでテキスト投稿を実行する（2段階：コンテナ作成→公開）。"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
PENDING_DIR = ROOT / "pending"
POSTED_DIR = ROOT / "posted"

THREADS_API = "https://graph.threads.net/v1.0"


def create_container(user_id: str, token: str, text: str) -> str:
    res = requests.post(
        f"{THREADS_API}/{user_id}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": token,
        },
        timeout=15,
    )
    res.raise_for_status()
    return res.json()["id"]


def publish_container(user_id: str, token: str, container_id: str) -> str:
    # コンテナの状態が FINISHED になるのを少し待つ
    for _ in range(5):
        time.sleep(2)
        status = requests.get(
            f"{THREADS_API}/{container_id}",
            params={"fields": "status", "access_token": token},
            timeout=10,
        ).json()
        if status.get("status") == "FINISHED":
            break

    res = requests.post(
        f"{THREADS_API}/{user_id}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": token,
        },
        timeout=15,
    )
    res.raise_for_status()
    return res.json()["id"]


def post_text(text: str) -> str:
    user_id = os.environ["THREADS_USER_ID"]
    token = os.environ["THREADS_ACCESS_TOKEN"]
    container_id = create_container(user_id, token, text)
    return publish_container(user_id, token, container_id)


def find_pending(job_id: str) -> Path:
    p = PENDING_DIR / f"{job_id}.json"
    if not p.exists():
        raise FileNotFoundError(f"pending file not found: {p}")
    return p


def archive(record: dict, posted_id: str) -> None:
    POSTED_DIR.mkdir(parents=True, exist_ok=True)
    record["status"] = "posted"
    record["posted_at"] = datetime.now(JST).isoformat()
    record["threads_post_id"] = posted_id
    out = POSTED_DIR / f"{record['job_id']}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (PENDING_DIR / f"{record['job_id']}.json").unlink(missing_ok=True)


def main() -> int:
    load_dotenv()
    job_id = os.environ.get("JOB_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    candidate_id = int(os.environ.get("CANDIDATE_ID") or (sys.argv[2] if len(sys.argv) > 2 else 0))
    if not job_id or candidate_id == 0:
        print("usage: publish.py <job_id> <candidate_id>", file=sys.stderr)
        return 1

    record = json.loads(find_pending(job_id).read_text(encoding="utf-8"))
    candidate = next((c for c in record["candidates"] if c["id"] == candidate_id), None)
    if candidate is None:
        print(f"candidate id={candidate_id} not found in job {job_id}", file=sys.stderr)
        return 1

    posted_id = post_text(candidate["text"])
    archive(record, posted_id)
    print(f"Posted to Threads: id={posted_id} (job={job_id}, candidate={candidate_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
