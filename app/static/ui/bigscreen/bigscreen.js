const REFRESH_MS = 10_000;

function $(id) {
  return document.getElementById(id);
}

// --- Utils ---

function formatNumber(value) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n.toLocaleString("zh-CN") : "-";
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// 简单的数字滚动动画
function animateValue(obj, start, end, duration) {
  if (!obj) return;
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    obj.innerHTML = formatNumber(Math.floor(progress * (end - start) + start));
    if (progress < 1) {
      window.requestAnimationFrame(step);
    }
  };
  window.requestAnimationFrame(step);
}

// 保存上一次的值，用于差量动画
const lastValues = {};
function updateValueWithAnim(id, newValue) {
    const el = $(id);
    if (!el) return;
    const start = lastValues[id] || 0;
    const end = Number(newValue) || 0;
    lastValues[id] = end;
    animateValue(el, start, end, 1000);
}


function setConn(ok, text) {
  const badge = $("connBadge");
  badge.innerHTML = ok 
      ? `<span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span> ${text}`
      : `<span class="w-2 h-2 rounded-full bg-slate-500"></span> ${text}`;
      
  badge.className = ok
    ? "px-4 py-1.5 rounded bg-emerald-900/60 border border-emerald-400/50 text-emerald-100 text-sm font-mono flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
    : "px-4 py-1.5 rounded bg-emerald-950/80 border border-emerald-500/30 text-slate-400 text-sm font-mono flex items-center gap-2";
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

// --- Connection ---

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

// --- Layout & Clock ---

function setupScale() {
  const root = $("scaleRoot");
  const baseW = 1920;
  const baseH = 1080;
  const resize = () => {
    const scale = Math.min(window.innerWidth / baseW, window.innerHeight / baseH);
    // Center the content
    const x = (window.innerWidth - baseW * scale) / 2;
    const y = (window.innerHeight - baseH * scale) / 2;
    root.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
  };
  resize();
  window.addEventListener("resize", resize);
}

function setupClock() {
  const tick = () => {
    const d = new Date();
    $("clock").textContent = d.toLocaleTimeString("zh-CN", { hour12: false });
    
    const dateStr = d.toLocaleDateString("zh-CN", { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    $("date").textContent = dateStr;
  };
  tick();
  setInterval(tick, 1000);
}

// --- Charts Configuration ---

// Common styles
const colorPalette = [
    ['rgba(34,197,94,0.9)', 'rgba(5,150,105,0.4)'], // Emerald
    ['rgba(59,130,246,0.9)', 'rgba(29,78,216,0.4)'], // Blue
    ['rgba(168,85,247,0.9)', 'rgba(126,34,206,0.4)'], // Purple
    ['rgba(245,158,11,0.9)', 'rgba(180,83,9,0.4)'],   // Amber
];

function chartBaseOption() {
  return {
    textStyle: { fontFamily: 'Mono', color: "rgba(226,255,238,0.7)" },
    grid: { left: 40, right: 20, top: 30, bottom: 20, containLabel: true },
    tooltip: { 
        trigger: "axis",
        backgroundColor: 'rgba(6, 20, 12, 0.9)',
        borderColor: '#10b981',
        textStyle: { color: '#fff' }
    },
  };
}

function buildBarOption(title, items, colorIndex = 0) {
  const names = (items || []).map((x) => x.name);
  const values = (items || []).map((x) => x.count);
  const [cStart, cEnd] = colorPalette[colorIndex % colorPalette.length];
  
  return {
    ...chartBaseOption(),
    xAxis: { 
        type: "value", 
        axisLabel: { color: "rgba(226,255,238,0.5)" }, 
        splitLine: { lineStyle: { color: "rgba(34,197,94,0.1)" } } 
    },
    yAxis: {
      type: "category",
      data: names.reverse(),
      axisLabel: { color: "rgba(226,255,238,0.8)", width: 100, overflow: "truncate" },
      axisLine: { lineStyle: { color: "rgba(34,197,94,0.3)" } },
    },
    series: [
      {
        type: "bar",
        data: values.reverse(),
        barWidth: 10,
        itemStyle: {
          borderRadius: [0, 5, 5, 0],
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: cStart },
            { offset: 1, color: "rgba(0,0,0,0)" },
          ]),
        },
        showBackground: true,
        backgroundStyle: { color: 'rgba(255,255,255,0.02)', borderRadius: [0, 5, 5, 0] }
      },
    ],
  };
}

function buildLineOption(seriesName, points) {
  const xs = (points || []).map((p) => p.hour);
  const ys = (points || []).map((p) => p.count);
  return {
    ...chartBaseOption(),
    grid: { ...chartBaseOption().grid, bottom: 10 }, // Adjust for x axis labels
    xAxis: { 
        type: "category", 
        boundaryGap: false,
        data: xs, 
        axisLabel: { color: "rgba(226,255,238,0.5)", fontSize: 10 }, 
        axisLine: { lineStyle: { color: "rgba(34,197,94,0.3)" } } 
    },
    yAxis: { 
        type: "value", 
        axisLabel: { color: "rgba(226,255,238,0.5)" }, 
        splitLine: { lineStyle: { color: "rgba(34,197,94,0.1)", type: 'dashed' } } 
    },
    series: [
      {
        name: seriesName,
        type: "line",
        data: ys,
        smooth: true,
        showSymbol: false,
        symbolSize: 8,
        lineStyle: { color: "#34d399", width: 3, shadowBlur: 10, shadowColor: "rgba(52, 211, 153, 0.5)" },
        areaStyle: { 
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(52, 211, 153, 0.4)" },
                { offset: 1, color: "rgba(52, 211, 153, 0.0)" },
            ]) 
        },
      },
    ],
  };
}

function buildAlarmBarOption(points) {
  const xs = (points || []).map((p) => p.hour);
  const ys = (points || []).map((p) => p.count);
  return {
    ...chartBaseOption(),
    tooltip: { ...chartBaseOption().tooltip, trigger: 'item' },
    xAxis: { 
        type: "category", 
        data: xs, 
        axisLabel: { color: "rgba(226,255,238,0.5)", fontSize: 10, interval: 2 }, 
        axisLine: { lineStyle: { color: "rgba(34,197,94,0.3)" } } 
    },
    yAxis: { 
        type: "value", 
        axisLabel: { color: "rgba(226,255,238,0.5)" }, 
        splitLine: { lineStyle: { color: "rgba(34,197,94,0.1)" } } 
    },
    series: [
      {
        type: "bar",
        data: ys,
        barWidth: '60%',
        itemStyle: { 
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "#f43f5e" },
                { offset: 1, color: "rgba(244, 63, 94, 0.2)" },
            ]),
            borderRadius: [4, 4, 0, 0]
        },
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

// --- Alarm List Scrolling ---

let alarmScrollTimer = null;
let currentAlarms = [];

function renderAlarmList(items) {
    // Only update if data changed (simple check)
    const newIds = items.map(x => x.created_at).join(',');
    const oldIds = currentAlarms.map(x => x.created_at).join(',');
    if (newIds === oldIds && items.length > 0) return;
    
    currentAlarms = items;
    const box = $("alarmList");
    box.innerHTML = "";
    
    // Duplicate list for seamless loop if enough items
    const renderItems = items.length > 5 ? [...items, ...items] : items;
    
    for (const a of renderItems) {
        const el = document.createElement("div");
        el.className = "rounded p-3 bg-emerald-900/20 border border-emerald-500/10 flex flex-col gap-1 hover:bg-emerald-900/40 transition-colors";
        
        let statusColor = "text-slate-400";
        if(a.alarmStatus === '未处理') statusColor = "text-rose-400";
        if(a.alarmStatus === '已解决') statusColor = "text-emerald-400";
        
        el.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="text-sm font-bold text-emerald-100/90 truncate w-2/3" title="${a.alarmName}">${a.alarmName || a.alarmCode}</div>
            <div class="text-xs ${statusColor} border border-current px-1 rounded scale-90 origin-right">${a.alarmStatus}</div>
        </div>
        <div class="flex items-center justify-between text-xs text-emerald-500/50 font-mono">
            <span>${(a.created_at || "").slice(5, 19).replace("T", " ")}</span>
            <span>${a.deviceCode.slice(-6)}</span>
        </div>
        <div class="text-xs text-emerald-200/60 truncate" title="${a.explanation}">${a.explanation || "-"}</div>
        `;
        box.appendChild(el);
    }
    
    startAlarmScroll();
}

function startAlarmScroll() {
    const box = $("alarmList");
    const wrapper = $("alarmListWrapper");
    
    if (alarmScrollTimer) clearInterval(alarmScrollTimer);
    
    if (box.scrollHeight <= wrapper.clientHeight) {
        box.style.transform = `translateY(0)`;
        return;
    }

    let y = 0;
    alarmScrollTimer = setInterval(() => {
        y -= 0.5; // speed
        if (Math.abs(y) >= (box.scrollHeight / 2)) {
             y = 0; // reset to top (seamless if list is duplicated)
        }
        box.style.transform = `translateY(${y}px)`;
    }, 30);
    
    // Pause on hover
    wrapper.onmouseenter = () => clearInterval(alarmScrollTimer);
    wrapper.onmouseleave = () => startAlarmScroll();
}


// --- Main Loop ---

async function refreshOnce() {
  const summary = await api("/admin/api/bigscreen/summary");
  if (summary?.resultCode !== "200") throw new Error(summary?.msg || "加载失败");
  
  updateValueWithAnim("kpiDevices", summary.devicesTotal);
  updateValueWithAnim("kpiOnline", summary.devicesOnline);
  updateValueWithAnim("kpiOffline", summary.devicesOffline);
  updateValueWithAnim("kpiData24h", summary.deviceData24h);
  updateValueWithAnim("kpiData1h", summary.deviceData1h);
  updateValueWithAnim("kpiAlarm24h", summary.alarmDeals24h);
  
  $("kpiUpdatedAt").textContent = (summary.updatedAt || "").slice(11, 19); // HH:mm:ss

  const trends = await api("/admin/api/bigscreen/trends?hours=24");
  if (trends?.resultCode !== "200") throw new Error(trends?.msg || "加载失败");
  charts.dataTrend.setOption(buildLineOption("数据条数", trends.deviceData));
  charts.alarmTrend.setOption(buildAlarmBarOption(trends.alarmDeals));

  const areas = await api("/admin/api/bigscreen/area-stats?top=12");
  if (areas?.resultCode !== "200") throw new Error(areas?.msg || "加载失败");
  charts.province.setOption(buildBarOption("省", areas.province, 0));
  charts.city.setOption(buildBarOption("市", areas.city, 1));
  charts.farm.setOption(buildBarOption("农场", areas.farm, 2));

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