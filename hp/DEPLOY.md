# 公開手順（GitHub Pages × 独自ドメイン kizashi-ya.com）

`hp/` フォルダを GitHub Actions で公開します。以下を順に進めてください。

## STEP 1. main にマージ
このブランチ（`claude/studio-hp-creation-yuw5t0`）を `main` にマージします。
マージ＝publishのトリガーになり、`.github/workflows/deploy-pages.yml` が動いて `hp/` が公開されます。
※ PR作成はこちらでも代行できます。

## STEP 2. Pages を「GitHub Actions」に設定
リポジトリ **Settings → Pages → Build and deployment → Source** を **「GitHub Actions」** に変更。
（初回はActionsタブでデプロイの成功を確認。数分でURLが発行されます）

## STEP 3. 独自ドメインを設定
1. **Settings → Pages → Custom domain** に `kizashi-ya.com` を入力して Save
2. **Enforce HTTPS** にチェック（無料SSL・反映まで数十分〜数時間）
   ※ `hp/CNAME` に `kizashi-ya.com` を同梱済み

## STEP 4. DNS をGitHubに向ける（ドメイン管理会社の管理画面）
- **Aレコード（apex: kizashi-ya.com）** を4つ登録：
  - 185.199.108.153
  - 185.199.109.153
  - 185.199.110.153
  - 185.199.111.153
- （任意・IPv6 AAAA）2606:50c0:8000::153 / 8001::153 / 8002::153 / 8003::153
- **www を使う場合**：`www` の CNAME を `1411998888z-ai.github.io` に向ける
- 反映はDNS次第で数分〜48時間

## STEP 5. お問い合わせフォームの有効化（FormSubmit）
公開後、**フォームから一度テスト送信** → `kizashiya.88@gmail.com` に届く
「Activate」メールのリンクを1回クリック（初回のみ）。以降ずっと届きます。

## STEP 6. Google Search Console（SEO・任意だが推奨）
1. https://search.google.com/search-console でプロパティ `kizashi-ya.com` を追加
2. 所有権確認（DNS TXT など）
3. サイトマップ `https://kizashi-ya.com/sitemap.xml` を送信

---
公開後URL（独自ドメイン反映前の確認用）: リポジトリのActionsデプロイで発行される `*.github.io` URL
