# 株式会社きざし屋 コーポレートサイト（マルチページ）

FrastoLink型の構成をベースに、きざし屋の実情報で作成した静的マルチページサイト。

## ページ構成
- `index.html` … TOP（Hero / ABOUT / BUSINESS preview / SERVICES(導入ツール) / MEMBER / NEWS / CONTACT）
- `business.html` … 事業詳細＋各事業のお客様の声（現在デモ・SAMPLE表示）
- `company.html` … PHILOSOPHY / 代表挨拶 / ご依頼の流れ / 会社概要
- `member.html` … メンバー紹介（準備中）
- `news.html` … お知らせ（準備中）
- `contact.html` … お問い合わせフォーム
- `assets/style.css`, `assets/app.js` … 共通CSS/JS

## 公開方法（GitHub Pages・無料・独自ドメイン対応）
1. GitHub リポジトリ Settings → Pages
2. Source を「Deploy from a branch」、ブランチ＋フォルダを `/hp` に指定
3. Custom domain に `kizashi-ya.com` を設定（`CNAME` 同梱済み）
4. ドメイン側DNSを GitHub Pages に向ける（Aレコード: 185.199.108-111.153、または www を CNAME で <user>.github.io）
5. 「Enforce HTTPS」にチェック（無料SSL）

## SEO
- 各ページに title / meta description / OGP / canonical、TOPに JSON-LD(Organization)
- sitemap.xml / robots.txt 同梱 → 公開後 Google Search Console に登録・送信

## 本公開前の差し替え必須項目
- VOICE（お客様の声）… 現在は「SAMPLE」表記のデモ。実際の声へ差し替え
- SERVICES（導入ツール）… ロゴ・内容
- MEMBER / NEWS … 内容（現在「準備中」）
- 写真素材 / ロゴ画像 / OGP画像(ogp.png) / メールアドレス
- お問い合わせフォームの送信先連携（Formspree等のフォームサービス接続）

## 画像の差し替え方法
`assets/img/` にオンブランドのSVGプレースホルダーを配置済み（人物・事業イメージ）。
実写に差し替えるには、同名で画像を置く or `<img src>` を実写ファイルに変更するだけ。
- hero.svg … TOPヒーロー右のビジュアル
- leader.svg … 代表ポートレート（company.html）
- team.svg … メンバー集合写真（member.html）
- portrait-1〜4.svg … お客様の声の人物写真（business.html／※本公開前に実際の声・写真へ差し替え）
- biz-liver / biz-brand / biz-marketing / biz-insidesales.svg … 各事業のイメージ
推奨：実写JPG/WebPを `assets/img/` に入れ、拡張子に合わせて src を変更（例 hero.jpg）。
