# 株式会社きざし屋 コーポレートサイト

FrastoLink型の構成をベースに、きざし屋の実情報で作成した静的サイト。

## 公開方法（GitHub Pages・無料・独自ドメイン対応）
1. GitHubリポジトリ Settings → Pages
2. Source を「Deploy from a branch」、フォルダを `/hp` に指定（または main の /hp）
3. Custom domain に `kizashi-ya.com` を設定（`CNAME` 同梱済み）
4. ドメイン側DNSで CNAME/A レコードを GitHub Pages に向ける
   - Aレコード: 185.199.108.153 / 185.199.109.153 / 185.199.110.153 / 185.199.111.153
   - もしくは www を CNAME で <user>.github.io に
5. 「Enforce HTTPS」にチェック（無料SSL）

## SEO
- title / meta description / OGP / JSON-LD(Organization) 実装済み
- sitemap.xml / robots.txt 同梱
- 公開後 Google Search Console にプロパティ登録 → sitemap 送信

## 未確定・要提供（信用サイトのため実データが必要）
- VOICE（お客様の声）: 実際の声
- SERVICES / PARTNERS: 実際の導入・提携先
- MEMBER / NEWS: 内容 or「準備中」
- ロゴ画像 / 写真素材 / メールアドレス
- ドメイン最終確認（kizashi-ya.com 前提）
