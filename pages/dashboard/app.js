/* 音乐卡片插件页。只用 DOM API 和字符串拼接，不引第三方库。 */

let bridge = null;
const state = { status: null, busy: false, settingsLoaded: false };

function el(id) {
  return document.getElementById(id);
}

function withTimeout(promise, timeoutMs, message) {
  return Promise.race([
    promise,
    new Promise(function (_, reject) {
      setTimeout(function () {
        reject(new Error(message));
      }, timeoutMs);
    }),
  ]);
}

async function waitForBridge(timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const found = window.AstrBotPluginPage || window.AstrBotPluginView;
    if (found) return found;
    await new Promise(function (resolve) {
      setTimeout(resolve, 50);
    });
  }
  return null;
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setNotice(text, kind) {
  const box = el("notice");
  if (!text) {
    box.hidden = true;
    box.textContent = "";
    return;
  }
  box.hidden = false;
  box.textContent = text;
  box.className = "notice " + (kind || "");
}

function formatAt(value) {
  const text = String(value || "").replace("T", " ");
  return text.slice(0, 16);
}

function renderAccount(data) {
  const account = data.account || {};
  const loggedIn = !!data.logged_in;
  const pill = el("loginPill");
  pill.textContent = loggedIn ? "已登录 " + (account.name || "") : "未登录";
  pill.className = "pill " + (loggedIn ? "ok" : "warn");
  el("accountBox").hidden = !loggedIn;
  el("loginBox").hidden = loggedIn;
  el("loginHint").textContent = loggedIn ? "" : "登录后才能去评论区留言";
  if (loggedIn) {
    el("accountName").textContent = account.name || "—";
    el("accountUid").textContent = account.userId ? "UID " + account.userId : "";
    const avatar = el("accountAvatar");
    if (account.avatar) {
      avatar.src = account.avatar;
      avatar.hidden = false;
    } else {
      avatar.hidden = true;
    }
  }
  el("subtitle").textContent = loggedIn
    ? "已登录 · 听歌 · 评论"
    : "未登录：能听能看，不能评论";
}

function renderListened(items) {
  const list = el("listenedList");
  if (!items || !items.length) {
    list.innerHTML = '<li class="empty">还没有听歌记录。点上面的「听一首」试试。</li>';
    return;
  }
  list.innerHTML = items
    .map(function (item) {
      const reaction = item.reaction
        ? '<p class="rec-note">' + escapeHtml(item.reaction) + "</p>"
        : "";
      const comment = item.commented
        ? '<span class="tag ok">已评论</span>'
        : item.source === "chat"
          ? '<span class="tag">聊天里听的</span>'
          : item.source === "auto"
            ? '<span class="tag">自己听的</span>'
            : "";
      const score = item.score ? '<span class="tag">' + item.score + " 分</span>" : "";
      const category = item.category
        ? '<span class="tag">' + escapeHtml(item.category) + "</span>"
        : "";
      const liked = item.like ? '<span class="tag ok">喜欢</span>' : "";
      const saved = item.saved
        ? '<span class="tag ok">' + escapeHtml(item.playlist || "已进歌单") + "</span>"
        : "";
      return (
        "<li>" +
        '<div class="rec-main"><strong>' +
        escapeHtml(item.name || item.song_id) +
        "</strong><span>" +
        escapeHtml(item.artist || "") +
        "</span></div>" +
        '<div class="rec-side"><span>' +
        formatAt(item.at) +
        "</span>" +
        comment +
        score +
        category +
        liked +
        saved +
        "</div>" +
        reaction +
        "</li>"
      );
    })
    .join("");
}

function renderListenedCounts(items) {
  const list = el("listenedCountsList");
  if (!items || !items.length) {
    list.innerHTML = '<li class="empty">还没有听歌记录。</li>';
    return;
  }
  list.innerHTML = items
    .map(function (item) {
      return (
        "<li>" +
        '<div class="rec-main"><strong>' +
        escapeHtml(item.name || item.song_id) +
        "</strong><span>" +
        escapeHtml(item.artist || "") +
        "</span></div>" +
        '<div class="rec-side"><span>听过 ' +
        (item.count || 0) +
        " 次</span><span>" +
        formatAt(item.last_at) +
        "</span></div>" +
        "</li>"
      );
    })
    .join("");
}

function renderComments(items) {
  const list = el("commentsList");
  if (!items || !items.length) {
    list.innerHTML = '<li class="empty">还没有评论记录。勾选「顺便评论」再听一首试试。</li>';
    return;
  }
  list.innerHTML = items
    .map(function (item) {
      const tag = item.ok
        ? '<span class="tag ok">成功</span>'
        : '<span class="tag bad">失败</span>';
      return (
        "<li>" +
        '<div class="rec-main"><strong>' +
        escapeHtml(item.name || item.song_id) +
        "</strong><span>" +
        escapeHtml(item.content || "") +
        "</span></div>" +
        '<div class="rec-side"><span>' +
        formatAt(item.at) +
        "</span>" +
        tag +
        "</div>" +
        (item.ok ? "" : '<p class="rec-note">' + escapeHtml(item.message || "") + "</p>") +
        "</li>"
      );
    })
    .join("");
}

function renderRecommendations(items) {
  const list = el("recsList");
  if (!items || !items.length) {
    list.innerHTML = '<li class="empty">还没有推荐记录。</li>';
    return;
  }
  list.innerHTML = items
    .map(function (item) {
      return (
        "<li>" +
        '<div class="rec-main"><strong>' +
        escapeHtml(item.song || "") +
        "</strong><span>推荐 " +
        (item.count || 0) +
        " 次" +
        (item.last_user ? " · 最近给 " + escapeHtml(item.last_user) : "") +
        "</span></div>" +
        '<div class="rec-side"><span>' +
        formatAt(item.last_at) +
        "</span></div>" +
        "</li>"
      );
    })
    .join("");
}

const pagerState = {
  listened: { page: 1, size: 10, pages: 1, total: 0 },
  listened_counts: { page: 1, size: 10, pages: 1, total: 0 },
  comments: { page: 1, size: 10, pages: 1, total: 0 },
  replies: { page: 1, size: 10, pages: 1, total: 0 },
  recommendations: { page: 1, size: 10, pages: 1, total: 0 },
};

function initPagers() {
  document.querySelectorAll(".pager").forEach(function (pager) {
    const kind = pager.getAttribute("data-kind");
    pager.innerHTML =
      '<button class="btn ghost" data-page="prev" type="button">上一页</button>' +
      '<span class="pager-info">第 <input class="pager-input" type="number" min="1" value="1" /> / <span class="pager-total">1</span> 页</span>' +
      '<button class="btn ghost" data-page="next" type="button">下一页</button>';
    pager.addEventListener("click", function (event) {
      const button = event.target.closest("[data-page]");
      if (!button) return;
      const state = pagerState[kind];
      const target =
        button.getAttribute("data-page") === "next"
          ? state.page + 1
          : state.page - 1;
      if (target >= 1 && target <= state.pages) loadList(kind, target);
    });
    pager.addEventListener("change", function (event) {
      if (!event.target.classList.contains("pager-input")) return;
      const value = parseInt(event.target.value, 10);
      if (!Number.isFinite(value)) return;
      const state = pagerState[kind];
      const target = Math.min(Math.max(1, value), state.pages);
      loadList(kind, target);
    });
  });
}

async function loadList(kind, page) {
  const state = pagerState[kind];
  if (!state) return;
  if (page) state.page = page;
  try {
    const params = { kind: kind, page: state.page, size: state.size };
    if (kind === "listened_counts") {
      params.sort = el("listenedCountsSort").value || "default";
    }
    const data = await bridge.apiGet("page/list", params);
    state.page = data.page || 1;
    state.pages = data.pages || 1;
    state.total = data.total || 0;
    const items = data.items || [];
    if (kind === "listened") renderListened(items);
    else if (kind === "listened_counts") {
      renderListenedCounts(items);
      el("listenedCountsMeta").textContent = "共 " + state.total + " 首";
    }
    else if (kind === "comments") renderComments(items);
    else if (kind === "replies") renderReplies(items);
    else if (kind === "recommendations") {
      renderRecommendations(items);
      el("recsMeta").textContent = "共 " + state.total + " 首";
    }
    updatePager(kind);
  } catch (error) {
    setNotice("读取列表失败：" + error.message, "error");
  }
}

function updatePager(kind) {
  const pager = document.querySelector('.pager[data-kind="' + kind + '"]');
  const state = pagerState[kind];
  if (!pager || !state) return;
  const input = pager.querySelector(".pager-input");
  const total = pager.querySelector(".pager-total");
  if (input) {
    input.value = state.page;
    input.max = state.pages;
  }
  if (total) total.textContent = state.pages;
  const prev = pager.querySelector('[data-page="prev"]');
  const next = pager.querySelector('[data-page="next"]');
  if (prev) prev.disabled = state.page <= 1;
  if (next) next.disabled = state.page >= state.pages;
}

function setPersonaForm(data) {
  const select = el("personaSelect");
  const personaId = data.persona_id || "";
  if (
    personaId &&
    !Array.from(select.options).some(function (option) {
      return option.value === personaId;
    })
  ) {
    const option = document.createElement("option");
    option.value = personaId;
    option.textContent = personaId;
    select.appendChild(option);
  }
  select.value = personaId;
  el("personaExtra").value = data.persona_extra || "";
}

async function loadPersonas() {
  try {
    const data = await bridge.apiGet("page/personas");
    const select = el("personaSelect");
    select.innerHTML = '<option value="">不加载人格</option>';
    (data.personas || []).forEach(function (item) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.name;
      select.appendChild(option);
    });
  } catch (error) {
    setNotice("读取人格列表失败：" + error.message, "warn");
  }
}

async function savePersona() {
  el("savePersonaBtn").disabled = true;
  try {
    await bridge.apiPost("page/settings", {
      persona_id: el("personaSelect").value,
      persona_extra: el("personaExtra").value.trim(),
    });
    setNotice("人格设置已保存", "ok");
  } catch (error) {
    setNotice("保存失败：" + error.message, "error");
  } finally {
    el("savePersonaBtn").disabled = false;
  }
}

function renderReplies(items) {
  const list = el("repliesList");
  if (!items || !items.length) {
    list.innerHTML = '<li class="empty">还没有收到回复。</li>';
    return;
  }
  list.innerHTML = items
    .map(function (item) {
      const mine = item.my_reply
        ? '<p class="rec-note">回了：' + escapeHtml(item.my_reply) + "</p>"
        : '<p class="rec-note">（未回复）</p>';
      return (
        "<li>" +
        '<div class="rec-main"><strong>' +
        escapeHtml(item.user || "有人") +
        "</strong><span>" +
        escapeHtml(item.content || "") +
        "</span></div>" +
        '<div class="rec-side"><span>' +
        escapeHtml(item.name || "") +
        " · " +
        formatAt(item.at) +
        "</span></div>" +
        mine +
        "</li>"
      );
    })
    .join("");
}

async function saveReply() {
  el("saveReplyBtn").disabled = true;
  try {
    await bridge.apiPost("page/settings", {
      auto_reply: el("autoReply").checked,
    });
    setNotice("回复设置已保存", "ok");
  } catch (error) {
    setNotice("保存失败：" + error.message, "error");
  } finally {
    el("saveReplyBtn").disabled = false;
  }
}

async function refresh() {
  try {
    const data = await bridge.apiGet("page/status");
    state.status = data;
    renderAccount(data);
    await Promise.all([
      loadList("listened", 1),
      loadList("listened_counts", 1),
      loadList("comments", 1),
      loadList("replies", 1),
      loadList("recommendations", 1),
    ]);
    el("autoReply").checked = !!data.auto_reply;
    el("replyHint").textContent =
      "每 " + (data.reply_interval || 30) + " 分钟检查一次";
    el("listenedMeta").textContent = "共 " + (data.listened_total || 0) + " 条";
    el("commentsMeta").textContent =
      "今天 " +
      (data.comments_today || 0) +
      " / " +
      (data.daily_limit || 0) +
      " 条，共 " +
      (data.comments_total || 0) +
      " 条";
    el("autoComment").checked = !!data.auto_comment;
    if (!state.settingsLoaded) {
      state.settingsLoaded = true;
      setPersonaForm(data);
    }
    setNotice("");
  } catch (error) {
    setNotice("读取状态失败：" + error.message, "error");
  }
}

async function cookieLogin() {
  const cookie = el("cookieInput").value.trim();
  if (!cookie) {
    setNotice("先粘贴 Cookie", "warn");
    return;
  }
  el("cookieBtn").disabled = true;
  try {
    await bridge.apiPost("page/login/cookie", { cookie: cookie });
    setNotice("Cookie 登录成功", "ok");
    el("cookieInput").value = "";
    await refresh();
  } catch (error) {
    setNotice("Cookie 登录失败：" + error.message, "error");
  } finally {
    el("cookieBtn").disabled = false;
  }
}

async function logout() {
  try {
    await bridge.apiPost("page/logout", {});
    setNotice("已退出登录", "ok");
    await refresh();
  } catch (error) {
    setNotice("退出失败：" + error.message, "error");
  }
}

async function listenOnce() {
  if (state.busy) return;
  const query = el("queryInput").value.trim();
  state.busy = true;
  el("listenBtn").disabled = true;
  el("listenStatus").textContent = query
    ? "正在听…（要读歌词、看评论，再写听后感，可能要十几秒）"
    : "正在按它的喜好挑歌…";
  el("listenResult").hidden = true;
  try {
    const data = await bridge.apiPost("page/listen", {
      query: query,
      auto_comment: el("autoComment").checked,
    });
    const entry = data.entry || {};
    el("resultSong").textContent = (entry.name || "") + " — " + (entry.artist || "");
    el("resultReaction").textContent = entry.reaction || "（它没说出什么）";
    el("listenResult").hidden = false;
    const extra = [];
    if (entry.score) extra.push(entry.score + " 分");
    if (entry.category) extra.push(entry.category);
    if (entry.saved) extra.push("已加入「" + (entry.playlist || "歌单") + "」");
    if (entry.commented) extra.push("已评论");
    el("listenStatus").textContent = extra.length
      ? "听完了（" + extra.join(" · ") + "）。"
      : "听完了。";
    await refresh();
  } catch (error) {
    el("listenStatus").textContent = "";
    setNotice("听歌失败：" + error.message, "error");
  } finally {
    state.busy = false;
    el("listenBtn").disabled = false;
  }
}

function bind() {
  initPagers();
  el("refreshBtn").addEventListener("click", refresh);
  el("cookieBtn").addEventListener("click", cookieLogin);
  el("savePersonaBtn").addEventListener("click", savePersona);
  el("saveReplyBtn").addEventListener("click", saveReply);
  el("listenedCountsSort").addEventListener("change", function () {
    loadList("listened_counts", 1);
  });
  el("logoutBtn").addEventListener("click", logout);
  el("switchBtn").addEventListener("click", function () {
    el("loginBox").hidden = false;
    el("cookieInput").focus();
  });
  el("listenBtn").addEventListener("click", listenOnce);
  el("queryInput").addEventListener("keydown", function (event) {
    if (event.key === "Enter") listenOnce();
  });
}

async function boot() {
  bridge = await waitForBridge(5000);
  if (!bridge) {
    setNotice(
      "没有检测到 AstrBot 页面桥接 —— 请从 WebUI 的「插件 → 听歌」进入；如果就是从那里进来的，刷新一次页面。",
      "error"
    );
    return;
  }
  try {
    await withTimeout(bridge.ready(), 6000, "桥接响应超时");
  } catch (error) {
    setNotice("页面桥接响应超时，如果下面一直是空白，刷新一次页面。", "warn");
  }
  bind();
  await loadPersonas();
  await refresh();
}

boot();
