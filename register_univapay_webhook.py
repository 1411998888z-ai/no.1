"""Univapay に Webhook を登録する（決済ステータスを GAS Web アプリへ通知させる）。

GAS の Web アプリ URL に ?token=WEBHOOK_SECRET を付けたものを Univapay に登録する。
管理画面から手動登録する場合はこのスクリプトは不要。

必要な環境変数:
  UNIVAPAY_JWT       … アプリトークン(JWT)
  UNIVAPAY_SECRET    … アプリトークンのシークレット
  UNIVAPAY_STORE_ID  … ストアID
  GAS_WEBHOOK_URL    … GAS ウェブアプリの /exec URL（?token= は付けない）
  WEBHOOK_SECRET     … GAS 側と同じ秘密文字列（URL の ?token= に付与される）
任意:
  UNIVAPAY_ENDPOINT  … 既定 https://api.univapay.com
  WEBHOOK_TRIGGERS   … カンマ区切り。既定 "charge_finished,charge_updated"
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = os.environ.get("UNIVAPAY_ENDPOINT", "https://api.univapay.com").rstrip("/")
JWT = os.environ["UNIVAPAY_JWT"]
SECRET = os.environ["UNIVAPAY_SECRET"]
STORE_ID = os.environ["UNIVAPAY_STORE_ID"]
GAS_WEBHOOK_URL = os.environ["GAS_WEBHOOK_URL"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
TRIGGERS = [
    t.strip()
    for t in os.environ.get("WEBHOOK_TRIGGERS", "charge_finished,charge_updated").split(",")
    if t.strip()
]


def build_webhook_url() -> str:
    """GAS URL に ?token=WEBHOOK_SECRET を付与する。"""
    parts = urllib.parse.urlsplit(GAS_WEBHOOK_URL)
    query = dict(urllib.parse.parse_qsl(parts.query))
    query["token"] = WEBHOOK_SECRET
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
    )


def main() -> None:
    url = f"{ENDPOINT}/stores/{STORE_ID}/webhooks"
    body = {
        "triggers": TRIGGERS,
        "url": build_webhook_url(),
        # GAS はヘッダを読めないため auth_token 自体での検証はしないが、設定はしておく
        "auth_token": WEBHOOK_SECRET,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SECRET}.{JWT}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Webhook 登録に失敗: {e.code} {e.read().decode('utf-8')}", file=sys.stderr)
        raise

    print("Webhook を登録しました:")
    print(f"  id       : {payload.get('id')}")
    print(f"  url      : {payload.get('url')}")
    print(f"  triggers : {payload.get('triggers')}")


if __name__ == "__main__":
    main()
