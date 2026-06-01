# Univapay 決済ステータス → スプレッドシート 反映 セットアップ

Univapay の Webhook を Google Apps Script (GAS) の Web アプリで受け取り、
決済1件＝1行でスプレッドシートに**リアルタイム**反映します。
営業メンバーは、そのスプレッドシートを開いておくだけで成功/失敗を把握できます。

- サーバー不要・完全無料（GAS の Web アプリ）
- 決済が発生・更新された瞬間に Univapay が Webhook を送る → 即座に行が追加/更新される
- 同じ決済IDは1行に集約され、`pending → successful/failed` のように状態が上書きされる

---

## 全体像

```
Univapay（決済発生）
   │  Webhook (POST, JSON)
   ▼
GAS ウェブアプリ /exec?token=○○○
   │  doPost が受信・検証・整形
   ▼
Google スプレッドシート「決済ログ」シート（1決済=1行で upsert）
```

---

## ① スプレッドシートと GAS を用意する

1. Google スプレッドシートを新規作成（名前は任意。例「Univapay決済ログ」）
2. メニュー **拡張機能 → Apps Script** を開く
3. 既定の `Code.gs` の中身を、このリポジトリの [`gas/Code.gs`](./gas/Code.gs) の内容で**すべて置き換える**
4. 保存（💾）

> この手順で作るとスクリプトはスプレッドシートに「紐付いた」状態になり、
> `SPREADSHEET_ID` の設定は不要です。

---

## ② スクリプト プロパティを設定する

Apps Script 画面の左メニュー **⚙️ プロジェクトの設定 → スクリプト プロパティ** で追加：

| プロパティ | 値 | 必須 |
|---|---|---|
| `WEBHOOK_SECRET` | 任意の長い秘密文字列（例：ランダムな40文字） | ✅ 推奨 |
| `SHEET_NAME` | 書き込み先シート名（未設定なら `決済ログ`） | 任意 |
| `UNIVAPAY_JWT` | カード名義/メールを表示したい場合のみ。アプリトークン(JWT) | 任意 |
| `UNIVAPAY_SECRET` | 同上。アプリトークンのシークレット | 任意 |

> **カード名義・メールアドレスについて**：これらは決済(charge)データに含まれず、取引トークン側にあります。
> `UNIVAPAY_JWT` と `UNIVAPAY_SECRET` を設定すると、Webhook 受信時にトークンAPIへ問い合わせて
> 「カード名義」「メールアドレス」列を自動で埋めます。未設定なら両列は空欄になり、他は通常どおり動きます。

`WEBHOOK_SECRET` は、後で Webhook URL の `?token=` に付けて照合します。
（GAS の `doPost` は HTTP ヘッダを読めないため、ヘッダ認証ではなく URL クエリで検証します）

---

## ③ ウェブアプリとしてデプロイ

1. 右上 **デプロイ → 新しいデプロイ**
2. 種類（⚙️）で「**ウェブアプリ**」を選択
3. 設定：
   - 説明：任意
   - 次のユーザーとして実行：**自分**
   - アクセスできるユーザー：**全員**
4. **デプロイ** → 初回は権限承認を求められるので許可
5. 表示される **ウェブアプリ URL**（`https://script.google.com/macros/s/XXXX/exec`）をコピー

> コードを修正したら、毎回「デプロイ → デプロイを管理 → 鉛筆 → バージョン:新バージョン」で更新してください。

---

## ④ Univapay に Webhook を登録する

登録する URL は、③でコピーした URL の末尾に `?token=WEBHOOK_SECRET` を付けたものです：

```
https://script.google.com/macros/s/XXXX/exec?token=②で決めたWEBHOOK_SECRET
```

トリガー（通知する種類）は最低限これを選びます：

- `charge_finished` … 決済が確定（成功/失敗が決まった）
- `charge_updated` … 決済の状態が更新された

### 方法A：管理画面から登録（権限があるなら一番簡単）

Univapay 管理画面の Webhook 設定で、上記 URL とトリガーを登録します。

### 方法B：API で登録（スクリプト）

このリポジトリの [`register_univapay_webhook.py`](./register_univapay_webhook.py) を使います。
以下の環境変数を設定して実行：

```bash
export UNIVAPAY_JWT="アプリトークンのJWT"
export UNIVAPAY_SECRET="アプリトークンのシークレット"
export UNIVAPAY_STORE_ID="ストアID"
export GAS_WEBHOOK_URL="https://script.google.com/macros/s/XXXX/exec"   # ?token= は付けない
export WEBHOOK_SECRET="②で決めた値"                                      # 自動で ?token= に付与される
# 任意: export WEBHOOK_TRIGGERS="charge_finished,charge_updated"

python register_univapay_webhook.py
```

成功すると登録された Webhook の `id` / `url` / `triggers` が表示されます。

---

## ⑤ 動作確認

1. Univapay でテスト決済（テストモード）を1件実行する
2. 数秒以内にスプレッドシートの「決済ログ」シートに行が追加される
3. ステータス列に `✅ 成功` / `❌ 失敗` などが表示されれば成功

ブラウザで `…/exec`（token なし）を開くと `{"result":"ok",...}` が返り、デプロイ自体の生存確認ができます。

---

## 反映される列

| 列 | 内容 |
|---|---|
| 受信日時 | スプレッドシートが Webhook を受け取った時刻 |
| イベント | `charge_finished` など |
| ステータス | `✅ 成功` `❌ 失敗` `⏳ 保留中` など（営業向け表示） |
| status(raw) | Univapay の生ステータス（`successful` 等） |
| 決済ID | charge の id（この列をキーに同一決済は1行へ集約） |
| モード | `live` / `test` |
| 金額 / 通貨 | 請求/確定金額と通貨 |
| サブスクID | 定期課金の場合 |
| トークンID | 取引トークンID |
| エラーコード / エラー詳細 | 失敗・エラー時のみ |
| 決済作成日時 | Univapay 側の作成日時（created_on） |
| 説明 | descriptor |
| metadata | charge の metadata（JSON） |

### ステータスの意味

| raw | 表示 | 意味 |
|---|---|---|
| `pending` | ⏳ 保留中 | 処理中 |
| `awaiting` | ⌛ 待機中 | 入金待ち等 |
| `authorized` | 🔐 オーソリ済 | 与信確保（売上確定前） |
| `successful` | ✅ 成功 | 決済成功 |
| `failed` | ❌ 失敗 | 決済失敗 |
| `error` | ⚠️ エラー | エラー |
| `canceled` | 🚫 キャンセル | 取消 |

---

## トラブルシュート

- **行が増えない**：Webhook URL の `?token=` と `WEBHOOK_SECRET` が一致しているか確認。Univapay 管理画面の Webhook 送信ログでレスポンスを確認。
- **`unauthorized` が返る**：token 不一致。URL のクエリを再確認。
- **コード修正が反映されない**：デプロイの「新バージョン」更新を忘れていないか確認。
- **見やすくしたい**：シートで status(raw) 列に対し「条件付き書式」を設定すると、成功=緑/失敗=赤などで色分けできます。
