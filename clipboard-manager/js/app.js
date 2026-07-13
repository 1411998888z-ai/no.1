/* ============================================================
 * Copypad — コピペリスト管理ツール
 * 階層: ファイル → グループ（属性）→ コピペ項目
 * - ワンタッチコピー / 検索
 * - ドラッグ＆ドロップで並び替え（グループ・項目、項目はグループ間移動も可）
 * - Firebase 設定があればクラウドでリアルタイム同期（無ければローカル保存）
 * ============================================================ */
(function () {
  "use strict";

  var STORAGE_KEY = "copypad.v1";
  var THEME_KEY = "copypad.theme";
  var CLIENT_ID = "c-" + Math.floor(performance.now()).toString(36) + "-" +
    (window.crypto && crypto.getRandomValues
      ? crypto.getRandomValues(new Uint32Array(1))[0].toString(36)
      : Math.floor(performance.timeOrigin || 0).toString(36));

  /* ---------- Utilities ----------
   * uid/seq は state の初期化（load→seed）より前に定義する必要がある
   * （var 巻き上げで seq が undefined のまま uid() が呼ばれると ID が壊れるため）
   */
  var seq = 0;
  function uid() {
    seq += 1;
    return "id-" + Math.floor(performance.now() * 1000).toString(36) + "-" + seq.toString(36);
  }

  /* ---------- State ----------
   * state = { files: [{ id, name, groups: [{ id, name, items: [{id,label,text}] }] }], activeId }
   */
  var state = load();

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

  function normItem(it) {
    return { id: it.id || uid(), label: it.label || "", text: it.text || "" };
  }

  function normalize(data) {
    data.files = (data.files || []).map(function (f) {
      var groups;
      if (Array.isArray(f.groups)) {
        groups = f.groups.map(function (g) {
          return {
            id: g.id || uid(),
            name: typeof g.name === "string" ? g.name : "グループ",
            items: Array.isArray(g.items) ? g.items.map(normItem) : [],
          };
        });
      } else if (Array.isArray(f.items)) {
        // 旧形式（ファイル直下に items）→ 1グループへ移行
        groups = [{ id: uid(), name: "グループ1", items: f.items.map(normItem) }];
      } else {
        groups = [];
      }
      return {
        id: f.id || uid(),
        name: typeof f.name === "string" ? f.name : "無題",
        groups: groups,
      };
    });
    if (!data.activeId || !data.files.some(function (f) { return f.id === data.activeId; })) {
      data.activeId = data.files.length ? data.files[0].id : null;
    }
    return data;
  }

  function seed() {
    var f1 = { id: uid(), name: "よく使う定型文", groups: [
      { id: uid(), name: "メール", items: [
        { id: uid(), label: "お礼メール 冒頭", text: "お世話になっております。\n先日はお忙しい中お時間をいただき、誠にありがとうございました。" },
        { id: uid(), label: "自分のメールアドレス", text: "example@example.com" },
      ] },
      { id: uid(), name: "署名", items: [
        { id: uid(), label: "会社署名", text: "──────────\n株式会社サンプル 山田太郎\nTEL: 03-0000-0000" },
      ] },
    ] };
    var f2 = { id: uid(), name: "SNS", groups: [
      { id: uid(), name: "プロフィール", items: [
        { id: uid(), label: "自己紹介", text: "ものづくりが好きなエンジニアです。日々学んだことを発信しています。" },
      ] },
      { id: uid(), name: "ハッシュタグ", items: [
        { id: uid(), label: "定番タグ", text: "#駆け出しエンジニア #プログラミング学習 #毎日投稿" },
      ] },
    ] };
    return { files: [f1, f2], activeId: f1.id };
  }

  // 同期・比較対象は「ファイル＋グループ＋項目」の中身（activeId は端末ごとなので除外）
  function filesJson(s) {
    return JSON.stringify((s.files || []).map(function (f) {
      return {
        id: f.id, name: f.name,
        groups: (f.groups || []).map(function (g) {
          return { id: g.id, name: g.name, items: g.items.map(function (it) {
            return { id: it.id, label: it.label, text: it.text };
          }) };
        }),
      };
    }));
  }

  /* ---------- Persistence（ローカル＋クラウド） ---------- */
  function saveLocal() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (e) { toast("保存に失敗しました（容量制限の可能性）"); }
  }

  function save(origin) {
    saveLocal();
    if (origin !== "remote") cloud.push();
  }

  function activeFile() {
    return state.files.find(function (f) { return f.id === state.activeId; }) || null;
  }
  function groupById(f, gid) {
    return f ? f.groups.find(function (g) { return g.id === gid; }) : null;
  }
  function fileItemCount(f) {
    return f.groups.reduce(function (n, g) { return n + g.items.length; }, 0);
  }

  /* ---------- DOM refs ---------- */
  var $ = function (id) { return document.getElementById(id); };
  var fileListEl = $("fileList");
  var groupsEl = $("groups");
  var addGroupBtn = $("addGroupBtn");
  var noGroupState = $("noGroupState");
  var noFileState = $("noFileState");
  var currentFileName = $("currentFileName");
  var itemCount = $("itemCount");
  var searchInput = $("searchInput");
  var reorderHint = $("reorderHint");

  var fileSortable = null;
  var groupSortable = null;
  var itemSortables = [];

  /* ---------- Render ---------- */
  function render() {
    renderFiles();
    renderGroups();
  }

  function renderFiles() {
    if (fileSortable) { fileSortable.destroy(); fileSortable = null; }
    fileListEl.innerHTML = "";
    state.files.forEach(function (f) {
      var li = document.createElement("li");
      li.className = "file-item" + (f.id === state.activeId ? " is-active" : "");
      li.dataset.id = f.id;
      li.innerHTML =
        '<span class="drag-handle" title="ドラッグで並び替え" aria-label="並び替え">⠿</span>' +
        '<span class="file-item__icon">🗂️</span>' +
        '<span class="file-item__name"></span>' +
        '<span class="file-item__count">' + fileItemCount(f) + '</span>' +
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
        if (e.target.closest(".drag-handle")) return;
        selectFile(f.id);
        closeSidebar();
      });
      fileListEl.appendChild(li);
    });

    if (window.Sortable && state.files.length > 1) {
      fileSortable = window.Sortable.create(fileListEl, {
        handle: ".drag-handle", animation: 150,
        ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
        onEnd: function (evt) {
          if (evt.oldIndex === evt.newIndex) return;
          var moved = state.files.splice(evt.oldIndex, 1)[0];
          state.files.splice(evt.newIndex, 0, moved);
          save(); render();
        },
      });
    }
  }

  function renderGroups() {
    if (groupSortable) { groupSortable.destroy(); groupSortable = null; }
    itemSortables.forEach(function (s) { s.destroy(); });
    itemSortables = [];

    var f = activeFile();
    noFileState.hidden = !!f;
    groupsEl.innerHTML = "";

    if (!f) {
      noGroupState.hidden = true;
      addGroupBtn.hidden = true;
      reorderHint.hidden = true;
      currentFileName.textContent = "—";
      itemCount.textContent = "0";
      return;
    }

    currentFileName.textContent = f.name;
    itemCount.textContent = String(fileItemCount(f));

    var q = searchInput.value.trim().toLowerCase();
    var filtering = q.length > 0;

    noGroupState.hidden = f.groups.length !== 0;
    addGroupBtn.hidden = f.groups.length === 0;
    reorderHint.hidden = !((f.groups.length > 1 || fileItemCount(f) > 1) && !filtering);

    f.groups.forEach(function (g) {
      var visibleItems = g.items.filter(function (it) {
        if (!filtering) return true;
        return (it.label + "\n" + it.text).toLowerCase().indexOf(q) !== -1;
      });
      // 検索中で一致ゼロのグループは隠す
      if (filtering && visibleItems.length === 0) return;
      groupsEl.appendChild(renderGroup(f, g, visibleItems, filtering));
    });

    if (filtering && groupsEl.children.length === 0) {
      var none = document.createElement("p");
      none.className = "empty__desc";
      none.style.textAlign = "center";
      none.textContent = "「" + searchInput.value + "」に一致する項目はありません。";
      groupsEl.appendChild(none);
      return;
    }

    // グループの並び替え（検索中は無効）
    if (window.Sortable && !filtering && f.groups.length > 1) {
      groupSortable = window.Sortable.create(groupsEl, {
        handle: ".group__drag", draggable: ".group", animation: 150,
        ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
        onEnd: function (evt) {
          if (evt.oldIndex === evt.newIndex) return;
          var moved = f.groups.splice(evt.oldIndex, 1)[0];
          f.groups.splice(evt.newIndex, 0, moved);
          save(); render();
        },
      });
    }
  }

  function renderGroup(f, g, visibleItems, filtering) {
    var section = document.createElement("section");
    section.className = "group";
    section.dataset.id = g.id;
    section.innerHTML =
      '<div class="group__head">' +
        '<span class="drag-handle group__drag" title="ドラッグで並び替え" aria-label="並び替え">⠿</span>' +
        '<div class="group__name"></div>' +
        '<span class="group__count">' + g.items.length + '</span>' +
        '<div class="group__actions">' +
          '<button class="group__add" data-act="add-item">＋ 項目</button>' +
          '<button class="icon-btn" data-act="rename-group" title="グループ名を変更">✎</button>' +
          '<button class="icon-btn icon-btn--danger" data-act="delete-group" title="グループを削除">🗑</button>' +
        '</div>' +
      '</div>' +
      '<div class="group__items" data-group="' + g.id + '"></div>';

    section.querySelector(".group__name").textContent = g.name;

    var head = section.querySelector(".group__head");
    head.addEventListener("click", function (e) {
      var act = e.target.closest("[data-act]");
      if (!act) return;
      e.stopPropagation();
      if (act.dataset.act === "add-item") openItemModal(g.id, null);
      else if (act.dataset.act === "rename-group") startRenameGroup(section, f, g);
      else if (act.dataset.act === "delete-group") requestDeleteGroup(f, g);
    });

    var itemsBox = section.querySelector(".group__items");
    if (visibleItems.length === 0) {
      var empty = document.createElement("p");
      empty.className = "group__empty";
      empty.textContent = filtering ? "一致する項目はありません" : "「＋ 項目」から追加、またはここに項目をドラッグ";
      itemsBox.appendChild(empty);
    } else {
      visibleItems.forEach(function (it) { itemsBox.appendChild(renderCard(g, it)); });
    }

    // 項目の並び替え＋グループ間移動（検索中は無効）
    if (window.Sortable && !filtering) {
      itemSortables.push(window.Sortable.create(itemsBox, {
        group: "copypad-items",
        handle: ".drag-handle", draggable: ".card", animation: 150,
        ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
        onEnd: onItemDrop,
      }));
    }
    return section;
  }

  function onItemDrop(evt) {
    var f = activeFile();
    if (!f) return;
    var fromG = groupById(f, evt.from.dataset.group);
    var toG = groupById(f, evt.to.dataset.group);
    if (!fromG || !toG) { render(); return; }
    if (fromG === toG && evt.oldIndex === evt.newIndex) return;
    var moved = fromG.items.splice(evt.oldIndex, 1)[0];
    if (!moved) { render(); return; }
    toG.items.splice(evt.newIndex, 0, moved);
    save(); render();
  }

  function renderCard(g, it) {
    var card = document.createElement("div");
    card.className = "card";
    card.dataset.id = it.id;
    card.innerHTML =
      '<div class="card__head">' +
        '<span class="drag-handle" title="ドラッグで並び替え・移動" aria-label="並び替え">⠿</span>' +
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
    requestAnimationFrame(function () {
      if (textEl.scrollHeight <= textEl.clientHeight + 2) textEl.classList.add("no-fade");
    });
    textEl.addEventListener("click", function () { textEl.classList.toggle("is-expanded"); });
    card.querySelector('[data-act="edit"]').addEventListener("click", function () { openItemModal(g.id, it); });
    card.querySelector('[data-act="delete"]').addEventListener("click", function () { requestDeleteItem(g, it); });
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
      ta.value = text; ta.style.position = "fixed"; ta.style.left = "-9999px";
      document.body.appendChild(ta); ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }

  /* ---------- File actions ---------- */
  function selectFile(id) {
    state.activeId = id;
    searchInput.value = "";
    saveLocal();
    render();
  }
  function addFile() {
    var f = { id: uid(), name: "新しいファイル", groups: [{ id: uid(), name: "グループ1", items: [] }] };
    state.files.push(f);
    state.activeId = f.id;
    save(); render();
    var li = fileListEl.querySelector('[data-id="' + f.id + '"]');
    if (li) startRenameFile(li, f);
  }
  function startRenameFile(li, f) {
    var nameEl = li.querySelector(".file-item__name");
    var input = document.createElement("input");
    input.className = "file-item__name-input";
    input.value = f.name; input.maxLength = 60;
    nameEl.replaceWith(input);
    input.focus(); input.select();
    var done = function (commit) {
      var v = input.value.trim();
      if (commit && v && v !== f.name) { f.name = v; save(); }
      render();
    };
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") done(true); else if (e.key === "Escape") done(false);
    });
    input.addEventListener("blur", function () { done(true); });
    input.addEventListener("click", function (e) { e.stopPropagation(); });
  }
  function requestDeleteFile(f) {
    confirmDialog(
      "ファイル「" + f.name + "」を削除します。中のグループ・項目もすべて削除されます。よろしいですか？",
      function () {
        var idx = state.files.findIndex(function (x) { return x.id === f.id; });
        state.files.splice(idx, 1);
        if (state.activeId === f.id) {
          state.activeId = state.files.length ? state.files[Math.max(0, idx - 1)].id : null;
        }
        save(); render();
        toast("ファイルを削除しました");
      }
    );
  }

  /* ---------- Group actions ---------- */
  function addGroup() {
    var f = activeFile();
    if (!f) { toast("先にファイルを作成してください"); return; }
    var g = { id: uid(), name: "新しいグループ", items: [] };
    f.groups.push(g);
    save(); render();
    var section = groupsEl.querySelector('.group[data-id="' + g.id + '"]');
    if (section) startRenameGroup(section, f, g);
  }
  function startRenameGroup(section, f, g) {
    var nameEl = section.querySelector(".group__name");
    if (!nameEl) return;
    var input = document.createElement("input");
    input.className = "group__name-input";
    input.value = g.name; input.maxLength = 60;
    nameEl.replaceWith(input);
    input.focus(); input.select();
    var done = function (commit) {
      var v = input.value.trim();
      if (commit && v && v !== g.name) { g.name = v; save(); }
      render();
    };
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") done(true); else if (e.key === "Escape") done(false);
    });
    input.addEventListener("blur", function () { done(true); });
    input.addEventListener("click", function (e) { e.stopPropagation(); });
  }
  function requestDeleteGroup(f, g) {
    var doDelete = function () {
      f.groups = f.groups.filter(function (x) { return x.id !== g.id; });
      save(); render();
      toast("グループを削除しました");
    };
    if (g.items.length === 0) { doDelete(); return; }
    confirmDialog(
      "グループ「" + g.name + "」を削除します。中の " + g.items.length + " 件の項目も削除されます。よろしいですか？",
      doDelete
    );
  }

  /* ---------- Item modal ---------- */
  var editingItemId = null;
  var editingFromGroupId = null;
  var itemModal = $("itemModal");
  var itemLabelInput = $("itemLabelInput");
  var itemTextInput = $("itemTextInput");
  var itemModalTitle = $("itemModalTitle");
  var itemGroupSelect = $("itemGroupSelect");
  var groupSelectField = $("groupSelectField");

  function isModalOpen() { return !itemModal.hidden; }

  function openItemModal(groupId, it) {
    var f = activeFile();
    if (!f) { toast("先にファイルを作成してください"); return; }
    if (f.groups.length === 0) { toast("先にグループを追加してください"); return; }

    // グループ選択肢を構築
    itemGroupSelect.innerHTML = "";
    f.groups.forEach(function (g) {
      var opt = document.createElement("option");
      opt.value = g.id; opt.textContent = g.name;
      itemGroupSelect.appendChild(opt);
    });
    itemGroupSelect.value = groupId || f.groups[0].id;
    groupSelectField.hidden = f.groups.length <= 1 && !it; // 1グループ＆新規なら選択不要

    editingItemId = it ? it.id : null;
    editingFromGroupId = it ? groupId : null;
    itemModalTitle.textContent = it ? "項目を編集" : "項目を追加";
    itemLabelInput.value = it ? it.label : "";
    itemTextInput.value = it ? it.text : "";
    // 編集時はグループ移動もできるよう常に表示
    if (it) groupSelectField.hidden = f.groups.length <= 1;

    itemModal.hidden = false;
    setTimeout(function () { itemLabelInput.focus(); }, 40);
  }
  function closeItemModal() {
    itemModal.hidden = true;
    editingItemId = null; editingFromGroupId = null;
    applyDeferredRemote();
  }
  function saveItem() {
    var f = activeFile();
    if (!f) return;
    var label = itemLabelInput.value.trim();
    var text = itemTextInput.value;
    if (!text.trim() && !label) { toast("ラベルか本文を入力してください"); return; }

    var targetGroup = groupById(f, itemGroupSelect.value) || f.groups[0];
    if (!targetGroup) { toast("グループがありません"); return; }

    if (editingItemId) {
      var fromG = groupById(f, editingFromGroupId) || f.groups[0];
      var idx = fromG.items.findIndex(function (x) { return x.id === editingItemId; });
      var it = idx >= 0 ? fromG.items[idx] : null;
      if (it) {
        it.label = label; it.text = text;
        if (targetGroup !== fromG) {
          fromG.items.splice(idx, 1);
          targetGroup.items.push(it);
        }
      }
    } else {
      targetGroup.items.push({ id: uid(), label: label, text: text });
    }
    save(); render(); closeItemModal();
    toast(editingItemId ? "更新しました" : "追加しました");
  }
  function requestDeleteItem(g, it) {
    confirmDialog(
      "項目「" + (it.label || "（ラベルなし）") + "」を削除します。よろしいですか？",
      function () {
        g.items = g.items.filter(function (x) { return x.id !== it.id; });
        save(); render();
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
    a.href = url; a.download = "copypad-backup-" + stamp + ".json"; a.click();
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
          "現在のデータを、読み込んだファイルの内容で置き換えます。よろしいですか？（同期が有効な場合は共有中の全員に反映されます）",
          function () {
            state = normalize(data);
            save(); render();
            toast("インポートしました");
          },
          "置き換える"
        );
      } catch (e) { toast("読み込みに失敗しました: " + e.message); }
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

  /* ---------- Sync status UI ---------- */
  var syncStatusEl = $("syncStatus");
  var syncLabelEl = $("syncLabel");
  function setSyncStatus(mode, text) {
    syncStatusEl.dataset.mode = mode;
    syncLabelEl.textContent = text;
  }

  /* ============================================================
   * Cloud sync (Firebase Firestore) — 任意
   * ============================================================ */
  var cloud = (function () {
    var cfg = window.COPYPAD_FIREBASE_CONFIG || {};
    var workspaceId = window.COPYPAD_WORKSPACE_ID || "team-main";
    var enabled = !!(window.firebase && cfg && cfg.apiKey && cfg.projectId);
    var docRef = null;
    var pushTimer = null;
    var lastPushedJson = null;
    var deferredRemote = null;

    function init() {
      if (!enabled) { setSyncStatus("local", "ローカル"); return; }
      try {
        firebase.initializeApp(cfg);
        var db = firebase.firestore();
        docRef = db.collection("workspaces").doc(workspaceId);
        setSyncStatus("connecting", "接続中…");
        docRef.onSnapshot({ includeMetadataChanges: false }, function (snap) {
          if (!snap.exists) { push(true); setSyncStatus("synced", "同期中"); return; }
          var data = snap.data() || {};
          if (!Array.isArray(data.files)) { setSyncStatus("synced", "同期中"); return; }
          var incomingJson = filesJson({ files: data.files });
          if (data.updatedByClient === CLIENT_ID && incomingJson === lastPushedJson) {
            setSyncStatus("synced", "同期中"); return;
          }
          if (incomingJson === filesJson(state)) { setSyncStatus("synced", "同期中"); return; }
          adoptRemote(data.files);
        }, function (err) {
          console.error("[Copypad] Firestore error:", err);
          setSyncStatus("error", "同期エラー");
          toast("同期エラー: " + (err && err.code ? err.code : err));
        });
      } catch (e) {
        console.error("[Copypad] Firebase init failed:", e);
        enabled = false;
        setSyncStatus("error", "同期エラー");
      }
    }

    function adoptRemote(files) {
      if (isModalOpen()) { deferredRemote = files; return; }
      var keepActive = state.activeId;
      state = normalize({ files: JSON.parse(JSON.stringify(files)), activeId: keepActive });
      save("remote"); render();
      setSyncStatus("synced", "同期を受信");
      setTimeout(function () { setSyncStatus("synced", "同期中"); }, 1200);
    }
    function flushDeferred() {
      if (deferredRemote) { var f = deferredRemote; deferredRemote = null; adoptRemote(f); }
    }
    function push(immediate) {
      if (!enabled || !docRef) return;
      clearTimeout(pushTimer);
      var run = function () {
        var payload = {
          files: JSON.parse(filesJson(state)).files,
          updatedByClient: CLIENT_ID,
          updatedAt: firebase.firestore.FieldValue.serverTimestamp(),
        };
        lastPushedJson = filesJson(state);
        setSyncStatus("saving", "保存中…");
        docRef.set(payload).then(function () {
          setSyncStatus("synced", "同期中");
        }, function (err) {
          console.error("[Copypad] push failed:", err);
          setSyncStatus("error", "保存失敗");
          toast("クラウド保存に失敗: " + (err && err.code ? err.code : err));
        });
      };
      if (immediate) run(); else pushTimer = setTimeout(run, 400);
    }
    return { init: init, push: push, flushDeferred: flushDeferred };
  })();

  function applyDeferredRemote() { cloud.flushDeferred(); }

  /* ---------- Wire up events ---------- */
  $("addFileBtn").addEventListener("click", addFile);
  $("noFileAddBtn").addEventListener("click", addFile);
  $("addGroupBtn").addEventListener("click", addGroup);
  $("noGroupAddBtn").addEventListener("click", addGroup);
  $("addItemBtn").addEventListener("click", function () { openItemModal(null, null); });
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

  searchInput.addEventListener("input", renderGroups);

  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-close]")) {
      closeItemModal();
      confirmModal.hidden = true; confirmCb = null;
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (!itemModal.hidden) closeItemModal();
      else if (!confirmModal.hidden) { confirmModal.hidden = true; confirmCb = null; }
      else closeSidebar();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !itemModal.hidden) saveItem();
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault(); searchInput.focus();
    }
  });

  /* ---------- Init ---------- */
  initTheme();
  render();
  cloud.init();
})();
