# X投稿候補 自動生成bot（→ LINEに毎朝配信）

@_x_saku_ 用の投稿アシスタント。毎朝7時(JST)に、投稿候補3案をLINEに届けます。
あなたは届いた案を精査してXに投稿するだけ。

## 構成

- **GitHub Actions**（毎朝cron実行・無料枠）
- **Google Gemini API**（投稿本文生成・無料枠）
- **LINE Messaging API**（配信・月200通無料）

すべて完全無料。

## フォロワー獲得最適化（Phase制）

新規アカウントが伸びるよう、強いネタから優先的に消費する設計：

- **Phase S**：王道の心理学用語 × 注目を集めやすい職業 × 鉄板の型のみ（最初の数週間）
- **Phase A**：S級を使い切ったら自動でAを開放
- **Phase B**：さらに使い切ったらB（応用編）に降格

組み合わせは `state.json` で管理、過去使用と被らないように選定されます。

## 投稿の型（8種）

- 共感→気づき型（S）
- 逆張り断定型（S）
- 脳科学/心理学解説型（A）
- 体験談→学び型（A）
- 箇条書きノウハウ型（A）
- 失敗エピソード型（B）
- 比喩で説明型（B）
- Q&A自問自答型（B）

## セットアップ

[SETUP.md](./SETUP.md) を参照してください（15分）。

## ファイル

- `generate_posts.py` — 投稿本文生成、`state.json` 更新、`pending_message.json` 出力
- `send_to_line.py` — `pending_message.json` を読んで LINE に送信
- `.github/workflows/daily.yml` — 毎朝の自動実行（生成 → state コミット → LINE送信）
- `state.json` — 使用済み(職業, 用語, 型)三つ組の記録
- `SETUP.md` — 初期セットアップ手順
