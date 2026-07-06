/**
 * Nova Prime｜STEP 0 アンケート 回答受信スクリプト（Google Apps Script）
 * ---------------------------------------------------------------
 * 役割：アンケートページ(index.html)の「提出」を受け取り、
 *       Googleスプレッドシートに1行ずつ追記する。
 *
 * 使い方は nova-prime/SETUP.md を参照。要点だけ：
 *   1. 回答をためたいスプレッドシートを1つ用意
 *   2. 拡張機能 → Apps Script にこのファイルの内容を貼る
 *   3. 下の SHEET_ID にそのスプレッドシートのIDを入れる
 *   4. デプロイ → 新しいデプロイ → 種類「ウェブアプリ」
 *      アクセスできるユーザー：「全員」
 *   5. 発行された /exec URL を index.html の ENDPOINT に貼る
 */

// ▼ 回答をためるスプレッドシートのID（URLの /d/ と /edit の間の文字列）
const SHEET_ID  = "ここにスプレッドシートIDを貼る";
const SHEET_NAME = "回答";

// ▼ 提出のたびにメール通知したい場合はアドレスを入れる（不要なら空のまま）
const NOTIFY_EMAIL = "";

// 列の並び（設問キー → 見出し）。ページ側の data のキーと対応
const COLUMNS = [
  ["_ts",    "提出日時"],
  ["cid",    "ID"],
  ["name",   "氏名"],
  ["mentor", "担当講師"],
  ["q1",  "Q1 職歴・経験"],
  ["q2",  "Q2 週間スケジュール"],
  ["q3",  "Q3 決め手"],
  ["q4",  "Q4 手に入れたいもの"],
  ["q5",  "Q5 制約がなければやりたいこと10個"],
  ["q6",  "Q6 1年後の理想の休日"],
  ["q7",  "Q7 初売上の瞬間の感情"],
  ["q8",  "Q8 3ヶ月後のなりたい姿"],
  ["q9",  "Q9 1ヶ月でやり切る目標"],
  ["q10", "Q10 タイプ"],
  ["q10_r", "Q10 タイプの理由"],
  ["q11", "Q11 作業する曜日・時間帯"],
  ["q12", "Q12 障害と対処（if-then）"],
  ["q13", "Q13 一番の不安"],
  ["q14", "Q14 聞けていないこと"],
  ["q15", "Q15 過去の挫折原因"],
  ["q16", "Q16 伝えておきたいこと"],
];

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000); // 同時提出でも行が壊れないように直列化
  try {
    const payload = JSON.parse(e.postData.contents);
    const a = payload.answers || {};

    const sheet = getSheet_();
    const row = COLUMNS.map(([key]) => {
      if (key === "_ts")  return new Date();
      if (key === "cid")    return payload.cid    || "";
      if (key === "name")   return payload.name   || "";
      if (key === "mentor") return payload.mentor || "";
      const v = a[key];
      return Array.isArray(v) ? v.join(" / ") : (v == null ? "" : v);
    });
    sheet.appendRow(row);

    if (NOTIFY_EMAIL) {
      MailApp.sendEmail(
        NOTIFY_EMAIL,
        `【STEP 0提出】${payload.name || "（氏名なし）"} さん / 担当:${payload.mentor || "-"}`,
        payload.text || "回答が提出されました。スプレッドシートをご確認ください。"
      );
    }

    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

// 動作確認用（ブラウザでウェブアプリURLを開くと表示される）
function doGet() {
  return ContentService
    .createTextOutput("Nova Prime STEP0 receiver is running.")
    .setMimeType(ContentService.MimeType.TEXT);
}

function getSheet_() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(COLUMNS.map(([, label]) => label));
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
