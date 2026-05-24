# セットアップ手順（所要時間：15分）

毎朝7時(JST)に、X投稿候補3案がLINEに届く仕組みです。完全無料で動きます。

---

## ① LINE公式アカウントを作る（Messaging API用）

1. <https://developers.line.biz/console/> にアクセス → LINEアカウントでログイン
2. 「プロバイダー」を新規作成（名前は何でもOK、例：`saku-bot`）
3. プロバイダー内で「**Messaging API**」のチャネルを新規作成
   - チャネル名：例「投稿候補bot」
   - 業種・カテゴリは適当でOK
4. 作成後、**チャネル基本設定**タブで一番下までスクロール
   - 「**チャネルアクセストークン（長期）**」の「発行」ボタンを押す
   - 表示された長い文字列をコピー → これが `LINE_CHANNEL_ACCESS_TOKEN`
5. 「**Messaging API設定**」タブを開く
   - QRコードが表示される → スマホのLINEアプリで読み込んで「友だち追加」
6. **自分のユーザーIDを取得する**
   - 「Messaging API設定」タブの「**Webhookの利用**」は OFF のままでOK
   - 「**応答メッセージ**」も OFF にしておく（自動返信を止める）
   - ユーザーIDは、bot を友だち追加した状態で次のコマンドをローカルPCで実行：
     ```bash
     curl -H "Authorization: Bearer YOUR_CHANNEL_ACCESS_TOKEN" \
       https://api.line.me/v2/bot/followers/ids
     ```
   - 返ってくる `userIds` の中の `Uxxxxxxxx...` があなたの `LINE_TO_USER_ID`
   - ※ コマンドが面倒なら、後述の「ユーザーID取得の代替手段」を参照

---

## ② Gemini APIキーを取得する

1. <https://aistudio.google.com/app/apikey> にアクセス → Googleアカウントでログイン
2. 「**Create API key**」ボタンを押す
3. プロジェクトは「Create API key in new project」でOK
4. 表示されたキーをコピー → これが `GEMINI_API_KEY`
5. 無料枠：`gemini-2.5-flash` は 1日1,500リクエストまで無料。毎朝1回なら余裕。

---

## ③ GitHub Secrets に3つの値を登録

1. このリポジトリの GitHub ページを開く
2. **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. 以下の3つを順番に登録：

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | ②で取得したキー |
| `LINE_CHANNEL_ACCESS_TOKEN` | ①で発行したトークン |
| `LINE_TO_USER_ID` | ①で取得した `Uxxxxx...` |

---

## ④ 動作確認

1. リポジトリの **Actions** タブを開く
2. 左メニューの「**Daily X post suggestions to LINE**」を選択
3. 右上の「**Run workflow**」 → 緑のボタンを押す
4. 1〜2分後、LINEに3案届けば成功

---

## ⑤ 以降は自動

毎朝 7:00 (JST) に自動で動きます。何もする必要はありません。

スケジュールを変えたい場合は `.github/workflows/daily.yml` の `cron` を編集してください。
（cron はUTCで書くので、JST 7:00 は UTC 22:00 前日 = `0 22 * * *`）

---

## ユーザーID取得の代替手段（curlが使えない場合）

LINE Developers Console の「Messaging API設定」タブで、
「Webhook URL」に <https://webhook.site/> で発行した一時URLを設定 → 一度自分でbotにメッセージを送る
→ webhook.site に届くJSONの `source.userId` がそれです。  
取得したらWebhook設定はOFFに戻してください。
