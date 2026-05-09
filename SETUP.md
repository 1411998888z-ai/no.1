# セットアップ手順

このドキュメントの手順を上から順番に進めれば、Threads自動投稿ボットが動き始めます。
全部完了するまで **60〜90分** ほどかかります。途中で止めて再開しても大丈夫です。

---

## 必要なもの（チェックリスト）

進める前に、以下のアカウントを用意してください（全部無料）。

- [ ] **GitHub** アカウント（このリポジトリにアクセスできる）
- [ ] **Google AI Studio** アカウント（投稿文の生成・**完全無料**）  
      https://aistudio.google.com/  
      ※有料でClaudeを使いたい場合は **Anthropic Console** https://console.anthropic.com/
- [ ] **Meta for Developers** アカウント（Threads投稿に使用）  
      https://developers.facebook.com/
- [ ] **LINE Developers** アカウント（承認通知用）  
      https://developers.line.biz/
- [ ] **Cloudflare** アカウント（LINEのボタンを受け取る中継サーバー）  
      https://dash.cloudflare.com/sign-up

メールアドレスだけで登録できます。**完全無料運用**ならクレジットカード登録は一切不要です。

---

## STEP 1: 投稿文生成のLLM APIキーを取得

**おすすめ：Gemini（無料）**。クレカ登録なしで完全無料運用できます。
品質を最大化したい場合は Claude（有料・月120円程度）。両方使えるので後から切替も可能です。

### パターンA：Gemini（無料・推奨）

1. https://aistudio.google.com/app/apikey にGoogleアカウントでログイン
2. 「Create API key」→ 「Create API key in new project」を選択
3. 表示された `AIza...` で始まる文字列をコピー → メモ帳に保存

> 1日1,500回まで無料。本構成では1日4回しか使わないので余裕で無料枠内。
> クレカ登録は不要。

**保存するもの：**
- `GEMINI_API_KEY` = `AIza...`

### パターンB：Claude（有料）

1. https://console.anthropic.com/ にログイン
2. 左メニュー「API Keys」→「Create Key」
3. 名前を `threads-bot` などにして作成
4. `sk-ant-...` で始まる文字列をコピー → メモ帳に保存
5. 「Plans & Billing」で最低5ドル分のクレジット購入（1日4投稿で月1ドル以下）

**保存するもの：**
- `ANTHROPIC_API_KEY` = `sk-ant-...`

### 使い分け

`LLM_PROVIDER` という設定で切替えます（後の STEP 5 で登録）。
- `gemini`（デフォルト）: Geminiを使う
- `claude`: Claudeを使う

---

## STEP 2: Threads API アクセストークンを取得

これが一番手数が多いです。ゆっくり進めてください。

### 2-1. Meta for Developersでアプリ作成

1. https://developers.facebook.com/apps/ にログイン
2. 「Create App」→ 用途は「Other」→ タイプは「Business」
3. アプリ名は `threads-bot` などで作成

### 2-2. Threads APIを有効化

1. アプリの管理画面で「Add Product」
2. 「Threads API」を「Set up」
3. 必要に応じてプライバシーポリシーURLを登録（ダミーでOK、後で本番URLに差し替え）

### 2-3. アクセストークン生成

1. 左メニュー「Threads API」→「Use cases」→「Access the Threads API」
2. 「Generate access token」 → ご自身のThreadsアカウントを選択
3. 短期トークンが発行される
4. **長期トークンに変換**：以下のURLをブラウザで開く（短期トークン部分を置き換え）

```
https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=【アプリのsecret】&access_token=【短期トークン】
```

5. 返ってきた `access_token` をコピー（60日有効）

### 2-4. User IDを取得

以下のURLをブラウザで開く（長期トークンを差し込む）：

```
https://graph.threads.net/v1.0/me?fields=id,username&access_token=【長期トークン】
```

返ってきた `id` の値（数字）をコピー。

**保存するもの：**
- `THREADS_ACCESS_TOKEN` = `THAA...`
- `THREADS_USER_ID` = `1234567890`

> 60日ごとにトークンを更新する必要があります。リマインダーを設定しておくと安全です。

---

## STEP 3: LINE Botを作成

### 3-1. プロバイダーとチャネル作成

1. https://developers.line.biz/console/ にログイン
2. 「Create new provider」→ 名前を `personal` などで作成
3. プロバイダーを開いて「Create a Messaging API channel」
4. 必須項目を入力：
   - Channel name: `Threads承認Bot`
   - Channel description: `Threads投稿の承認用`
   - Category: `Personal`
   - Subcategory: `Personal (other)`

### 3-2. トークンとシークレットを取得

1. 作成したチャネルの「Basic settings」タブ
2. **Channel secret** をコピー
3. 「Messaging API」タブに移動
4. 一番下の「Channel access token」で「Issue」をクリック
5. 表示された **長期トークン** をコピー

### 3-3. あなたのLINE User IDを取得

1. 「Messaging API」タブの上部、QRコードでBotを友だち追加
2. 「Basic settings」タブ → 「Your user ID」をコピー  
   （`U` で始まる文字列）

### 3-4. 自動応答をオフにする

1. 「Messaging API」タブ
2. 「Auto-reply messages」を **Disabled** に
3. 「Greeting messages」も **Disabled** に
4. 「Webhook」を **Enabled** に（URLは後で設定）

**保存するもの：**
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `LINE_USER_ID` = `U...`

---

## STEP 4: GitHub Personal Access Token を作成

Cloudflare WorkerからGitHub Actionsを起動するために必要です。

1. https://github.com/settings/tokens?type=beta
2. 「Generate new token (fine-grained)」
3. 設定：
   - Token name: `threads-bot-dispatch`
   - Repository access: `Only select repositories` → このリポジトリを選択
   - Permissions:
     - **Repository permissions** → **Contents** → `Read and write`
     - **Repository permissions** → **Metadata** → `Read-only`（自動）
4. 生成された `github_pat_...` をコピー

**保存するもの：**
- `GITHUB_TOKEN` = `github_pat_...`

---

## STEP 5: GitHub Secrets を登録

1. このリポジトリの「Settings」→「Secrets and variables」→「Actions」
2. 「New repository secret」で以下をすべて登録：

**Secrets**（機密情報、Secrets タブで登録）:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | STEP 1-A で取得（Geminiを使う場合） |
| `ANTHROPIC_API_KEY` | STEP 1-B で取得（Claudeを使う場合） |
| `THREADS_USER_ID` | STEP 2-4 で取得 |
| `THREADS_ACCESS_TOKEN` | STEP 2-3 で取得 |
| `LINE_CHANNEL_ACCESS_TOKEN` | STEP 3-2 で取得 |
| `LINE_USER_ID` | STEP 3-3 で取得 |

**Variables**（プロバイダ切替、Variables タブで登録 ※任意）:

| Name | Value | デフォルト |
|---|---|---|
| `LLM_PROVIDER` | `gemini` または `claude` | 未設定なら `gemini` |

---

## STEP 6: Cloudflare Workerをデプロイ

### 6-1. Wrangler CLIをインストール

```bash
npm install -g wrangler
wrangler login   # ブラウザでCloudflareにログインを求められる
```

### 6-2. Secretsを登録

```bash
cd workers
wrangler secret put LINE_CHANNEL_SECRET
# プロンプトが出るので STEP 3-2 のシークレットを貼り付け

wrangler secret put LINE_CHANNEL_ACCESS_TOKEN
# STEP 3-2 のトークンを貼り付け

wrangler secret put GITHUB_TOKEN
# STEP 4 のトークンを貼り付け

wrangler secret put GITHUB_REPO
# このリポジトリの owner/name を貼り付け（例: 1411998888z-ai/no.1）
```

### 6-3. デプロイ

```bash
wrangler deploy
```

完了すると `https://threads-bot-webhook.<your-subdomain>.workers.dev` のようなURLが表示されます。
**このURLをコピー** してください。

### 6-4. LINE側にWebhook URLを設定

1. LINE Developers Console → 作成したチャネル → 「Messaging API」タブ
2. 「Webhook URL」に上記URLを貼り付けて「Update」
3. 「Verify」をクリックして `Success` が出ればOK
4. 「Use webhook」を **ON** に

---

## STEP 7: ブランチをmainにマージ

GitHub Actionsの定期実行（cron）は **デフォルトブランチでのみ動作** します。
このコードを `main` ブランチに取り込んでください。

1. GitHubで `claude/threads-operational-support-8yKZi` → `main` のPull Requestを作成
2. マージ

> マージしないと「Run workflow」での手動実行は動きますが、毎日の定時実行は走りません。

---

## STEP 8: 動作テスト

### 8-1. 候補生成を手動実行

1. GitHubリポジトリの「Actions」タブ
2. 左メニュー「Generate post candidates」
3. 「Run workflow」→「Run」をクリック
4. 緑のチェックが付くまで待つ（1〜2分）
5. **LINEに3案がカルーセルで届く** ことを確認

### 8-2. LINEで「案1を採用」をタップ

1. 1〜2分後、Threadsに投稿されているか確認
2. GitHub Actionsの「Publish approved post」が走っていることも確認

### 8-3. 自動運用スタート

ここまで動けばOKです。明朝5:30から自動で動き始めます。

---

## トラブルシューティング

### LINEに通知が来ない
- GitHub Actionsのログで `notify.py` が成功しているか確認
- `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` が正しいか
- LINEで自分のBotを **友だち追加済み** か

### LINEのボタンを押しても反応しない
- LINE Developers Console → 「Webhook URL」が正しいか
- 「Use webhook」が ON か
- Cloudflare Workersのログ（`wrangler tail` で見られる）に401エラーが出ていないか
  - 401なら `LINE_CHANNEL_SECRET` が違う

### Threadsへの投稿が失敗する
- `THREADS_ACCESS_TOKEN` が60日切れの可能性
- STEP 2-3 をやり直してトークンを更新し、Secretsも更新

### 投稿時刻がずれる
- GitHubのcronはUTC基準。`.github/workflows/generate.yml` のcron式を確認
- GitHub Actionsのcronは数分の遅延がある（仕様）

---

## 運用Tips

- **トークン有効期限のリマインダー**：Threadsのトークンは60日で切れる
- **コスト**：
  - Gemini運用：**0円**（無料枠1日1,500回 vs 必要4回）
  - Claude運用：1投稿あたり約0.01ドル、月120円程度
- **LLM切替**：GitHub Variables の `LLM_PROVIDER` を `gemini` ⇄ `claude` で切替
- **テーマ変更**：`src/prompts/business.txt` を編集してコミット
- **時刻変更**：`.github/workflows/generate.yml` のcron式を編集
- **一時停止**：「Actions」タブ → 「Generate post candidates」→「...」→「Disable workflow」
