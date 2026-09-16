# 三段タスク

新規追加 / 未完了 / 完了 の三段構成のタスク管理ツール。iPhone と MacBook の
どちらからでも同じ URL を開いて使えて、タスクは同じアカウント間で同期される。

公開先: https://claude.ai/artifact/6mjgnPvLwGDLDUfHaaW4f3

## 使い方

- **新規追加** — 入力欄にやることを書いて `Enter`（改行は `Shift`+`Enter`）か「追加」ボタン。
  日本語入力の変換確定では追加されない。
- **未完了** — 各行の丸ボタンを押すと完了タスクへ移動する。新しいものが上。
- **完了** — 丸ボタンをもう一度押すと未完了に戻る。完了した時刻を各行に表示。
  セクションごと隠せるほか、「全部削除」でまとめて消せる。
- 各行の `×` はそのタスクの削除。

## 構成

`artifact.html` が唯一のソース。Claude Artifact として公開するページなので
`<!doctype>` / `<html>` / `<head>` / `<body>` は公開時に付与される前提で省いてある。
外部依存は Google Fonts（Zen Old Mincho / Zen Kaku Gothic New）のみ。

保存は Artifact の `db` 機能（`capabilities: {db: {}}`）を使い、`tasks` コレクションに
1 タスク = 1 ドキュメントで持つ。

```
tasks/<id> = { text: string, done: boolean, createdAt: number, completedAt: number|null }
```

`db` が使えないビュー（機能が無効、権限が下りない等）では localStorage に退避し、
ヘッダーの状態表示が「この端末のみに保存」に変わる。後から `db` が使えるように
なった初回に、その端末のローカル分を一度だけ同期先へ移送する。

## 更新のしかた

`artifact.html` を編集し、同じ URL に再公開する（Artifact ツールに上記 URL を
`url` として渡す）。ファイルパスを変えると別の Artifact になる。
