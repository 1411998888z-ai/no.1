/* ============================================================
 * Copypad — コピペリスト管理ツール
 * データはブラウザの localStorage に保存されます（サーバー不要）。
 * ============================================================ */
(function () {
  "use strict";

  var STORAGE_KEY = "copypad.v1";
  var THEME_KEY = "copypad.theme";

  /* ---------- State ---------- */
  // state = { files: [{ id, name, items: [{ id, label, text }] }], activeId }
  var state = load();

  /* ---------- Utilities ---------- */
  function uid() {
    return "id-" + Date.now().toString(36) + "-" + Math.floor(Math.random() * 1e6).toString(36);
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.files)) return normalize(parsed);
      }
    } catch (e) { /* fall through to seed */ }
    return seed();
  }

  function normalize(data) {
    data.files = data.files.map(function (f) {
      return {
        id: f.id || uid(),
        name: typeof f.name === "string" ? f.name : "無題",
        items: Array.isArray(f.items) ? f.items.map(function (it) {
          return { id: it.id || uid(), label: it.label || "", text: it.text || "" };
        }) : [],
      };
    });
    if (!data.activeId || !data.files.some(function (f) { return f.id === data.activeId; })) {
      data.activeId = data.files.length ? data.files[0].id : null;
    }
    return data;
  }

  function seed() {
    var f1 = { id: uid(), name: "よく使う定型文", items: [
      { id: uid(), label: "お礼メール 冒頭", text: "お世話になっております。\n先日はお忙しい中お時間をいただき、誠にありがとうございました。" },
      { id: uid(), label: "自分のメールアドレス", text: "example@example.com" },
    ] };
    var f2 = { id: uid(), name: "SNS", items: [
      { id: uid(), label: "プロフィール文", text: "ものづくりが好きなエンジニアです。日々学んだことを発信しています。" },
      { id: uid(), label: "ハッシュタグ", text: "#駆け出しエンジニア #プログラミング学習 #毎日投稿" },
    ] };
    return { files: [f1, f2], activeId: f1.id };
  }

  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (e) { toast("保存に失敗しました（容量制限の可能性）"); }
  }

  function activeFile() {
    return state.files.find(function (f) { return f.id === state.activeId; }) || null;
  }

  /* ---------- DOM refs ---------- */
  var $ = function (id) { return document.getElementById(id); };
  var fileListEl = $("fileList");
  var itemsEl = $("items");
  var emptyState = $("emptyState");
  var noFileState = $("noFileState");
  var currentFileName = $("currentFileName");
  var itemCount = $("itemCount");
  var searchInput = $("searchInput");

  /* ---------- Render ---------- */
  function render() {
    renderFiles();
    renderItems();
  }

  function renderFiles() {
    fileListEl.innerHTML = "";
    state.files.forEach(function (f) {
      var li = document.createElement("li");
      li.className = "file-item" + (f.id === state.activeId ? " is-active" : "");
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", f.id === state.activeId ? "true" : "false");
      li.dataset.id = f.id;

      li.innerHTML =
        '<span class="file-item__icon">🗂️</span>' +
        '<span class="file-item__name"></span>' +
        '<span class="file-item__count">' + f.items.length + '</span>' +
        '<span class="file-item__actions">' +
          '<button class="icon-btn" data-act="rename" title="名前を変更">✎</button>' +
          '<button class="icon-btn icon-btn--danger" data-act="delete-file" title="削除">🗑</button>' +
        '</span>';
      li.querySelector(".file-item__name").textContent = f.name;

      li.addEventListener("click", function (e) {
        var act = e.target.closest("[data-act]");
        if (act) {
          e.stopPropagation();
          if (act.dataset.act === "rename") startRenameFile(li, f);
          else if (act.dataset.act === "delete-file") requestDeleteFile(f);
          return;
        }
        selectFile(f.id);
        closeSidebar();
      });

      fileListEl.appendChild(li);
    });
  }

  function renderItems() {
    var f = activeFile();

    noFileState.hidden = !!f;
    if (!f) {
      itemsEl.innerHTML = "";
      emptyState.hidden = true;
      currentFileName.textContent = "—";
      itemCount.textContent = "0";
      return;
    }

    currentFileName.textContent = f.name;
    itemCount.textContent = String(f.items.length);

    var q = searchInput.value.trim().toLowerCase();
    var list = f.items.filter(function (it) {
      if (!q) return true;
      return (it.label + "\n" + it.text).toLowerCase().indexOf(q) !== -1;
    });

    itemsEl.innerHTML = "";
    emptyState.hidden = f.items.length !== 0;

    if (f.items.length && list.length === 0) {
      var none = document.createElement("p");
      none.className = "empty__desc";
      none.style.gridColumn = "1 / -1";
      none.style.textAlign = "center";
      none.textContent = "「" + searchInput.value + "」に一致する項目はありません。";
      itemsEl.appendChild(none);
      return;
    }

    list.forEach(function (it) { itemsEl.appendChild(renderCard(it)); });
  }

  function renderCard(it) {
    var card = document.createElement("div");
    card.className = "card";
    card.dataset.id = it.id;

    card.innerHTML =
      '<div class="card__head">' +
        '<div class="card__label"></div>' +
        '<div class="card__actions">' +
          '<button class="icon-btn" data-act="edit" title="編集">✎</button>' +
          '<button class="icon-btn icon-btn--danger" data-act="delete" title="削除">🗑</button>' +
        '</div>' +
      '</div>' +
      '<div class="card__text" title="クリックで全文表示"></div>' +
      '<button class="copy-btn" data-act="copy"><span class="copy-btn__label">📋 コピー</span></button>';

    card.querySelector(".card__label").textContent = it.label;
    var textEl = card.querySelector(".card__text");
    textEl.textContent = it.text;

    // 短いテキストはフェード無し
    requestAnimationFrame(function () {
      if (textEl.scrollHeight <= textEl.clientHeight + 2) textEl.classList.add("no-fade");
    });

    textEl.addEventListener("click", function () { textEl.classList.toggle("is-expanded"); });

    card.querySelector('[data-act="edit"]').addEventListener("click", function () { openItemModal(it); });
    card.querySelector('[data-act="delete"]').addEventListener("click", function () { requestDeleteItem(it); });
    card.querySelector('[data-act="copy"]').addEventListener("click", function () { copyItem(it, card); });

    return card;
  }

  /* ---------- Copy ---------- */
  function copyItem(it, card) {
    copyText(it.text).then(function (ok) {
      if (!ok) { toast("コピーに失敗しました"); return; }
      var btn = card.querySelector(".copy-btn");
      var label = btn.querySelector(".copy-btn__label");
      var prev = label.textContent;
      btn.classList.add("is-copied");
      card.classList.add("is-copied");
      label.textContent = "✓ コピー完了";
      toast("コピーしました: " + (it.label || "（ラベルなし）"));
      setTimeout(function () {
        btn.classList.remove("is-copied");
        card.classList.remove("is-copied");
        label.textContent = prev;
      }, 1400);
    });
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () { return legacyCopy(text); });
    }
    return Promise.resolve(legacyCopy(text));
  }

  function legacyCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }

  /* ---------- File actions ---------- */
  function selectFile(id) {
    state.activeId = id;
    searchInput.value = "";
    save();
    render();
  }

  function addFile() {
    var f = { id: uid(), name: "新しいファイル", items: [] };
    state.files.push(f);
    state.activeId = f.id;
    save();
    render();
    // すぐ名前編集に入る
    var li = fileListEl.querySelector('[data-id="' + f.id + '"]');
    if (li) startRenameFile(li, f);
  }

  function startRenameFile(li, f) {
    var nameEl = li.querySelector(".file-item__name");
    var input = document.createElement("input");
    input.className = "file-item__name-input";
    input.value = f.name;
    input.maxLength = 60;
    nameEl.replaceWith(input);
    input.focus();
    input.select();

    var done = function (commit) {
      var v = input.value.trim();
      if (commit && v) { f.name = v; save(); }
      render();
    };
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") done(true);
      else if (e.key === "Escape") done(false);
    });
    input.addEventListener("blur", function () { done(true); });
    input.addEventListener("click", function (e) { e.stopPropagation(); });
  }

  function requestDeleteFile(f) {
    confirmDialog(
      "ファイル「" + f.name + "」を削除します。中の " + f.items.length + " 件の項目もすべて削除されます。よろしいですか？",
      function () {
        var idx = state.files.findIndex(function (x) { return x.id === f.id; });
        state.files.splice(idx, 1);
        if (state.activeId === f.id) {
          state.activeId = state.files.length ? state.files[Math.max(0, idx - 1)].id : null;
        }
        save();
        render();
        toast("ファイルを削除しました");
      }
    );
  }

  /* ---------- Item modal ---------- */
  var editingItemId = null;
  var itemModal = $("itemModal");
  var itemLabelInput = $("itemLabelInput");
  var itemTextInput = $("itemTextInput");
  var itemModalTitle = $("itemModalTitle");

  function openItemModal(it) {
    var f = activeFile();
    if (!f) { toast("先にファイルを作成してください"); return; }
    editingItemId = it ? it.id : null;
    itemModalTitle.textContent = it ? "項目を編集" : "項目を追加";
    itemLabelInput.value = it ? it.label : "";
    itemTextInput.value = it ? it.text : "";
    itemModal.hidden = false;
    setTimeout(function () { itemLabelInput.focus(); }, 40);
  }

  function closeItemModal() { itemModal.hidden = true; editingItemId = null; }

  function saveItem() {
    var f = activeFile();
    if (!f) return;
    var label = itemLabelInput.value.trim();
    var text = itemTextInput.value;
    if (!text.trim() && !label) { toast("ラベルか本文を入力してください"); return; }

    if (editingItemId) {
      var it = f.items.find(function (x) { return x.id === editingItemId; });
      if (it) { it.label = label; it.text = text; }
    } else {
      f.items.push({ id: uid(), label: label, text: text });
    }
    save();
    render();
    closeItemModal();
    toast(editingItemId ? "更新しました" : "追加しました");
  }

  function requestDeleteItem(it) {
    confirmDialog(
      "項目「" + (it.label || "（ラベルなし）") + "」を削除します。よろしいですか？",
      function () {
        var f = activeFile();
        f.items = f.items.filter(function (x) { return x.id !== it.id; });
        save();
        render();
        toast("削除しました");
      }
    );
  }

  /* ---------- Confirm dialog ---------- */
  var confirmModal = $("confirmModal");
  var confirmMessage = $("confirmMessage");
  var confirmOkBtn = $("confirmOkBtn");
  var confirmCb = null;

  function confirmDialog(msg, cb, okLabel) {
    confirmMessage.textContent = msg;
    confirmCb = cb;
    confirmOkBtn.textContent = okLabel || "削除";
    confirmModal.hidden = false;
  }
  confirmOkBtn.addEventListener("click", function () {
    confirmModal.hidden = true;
    if (confirmCb) confirmCb();
    confirmCb = null;
  });

  /* ---------- Import / Export ---------- */
  function exportData() {
    var blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    var d = new Date();
    var stamp = d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate());
    a.href = url;
    a.download = "copypad-backup-" + stamp + ".json";
    a.click();
    URL.revokeObjectURL(url);
    toast("エクスポートしました");
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function importData(file) {
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var data = JSON.parse(String(reader.result));
        if (!data || !Array.isArray(data.files)) throw new Error("形式が不正です");
        confirmDialog(
          "現在のデータを、読み込んだファイルの内容で置き換えます。よろしいですか？（先に現在のデータをエクスポートしておくと安全です）",
          function () {
            state = normalize(data);
            save();
            render();
            toast("インポートしました");
          },
          "置き換える"
        );
      } catch (e) {
        toast("読み込みに失敗しました: " + e.message);
      }
    };
    reader.readAsText(file);
  }

  /* ---------- Toast ---------- */
  var toastEl = $("toast");
  var toastTimer = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("is-show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("is-show"); }, 1900);
  }

  /* ---------- Theme ---------- */
  function initTheme() {
    var t = localStorage.getItem(THEME_KEY);
    if (t) document.documentElement.setAttribute("data-theme", t);
  }
  function toggleTheme() {
    var cur = document.documentElement.getAttribute("data-theme");
    var mqDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    // 現在の実効テーマを判定して反転
    var effective = cur || (mqDark ? "dark" : "light");
    var next = effective === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
  }

  /* ---------- Sidebar (mobile) ---------- */
  var sidebar = $("sidebar");
  var scrim = $("scrim");
  function openSidebar() { sidebar.classList.add("is-open"); scrim.classList.add("is-open"); }
  function closeSidebar() { sidebar.classList.remove("is-open"); scrim.classList.remove("is-open"); }

  /* ---------- Wire up events ---------- */
  $("addFileBtn").addEventListener("click", addFile);
  $("noFileAddBtn").addEventListener("click", addFile);
  $("addItemBtn").addEventListener("click", function () { openItemModal(null); });
  $("emptyAddBtn").addEventListener("click", function () { openItemModal(null); });
  $("saveItemBtn").addEventListener("click", saveItem);
  $("exportBtn").addEventListener("click", exportData);
  $("importBtn").addEventListener("click", function () { $("importInput").click(); });
  $("importInput").addEventListener("change", function (e) {
    if (e.target.files && e.target.files[0]) importData(e.target.files[0]);
    e.target.value = "";
  });
  $("themeBtn").addEventListener("click", toggleTheme);
  $("menuBtn").addEventListener("click", openSidebar);
  $("sidebarClose").addEventListener("click", closeSidebar);
  scrim.addEventListener("click", closeSidebar);

  searchInput.addEventListener("input", renderItems);

  // モーダルの閉じる（背景・キャンセル）
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-close]")) {
      closeItemModal();
      confirmModal.hidden = true;
      confirmCb = null;
    }
  });

  // キーボード
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (!itemModal.hidden) closeItemModal();
      else if (!confirmModal.hidden) { confirmModal.hidden = true; confirmCb = null; }
      else closeSidebar();
    }
    // Ctrl/Cmd + Enter でモーダル保存
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !itemModal.hidden) {
      saveItem();
    }
    // Ctrl/Cmd + K で検索フォーカス
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      searchInput.focus();
    }
  });

  /* ---------- Init ---------- */
  initTheme();
  render();
})();
