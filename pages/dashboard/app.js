/* 音乐卡片插件页。只用 DOM API 和字符串拼接，不引第三方库。 */

let bridge = null;
const state = { status: null, qrTimer: 0, busy: false };

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
  el("loginHint").textContent = loggedIn ? "" : "登录后才能去评论区留言";
  el("loginBtn").textContent = loggedIn ? "换一个账号" : "扫码登录";
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
  el("subtitle").textContent = loggedIn ? "扫码登录 · 听歌 · 评论" : "未登录：能听能看，不能评论";
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
        "</div>" +
        reaction +
        "</li>"
      );
    })
    .join("");
}

function renderComments(items) {
  const list = el("commentsList");
  if (!items || !items.length) {
    list.innerHTML = '<li class="empty">还没有评论记录。</li>';
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

async function refresh() {
  try {
    const data = await bridge.apiGet("page/status");
    state.status = data;
    renderAccount(data);
    renderListened(data.listened || []);
    renderComments(data.comments || []);
    el("listenedMeta").textContent =
      "共 " + (data.listened_total || 0) + " 条";
    el("commentsMeta").textContent =
      "今天 " +
      (data.comments_today || 0) +
      " / " +
      (data.daily_limit || 0) +
      " 条，共 " +
      (data.comments_total || 0) +
      " 条";
    if (!state.busy && document.activeElement !== el("queryInput")) {
      el("queryInput").value = data.listen_query || "";
    }
    el("autoComment").checked = !!data.auto_comment;
    setNotice("");
  } catch (error) {
    setNotice("读取状态失败：" + error.message, "error");
  }
}

function stopQrTimer() {
  if (state.qrTimer) {
    clearInterval(state.qrTimer);
    state.qrTimer = 0;
  }
}

async function startLogin() {
  stopQrTimer();
  el("qrBox").hidden = true;
  el("qrState").textContent = "正在生成二维码…";
  try {
    const data = await bridge.apiPost("page/login/qr", {});
    el("qrBox").hidden = false;
    if (data.image) {
      el("qrImage").src = data.image;
      el("qrImage").hidden = false;
      el("qrLink").hidden = true;
    } else {
      el("qrImage").hidden = true;
      el("qrLink").hidden = false;
      el("qrLink").href = data.url || "#";
    }
    el("qrState").textContent = "用网易云 App 扫码并确认";
    state.qrTimer = setInterval(function () {
      pollLogin(data.key);
    }, 2000);
  } catch (error) {
    el("qrState").textContent = "";
    setNotice("生成二维码失败：" + error.message, "error");
  }
}

async function pollLogin(key) {
  try {
    const result = await bridge.apiPost("page/login/poll", { key: key });
    if (result.state === "confirmed") {
      stopQrTimer();
      el("qrBox").hidden = true;
      el("qrState").textContent = "登录成功";
      setNotice("登录成功", "ok");
      await refresh();
      return;
    }
    if (result.state === "scanned") {
      el("qrState").textContent = "已扫码，请在手机上确认";
      return;
    }
    if (result.state === "expired") {
      stopQrTimer();
      el("qrState").textContent = "二维码过期了，重新点一次扫码登录";
      return;
    }
    el("qrState").textContent = result.message || "等待扫码…";
  } catch (error) {
    stopQrTimer();
    el("qrState").textContent = "";
    setNotice("查询扫码状态失败：" + error.message, "error");
  }
}

async function listenOnce() {
  if (state.busy) return;
  const query = el("queryInput").value.trim();
  if (!query) {
    setNotice("先填一个歌名或歌手", "warn");
    return;
  }
  state.busy = true;
  el("listenBtn").disabled = true;
  el("listenStatus").textContent = "正在听…（要读歌词、看评论，再写听后感，可能要十几秒）";
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
    el("listenStatus").textContent = entry.commented
      ? "听完了，也去评论区留言了。"
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
    stopQrTimer();
    el("qrBox").hidden = true;
    el("qrState").textContent = "";
    setNotice("已退出登录", "ok");
    await refresh();
  } catch (error) {
    setNotice("退出失败：" + error.message, "error");
  }
}

function bind() {
  el("refreshBtn").addEventListener("click", refresh);
  el("loginBtn").addEventListener("click", startLogin);
  el("logoutBtn").addEventListener("click", logout);
  el("cookieBtn").addEventListener("click", cookieLogin);
  el("listenBtn").addEventListener("click", listenOnce);
  el("queryInput").addEventListener("keydown", function (event) {
    if (event.key === "Enter") listenOnce();
  });
}

async function boot() {
  bridge = await waitForBridge(5000);
  if (!bridge) {
    setNotice("没有检测到 AstrBot 页面桥接 —— 请从 WebUI 的「插件 → 听歌」进入；如果就是从那里进来的，刷新一次页面。", "error");
    return;
  }
  try {
    await withTimeout(bridge.ready(), 6000, "桥接响应超时");
  } catch (error) {
    setNotice("页面桥接响应超时，如果下面一直是空白，刷新一次页面。", "warn");
  }
  bind();
  await refresh();
}

boot();
