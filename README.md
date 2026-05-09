# Threads 自動投稿ボット

Claude APIで投稿候補を生成 → LINEで承認 → Threadsへ自動投稿する仕組みです。

## 動作フロー

```
[5:30 / 10:30 / 15:30 / 20:30 JST]
 └─ GitHub Actionsが起動
     └─ Claudeが3案を生成
         └─ LINEに承認用メッセージ送信
             └─ あなたがLINEで「採用 / 再生成 / 却下」をタップ
                 └─ Cloudflare WorkerがGitHub Actionsを起動
                     └─ Threadsへ投稿（6:00 / 11:00 / 16:00 / 21:00）
```

## ディレクトリ構成

```
.
├── src/
│   ├── generate.py       投稿候補3案を生成
│   ├── notify.py         LINEへ承認メッセージ送信
│   ├── publish.py        Threadsへ投稿
│   └── prompts/
│       └── business.txt  ビジネス・マーケティング用プロンプト
├── workers/
│   ├── webhook.js        LINEからの承認を受けるCloudflare Worker
│   └── wrangler.toml
├── .github/workflows/
│   ├── generate.yml      30分前に候補を生成
│   └── publish.yml       承認時に投稿
├── pending/              承認待ちの投稿候補（自動生成）
├── posted/               投稿済みアーカイブ（自動生成）
├── requirements.txt
└── SETUP.md              初期セットアップ手順
```

## 初めて使う方へ

[SETUP.md](./SETUP.md) を順番に進めてください。所要時間は60〜90分です。

## 投稿スケジュール

| 時刻 | 候補生成 | 投稿予定 |
|---|---|---|
| 朝 | 5:30 | 6:00 |
| 昼前 | 10:30 | 11:00 |
| 夕方 | 15:30 | 16:00 |
| 夜 | 20:30 | 21:00 |

時刻はすべて **JST**。承認しなかった場合は投稿されません（手動承認制）。

## 投稿テーマの変更

`src/prompts/business.txt` を編集すれば、生成される投稿のトーン・テーマを変えられます。

## ローカルテスト

```bash
pip install -r requirements.txt
cp .env.example .env  # 値を埋める
python src/generate.py            # pending/にJSON生成
python src/notify.py pending/<job_id>.json  # LINEに送信
python src/publish.py <job_id> 1  # 案1をThreadsへ投稿
```
