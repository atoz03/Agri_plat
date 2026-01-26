// 说明：本文件刻意使用“零构建”方案，便于演示与快速上手。

const STORAGE_KEY = "agri_demo_ui_state_v1";

function $(id) {
  return document.getElementById(id);
}

function showError(message) {
  const box = $("errorBox");
  if (!message) {
    box.classList.add("hidden");
    box.textContent = "";
    return;
  }
  box.textContent = message;
  box.classList.remove("hidden");
}

function safeJsonStringify(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function truncate(text, maxLen = 160) {
  const s = String(text ?? "");
  return s.length > maxLen ? s.slice(0, maxLen) + "..." : s;
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveState(partial) {
  const current = loadState();
  const next = { ...current, ...partial };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

const state = {
  baseUrl: "",
  appkey: "DEMO_APP",
  token: null,
  devicesPage: 1,
  devicesLimit: 20,
  devicesQuery: "",
};

function getHeaders() {
  if (!state.appkey || !state.token) return {};
  return { token: state.token, appkey: state.appkey };
}

async function apiFetch(path, options = {}) {
  const url = state.baseUrl ? state.baseUrl + path : path;
  const headers = { ...(options.headers || {}), ...getHeaders() };
  const resp = await fetch(url, { ...options, headers });
  const text = await resp.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = text;
  }
  if (!resp.ok) {
    const msg = typeof data === "object" && data ? (data.msg || data.detail?.msg || data.detail || text) : text;
    throw new Error(`请求失败：${resp.status} ${msg}`);
  }
  return data;
}

function updateConnStatus() {
  const status = $("connStatus");
  const tokenPreview = $("tokenPreview");
  if (state.token) {
    status.textContent = `已连接（${state.appkey}）`;
    status.className = "px-2 py-1 rounded bg-emerald-50 text-emerald-700";
    tokenPreview.textContent = truncate(state.token, 64);
  } else {
    status.textContent = "未连接";
    status.className = "px-2 py-1 rounded bg-slate-100";
    tokenPreview.textContent = "-";
  }
}

function switchView(viewName) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  const active = document.getElementById(`view-${viewName}`);
  if (active) active.classList.remove("hidden");

  document.querySelectorAll(".nav-btn").forEach((btn) => {
    const isActive = btn.dataset.view === viewName;
    btn.className = isActive
      ? "nav-btn w-full text-left px-3 py-2 rounded-lg bg-emerald-50 text-emerald-700"
      : "nav-btn w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50";
  });
}

function renderSummary(summary) {
  const cards = [
    { key: "devices", label: "设备" },
    { key: "deviceData", label: "设备数据" },
    { key: "alarmDeals", label: "告警处置" },
    { key: "auditLogs", label: "审计日志" },
    { key: "fileExchange", label: "文件交换" },
    { key: "middleExchange", label: "中间库交换" },
    { key: "mqRecords", label: "消息队列" },
  ];
  const container = $("summaryCards");
  container.innerHTML = "";
  for (const c of cards) {
    const value = summary?.[c.key] ?? 0;
    const el = document.createElement("div");
    el.className = "rounded-lg border bg-white p-3";
    el.innerHTML = `
      <div class="text-xs text-slate-500">${c.label}</div>
      <div class="mt-1 text-2xl font-semibold">${value}</div>
    `;
    container.appendChild(el);
  }
}

async function loadOverview() {
  showError("");
  if (!state.token) {
    renderSummary({});
    return;
  }
  const data = await apiFetch("/admin/api/summary");
  if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
  renderSummary(data);
}

function renderDevicesTable(payload) {
  const tbody = $("devicesTbody");
  tbody.innerHTML = "";
  for (const d of payload.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2 font-mono text-xs">${d.deviceCode}</td>
      <td class="px-3 py-2">${d.deviceName || "-"}</td>
      <td class="px-3 py-2">${d.deviceTypeName || "-"}</td>
      <td class="px-3 py-2">${[d.provinceName, d.cityName, d.farmName].filter(Boolean).join(" / ")}</td>
      <td class="px-3 py-2 text-xs text-slate-600">${d.updated_at || "-"}</td>
      <td class="px-3 py-2">
        <button class="btnJumpData rounded bg-slate-100 px-2 py-1 text-xs hover:bg-slate-200" data-device="${d.deviceCode}">
          查看数据
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  }
  $("devicesPager").textContent = `第 ${payload.page} 页 / 共 ${Math.ceil((payload.total || 0) / payload.limit || 1)} 页（总数：${payload.total || 0}）`;
  document.querySelectorAll(".btnJumpData").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("dataDeviceCode").value = btn.dataset.device;
      switchView("deviceData");
      void loadDeviceData();
    });
  });
}

async function loadDevices() {
  showError("");
  if (!state.token) throw new Error("请先获取 token");
  const params = new URLSearchParams();
  if (state.devicesQuery) params.set("q", state.devicesQuery);
  params.set("page", String(state.devicesPage));
  params.set("limit", String(state.devicesLimit));
  const data = await apiFetch(`/admin/api/devices?${params.toString()}`);
  if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
  renderDevicesTable(data);
}

function renderDeviceDataTable(payload) {
  const tbody = $("deviceDataTbody");
  tbody.innerHTML = "";
  for (const r of payload.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2 text-xs text-slate-600">${r.created_at}</td>
      <td class="px-3 py-2 font-mono text-xs">${r.messageType}</td>
      <td class="px-3 py-2 font-mono text-xs">${r.reportTime}</td>
      <td class="px-3 py-2 text-xs">${truncate(safeJsonStringify(r.content), 220)}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadDeviceData() {
  showError("");
  if (!state.token) throw new Error("请先获取 token");
  const deviceCode = $("dataDeviceCode").value.trim();
  if (!deviceCode) throw new Error("请输入 deviceCode");
  const params = new URLSearchParams({ deviceCode, limit: "200" });
  const data = await apiFetch(`/admin/api/device-data?${params.toString()}`);
  if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
  renderDeviceDataTable(data);
}

function renderAlarmsTable(payload) {
  const tbody = $("alarmsTbody");
  tbody.innerHTML = "";
  for (const r of payload.items || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2 text-xs text-slate-600">${r.created_at}</td>
      <td class="px-3 py-2 font-mono text-xs">${r.deviceCode}</td>
      <td class="px-3 py-2">${r.alarmName || r.alarmCode}</td>
      <td class="px-3 py-2">${r.alarmStatus}</td>
      <td class="px-3 py-2">${r.handler || "-"}</td>
      <td class="px-3 py-2 text-xs">${truncate(r.explanation || "-", 80)}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadAlarms() {
  showError("");
  if (!state.token) throw new Error("请先获取 token");
  const data = await apiFetch(`/admin/api/alarm-deals?limit=200`);
  if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
  renderAlarmsTable(data);
}

async function loadExchange() {
  showError("");
  const [mq, middle] = await Promise.all([
    apiFetch("/exchange/mq/history").catch((e) => ({ error: e.message })),
    apiFetch("/exchange/middle/pull").catch((e) => ({ error: e.message })),
  ]);
  $("mqHistoryPre").textContent = safeJsonStringify(mq);
  $("middleExchangePre").textContent = safeJsonStringify(middle);
}

async function loadDictionary() {
  showError("");
  const data = await apiFetch("/data/dictionary");
  $("dictionaryPre").textContent = safeJsonStringify(data);
}

async function connect() {
  showError("");
  const appkey = $("appkeyInput").value.trim();
  if (!appkey) throw new Error("请输入 appkey");
  const resp = await apiFetch("/api/sp-token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appkey }),
  });
  if (resp?.code !== "200" || !resp?.token) throw new Error(resp?.msg || "获取 token 失败");
  state.appkey = appkey;
  state.token = resp.token;
  saveState({ appkey: state.appkey, token: state.token });
  updateConnStatus();
  await loadOverview();
}

function disconnect() {
  state.token = null;
  saveState({ token: null });
  updateConnStatus();
  renderSummary({});
}

function bindEvents() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      switchView(view);
      // 切换时按需刷新，避免首屏请求过多
      if (view === "overview") void loadOverview().catch((e) => showError(e.message));
      if (view === "devices") void loadDevices().catch((e) => showError(e.message));
      if (view === "alarms") void loadAlarms().catch((e) => showError(e.message));
      if (view === "exchange") void loadExchange().catch((e) => showError(e.message));
      if (view === "dictionary") void loadDictionary().catch((e) => showError(e.message));
    });
  });

  $("btnConnect").addEventListener("click", () => void connect().catch((e) => showError(e.message)));
  $("btnDisconnect").addEventListener("click", () => disconnect());

  $("btnRefreshOverview").addEventListener("click", () => void loadOverview().catch((e) => showError(e.message)));

  $("btnSearchDevices").addEventListener("click", () => {
    state.devicesQuery = $("deviceQuery").value.trim();
    state.devicesPage = 1;
    void loadDevices().catch((e) => showError(e.message));
  });
  $("btnPrevDevices").addEventListener("click", () => {
    if (state.devicesPage > 1) state.devicesPage -= 1;
    void loadDevices().catch((e) => showError(e.message));
  });
  $("btnNextDevices").addEventListener("click", () => {
    state.devicesPage += 1;
    void loadDevices().catch((e) => showError(e.message));
  });

  $("btnLoadDeviceData").addEventListener("click", () => void loadDeviceData().catch((e) => showError(e.message)));
  $("btnLoadAlarms").addEventListener("click", () => void loadAlarms().catch((e) => showError(e.message)));
  $("btnLoadExchange").addEventListener("click", () => void loadExchange().catch((e) => showError(e.message)));
  $("btnLoadDictionary").addEventListener("click", () => void loadDictionary().catch((e) => showError(e.message)));
}

function initFromStorage() {
  const saved = loadState();
  if (saved.appkey) state.appkey = saved.appkey;
  if (saved.token) state.token = saved.token;
  $("appkeyInput").value = state.appkey;
}

function main() {
  initFromStorage();
  updateConnStatus();
  bindEvents();
  switchView("overview");
  if (state.token) {
    void loadOverview().catch(() => disconnect());
  }
}

main();

