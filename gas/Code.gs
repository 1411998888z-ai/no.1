/**
 * Univapay 決済ステータス → Google スプレッドシート 反映用 Web アプリ
 *
 * Univapay の Webhook を受け取り、決済1件につき1行を「決済ID」キーで
 * upsert（無ければ追加・あれば更新）してスプレッドシートに反映する。
 * 営業メンバーがリアルタイムで成功/失敗を把握できるようにするのが目的。
 *
 * --- 前提 ---
 * - このスクリプトは反映先スプレッドシートに「紐付いた（コンテナバインド）」状態で作成する想定。
 *   （スプレッドシート → 拡張機能 → Apps Script で開けば自動でバインドされる）
 * - スクリプトプロパティに以下を設定しておくこと（プロジェクトの設定 → スクリプト プロパティ）:
 *     WEBHOOK_SECRET   … Webhook URL の ?token= で照合する任意の秘密文字列（必須・推奨）
 *     SHEET_NAME       … 書き込み先シート名（任意・既定 "決済ログ"）
 *     SPREADSHEET_ID   … スタンドアロンで使う場合のみ指定（バインド運用なら不要）
 *
 * --- デプロイ ---
 * デプロイ → 新しいデプロイ → 種類「ウェブアプリ」
 *   次のユーザーとして実行: 自分
 *   アクセスできるユーザー: 全員
 * 発行された /exec URL の末尾に ?token=WEBHOOK_SECRET を付けたものを
 * Univapay の Webhook URL に登録する。
 */

// ステータス(raw) → 表示用ラベル。営業がひと目で分かるよう絵文字付き。
var STATUS_LABELS = {
  pending: "⏳ 保留中",      // ⏳ 保留中
  awaiting: "⌛ 待機中",      // ⌛ 待機中
  authorized: "🔐 オーソリ済", // 🔐 オーソリ済
  successful: "✅ 成功",          // ✅ 成功
  failed: "❌ 失敗",              // ❌ 失敗
  error: "⚠️ エラー",    // ⚠️ エラー
  canceled: "🚫 キャンセル" // 🚫 キャンセル
};

var HEADERS = [
  "受信日時",       // 受信日時
  "イベント",       // イベント
  "ステータス", // ステータス
  "status(raw)",
  "決済ID",                 // 決済ID
  "モード",             // モード(live/test)
  "金額",                   // 金額
  "通貨",                   // 通貨
  "サブスクID",     // サブスクID
  "トークンID",     // トークンID
  "エラーコード", // エラーコード
  "エラー詳細",       // エラー詳細
  "決済作成日時", // 決済作成日時(created_on)
  "説明",                   // 説明(descriptor)
  "metadata"
];

var ID_COL = 5; // 「決済ID」列（1始まり）。upsert のキー。

function doPost(e) {
  var props = PropertiesService.getScriptProperties();
  var secret = props.getProperty("WEBHOOK_SECRET");

  // ?token= による簡易認証（GAS の doPost は HTTP ヘッダを読めないためクエリで照合）
  if (secret) {
    var got = e && e.parameter ? e.parameter.token : null;
    if (got !== secret) {
      return jsonOut_({ result: "unauthorized" });
    }
  }

  var body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonOut_({ result: "bad_request", error: String(err) });
  }

  var event = body.event || body.type || "";
  var data = body.data || {};

  var lock = LockService.getScriptLock();
  lock.waitLock(20000); // 同時受信時の行重複を防ぐ
  try {
    upsertRow_(event, data);
  } finally {
    lock.releaseLock();
  }

  return jsonOut_({ result: "ok" });
}

// 動作確認用。ブラウザで /exec を開いたときに 200 を返すだけ。
function doGet() {
  return jsonOut_({ result: "ok", service: "univapay-webhook-to-sheet" });
}

function upsertRow_(event, data) {
  var sheet = getSheet_();
  ensureHeader_(sheet);

  var row = buildRow_(event, data);
  var id = row[ID_COL - 1];

  var targetRow = id ? findRowById_(sheet, id) : 0;
  if (targetRow > 0) {
    sheet.getRange(targetRow, 1, 1, row.length).setValues([row]);
  } else {
    sheet.appendRow(row);
  }
}

function buildRow_(event, data) {
  var status = pick_(data, "status") || "";
  var amount = firstDefined_(pick_(data, "charged_amount"), pick_(data, "requested_amount"), pick_(data, "amount"), "");
  var currency = firstDefined_(pick_(data, "charged_currency"), pick_(data, "requested_currency"), pick_(data, "currency"), "");

  var err = pick_(data, "error");
  var errCode = "";
  var errDetail = "";
  if (err && typeof err === "object") {
    errCode = err.code || "";
    errDetail = err.message || err.detail || JSON.stringify(err);
  }

  var metadata = pick_(data, "metadata");
  var metadataStr = (metadata && typeof metadata === "object") ? JSON.stringify(metadata) : (metadata || "");

  return [
    new Date(),                                   // 受信日時
    event,                                        // イベント
    STATUS_LABELS[status] || status,              // ステータス（表示用）
    status,                                        // status(raw)
    pick_(data, "id") || "",                      // 決済ID
    pick_(data, "mode") || "",                    // モード
    amount,                                        // 金額
    currency,                                      // 通貨
    pick_(data, "subscription_id") || "",         // サブスクID
    pick_(data, "transaction_token_id") || "",    // トークンID
    errCode,                                       // エラーコード
    errDetail,                                      // エラー詳細
    pick_(data, "created_on") || "",              // 決済作成日時
    pick_(data, "descriptor") || "",              // 説明
    metadataStr                                    // metadata
  ];
}

function findRowById_(sheet, id) {
  var last = sheet.getLastRow();
  if (last < 2) return 0; // ヘッダのみ
  var ids = sheet.getRange(2, ID_COL, last - 1, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === String(id)) {
      return i + 2; // ヘッダ分 +1、0始まり補正 +1
    }
  }
  return 0;
}

function ensureHeader_(sheet) {
  if (sheet.getLastRow() >= 1) {
    var first = sheet.getRange(1, 1).getValue();
    if (first) return; // 既にヘッダあり
  }
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight("bold");
  sheet.setFrozenRows(1);
}

function getSheet_() {
  var props = PropertiesService.getScriptProperties();
  var sheetName = props.getProperty("SHEET_NAME") || "決済ログ"; // 既定 "決済ログ"
  var ssId = props.getProperty("SPREADSHEET_ID");
  var ss = ssId ? SpreadsheetApp.openById(ssId) : SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) {
    throw new Error("Spreadsheet not found. Bind the script to a sheet or set SPREADSHEET_ID.");
  }
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }
  return sheet;
}

// snake_case / camelCase どちらのキーでも取り出せるようにする
function pick_(obj, snakeKey) {
  if (!obj || typeof obj !== "object") return undefined;
  if (obj[snakeKey] !== undefined) return obj[snakeKey];
  var camel = snakeKey.replace(/_([a-z])/g, function (m, c) { return c.toUpperCase(); });
  return obj[camel];
}

function firstDefined_() {
  for (var i = 0; i < arguments.length; i++) {
    if (arguments[i] !== undefined && arguments[i] !== null && arguments[i] !== "") {
      return arguments[i];
    }
  }
  return "";
}

function jsonOut_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
