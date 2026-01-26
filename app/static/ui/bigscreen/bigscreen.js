const REFRESH_MS = 10_000;

function $(id) {
  return document.getElementById(id);
}

function formatNumber(value) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n.toLocaleString("zh-CN") : "-";
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function setConn(ok, text) {
  const badge = $("connBadge");
  badge.textContent = text;
  badge.className = ok
    ? "px-3 py-1 rounded-lg bg-emerald-900/40 border border-emerald-400/30 text-sm"
    : "px-3 py-1 rounded-lg bg-emerald-950/60 border border-emerald-500/20 text-sm";
}

const state = {
  appkey: "DEMO_APP",
  token: null,
};

function headers() {
  if (!state.token) return {};
  return { token: state.token, appkey: state.appkey };
}

async function api(path, options = {}) {
  const resp = await fetch(path, { ...options, headers: { ...(options.headers || {}), ...headers() } });
  const text = await resp.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = text;
  }
  if (!resp.ok) throw new Error(typeof data === "object" ? data?.msg || "请求失败" : text);
  return data;
}

async function connect() {
  const r = await api("/api/sp-token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appkey: state.appkey }),
  });
  if (r?.code !== "200" || !r?.token) throw new Error(r?.msg || "获取 token 失败");
  state.token = r.token;
  setConn(true, "已连接");
}

function setupScale() {
  const root = $("scaleRoot");
  const baseW = 1920;
  const baseH = 1080;
  const resize = () => {
    const scale = Math.min(window.innerWidth / baseW, window.innerHeight / baseH);
    root.style.transform = `scale(${scale})`;
  };
  resize();
  window.addEventListener("resize", resize);
}

function setupClock() {
  const tick = () => {
    const d = new Date();
    $("clock").textContent = d.toLocaleString("zh-CN", { hour12: false });
  };
  tick();
  setInterval(tick, 1000);
}

function chartBaseOption() {
  return {
    textStyle: { color: "rgba(226,255,238,0.9)" },
    grid: { left: 36, right: 18, top: 22, bottom: 28 },
    tooltip: { trigger: "axis" },
  };
}

function buildBarOption(title, items) {
  const names = (items || []).map((x) => x.name);
  const values = (items || []).map((x) => x.count);
  return {
    ...chartBaseOption(),
    xAxis: { type: "value", axisLabel: { color: "rgba(226,255,238,0.65)" }, splitLine: { lineStyle: { color: "rgba(34,197,94,0.10)" } } },
    yAxis: {
      type: "category",
      data: names.reverse(),
      axisLabel: { color: "rgba(226,255,238,0.75)", width: 140, overflow: "truncate" },
      axisLine: { lineStyle: { color: "rgba(34,197,94,0.18)" } },
    },
    series: [
      {
        type: "bar",
        data: values.reverse(),
        barWidth: 12,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: "rgba(34,197,94,0.9)" },
            { offset: 1, color: "rgba(22,163,74,0.35)" },
          ]),
        },
      },
    ],
  };
}

function buildLineOption(seriesName, points) {
  const xs = (points || []).map((p) => p.hour);
  const ys = (points || []).map((p) => p.count);
  return {
    ...chartBaseOption(),
    xAxis: { type: "category", data: xs, axisLabel: { color: "rgba(226,255,238,0.65)", rotate: 35 }, axisLine: { lineStyle: { color: "rgba(34,197,94,0.18)" } } },
    yAxis: { type: "value", axisLabel: { color: "rgba(226,255,238,0.65)" }, splitLine: { lineStyle: { color: "rgba(34,197,94,0.10)" } } },
    series: [
      {
        name: seriesName,
        type: "line",
        data: ys,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: "rgba(34,197,94,0.95)", width: 2 },
        areaStyle: { color: "rgba(34,197,94,0.12)" },
      },
    ],
  };
}

function buildAlarmBarOption(points) {
  const xs = (points || []).map((p) => p.hour);
  const ys = (points || []).map((p) => p.count);
  return {
    ...chartBaseOption(),
    xAxis: { type: "category", data: xs, axisLabel: { color: "rgba(226,255,238,0.65)", rotate: 35 }, axisLine: { lineStyle: { color: "rgba(34,197,94,0.18)" } } },
    yAxis: { type: "value", axisLabel: { color: "rgba(226,255,238,0.65)" }, splitLine: { lineStyle: { color: "rgba(34,197,94,0.10)" } } },
    series: [
      {
        type: "bar",
        data: ys,
        barWidth: 10,
        itemStyle: { color: "rgba(34,197,94,0.75)" },
      },
    ],
  };
}

const charts = {
  province: null,
  city: null,
  farm: null,
  dataTrend: null,
  alarmTrend: null,
};

function initCharts() {
  charts.province = echarts.init($("provinceChart"));
  charts.city = echarts.init($("cityChart"));
  charts.farm = echarts.init($("farmChart"));
  charts.dataTrend = echarts.init($("dataTrendChart"));
  charts.alarmTrend = echarts.init($("alarmTrendChart"));
  window.addEventListener("resize", () => Object.values(charts).forEach((c) => c?.resize()));
}

function renderAlarmList(items) {
  const box = $("alarmList");
  box.innerHTML = "";
  for (const a of items || []) {
    const el = document.createElement("div");
    el.className = "rounded-xl p-3 bg-emerald-950/35 border border-emerald-500/10";
    el.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <div class="text-sm font-semibold text-emerald-100/90">${a.alarmName || a.alarmCode}</div>
        <div class="text-xs text-emerald-200/60 font-mono">${(a.created_at || "").slice(0, 19).replace("T", " ")}</div>
      </div>
      <div class="mt-1 text-xs text-emerald-200/70 font-mono break-all">设备：${a.deviceCode}</div>
      <div class="mt-1 text-xs text-emerald-200/60">${a.explanation || "-"}</div>
    `;
    box.appendChild(el);
  }
}

async function refreshOnce() {
  const summary = await api("/admin/api/bigscreen/summary");
  if (summary?.resultCode !== "200") throw new Error(summary?.msg || "加载失败");
  $("kpiDevices").textContent = formatNumber(summary.devicesTotal);
  $("kpiOnline").textContent = formatNumber(summary.devicesOnline);
  $("kpiOffline").textContent = formatNumber(summary.devicesOffline);
  $("kpiData24h").textContent = formatNumber(summary.deviceData24h);
  $("kpiData1h").textContent = formatNumber(summary.deviceData1h);
  $("kpiAlarm24h").textContent = formatNumber(summary.alarmDeals24h);
  $("kpiUpdatedAt").textContent = (summary.updatedAt || "").slice(0, 19).replace("T", " ");

  const trends = await api("/admin/api/bigscreen/trends?hours=24");
  if (trends?.resultCode !== "200") throw new Error(trends?.msg || "加载失败");
  charts.dataTrend.setOption(buildLineOption("数据条数", trends.deviceData));
  charts.alarmTrend.setOption(buildAlarmBarOption(trends.alarmDeals));

  const areas = await api("/admin/api/bigscreen/area-stats?top=12");
  if (areas?.resultCode !== "200") throw new Error(areas?.msg || "加载失败");
  charts.province.setOption(buildBarOption("省", areas.province));
  charts.city.setOption(buildBarOption("市", areas.city));
  charts.farm.setOption(buildBarOption("农场", areas.farm));

  const alarms = await api("/admin/api/bigscreen/latest-alarms?limit=20");
  if (alarms?.resultCode !== "200") throw new Error(alarms?.msg || "加载失败");
  renderAlarmList(alarms.items);
}

async function loopRefresh() {
  while (true) {
    try {
      if (!state.token) {
        await connect();
      }
      await refreshOnce();
      setConn(true, "已连接");
    } catch (e) {
      setConn(false, `异常：${e?.message || "未知错误"}`);
      // token 失效/未连接时重试连接
      state.token = null;
    }
    await sleep(REFRESH_MS);
  }
}

function main() {
  setupScale();
  setupClock();
  initCharts();
  $("btnConnect").addEventListener("click", () => connect().catch((e) => setConn(false, e.message)));
  loopRefresh();
}

main();
