// 说明：本文件刻意使用“零构建”方案，便于演示与快速上手。

const STORAGE_KEY = "agri_demo_ui_state_v2";

function $(id) {
  return document.getElementById(id);
}

// --- Loading Control ---
function showLoading() {
  $("loadingOverlay").classList.remove("hidden");
}

function hideLoading() {
  $("loadingOverlay").classList.add("hidden");
}

function showError(message) {
  const box = $("errorBox");
  if (!message) {
    box.classList.add("hidden");
    $("errorMsg").textContent = "";
    return;
  }
  $("errorMsg").textContent = message;
  box.classList.remove("hidden");
  // 3秒后自动隐藏
  setTimeout(() => {
    box.classList.add("hidden");
  }, 5000);
}

// --- Utils ---

function formatTime() {
  const now = new Date();
  $("sysTime").textContent = now.toLocaleString("zh-CN", {
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
setInterval(formatTime, 1000);
formatTime();

function safeJsonStringify(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

// JSON 语法高亮
function syntaxHighlight(json) {
  if (typeof json !== 'string') {
    json = JSON.stringify(json, null, 2);
  }
  json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return json.replace(/("(\u[a-zA-Z0-9]{4}|\\[^u]|[^\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?)/g, function (match) {
    let cls = 'json-number';
    if (/^"/.test(match)) {
      if (/:$/.test(match)) {
        cls = 'json-key';
      } else {
        cls = 'json-string';
      }
    } else if (/true|false/.test(match)) {
      cls = 'json-boolean';
    } else if (/null/.test(match)) {
      cls = 'json-null';
    }
    return '<span class="' + cls + '">' + match + '</span>';
  });
}

function truncate(text, maxLen = 160) {
  const s = String(text ?? "");
  return s.length > maxLen ? s.slice(0, maxLen) + "..." : s;
}

// --- State Management ---

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
  devicesLimit: 10,
  devicesQuery: "",
};

function getHeaders() {
  if (!state.appkey || !state.token) return {};
  return { token: state.token, appkey: state.appkey };
}

async function apiFetch(path, options = {}) {
  const url = state.baseUrl ? state.baseUrl + path : path;
  const headers = { ...(options.headers || {}), ...getHeaders() };
  try {
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
  } catch (e) {
    throw e;
  }
}

function updateConnStatus() {
  const status = $("connStatus");
  const tokenPreview = $("tokenPreview");
  if (state.token) {
    status.innerHTML = `<i class="fa-solid fa-link mr-1"></i>已连接`;
    status.className = "px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200 transition-colors";
    tokenPreview.textContent = truncate(state.token, 64);
  } else {
    status.innerHTML = `<i class="fa-solid fa-link-slash mr-1"></i>未连接`;
    status.className = "px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200 transition-colors";
    tokenPreview.textContent = "-";
  }
}

// --- Views & Rendering ---

function switchView(viewName) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  const active = document.getElementById(`view-${viewName}`);
  if (active) active.classList.remove("hidden");

  document.querySelectorAll(".nav-btn").forEach((btn) => {
    const isActive = btn.dataset.view === viewName;
    const icon = btn.querySelector("i");
    
    if (isActive) {
       btn.className = "nav-btn group flex items-center w-full px-3 py-2 text-sm font-medium rounded-lg bg-emerald-50 text-emerald-700 transition-colors";
       if(icon) icon.className = icon.className.replace("text-slate-400", "text-emerald-600");
    } else {
       btn.className = "nav-btn group flex items-center w-full px-3 py-2 text-sm font-medium rounded-lg text-slate-600 hover:bg-emerald-50 hover:text-emerald-700 transition-colors";
       if(icon) icon.className = icon.className.replace("text-emerald-600", "text-slate-400");
    }
  });
  
  // Resize charts if overview is shown
  if (viewName === "overview" && charts.trend && charts.dist) {
      requestAnimationFrame(() => {
          charts.trend.resize();
          charts.dist.resize();
      });
  }
}

const charts = {
    trend: null,
    dist: null
};

function initOverviewCharts() {
    if (charts.trend) return; // already inited
    
    charts.trend = echarts.init($("chartDataTrend"));
    charts.dist = echarts.init($("chartDist"));
    
    window.addEventListener("resize", () => {
        charts.trend?.resize();
        charts.dist?.resize();
    });
}

function renderOverviewCharts(summary) {
    // Mock Trend Data based on summary or random
    const hours = Array.from({length: 24}, (_, i) => `${i}:00`);
    const trendData = hours.map(() => Math.floor(Math.random() * 50) + 10);
    
    const optionTrend = {
        grid: { top: 30, right: 20, bottom: 20, left: 40, containLabel: true },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: hours, axisLine: { lineStyle: { color: '#cbd5e1' } } },
        yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
        series: [{
            data: trendData,
            type: 'line',
            smooth: true,
            symbol: 'none',
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: 'rgba(16, 185, 129, 0.4)' },
                  { offset: 1, color: 'rgba(16, 185, 129, 0.05)' }
                ])
            },
            itemStyle: { color: '#10b981' }
        }]
    };
    charts.trend.setOption(optionTrend);

    // Pie Chart
    const optionDist = {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, icon: 'circle' },
        series: [
            {
                name: '数据分布',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
                label: { show: false, position: 'center' },
                emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
                data: [
                    { value: summary.devices || 10, name: '设备' },
                    { value: summary.deviceData || 100, name: '数据' },
                    { value: summary.alarmDeals || 5, name: '告警' },
                    { value: summary.fileExchange || 2, name: '文件' },
                    { value: summary.middleExchange || 12, name: '中间库' }
                ]
            }
        ]
    };
    charts.dist.setOption(optionDist);
}

function renderSummary(summary) {
  const cardsConfig = [
    { key: "devices", label: "接入设备", icon: "fa-microchip", color: "text-blue-500", bg: "bg-blue-50" },
    { key: "deviceData", label: "数据上报", icon: "fa-database", color: "text-emerald-500", bg: "bg-emerald-50" },
    { key: "alarmDeals", label: "告警处置", icon: "fa-bell", color: "text-rose-500", bg: "bg-rose-50" },
    { key: "mqRecords", label: "消息积压", icon: "fa-envelope", color: "text-amber-500", bg: "bg-amber-50" },
  ];
  
  const container = $("summaryCards");
  container.innerHTML = "";
  for (const c of cardsConfig) {
    const value = summary?.[c.key] ?? 0;
    const el = document.createElement("div");
    el.className = "rounded-xl border border-slate-100 bg-white p-4 shadow-sm flex items-center gap-4 transition-transform hover:-translate-y-1";
    el.innerHTML = `
      <div class="h-12 w-12 rounded-full ${c.bg} flex items-center justify-center shrink-0">
         <i class="fa-solid ${c.icon} ${c.color} text-xl"></i>
      </div>
      <div>
        <div class="text-xs text-slate-500 font-medium">${c.label}</div>
        <div class="text-2xl font-bold text-slate-800 mt-0.5">${value.toLocaleString()}</div>
      </div>
    `;
    container.appendChild(el);
  }
  
  renderOverviewCharts(summary);
}

async function loadOverview() {
  showError("");
  if (!state.token) {
    renderSummary({});
    return;
  }
  initOverviewCharts();
  showLoading();
  try {
      const data = await apiFetch("/admin/api/summary");
      if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
      renderSummary(data);
  } catch(e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

// --- Devices ---

function renderDevicesTable(payload) {
  const tbody = $("devicesTbody");
  tbody.innerHTML = "";
  
  if (!payload.items || payload.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-slate-400 text-xs">暂无数据</td></tr>`;
      return;
  }

  for (const d of payload.items || []) {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition-colors";
    
    // Type Badge
    let typeBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">${d.deviceTypeName || "未知"}</span>`;
    
    tr.innerHTML = `
      <td class="px-5 py-3 font-mono text-xs text-slate-600">${d.deviceCode}</td>
      <td class="px-5 py-3 font-medium text-slate-800">${d.deviceName || "-"}</td>
      <td class="px-5 py-3">${typeBadge}</td>
      <td class="px-5 py-3 text-xs text-slate-500">${[d.provinceName, d.cityName, d.farmName].filter(Boolean).join(" / ")}</td>
      <td class="px-5 py-3 text-xs text-slate-400 font-mono">${d.updated_at ? d.updated_at.replace('T', ' ') : "-"}</td>
      <td class="px-5 py-3 text-right">
        <button class="btnJumpData text-xs font-medium text-emerald-600 hover:text-emerald-800 transition-colors" data-device="${d.deviceCode}">
          <i class="fa-solid fa-chart-simple mr-1"></i>数据
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  }
  
  const total = payload.total || 0;
  const pages = Math.ceil(total / (payload.limit || 1)) || 1;
  $("devicesPager").textContent = `第 ${payload.page} / ${pages} 页（共 ${total} 条）`;
  
  $("btnPrevDevices").disabled = payload.page <= 1;
  $("btnNextDevices").disabled = payload.page >= pages;

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
  showLoading();
  try {
    const params = new URLSearchParams();
    if (state.devicesQuery) params.set("q", state.devicesQuery);
    params.set("page", String(state.devicesPage));
    params.set("limit", String(state.devicesLimit));
    const data = await apiFetch(`/admin/api/devices?${params.toString()}`);
    if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
    renderDevicesTable(data);
  } catch(e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

// --- Device Data ---

function renderDeviceDataTable(payload) {
  const tbody = $("deviceDataTbody");
  tbody.innerHTML = "";
  
  if (!payload.items || payload.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="px-5 py-8 text-center text-slate-400 text-xs">暂无数据</td></tr>`;
      return;
  }

  for (const r of payload.items || []) {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition-colors";
    
    // 解析内容，如果是 JSON 则美化，否则截断显示
    let contentHtml = "";
    if (typeof r.content === 'object') {
        contentHtml = `<pre class="text-[10px] bg-slate-100 p-2 rounded max-h-24 overflow-auto scrollbar-thin">${safeJsonStringify(r.content)}</pre>`;
    } else {
        contentHtml = `<span class="text-xs text-slate-600 break-all">${truncate(String(r.content), 200)}</span>`;
    }

    tr.innerHTML = `
      <td class="px-5 py-3 text-xs text-slate-500 font-mono align-top">${r.created_at ? r.created_at.replace('T', ' ') : '-'}</td>
      <td class="px-5 py-3 font-mono text-xs text-emerald-600 font-medium align-top">${r.messageType}</td>
      <td class="px-5 py-3 align-top">${contentHtml}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadDeviceData() {
  showError("");
  if (!state.token) throw new Error("请先获取 token");
  const deviceCode = $("dataDeviceCode").value.trim();
  if (!deviceCode) throw new Error("请输入 deviceCode");
  
  showLoading();
  try {
      const params = new URLSearchParams({ deviceCode, limit: "50" }); // Limit 50 for smoother rendering
      const data = await apiFetch(`/admin/api/device-data?${params.toString()}`);
      if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
      renderDeviceDataTable(data);
  } catch (e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

// --- Alarms ---

function renderAlarmsTable(payload) {
  const tbody = $("alarmsTbody");
  tbody.innerHTML = "";
  
  if (!payload.items || payload.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-slate-400 text-xs">暂无告警</td></tr>`;
      return;
  }

  for (const r of payload.items || []) {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition-colors";
    
    // Status Badge
    let statusColor = "bg-slate-100 text-slate-600";
    if (r.alarmStatus === "未处理") statusColor = "bg-rose-100 text-rose-700";
    else if (r.alarmStatus === "处理中") statusColor = "bg-amber-100 text-amber-700";
    else if (r.alarmStatus === "已解决") statusColor = "bg-emerald-100 text-emerald-700";
    
    tr.innerHTML = `
      <td class="px-5 py-3 text-xs text-slate-500 font-mono">${r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '-'}</td>
      <td class="px-5 py-3 font-mono text-xs text-slate-600">${r.deviceCode}</td>
      <td class="px-5 py-3 font-medium text-slate-800">${r.alarmName || r.alarmCode}</td>
      <td class="px-5 py-3"><span class="px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}">${r.alarmStatus}</span></td>
      <td class="px-5 py-3 text-sm">${r.handler || "-"}</td>
      <td class="px-5 py-3 text-xs text-slate-500 truncate max-w-xs" title="${r.explanation}">${r.explanation || "-"}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadAlarms() {
  showError("");
  if (!state.token) throw new Error("请先获取 token");
  
  showLoading();
  try {
      const data = await apiFetch(`/admin/api/alarm-deals?limit=50`);
      if (data?.resultCode !== "200") throw new Error(data?.msg || "加载失败");
      renderAlarmsTable(data);
  } catch(e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

// --- Exchange ---

async function loadExchange() {
  showError("");
  showLoading();
  try {
      const [mq, middle] = await Promise.all([
        apiFetch("/exchange/mq/history").catch((e) => ({ error: e.message })),
        apiFetch("/exchange/middle/pull").catch((e) => ({ error: e.message })),
      ]);
      
      // Use Syntax Highlight
      $("mqHistoryContainer").innerHTML = `<pre>${syntaxHighlight(JSON.stringify(mq, null, 2))}</pre>`;
      $("middleExchangeContainer").innerHTML = `<pre>${syntaxHighlight(JSON.stringify(middle, null, 2))}</pre>`;
  } catch(e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

// --- Dictionary ---

async function loadDictionary() {
  showError("");
  showLoading();
  try {
      const data = await apiFetch("/data/dictionary");
      $("dictionaryContainer").innerHTML = `<pre>${syntaxHighlight(JSON.stringify(data, null, 2))}</pre>`;
  } catch(e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

// --- Connection ---

async function connect() {
  showError("");
  const appkey = $("appkeyInput").value.trim();
  if (!appkey) throw new Error("请输入 appkey");
  
  showLoading();
  try {
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
  } catch(e) {
      showError(e.message);
  } finally {
      hideLoading();
  }
}

function disconnect() {
  state.token = null;
  saveState({ token: null });
  updateConnStatus();
  renderSummary({}); // Clear dashboard
}

// --- Main ---

function bindEvents() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      switchView(view);
      
      // Lazy load
      if (view === "overview") void loadOverview().catch((e) => showError(e.message));
      if (view === "devices" && state.token) void loadDevices().catch((e) => showError(e.message));
      if (view === "alarms" && state.token) void loadAlarms().catch((e) => showError(e.message));
      if (view === "exchange") void loadExchange().catch((e) => showError(e.message));
      if (view === "dictionary") void loadDictionary().catch((e) => showError(e.message));
    });
  });

  $("btnConnect").addEventListener("click", () => void connect().catch((e) => showError(e.message)));
  $("btnDisconnect").addEventListener("click", () => disconnect());

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
  initOverviewCharts(); // Pre-init charts
  switchView("overview");
  if (state.token) {
    void loadOverview().catch(() => disconnect());
  }
}

main();