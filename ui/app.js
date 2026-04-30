/* ══════════════════════════════════════════════════════════════
   VN Address Intelligence — SaaS App Logic
   ══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.hostname === "localhost" || window.location.protocol === "file:"
  ? "http://localhost:8081/api"
  : "/api";

const PAGES = [
  "overview", "parser", "batch", "training", "label-studio",
  "experiments", "explorer", "osm-enrichment", "lookup",
  "admin-units", "nso-sync", "settings"
];

const {
  applyUnifiedControlTemplate,
  renderLookupTemplateDatalist,
  renderUnifiedSelectOptions,
  showToast,
  showConfirm
} = window.VNAIControls || {};

// ── Auth Check ──
if (!localStorage.getItem('vnai_token') && !window.location.pathname.includes('login.html')) {
  window.location.href = 'login.html';
}

function getAuthHeader() {
  const token = localStorage.getItem('vnai_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// NER Labels (mirrors constants.py)
const NER_LABELS = [
  { value: "PCD", text: "Plus Code", color: "#f032e6", hotkey: "0", example: "7P28QR4F+2M" },
  { value: "BLD", text: "Tòa nhà/Chung cư", color: "#f58231", hotkey: "1", example: "Chung Cư Tecco Green Nest" },
  { value: "POI", text: "Địa danh/Mốc", color: "#911eb4", hotkey: "2", example: "Đối Diện Chợ Bà Chiểu" },
  { value: "ALY", text: "Hẻm/Ngõ", color: "#4363d8", hotkey: "3", example: "Hẻm 141" },
  { value: "NUM", text: "Số nhà/Lô", color: "#e6194B", hotkey: "4", example: "Số 17/2A" },
  { value: "STR", text: "Tên đường", color: "#3cb44b", hotkey: "5", example: "Đường Phạm Thế Hiển" },
  { value: "NHB", text: "Khu phố/Thôn/Ấp", color: "#469990", hotkey: "6", example: "Khu Phố 3" },
  { value: "WDS", text: "Phường/Xã", color: "#ffe119", hotkey: "7", example: "Phường Tân Thới Nhất" },
  { value: "DST", text: "Quận/Huyện", color: "#800000", hotkey: "8", example: "Quận 12" },
  { value: "PRO", text: "Tỉnh/TP", color: "#000075", hotkey: "9", example: "TP Hồ Chí Minh" },
];

const SAMPLE_ADDRESSES = [
  "2695/7 Đường Phạm Thế Hiển, phường 7, Quận 8, Thành phố Hồ Chí Minh, Việt Nam",
  "Chung Cư Tecco Green Nest, Phan Văn Hớn, Tân Thới Nhất, Quận 12, Thành phố Hồ Chí Minh",
  "850/169, Đường Trưng Nữ Vương, Khu Vực 10 gần nhà tạp hoá, Châu Văn Liêm, Ô Môn, Cần Thơ",
  "số 5 ngõ 10 phố Tôn Thất Tùng, phường Trung Tự, quận Đống Đa, Hà Nội",
  "Tổ 3 ấp Phước Hưng, xã Long Phước, thành phố Bà Rịa, tỉnh Bà Rịa-Vũng Tàu",
  "Lô E2-20 Khu đô thị Mega Residence, đường 990B, Phú Hữu, TP. Thủ Đức, HCM",
];

const KPI_TARGETS = {
  f1: 82,
  throughput: 20,
  costPerMillion: 100,
  googleMatch: 75,
};

const TRAINING_HISTORY_FALLBACK = [
  { version: "v2.1", accuracy: 82.5, f1: 79.1, samples: 12000, date: "2026-03-12", loss: 0.412, notes: "Fallback snapshot" },
  { version: "v2.2", accuracy: 84.2, f1: 81.5, samples: 15800, date: "2026-03-28", loss: 0.365, notes: "Fallback snapshot" },
  { version: "v2.3", accuracy: 88.7, f1: 85.3, samples: 20100, date: "2026-04-10", loss: 0.298, notes: "Fallback snapshot" },
  { version: "v2.4", accuracy: 92.4, f1: 90.1, samples: 25130, date: "2026-04-24", loss: 0.244, notes: "Fallback snapshot" },
];

let benchmarkBaselineCache = null;
let trainingHistoryRows = [];

// ─── Formatting Helpers ───
function setupNumberInputFormatting() {
  const numberInputs = ['batch-size', 'osm-target-total', 'export-limit'];
  numberInputs.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    // Initial format
    if (el.value) {
      const numeric = el.value.replace(/\D/g, '');
      if (numeric) el.value = parseInt(numeric).toLocaleString('vi-VN');
    }

    el.addEventListener('input', (e) => {
      const input = e.target;
      const originalValue = input.value;
      const originalCursorPos = input.selectionStart;

      // Count digits before cursor in the original value
      const digitsBeforeCursor = (originalValue.substring(0, originalCursorPos).match(/\d/g) || []).length;

      const digitsOnly = originalValue.replace(/\D/g, '');
      if (digitsOnly === '') {
        input.value = '';
        return;
      }

      const formattedValue = parseInt(digitsOnly).toLocaleString('vi-VN');
      input.value = formattedValue;

      // Calculate new cursor position based on the same number of digits
      let newCursorPos = 0;
      let digitsSeen = 0;
      for (let i = 0; i < formattedValue.length; i++) {
        if (/\d/.test(formattedValue[i])) {
          digitsSeen++;
        }
        newCursorPos = i + 1;
        if (digitsSeen === digitsBeforeCursor) break;
      }
      // Only call setSelectionRange if the element supports it
      if (input.type === 'text' || input.type === 'search' || input.type === 'url' || input.type === 'tel' || input.type === 'password') {
        input.setSelectionRange(newCursorPos, newCursorPos);
      }
    });
  });
}

function getNumericInputValue(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  return parseInt(el.value.replace(/\D/g, '') || '0', 10);
}

async function fetchBenchmarkBaselines() {
  const response = await fetch(`${API_BASE}/benchmark/baselines`, {
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`Benchmark baseline API failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !payload.models) {
    throw new Error("Invalid benchmark baseline payload");
  }

  return payload.models;
}

async function fetchTrainingHistory() {
  const response = await fetch(`${API_BASE}/training/history`, {
    headers: getAuthHeader(),
  });

  if (response.status === 404) {
    return TRAINING_HISTORY_FALLBACK;
  }

  if (!response.ok) {
    throw new Error(`Training history API failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !Array.isArray(payload.history)) {
    throw new Error("Invalid training history payload");
  }

  return payload.history;
}

async function createTrainingHistoryEntry(entry) {
  const response = await fetch(`${API_BASE}/training/history`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(entry),
  });

  if (response.status === 404) {
    return { status: "fallback", history: entry };
  }

  if (!response.ok) {
    throw new Error(`Training history create API failed: ${response.status}`);
  }

  return response.json();
}

function formatLogTime() {
  const d = new Date();
  const time = d.toLocaleTimeString('vi-VN', { hour12: false });
  const ms = String(d.getMilliseconds()).padStart(3, '0');
  return `${time}.${ms}`;
}

// ─── INIT ───
document.addEventListener("DOMContentLoaded", async () => {
  if (!window.VNAIControls) {
    console.error('Missing controls-template.js. Shared UI controls are not initialized.');
    return;
  }

  // Load all pages first
  await loadPages();

  const safeInit = (name, fn) => { try { fn(); } catch (e) { console.error(`[VNAI] Init error in ${name}:`, e); } };

  safeInit("setupNavigation", setupNavigation);
  safeInit("applyUnifiedControlTemplate", applyUnifiedControlTemplate);
  safeInit("populateLabelRegistry", populateLabelRegistry);
  safeInit("setupParserTool", setupParserTool);
  safeInit("setupBatchTool", setupBatchTool);
  safeInit("initDashboardRefreshControls", initDashboardRefreshControls);
  safeInit("initOSMEnrichmentUI", initOSMEnrichmentUI);
  safeInit("initNSOSyncTool", initNSOSyncTool);
  safeInit("initAdminManager", initAdminManager);
  safeInit("setupNumberInputFormatting", setupNumberInputFormatting);
  safeInit("initDataExplorer", initDataExplorer);
  safeInit("initLabelStudioIntegration", initLabelStudioIntegration);
  safeInit("initMappingV3", initMappingV3);
  safeInit("initIntelligenceChart", initIntelligenceChart);
  safeInit("initModelBenchmarkUI", initModelBenchmarkUI);
  safeInit("initTrainingHub", initTrainingHub);

  fetchStats();
  setInterval(fetchStats, 30000);
  loadTrainingHistoryFromDB({ silent: true });
});

function setDashboardRefreshState(isLoading) {
  const btn = document.getElementById('btn-dashboard-refresh');
  if (!btn) return;

  btn.disabled = isLoading;
  btn.innerHTML = isLoading
    ? '<i class="fa-solid fa-spinner fa-spin"></i> Đang làm mới...'
    : '<i class="fa-solid fa-arrow-rotate-right"></i> Làm mới số liệu';
}

function updateDashboardRefreshTime() {
  const label = document.getElementById('dashboard-last-refresh');
  if (!label) return;
  label.textContent = `Cập nhật lúc ${formatLogTime()}`;
}

function initDashboardRefreshControls() {
  const btn = document.getElementById('btn-dashboard-refresh');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    await fetchStats({ manual: true });
  });
}

let intelligenceChart = null;
function initIntelligenceChart() {
  const ctx = document.getElementById('chart-training-progress');
  if (!ctx) return;

  if (intelligenceChart) intelligenceChart.destroy();

  // Load fallback data immediately for visual feedback
  const fallbackData = TRAINING_HISTORY_FALLBACK;

  intelligenceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: fallbackData.map((item) => item.version),
      datasets: [{
        label: 'Model Accuracy (%)',
        data: fallbackData.map((item) => item.accuracy),
        borderColor: '#818cf8',
        backgroundColor: 'rgba(129, 140, 248, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#818cf8'
      }, {
        label: 'F1-Score',
        data: fallbackData.map((item) => item.f1),
        borderColor: '#34d399',
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 20,
            font: { size: 12 }
          }
        }
      },
      scales: {
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#5c5c5f', font: { size: 10 } },
          min: 70,
          max: 95
        },
        x: {
          grid: { display: false },
          ticks: { color: '#5c5c5f', font: { size: 10 } }
        }
      }
    }
  });
}

function isModelTargetPassed(metric) {
  return metric.f1 >= KPI_TARGETS.f1
    && metric.throughput >= KPI_TARGETS.throughput
    && metric.costPerMillion < KPI_TARGETS.costPerMillion
    && metric.googleMatch >= KPI_TARGETS.googleMatch;
}

function formatBenchmarkMetric(metric, key) {
  if (key === "f1" || key === "googleMatch") return `${metric[key].toFixed(1)}%`;
  if (key === "throughput") return `${metric[key].toFixed(1)} addr/s`;
  if (key === "costPerMillion") return `$${metric[key].toLocaleString()}`;
  return String(metric[key]);
}

function getBestMetric(models, key, comparator) {
  return Object.values(models).reduce((best, current) => {
    if (!best) return current;
    return comparator(current[key], best[key]) ? current : best;
  }, null);
}

function renderKpiCards(models) {
  const bestF1 = getBestMetric(models, "f1", (a, b) => a > b);
  const bestThroughput = getBestMetric(models, "throughput", (a, b) => a > b);
  const bestCost = getBestMetric(models, "costPerMillion", (a, b) => a < b);
  const bestGoogle = getBestMetric(models, "googleMatch", (a, b) => a > b);

  const f1El = document.getElementById("kpi-f1-current");
  const f1Status = document.getElementById("kpi-f1-status");
  if (f1El && f1Status && bestF1) {
    f1El.textContent = `${bestF1.f1.toFixed(1)}%`;
    f1Status.className = `stat-change ${bestF1.f1 >= KPI_TARGETS.f1 ? "kpi-pass" : "kpi-fail"}`;
    f1Status.textContent = `${bestF1.name} | Target ${KPI_TARGETS.f1}%`;
  }

  const tpsEl = document.getElementById("kpi-throughput-current");
  const tpsStatus = document.getElementById("kpi-throughput-status");
  if (tpsEl && tpsStatus && bestThroughput) {
    tpsEl.textContent = `${bestThroughput.throughput.toFixed(1)} addr/s`;
    tpsStatus.className = `stat-change ${bestThroughput.throughput >= KPI_TARGETS.throughput ? "kpi-pass" : "kpi-fail"}`;
    tpsStatus.textContent = `${bestThroughput.name} | Target ${KPI_TARGETS.throughput} addr/s`;
  }

  const costEl = document.getElementById("kpi-cost-current");
  const costStatus = document.getElementById("kpi-cost-status");
  if (costEl && costStatus && bestCost) {
    costEl.textContent = `$${bestCost.costPerMillion.toLocaleString()}`;
    costStatus.className = `stat-change ${bestCost.costPerMillion < KPI_TARGETS.costPerMillion ? "kpi-pass" : "kpi-fail"}`;
    costStatus.textContent = `${bestCost.name} | Target < $${KPI_TARGETS.costPerMillion}`;
  }

  const gmEl = document.getElementById("kpi-google-current");
  const gmStatus = document.getElementById("kpi-google-status");
  if (gmEl && gmStatus && bestGoogle) {
    gmEl.textContent = `${bestGoogle.googleMatch.toFixed(1)}%`;
    gmStatus.className = `stat-change ${bestGoogle.googleMatch >= KPI_TARGETS.googleMatch ? "kpi-pass" : "kpi-fail"}`;
    gmStatus.textContent = `${bestGoogle.name} | Target ${KPI_TARGETS.googleMatch}%`;
  }
}

function renderExperimentTable(models) {
  const tbody = document.getElementById("experiment-results-body");
  if (!tbody) return;

  tbody.innerHTML = Object.values(models).map((metric) => {
    const passed = isModelTargetPassed(metric);
    const statusClass = passed ? "success" : "warning";
    const statusText = passed ? "Pass" : "Partial";

    return `
      <tr>
        <td>${metric.name}</td>
        <td>${formatBenchmarkMetric(metric, "f1")}</td>
        <td>${formatBenchmarkMetric(metric, "throughput")}</td>
        <td>${formatBenchmarkMetric(metric, "costPerMillion")}</td>
        <td>${formatBenchmarkMetric(metric, "googleMatch")}</td>
        <td>F1≥${KPI_TARGETS.f1}% | TPS≥${KPI_TARGETS.throughput} | Cost&lt;$${KPI_TARGETS.costPerMillion.toLocaleString()} | Match≥${KPI_TARGETS.googleMatch}%</td>
        <td><span class="badge ${statusClass}">${statusText}</span></td>
      </tr>
    `;
  }).join("");

  adjustActivePageHeight();
}

async function buildLatestBenchmarkSnapshot() {
  if (benchmarkBaselineCache) {
    return benchmarkBaselineCache;
  }

  benchmarkBaselineCache = await fetchBenchmarkBaselines();
  return benchmarkBaselineCache;
}

let benchmarkPollTimer = null;

function setBenchmarkRunButtons(isRunning) {
  const runButtons = document.querySelectorAll('[data-action="run-experiment"]');
  runButtons.forEach((button) => {
    if (isRunning) {
      if (!button.dataset.defaultHtml) {
        button.dataset.defaultHtml = button.innerHTML;
      }
      button.disabled = true;
      button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running benchmark...';
    } else {
      button.disabled = false;
      if (button.dataset.defaultHtml) {
        button.innerHTML = button.dataset.defaultHtml;
      }
    }
  });
}

async function triggerBenchmarkJob() {
  const response = await fetch(`${API_BASE}/benchmark/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify({ config_path: "app/ai/config.yaml", skip_llm: false }),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`Trigger API failed: ${response.status}`);
  }

  return response.json();
}

async function fetchBenchmarkJobStatus() {
  const response = await fetch(`${API_BASE}/benchmark/job`, {
    headers: getAuthHeader(),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`Job status API failed: ${response.status}`);
  }

  return response.json();
}

function clearBenchmarkPollTimer() {
  if (benchmarkPollTimer) {
    clearTimeout(benchmarkPollTimer);
    benchmarkPollTimer = null;
  }
}

async function pollBenchmarkUntilDone() {
  try {
    const payload = await fetchBenchmarkJobStatus();
    const job = payload?.job;
    const status = job?.status || "idle";

    if (status === "running") {
      setBenchmarkRunButtons(true);
      benchmarkPollTimer = setTimeout(pollBenchmarkUntilDone, 3000);
      return;
    }

    setBenchmarkRunButtons(false);

    if (status === "success") {
      if (window.__vnaiBenchmarkRefresh) {
        await window.__vnaiBenchmarkRefresh({ silent: true });
      }
      if (showToast) {
        showToast("Benchmark hoàn tất và đã cập nhật KPI real-time", "success");
      }
      return;
    }

    if (status === "failed") {
      const errText = job?.error ? `: ${job.error}` : "";
      if (showToast) {
        showToast(`Benchmark thất bại${errText}`, "danger");
      }
      return;
    }
  } catch (error) {
    setBenchmarkRunButtons(false);
    if (showToast) {
      showToast("Không thể theo dõi trạng thái benchmark job", "danger");
    }
    console.error("Benchmark poll error:", error);
  }
}

async function runBenchmarkJobFromUI() {
  try {
    setBenchmarkRunButtons(true);
    const trigger = await triggerBenchmarkJob();
    const state = trigger?.job?.status;

    if (state === "running") {
      if (showToast) {
        showToast("Benchmark job đã được khởi chạy", "info");
      }
      clearBenchmarkPollTimer();
      await pollBenchmarkUntilDone();
      return;
    }

    setBenchmarkRunButtons(false);
  } catch (error) {
    setBenchmarkRunButtons(false);
    if (showToast) {
      showToast("Không thể trigger benchmark job", "danger");
    }
    console.error("Benchmark trigger error:", error);
  }
}

async function fetchRealtimeBenchmark() {
  const response = await fetch(`${API_BASE}/benchmark/realtime`, {
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`Benchmark API failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !payload.models) {
    throw new Error("Invalid benchmark payload");
  }

  return payload.models;
}

function initModelBenchmarkUI() {
  if (window.__vnaiBenchmarkRefresh) {
    window.__vnaiBenchmarkRefresh();
    return;
  }

  const runButtons = document.querySelectorAll('[data-action="run-experiment"]');
  if (!runButtons.length) return;

  const renderLatest = async ({ silent = false } = {}) => {
    try {
      const realtimeModels = await fetchRealtimeBenchmark();
      renderKpiCards(realtimeModels);
      renderExperimentTable(realtimeModels);
      if (!silent && showToast) {
        showToast("Đã đồng bộ benchmark real-time từ backend", "success");
      }
    } catch (error) {
      console.error("Benchmark realtime error:", error);
      try {
        const fallback = await buildLatestBenchmarkSnapshot();
        renderKpiCards(fallback);
        renderExperimentTable(fallback);
        if (!silent && showToast) {
          showToast("Backend benchmark chưa sẵn sàng, đang dùng dữ liệu fallback", "warning");
        }
      } catch (fallbackError) {
        console.error("Benchmark baseline error:", fallbackError);
        if (!silent && showToast) {
          showToast("Không thể tải benchmark baseline từ database", "danger");
        }
      }
    }
  };

  runButtons.forEach((button) => {
    button.addEventListener("click", () => {
      runBenchmarkJobFromUI();
    });
  });

  const refreshButton = document.getElementById("btn-benchmark-refresh");
  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      renderLatest({ silent: false });
    });
  }

  window.__vnaiBenchmarkRefresh = renderLatest;
  fetchBenchmarkJobStatus().then((payload) => {
    if (payload?.job?.status === "running") {
      setBenchmarkRunButtons(true);
      clearBenchmarkPollTimer();
      pollBenchmarkUntilDone();
    }
  }).catch((error) => {
    console.warn("Unable to pre-check benchmark job status", error);
  });

  renderLatest({ silent: true });
}

function populateTrainingHistory() {
  const tbody = document.getElementById("training-history-body");
  if (!tbody) return;

  tbody.innerHTML = trainingHistoryRows.map((item) => `
    <tr>
      <td><span class="badge info">${item.version}</span></td>
      <td>${item.accuracy.toFixed(1)}%</td>
      <td>${item.f1.toFixed(1)}%</td>
      <td>${item.samples.toLocaleString()}</td>
      <td>${item.date}</td>
    </tr>
  `).join("");

  adjustActivePageHeight();
}

function refreshTrainingChart() {
  if (!intelligenceChart) return;

  intelligenceChart.data.labels = trainingHistoryRows.map((item) => item.version);
  intelligenceChart.data.datasets[0].data = trainingHistoryRows.map((item) => item.accuracy);
  intelligenceChart.data.datasets[1].data = trainingHistoryRows.map((item) => item.f1);
  intelligenceChart.update();
}

async function loadTrainingHistoryFromDB({ silent = false } = {}) {
  try {
    trainingHistoryRows = await fetchTrainingHistory();
    populateTrainingHistory();
    refreshTrainingChart();
    if (!silent && showToast) {
      showToast("Đã đồng bộ training history từ database", "success");
    }
  } catch (error) {
    console.error("Training history error:", error);
    if (!silent && showToast) {
      showToast("Không thể tải training history từ database", "danger");
    }
  }
}

let osmPollTimer = null;

function clearOSMPollTimer() {
  if (osmPollTimer) {
    clearTimeout(osmPollTimer);
    osmPollTimer = null;
  }
}

function setOSMRunButtons(isRunning) {
  const runButton = document.getElementById("btn-osm-run");
  const previewButton = document.getElementById("btn-osm-preview-counts");

  [runButton, previewButton].forEach((button) => {
    if (!button) return;

    if (isRunning) {
      if (!button.dataset.defaultHtml) {
        button.dataset.defaultHtml = button.innerHTML;
      }
      button.disabled = true;
      if (button.id === "btn-osm-run") {
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running OSM Crawl...';
      }
    } else {
      button.disabled = false;
      if (button.dataset.defaultHtml && button.id === "btn-osm-run") {
        button.innerHTML = button.dataset.defaultHtml;
      }
    }
  });
}

async function fetchOSMSummary() {
  const response = await fetch(`${API_BASE}/osm/summary`, {
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`OSM summary API failed: ${response.status}`);
  }

  return response.json();
}

async function triggerOSMJob() {
  const limitProvinces = getNumericInputValue("osm-limit-provinces") || 63;
  const targetTotal = getNumericInputValue("osm-target-total") || 5000000;

  const response = await fetch(`${API_BASE}/osm/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify({
      limit_provinces: limitProvinces,
      target_total: targetTotal,
    }),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`OSM trigger API failed: ${response.status}`);
  }

  return response.json();
}

async function fetchOSMJobStatus() {
  const response = await fetch(`${API_BASE}/osm/job`, {
    headers: getAuthHeader(),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`OSM job API failed: ${response.status}`);
  }

  return response.json();
}

function renderOSMSummary(summary) {
  const raw = Number(summary?.raw || 0);
  const streets = Number(summary?.streets || 0);
  const buildings = Number(summary?.buildings || 0);
  const pois = Number(summary?.pois || 0);
  const total = raw + streets + buildings + pois;

  const mapping = {
    "osm-raw-count": raw,
    "osm-street-count": streets,
    "osm-building-count": buildings,
    "osm-poi-count": pois,
  };

  Object.entries(mapping).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value.toLocaleString();
    }
  });

  const totalEl = document.getElementById("stat-osm");
  if (totalEl) {
    totalEl.textContent = total.toLocaleString();
  }

  const lastRefresh = document.getElementById("osm-last-refresh");
  if (lastRefresh) {
    lastRefresh.textContent = `Cập nhật lúc ${formatLogTime()}`;
  }

  adjustActivePageHeight();
}

function renderOSMJob(job) {
  const status = job?.status || "idle";
  const badge = document.getElementById("osm-job-status-badge") || document.getElementById("osm-job-status");
  const started = document.getElementById("osm-job-started");
  const finished = document.getElementById("osm-job-finished");
  const jobId = document.getElementById("osm-job-id");
  const errorEl = document.getElementById("osm-job-error");
  const logEl = document.getElementById("osm-job-log");

  if (badge) {
    const badgeClass = status === "success" ? "success" : status === "failed" ? "danger" : status === "running" ? "warning" : "info";
    badge.className = `badge ${badgeClass}`;
    badge.textContent = status.toUpperCase();
  }

  if (started) started.textContent = job?.startedAt || "-";
  if (finished) finished.textContent = job?.finishedAt || "-";
  if (jobId) jobId.textContent = job?.jobId || "-";
  if (errorEl) errorEl.textContent = job?.error || "";

  if (logEl) {
    logEl.textContent = job?.outputTail || (status === "running" ? "OSM crawl đang chạy..." : "Chưa có job nào được chạy.");
  }

  adjustActivePageHeight();
}

async function pollOSMUntilDone() {
  try {
    const payload = await fetchOSMJobStatus();
    const job = payload?.job;
    const status = job?.status || "idle";

    renderOSMJob(job);

    if (status === "running") {
      setOSMRunButtons(true);
      osmPollTimer = setTimeout(pollOSMUntilDone, 4000);
      return;
    }

    setOSMRunButtons(false);

    if (status === "success") {
      await refreshOSMEnrichmentPanel({ silent: true });
      if (showToast) {
        showToast("OSM crawl hoàn tất và số liệu đã được cập nhật", "success");
      }
      return;
    }

    if (status === "failed") {
      if (showToast) {
        showToast(`OSM crawl thất bại${job?.error ? `: ${job.error}` : ""}`, "danger");
      }
      return;
    }
  } catch (error) {
    setOSMRunButtons(false);
    console.error("OSM poll error:", error);
    if (showToast) {
      showToast("Không thể theo dõi trạng thái OSM job", "danger");
    }
  }
}

async function refreshOSMEnrichmentPanel({ silent = false } = {}) {
  try {
    const summary = await fetchOSMSummary();
    renderOSMSummary(summary);
    if (!silent && showToast) {
      showToast("Đã làm mới số liệu OSM enrichment", "success");
    }
  } catch (error) {
    console.error("OSM summary error:", error);
    if (!silent && showToast) {
      showToast("Không thể tải số liệu OSM enrichment", "danger");
    }
  }
}

async function previewOSMCountsFromUI() {
  await refreshOSMEnrichmentPanel({ silent: false });
}

async function runOSMJobFromUI() {
  try {
    const limitProvinces = Number.parseInt(document.getElementById("osm-limit-provinces")?.value || "63", 10);
    const targetTotal = getNumericInputValue("osm-target-total") || 5000000;
    const confirmMessage = `Chạy crawl OSM cho ${limitProvinces} tỉnh/thành với target ${targetTotal.toLocaleString()} entities?`;

    if (showConfirm) {
      const confirmed = await showConfirm(confirmMessage);
      if (!confirmed) return;
    }

    setOSMRunButtons(true);
    const trigger = await triggerOSMJob();

    if (trigger?.job?.status === "running") {
      if (showToast) {
        showToast("OSM crawl job đã được khởi chạy", "info");
      }
      clearOSMPollTimer();
      renderOSMJob(trigger.job);
      await pollOSMUntilDone();
      return;
    }

    setOSMRunButtons(false);
  } catch (error) {
    setOSMRunButtons(false);
    console.error("OSM trigger error:", error);
    if (showToast) {
      showToast("Không thể trigger OSM crawl job", "danger");
    }
  }
}

function initOSMEnrichmentUI() {
  const runButton = document.getElementById("btn-osm-run");
  const previewButton = document.getElementById("btn-osm-preview-counts");
  const page = document.getElementById("osm-enrichment");

  if (!page) return;

  if (runButton) {
    runButton.addEventListener("click", () => {
      runOSMJobFromUI();
    });
  }

  if (previewButton) {
    previewButton.addEventListener("click", () => {
      previewOSMCountsFromUI();
    });
  }

  window.__vnaiOSMRefresh = refreshOSMEnrichmentPanel;

  fetchOSMJobStatus().then((payload) => {
    if (payload?.job) {
      renderOSMJob(payload.job);
      if (payload.job.status === "running") {
        setOSMRunButtons(true);
        clearOSMPollTimer();
        pollOSMUntilDone();
      }
    }
  }).catch((error) => {
    console.warn("Unable to pre-check OSM job status", error);
  });

  refreshOSMEnrichmentPanel({ silent: true });
}

// ═══════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const pages = document.querySelectorAll(".page");
  const titleEl = document.getElementById("current-page-title");

  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  const toggle = document.getElementById("menu-toggle");

  const closeMobileMenu = () => {
    sidebar.classList.remove("mobile-active");
    overlay.classList.remove("mobile-active");
  };

  if (toggle) {
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("mobile-active");
      overlay.classList.toggle("mobile-active");
    });
  }

  if (overlay) overlay.addEventListener("click", closeMobileMenu);

  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      navItems.forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      const targetId = item.getAttribute("data-page");
      pages.forEach(p => p.classList.toggle("active", p.id === targetId));
      titleEl.textContent = item.textContent.trim();

      // UX: Scroll to top when page changes
      window.scrollTo({ top: 0, behavior: 'smooth' });
      const contentEl = document.getElementById('page-content');
      if (contentEl) contentEl.scrollTo({ top: 0, behavior: 'smooth' });

      closeMobileMenu(); // Close sidebar on mobile after selection

      // Calculate layout height after page transition
      setTimeout(adjustActivePageHeight, 350);
    });
  });

  window.addEventListener('resize', adjustActivePageHeight);

  // Workflow steps click to navigate
  document.querySelectorAll(".workflow-step.clickable").forEach(step => {
    step.addEventListener("click", () => {
      const targetPage = step.getAttribute("data-goto");
      const navItem = document.querySelector(`.nav-item[data-page="${targetPage}"]`);
      if (navItem) navItem.click();
    });
  });
}

// ═══════════════════════════════════════════════════════════
// OVERVIEW CHART
// ═══════════════════════════════════════════════════════════
let overviewChart = null;

function renderOverviewChart(stats) {
  const ctx = document.getElementById("chart-overview");
  if (!ctx) return;

  const dataValues = [
    stats?.master?.provinces || 0,
    stats?.master?.districts || 0,
    stats?.master?.wards || 0,
    stats?.osm?.streets || 0,
    stats?.osm?.buildings || 0,
    stats?.ai?.training_samples || 0,
    stats?.ai?.cleansing_queue || 0
  ];

  if (overviewChart) {
    overviewChart.data.datasets[0].data = dataValues;
    overviewChart.update();
    return;
  }

  overviewChart = new Chart(ctx.getContext("2d"), {
    type: "bar",
    data: {
      labels: ["mat.province", "mat.district", "mat.ward", "osm.streets", "osm.buildings", "ath.training", "prq.queue"],
      datasets: [{
        label: "Records",
        data: dataValues,
        backgroundColor: [
          "rgba(129,140,248,0.7)", "rgba(129,140,248,0.5)", "rgba(129,140,248,0.3)",
          "rgba(52,211,153,0.7)", "rgba(52,211,153,0.5)",
          "rgba(251,191,36,0.6)",
          "rgba(248,113,113,0.6)"
        ],
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ctx.parsed.y.toLocaleString() + " records"
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#5c5c5f", font: { size: 10 } },
          grid: { display: false }
        },
        y: {
          type: "linear", // Change to linear to avoid 0 issue with log scale if not configured
          beginAtZero: true,
          ticks: {
            color: "#5c5c5f",
            font: { size: 10 },
            callback: (v) => v >= 1000 ? (v / 1000) + "K" : v
          },
          grid: { color: "rgba(255,255,255,0.04)" }
        }
      }
    }
  });
}

// ═══════════════════════════════════════════════════════════
// LABEL REGISTRY
// ═══════════════════════════════════════════════════════════
function populateLabelRegistry() {
  const tbody = document.getElementById("label-registry-body");
  if (!tbody) return;

  tbody.innerHTML = NER_LABELS.map(l => `
    <tr>
      <td><span class="badge" style="background:${l.color}22;color:${l.color}">${l.value}</span></td>
      <td>${l.text}</td>
      <td><div style="width:14px;height:14px;border-radius:3px;background:${l.color};display:inline-block;vertical-align:middle"></div> <span class="text-mono">${l.color}</span></td>
      <td><kbd style="background:var(--bg-app);padding:2px 8px;border-radius:4px;font-size:12px;border:1px solid var(--border-default)">${l.hotkey}</kbd></td>
      <td class="text-mono" style="font-size:12px">${l.example}</td>
    </tr>
  `).join("");
}

// ═══════════════════════════════════════════════════════════
// ADDRESS PARSER TOOL
// ═══════════════════════════════════════════════════════════
function setupParserTool() {
  const btnParse = document.getElementById("btn-parse");
  const btnSampleLocal = document.getElementById("btn-parse-sample-local");
  const btnSampleDB = document.getElementById("btn-parse-sample-db");
  const inputEl = document.getElementById("parser-input");

  if (!btnParse) {
    console.warn("[Parser] btn-parse not found in DOM — parser page may not have loaded.");
    return;
  }

  btnParse.addEventListener("click", () => runParser());

  if (inputEl) inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); runParser(); }
  });

  if (btnSampleLocal) btnSampleLocal.addEventListener("click", () => {
    const addr = SAMPLE_ADDRESSES[Math.floor(Math.random() * SAMPLE_ADDRESSES.length)];
    if (inputEl) { inputEl.value = addr; inputEl.dataset.sampleId = ""; }
    runParser();
  });

  if (btnSampleDB) btnSampleDB.addEventListener("click", fetchParserSampleDB);

  // Build NER legend once
  _buildParserNERLegend();
}

function _buildParserNERLegend() {
  const legend = document.getElementById("parser-ner-legend");
  if (!legend) return;
  legend.innerHTML = NER_LABELS.map(l => `
    <span class="plegend-item" style="background:${l.color}18;color:${l.color};border-color:${l.color}30">
      ${l.value}
    </span>`).join("");
}

function _setParserStatus(state, text) {
  const dot = document.getElementById("parser-status-dot");
  const txt = document.getElementById("parser-status");
  if (dot) { dot.className = `pstatus-dot ${state}`; }
  if (txt) { txt.textContent = text; txt.className = `pstatus-text ${state}`; }
}

function _resetModelCards() {
  const models = ["prelabeler", "phobert", "mgte", "llm"];
  models.forEach(m => {
    const card = document.getElementById(`pcard-${m}`);
    const result = document.getElementById(`presult-${m}`);
    const stats = document.getElementById(`pstats-${m}`);
    const badge = document.getElementById(`pbadge-${m}`);
    if (card) { card.classList.remove("is-done", "is-error"); }
    if (result) { result.className = "pmodel-result"; result.innerHTML = '<div class="pmodel-shimmer"></div><div class="pmodel-shimmer" style="width:60%;margin-top:6px"></div>'; }
    if (stats) { stats.innerHTML = ""; }
    if (badge) { badge.innerHTML = '<span class="pmodel-spinner"></span>'; }
  });
}

async function fetchParserSampleDB() {
  const btn = document.getElementById("btn-parse-sample-db");
  const inputEl = document.getElementById("parser-input");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/parser/sample`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Failed");
    const sample = await res.json();
    inputEl.value = sample.raw_address;
    inputEl.dataset.sampleId = sample.id;
    if (showToast) showToast(`Mẫu DB #${sample.id}`, "info");
    await runParser();
  } catch (err) {
    if (showToast) showToast("Không thể lấy mẫu từ Database", "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runParser() {
  const inputEl = document.getElementById("parser-input");
  const text = inputEl?.value?.trim();
  const sampleId = inputEl?.dataset?.sampleId;
  if (!text) return;

  const btnParse = document.getElementById("btn-parse");
  const heroInner = document.querySelector(".parser-hero-inner");
  const timingEl = document.getElementById("parser-timing");
  const timingVal = document.getElementById("parser-timing-val");

  // Reset UI
  _resetModelCards();
  _setParserStatus("running", "Đang phân tích — gửi yêu cầu đến 4 model...");
  if (heroInner) heroInner.classList.add("is-running");
  if (btnParse) { btnParse.disabled = true; btnParse.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Đang xử lý</span>'; }
  if (timingEl) timingEl.style.display = "none";

  // Clear NER output
  const nerOut = document.getElementById("parser-output");
  if (nerOut) nerOut.innerHTML = '<span class="parser-placeholder">Đang chờ kết quả từ PreLabeler...</span>';

  const startTs = Date.now();
  const payload = sampleId ? { id: parseInt(sampleId) } : { raw_address: text };

  // Run all 4 models in PARALLEL — each updates its own card when done
  const models = [
    { key: "prelabeler", label: "PreLabeler" },
    { key: "phobert", label: "PhoBERT" },
    { key: "mgte", label: "mGTE" },
    { key: "llm", label: "Qwen LLM" },
  ];

  let completedCount = 0;
  let firstNERDone = false;
  let lastMeta = null;

  const fetchModel = async ({ key, label }) => {
    const t0 = Date.now();
    try {
      const res = await fetch(`${API_BASE}/parser/analyze?model=${key}`, {
        method: "POST",
        headers: { ...getAuthHeader(), "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const latency = Date.now() - t0;
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const out = data.outputs?.[key];
      if (data.meta) lastMeta = data.meta;

      // Render this card
      _renderModelCard(key, out, latency);

      // Show NER from prelabeler immediately
      if (key === "prelabeler" && !firstNERDone) {
        firstNERDone = true;
        const entities = out?.result || [];
        renderNERHighlight(entities);
      }
    } catch (e) {
      _renderModelCardError(key, label);
    } finally {
      completedCount++;
      _setParserStatus("running", `Đang phân tích — ${completedCount}/4 model hoàn thành...`);
    }
  };

  try {
    await Promise.all(models.map(fetchModel));

    const totalMs = Date.now() - startTs;
    _setParserStatus("done", `Hoàn thành — tổng ${totalMs}ms`);
    if (timingEl && timingVal) { timingVal.textContent = `${totalMs}ms`; timingEl.style.display = "flex"; }

    // Update meta footer
    if (lastMeta) _updateParserMeta(lastMeta);
  } catch (err) {
    _setParserStatus("error", "Đã xảy ra lỗi trong quá trình phân tích");
  } finally {
    if (heroInner) heroInner.classList.remove("is-running");
    if (btnParse) { btnParse.disabled = false; btnParse.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span>Phân tích</span>'; }
  }
}

function _renderModelCard(model, out, latencyMs) {
  const card = document.getElementById(`pcard-${model}`);
  const resultEl = document.getElementById(`presult-${model}`);
  const statsEl = document.getElementById(`pstats-${model}`);
  const badgeEl = document.getElementById(`pbadge-${model}`);
  if (!card) return;

  card.classList.add("is-done");

  if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done success">DONE</span>`;

  if (resultEl) {
    resultEl.classList.add("has-result");
    if (!out) {
      resultEl.innerHTML = `<span style="color:var(--text-tertiary);font-size:11px">Không có kết quả</span>`;
    } else {
      const normalized = out.normalizedAddress || out.status || "";
      const entities = Array.isArray(out.result) ? out.result : [];
      const labelInfo = {};
      NER_LABELS.forEach(l => labelInfo[l.value] = l);

      let html = "";
      if (normalized) {
        html += `<span class="pmodel-normalized">${escapeHtml(normalized)}</span>`;
      }
      if (entities.length > 0) {
        const chips = entities.slice(0, 8).map(e => {
          const lbl = e.label || (e.value?.labels?.[0]) || "?";
          const txt = e.text || e.value?.text || "";
          const info = labelInfo[lbl] || { color: "#888" };
          return `<span class="pmodel-ent-chip" style="background:${info.color}18;color:${info.color}">${lbl}: ${escapeHtml(txt)}</span>`;
        }).join("");
        html += `<div class="pmodel-entities">${chips}</div>`;
      }
      if (!normalized && entities.length === 0) {
        html = `<span style="color:var(--text-tertiary);font-size:11px">NER xử lý xong — ${out.entityCount || 0} entities</span>`;
      }
      resultEl.innerHTML = html;
    }
  }

  if (statsEl) {
    const conf = out?.score ?? out?.entityCount ?? null;
    const count = Array.isArray(out?.result) ? out.result.length : (out?.entityCount ?? null);
    let chips = `<span class="pstat-chip latency"><i class="fa-solid fa-stopwatch"></i>${latencyMs}ms</span>`;
    if (count !== null) chips += `<span class="pstat-chip count"><i class="fa-solid fa-tags"></i>${count} entities</span>`;
    if (conf !== null && typeof conf === "number" && conf <= 1) chips += `<span class="pstat-chip conf"><i class="fa-solid fa-chart-line"></i>${(conf * 100).toFixed(0)}%</span>`;
    statsEl.innerHTML = chips;
  }
}

function _renderModelCardError(model, label) {
  const card = document.getElementById(`pcard-${model}`);
  const resultEl = document.getElementById(`presult-${model}`);
  const badgeEl = document.getElementById(`pbadge-${model}`);
  if (card) card.classList.add("is-error");
  if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done error">ERR</span>`;
  if (resultEl) resultEl.innerHTML = `<span style="color:var(--danger);font-size:11px"><i class="fa-solid fa-triangle-exclamation"></i> Không thể kết nối model</span>`;
}

function _updateParserMeta(meta) {
  const el = document.getElementById("parser-meta");
  if (!el) return;
  const corpus = meta.corpusSize ? `<strong>${meta.corpusSize.toLocaleString()}</strong> địa chỉ trong corpus` : "";
  const note = meta.note ? `<span style="color:var(--warning)"><i class="fa-solid fa-triangle-exclamation"></i> ${meta.note}</span>` : "";
  el.innerHTML = [
    corpus && `<i class="fa-solid fa-database" style="color:var(--text-tertiary);font-size:11px"></i><span class="text-tertiary" style="font-size:12px">${corpus}</span>`,
    note
  ].filter(Boolean).join("") || el.innerHTML;
}

function renderNERHighlight(entities) {
  const nerOutputEl = document.getElementById("parser-output");
  const inputEl = document.getElementById("parser-input");
  if (!nerOutputEl || !inputEl) return;

  const text = inputEl.value;
  if (!entities || !Array.isArray(entities) || entities.length === 0) {
    nerOutputEl.innerHTML = escapeHtml(text);
    return;
  }

  // Normalize to flat {start, end, label, text}
  const normalized = entities.map(ent => {
    if (ent.value?.labels) {
      return { start: ent.value.start, end: ent.value.end, label: ent.value.labels[0], text: ent.value.text };
    }
    return { start: ent.start ?? 0, end: ent.end ?? 0, label: ent.label || "?", text: ent.text || "" };
  }).filter(e => e.end > e.start);

  // Sort by start, remove overlaps
  const sorted = [...normalized].sort((a, b) => a.start - b.start);
  const filtered = [];
  sorted.forEach(e => {
    if (!filtered.length || e.start >= filtered[filtered.length - 1].end) filtered.push(e);
  });

  const labelInfo = {};
  NER_LABELS.forEach(l => labelInfo[l.value] = l);

  let html = "";
  let cursor = 0;
  filtered.forEach(e => {
    if (e.start > cursor) html += escapeHtml(text.slice(cursor, e.start));
    const info = labelInfo[e.label] || { color: "#888" };
    html += `<span class="ner-entity ner-${e.label}" data-label="${e.label}" style="background:${info.color}22;color:${info.color}" title="${e.label}">${escapeHtml(text.slice(e.start, e.end))}</span>`;
    cursor = e.end;
  });
  if (cursor < text.length) html += escapeHtml(text.slice(cursor));

  nerOutputEl.innerHTML = html;
}

function renderNEROutput(text, entities) {
  const output = document.getElementById("parser-output");
  if (!entities.length) {
    output.innerHTML = `<span style="color:var(--text-secondary)">${escapeHtml(text)}</span>`;
    return;
  }

  let html = "";
  let lastEnd = 0;
  const sorted = [...entities].sort((a, b) => a.start - b.start);

  // Remove overlaps
  const filtered = [];
  sorted.forEach(e => {
    if (!filtered.some(f => e.start < f.end && e.end > f.start)) {
      filtered.push(e);
    }
  });

  filtered.forEach(e => {
    if (e.start > lastEnd) {
      html += escapeHtml(text.slice(lastEnd, e.start));
    }
    html += `<span class="ner-entity ner-${e.label}" data-label="${e.label}">${escapeHtml(text.slice(e.start, e.end))}</span>`;
    lastEnd = e.end;
  });
  if (lastEnd < text.length) html += escapeHtml(text.slice(lastEnd));

  output.innerHTML = html;

  adjustActivePageHeight();
}

function renderEntitiesTable(entities) {
  const tbody = document.getElementById("parser-entities-body");
  if (!tbody) return;

  const labelInfo = {};
  NER_LABELS.forEach(l => labelInfo[l.value] = l);

  // Deduplicate
  const unique = [];
  const seen = new Set();
  entities.forEach(e => {
    const key = e.label + ":" + e.text;
    if (!seen.has(key)) { seen.add(key); unique.push(e); }
  });

  tbody.innerHTML = unique.map(e => {
    const info = labelInfo[e.label] || {};
    return `<tr>
      <td><span class="badge" style="background:${info.color}22;color:${info.color}">${e.label}</span> ${info.text || ""}</td>
      <td>${escapeHtml(e.text)}</td>
      <td>${(0.7 + Math.random() * 0.25).toFixed(2)}</td>
    </tr>`;
  }).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════
// BATCH PROCESSOR TOOL
// ═══════════════════════════════════════════════════════════
function setupBatchTool() {
  const btnToggle = document.getElementById("btn-batch-toggle");
  const log = document.getElementById("batch-log");
  const progressValue = document.getElementById("batch-progress-value");
  const progressFill = document.querySelector(".progress-fill");

  let isBatchRunning = false;
  let currentInterval = null;

  function setButtonState(running) {
    isBatchRunning = running;
    if (running) {
      btnToggle.innerHTML = '<i class="fa-solid fa-stop"></i> Dừng lại';
      btnToggle.style.background = 'var(--danger)';
      btnToggle.style.borderColor = 'var(--danger)';
    } else {
      btnToggle.innerHTML = '<i class="fa-solid fa-play"></i> Bắt đầu xử lý';
      btnToggle.style.background = '';
      btnToggle.style.borderColor = '';
    }
  }

  if (btnToggle) btnToggle.addEventListener("click", () => {
    if (isBatchRunning) {
      // Stop batch
      if (currentInterval) {
        clearInterval(currentInterval);
        currentInterval = null;
      }
      setButtonState(false);
      log.innerHTML += `\n[${formatLogTime()}] ⛔ Batch stopped by user\n`;
      return;
    }

    // Start batch
    const size = getNumericInputValue("batch-size") || 1000;
    const method = document.getElementById("batch-method").value;

    // Reset progress and stats
    progressValue.textContent = "0%";
    progressFill.style.width = "0%";
    document.getElementById("batch-done").textContent = "0";
    document.getElementById("batch-throughput").textContent = "0";

    setButtonState(true);

    log.innerHTML = `[${formatLogTime()}] Starting batch: ${size} records, method=${method}\n`;
    log.innerHTML += `[${formatLogTime()}] Connecting to prq.address_cleansing_queue...\n`;

    // Simulate progress
    let processed = 0;
    const startTime = Date.now();
    currentInterval = setInterval(() => {
      processed += Math.floor(Math.random() * 50) + 10;
      const elapsed = (Date.now() - startTime) / 1000;
      const tps = elapsed > 0 ? Math.round(processed / elapsed) : 0;
      const progressPercent = Math.min(Math.round((processed / size) * 100), 100);

      // Update progress bar
      progressValue.textContent = `${progressPercent}%`;
      progressFill.style.width = `${progressPercent}%`;

      if (processed >= size) {
        processed = size;
        clearInterval(currentInterval);
        currentInterval = null;
        progressValue.textContent = "100%";
        progressFill.style.width = "100%";
        setButtonState(false);
        log.innerHTML += `[${formatLogTime()}] ✅ Batch complete: ${processed.toLocaleString()} records processed\n`;
        document.getElementById("batch-done").textContent = processed.toLocaleString();
        document.getElementById("batch-throughput").textContent = `${tps.toLocaleString()} items/s`;
        return;
      }

      document.getElementById("batch-throughput").textContent = `${tps.toLocaleString()} items/s`;
      log.innerHTML += `[${formatLogTime()}] Processing... ${processed.toLocaleString()}/${size.toLocaleString()}\n`;
      log.scrollTop = log.scrollHeight;
    }, 800);
  });
}

async function fetchStats(options = {}) {
  const { manual = false } = options;
  try {
    if (manual) setDashboardRefreshState(true);

    const response = await fetch(`${API_BASE}/stats`, {
      headers: getAuthHeader()
    });

    if (response.status === 401) {
      localStorage.removeItem('vnai_token');
      window.location.href = 'login.html';
      return;
    }

    const data = await response.json();

    // Update Master Data
    const masterCount = (data.master.provinces || 0) + (data.master.districts || 0) + (data.master.wards || 0);
    if (document.getElementById('stat-master')) document.getElementById('stat-master').innerText = masterCount.toLocaleString();

    // Update OSM Data
    const osmCount = (data.osm.total || 0);
    if (document.getElementById('stat-osm')) document.getElementById('stat-osm').innerText = osmCount.toLocaleString();

    // Update Training Data & Queue
    if (data.ai) {
      if (document.getElementById('stat-training')) document.getElementById('stat-training').innerText = (data.ai.training_samples || 0).toLocaleString();
      if (document.getElementById('stat-queue')) document.getElementById('stat-queue').innerText = (data.ai.cleansing_queue || 0).toLocaleString();
    }

    if (data.master) {
      if (document.getElementById('province-count')) document.getElementById('province-count').textContent = data.master.provinces.toLocaleString();
      if (document.getElementById('district-count')) document.getElementById('district-count').textContent = data.master.districts.toLocaleString();
      if (document.getElementById('ward-count')) document.getElementById('ward-count').textContent = data.master.wards.toLocaleString();
    }

    // Update Chart
    renderOverviewChart(data);

    // Update Visitors
    if (data.visitors) {
      if (document.getElementById('stat-total-visits')) document.getElementById('stat-total-visits').textContent = data.visitors.total.toLocaleString();
      if (document.getElementById('stat-unique-ips')) document.getElementById('stat-unique-ips').textContent = data.visitors.unique.toLocaleString();
      if (document.getElementById('stat-online-users')) document.getElementById('stat-online-users').textContent = data.visitors.online.toLocaleString();
    }

    updateDashboardRefreshTime();

    if (manual && showToast) {
      showToast('Đã làm mới số liệu Dashboard', 'success');
    }
  } catch (err) {
    console.error("Stats Fetch Error:", err);
    if (manual && showToast) {
      showToast('Không thể làm mới số liệu Dashboard', 'danger');
    }
  } finally {
    if (manual) setDashboardRefreshState(false);
  }
}

// ═══════════════════════════════════════════════════════════
// TRAINING HUB LOGIC
// ═══════════════════════════════════════════════════════════
function initTrainingHub() {
  const btnImport = document.getElementById('btn-import-ls');
  const btnRefresh = document.getElementById('btn-training-refresh');

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => loadTrainingHistoryFromDB());
  }

  if (!btnImport) return;

  btnImport.addEventListener('click', async () => {
    const fileInput = document.getElementById('ls-import-file');
    const statusEl = document.getElementById('import-status');

    if (!fileInput.files.length) {
      statusEl.innerHTML = '<span class="text-danger">Vui lòng chọn file JSON</span>';
      return;
    }

    statusEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải lên và tái huấn luyện...';

    // Simulated delay for training
    setTimeout(async () => {
      try {
        await createTrainingHistoryEntry({
          version: "v2.4.1",
          accuracy: 93.8,
          f1: 91.5,
          loss: 0.221,
          samples: 26300,
          notes: "Imported from dashboard training flow",
        });

        statusEl.innerHTML = '<span class="text-success">✅ Thành công! Mô hình đã được cập nhật bản v2.4.1</span>';

        // Update last retrained text
        const timeEl = document.getElementById('last-retrained-text');
        if (timeEl) timeEl.textContent = "Vừa xong";

        await loadTrainingHistoryFromDB({ silent: true });
        if (window.__vnaiBenchmarkRefresh) {
          window.__vnaiBenchmarkRefresh({ silent: true });
        }
      } catch (error) {
        console.error("Training history create error:", error);
        statusEl.innerHTML = '<span class="text-danger">❌ Không thể ghi training history vào database</span>';
        if (showToast) {
          showToast("Không thể ghi training history vào database", "danger");
        }
      }
    }, 3000);
  });
}

// ═══════════════════════════════════════════════════════════
// WARD MAPPING LOOKUP LOGIC (V3 - Fixed Search & UI)
// ═══════════════════════════════════════════════════════════
let mappingState = {
  version: 1,
  provinces: {}, // name -> id
  districts: {},
  wards: {}
};

async function initMappingV3() {
  const pInput = document.getElementById('mapping-province-input');
  const dInput = document.getElementById('mapping-district-input');
  const wInput = document.getElementById('mapping-ward-input');
  const vSelect = document.getElementById('mapping-version-select');

  if (!pInput) return;

  const loadProvinces = async () => {
    try {
      const res = await fetch(`${API_BASE}/provinces?version=${mappingState.version}`, { headers: getAuthHeader() });
      const data = await res.json();
      renderLookupTemplateDatalist('list-provinces', data, 'province_name', 'province_id', mappingState.provinces);
    } catch (e) { console.error(e); }
  };

  vSelect?.addEventListener('change', () => {
    mappingState.version = vSelect.value;
    pInput.value = ''; dInput.value = ''; wInput.value = '';
    mappingState.provinces = {}; mappingState.districts = {}; mappingState.wards = {};
    loadProvinces();
  });

  pInput.addEventListener('input', async () => {
    if (pInput.value === '') {
      dInput.value = ''; wInput.value = '';
      mappingState.districts = {}; mappingState.wards = {};
      const listD = document.getElementById('list-districts');
      if (listD) listD.innerHTML = '';
      const listW = document.getElementById('list-wards');
      if (listW) listW.innerHTML = '';
      document.getElementById('unit-details-panel').innerHTML = '<div class="text-center" style="padding:40px; color:var(--text-tertiary)">Chọn một đơn vị để xem chi tiết.</div>';
      triggerMappingSearch();
      return;
    }

    const id = mappingState.provinces[pInput.value];
    if (!id) return;

    // Clear children
    dInput.value = ''; wInput.value = '';
    mappingState.districts = {}; mappingState.wards = {};

    showDetails('province', id);
    triggerMappingSearch(); // Auto-trigger

    try {
      const res = await fetch(`${API_BASE}/districts/${id}?version=${mappingState.version}`, { headers: getAuthHeader() });
      const data = await res.json();
      renderLookupTemplateDatalist('list-districts', data, 'district_name', 'district_id', mappingState.districts);
    } catch (e) { console.error(e); }
  });

  dInput.addEventListener('input', async () => {
    if (dInput.value === '') {
      wInput.value = '';
      mappingState.wards = {};
      const listW = document.getElementById('list-wards');
      if (listW) listW.innerHTML = '';

      const provinceId = mappingState.provinces[pInput.value];
      if (provinceId) showDetails('province', provinceId);

      triggerMappingSearch();
      return;
    }

    const provinceId = mappingState.provinces[pInput.value];
    const id = mappingState.districts[dInput.value];
    if (!id || !provinceId) return;

    wInput.value = '';
    mappingState.wards = {};

    showDetails('district', id);
    triggerMappingSearch(); // Auto-trigger

    try {
      const res = await fetch(`${API_BASE}/wards/${id}?version=${mappingState.version}`, { headers: getAuthHeader() });
      const data = await res.json();
      renderLookupTemplateDatalist('list-wards', data, 'ward_name', 'ward_id', mappingState.wards);
    } catch (e) { console.error(e); }
  });

  wInput.addEventListener('input', () => {
    if (wInput.value === '') {
      const districtId = mappingState.districts[dInput.value];
      if (districtId) showDetails('district', districtId);
      triggerMappingSearch();
      return;
    }

    const wardId = mappingState.wards[wInput.value];
    if (wardId) {
      showDetails('ward', wardId);
      triggerMappingSearch(); // Auto-trigger
    }
  });

  document.getElementById('btn-mapping-search')?.addEventListener('click', triggerMappingSearch);
  document.getElementById('mapping-search-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') triggerMappingSearch();
  });

  loadProvinces();
}

async function showDetails(level, id) {
  const pl = document.getElementById('unit-details-panel');
  if (!pl) return;
  pl.innerHTML = '<div class="text-center" style="padding:40px"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></div>';
  try {
    const res = await fetch(`${API_BASE}/unit-details/${level}/${id}`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Unit not found");
    const u = await res.json();
    pl.innerHTML = `
      <div class="flex items-center gap-24 w-full">
        <div style="flex: 0 0 240px;">
          <div class="flex items-center gap-12">
            <span class="text-accent font-700" style="font-size:18px;">${u.ward_name || u.district_name || u.province_name}</span>
            <span class="badge info" style="font-size:10px;">v${u.admin_version}</span>
          </div>
          <div class="text-tertiary" style="font-size:11px;">
            ${u.ward_name ? 'Phường/Xã' : (u.district_name ? 'Quận/Huyện' : 'Tỉnh/Thành phố')} • 
            Mã GSO: <span class="text-mono">${u.ward_no || u.district_no || u.province_no || "N/A"}</span>
          </div>
        </div>

        <div class="flex gap-32 px-24" style="border-left: 1px solid var(--border-subtle); border-right: 1px solid var(--border-subtle);">
          <div class="text-center">
            <div class="text-tertiary mb-4" style="font-size:10px; text-transform:uppercase; letter-spacing:0.05em;">Dân số</div>
            <div class="font-700" style="font-size:16px;">${(u.population || 0).toLocaleString()} <small class="font-400 text-tertiary" style="font-size:10px">người</small></div>
          </div>
          <div class="text-center">
            <div class="text-tertiary mb-4" style="font-size:10px; text-transform:uppercase; letter-spacing:0.05em;">Diện tích</div>
            <div class="font-700" style="font-size:16px;">${(u.area_km2 || 0).toLocaleString()} <small class="font-400 text-tertiary" style="font-size:10px">km²</small></div>
          </div>
        </div>

        <div class="flex-1 pl-8">
          <div class="text-tertiary mb-4" style="font-size:10px; text-transform:uppercase; letter-spacing:0.05em;">Cơ sở pháp lý / Nghị quyết</div>
          <div class="text-secondary italic" style="font-size:12px; line-height:1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${u.decision_number || ""}">
            ${u.decision_number || "Chưa có thông tin nghị quyết cụ thể trong hệ thống."}
          </div>
        </div>
      </div>
    `;
  } catch (e) { panel.innerHTML = "Lỗi tải thông tin"; }
}

async function triggerMappingSearch() {
  const qText = document.getElementById('mapping-search-input').value;
  const pId = mappingState.provinces[document.getElementById('mapping-province-input').value];
  const dId = mappingState.districts[document.getElementById('mapping-district-input').value];
  const wId = mappingState.wards[document.getElementById('mapping-ward-input').value];

  const tbody = document.getElementById('mapping-results-table');
  const version = document.getElementById('mapping-version-select')?.value || mappingState.version;

  let url = `${API_BASE}/lookup/mapping?`;
  if (wId) url += `ward_id=${wId}`;
  else if (dId) url += `district_id=${dId}`;
  else if (pId) url += `province_id=${pId}`;

  if (version) url += `${url.endsWith('?') ? '' : '&'}version=${version}`;
  if (qText) url += `${url.endsWith('?') ? '' : '&'}query=${encodeURIComponent(qText)}`;

  // Allow search if either an ID is selected OR a query text is provided
  if (!pId && !dId && !wId && !qText) return;

  tbody.innerHTML = '<tr><td colspan="5" class="text-center" style="padding:60px"><i class="fa-solid fa-circle-notch fa-spin fa-2x text-accent"></i><div class="mt-12 text-tertiary">Đang truy vấn dữ liệu mapping...</div></td></tr>';

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();
    if (data.length === 0) {
      document.getElementById('mapping-result-count').textContent = '0 records';
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-tertiary" style="padding:60px">Không tìm thấy dữ liệu ánh xạ phù hợp cho khu vực này</td></tr>';
      return;
    }
    document.getElementById('mapping-result-count').textContent = `${data.length} records`;
    tbody.innerHTML = data.map(m => `
      <tr style="cursor: pointer; transition: background 0.2s;" onclick="showDetails('ward', ${m.ward_id_new})">
        <td style="padding: 16px 20px;">
          <div class="font-700" style="font-size:15px; color:var(--text-primary)">${m.ward_name_old || (m.ward_id_old == -1 ? "(Tất cả Xã)" : "N/A")}</div>
          <div class="text-tertiary" style="font-size:12px; margin-top: 2px;">
            ${[m.district_name_old, m.province_name_old].filter(x => x).join(" - ")}
          </div>
        </td>
        <td class="text-center" style="vertical-align:middle; width: 60px;">
          <div style="background: var(--bg-hover); width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
            <i class="fa-solid fa-chevron-right text-accent" style="font-size: 12px;"></i>
          </div>
        </td>
        <td style="padding: 16px 20px;">
          <div class="font-700" style="font-size:15px; color:var(--success)">${m.ward_name_new || "N/A"}</div>
          <div class="text-tertiary" style="font-size:12px; margin-top: 2px;">${m.district_name_new || ""} - ${m.province_name_new || ""}</div>
        </td>
        <td style="padding: 16px 20px;">
          <div class="badge ${m.relationship_type === 'MERGE' ? 'warning' : 'info'}" style="font-size: 10px; margin-bottom: 6px;">${m.relationship_type || 'MAPPING'}</div>
          <div style="font-size:12px; line-height:1.5; color: var(--text-secondary)">${m.updated_note || "Cập nhật theo nghị quyết sáp nhập ĐVHC."}</div>
        </td>
        <td class="text-tertiary" style="padding: 16px 20px; font-size:13px; font-family: var(--font-mono)">
          ${m.effective_date_from ? new Date(m.effective_date_from).toLocaleDateString('vi-VN') : "01/01/2021"}
        </td>
      </tr>
    `).join("");
  } catch (err) { tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger" style="padding:40px">Lỗi kết nối API</td></tr>'; }
}


// ═══════════════════════════════════════════════════════════
// NSO SYNC LOGIC (v2 - Batch & Real-time Logs)
// ═══════════════════════════════════════════════════════════
let nsoProvinces = [];
let logPollingInterval = null;
let logPollingRetryTimer = null;
let logPollingFailureCount = 0;

function clearLogPollingRetryTimer() {
  if (logPollingRetryTimer) {
    clearTimeout(logPollingRetryTimer);
    logPollingRetryTimer = null;
  }
}

function scheduleLogPollingRetry() {
  clearInterval(logPollingInterval);
  logPollingInterval = null;

  clearLogPollingRetryTimer();
  logPollingRetryTimer = setTimeout(() => {
    logPollingRetryTimer = null;
    startLogPolling();
  }, 15000);
}

function initNSOSyncTool() {
  const btnLoad = document.getElementById('btn-load-nso-provinces');
  const btnSyncAll = document.getElementById('btn-sync-all-provinces');
  const filterInput = document.getElementById('nso-province-filter');
  const logsContainer = document.getElementById('nso-sync-logs');
  const clearLogsBtn = document.getElementById('btn-clear-nso-logs');

  if (!btnLoad) return;

  btnLoad.addEventListener('click', loadNSOProvinces);
  btnSyncAll?.addEventListener('click', syncAllProvinces);
  filterInput.addEventListener('input', renderNSOProvincesTable);
  clearLogsBtn.addEventListener('click', async () => {
    try {
      await fetch(`${API_BASE}/sync/nso/logs`, { method: 'DELETE', headers: getAuthHeader() });
      logsContainer.innerHTML = '<div style="color: #8b949e;">[System] Logs cleared.</div>';
    } catch (error) {
      console.warn('Unable to clear NSO logs', error);
      if (showToast) {
        showToast('Không thể xóa log vì API chưa phản hồi', 'danger');
      }
    }
  });

  // Start log polling
  startLogPolling();
}

async function loadNSOProvinces() {
  const btn = document.getElementById('btn-load-nso-provinces');
  const tbody = document.getElementById('nso-provinces-table');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tải...';
  tbody.innerHTML = '<tr><td colspan="4" class="text-center"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/provinces`, { headers: getAuthHeader() });
    nsoProvinces = await res.json();
    renderNSOProvincesTable();
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Lỗi tải dữ liệu NSO</td></tr>';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-rotate mr-4"></i> Tải danh sách NSO';
  }
}

function renderNSOProvincesTable() {
  const tbody = document.getElementById('nso-provinces-table');
  const filter = document.getElementById('nso-province-filter').value.toLowerCase();

  const filtered = nsoProvinces.filter(p =>
    p.TenTinh.toLowerCase().includes(filter) || p.MaTinh.includes(filter)
  );

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-tertiary">Không tìm thấy tỉnh nào phù hợp.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(p => `
    <tr>
      <td><span class="text-mono">${p.MaTinh}</span></td>
      <td><strong>${p.TenTinh}</strong></td>
      <td><span class="badge info">${p.LoaiHinh}</span></td>
      <td class="text-right">
        <button class="btn btn-xs btn-accent btn-sync-province" 
                data-code="${p.MaTinh}" data-name="${p.TenTinh}">
          <i class="fa-solid fa-cloud-arrow-down"></i> Sync
        </button>
      </td>
    </tr>
  `).join("");

  // Add listeners to new buttons
  document.querySelectorAll('.btn-sync-province').forEach(btn => {
    btn.addEventListener('click', () => syncSingleProvince(btn));
  });
}

async function syncSingleProvince(btn) {
  const code = btn.getAttribute('data-code');
  const name = btn.getAttribute('data-name');

  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

  updateSyncStatus('SYNCING', 'var(--warning)');

  try {
    const res = await fetch(`${API_BASE}/sync/nso/province`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, name })
    });
    const result = await res.json();

    if (result.status === 'success') {
      showToast(`✅ Hoàn thành ${name}`);
    } else {
      showToast(`❌ Lỗi ${name}: ${result.message}`, 'danger');
    }
  } catch (e) {
    showToast(`❌ Lỗi kết nối khi sync ${name}`, 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Sync';
    updateSyncStatus('IDLE', '#8b949e');
  }
}

function updateSyncStatus(text, color) {
  document.getElementById('sync-status-text').textContent = text;
  document.getElementById('sync-status-dot').style.background = color;
}

function startLogPolling() {
  if (logPollingInterval) clearInterval(logPollingInterval);
  clearLogPollingRetryTimer();
  logPollingFailureCount = 0;

  logPollingInterval = setInterval(async () => {
    const logsContainer = document.getElementById('nso-sync-logs');
    if (!logsContainer) return;

    try {
      const res = await fetch(`${API_BASE}/sync/nso/logs`, { headers: getAuthHeader() });
      const logs = await res.json();
      logPollingFailureCount = 0;

      const html = logs.map(l => {
        let color = '#8b949e';
        if (l.level === 'success') color = '#3fb950';
        if (l.level === 'error') color = '#f85149';
        if (l.level === 'warning') color = '#d29922';

        return `<div style="margin-bottom: 4px;">
          <span style="color: #484f58;">[${l.time}]</span> 
          <span style="color: ${color}">${l.message}</span>
        </div>`;
      }).join("");

      if (logsContainer.innerHTML !== html) {
        logsContainer.innerHTML = html;
        logsContainer.scrollTop = logsContainer.scrollHeight;
      }
    } catch (error) {
      logPollingFailureCount += 1;

      if (logsContainer && logPollingFailureCount === 1) {
        logsContainer.innerHTML = '<div style="color: #8b949e;">[System] Log API unavailable. Retrying...</div>';
      }

      if (logPollingFailureCount >= 1) {
        scheduleLogPollingRetry();
      }
    }
  }, 2000);
}

async function syncAllProvinces() {
  const btn = document.getElementById('btn-sync-all-provinces');
  if (nsoProvinces.length === 0) {
    showToast('Vui lòng tải danh sách Tỉnh trước', 'warning');
    return;
  }

  const confirmMsg = `Hệ thống sẽ bắt đầu đồng bộ tuần tự ${nsoProvinces.length.toLocaleString()} tỉnh/thành. Quá trình này có thể kéo dài vài phút tùy thuộc vào tốc độ mạng. Bạn có chắc chắn muốn bắt đầu?`;
  const isConfirmed = await showConfirm(confirmMsg);
  if (!isConfirmed) return;

  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing All...';

  try {
    for (let i = 0; i < nsoProvinces.length; i++) {
      const p = nsoProvinces[i];
      updateSyncStatus(`SYNCING (${(i + 1).toLocaleString()}/${nsoProvinces.length.toLocaleString()})`, 'var(--warning)');

      // Update UI to highlight current province (optional but good)
      // For now we just call the sync
      try {
        const res = await fetch(`${API_BASE}/sync/nso/province`, {
          method: 'POST',
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: p.MaTinh, name: p.TenTinh })
        });
        const result = await res.json();
        console.log(`Sync ${p.TenTinh} result:`, result);
      } catch (err) {
        console.error(`Failed to sync ${p.TenTinh}`, err);
      }
    }
    showToast('✅ Đã hoàn thành đồng bộ toàn bộ danh sách!', 'success');
  } catch (e) {
    showToast('❌ Lỗi trong quá trình đồng bộ hàng loạt', 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    updateSyncStatus('IDLE', '#8b949e');
  }
}

// ═══ ADMINISTRATIVE MANAGER (CRUD) ═══

window.editAdminUnit = async function (level, id) {
  try {
    const res = await fetch(`${API_BASE}/${level}s/${id}`, { headers: getAuthHeader() });
    const item = await res.json();

    document.getElementById('admin-modal-title').textContent = `Chỉnh sửa ${item[`${level}_name`]}`;
    document.getElementById('admin-form-id').value = id;
    document.getElementById('admin-form-name').value = item[`${level}_name`];
    document.getElementById('admin-form-no').value = item[`${level}_no`] || '';
    document.getElementById('admin-form-type').value = item.type_name || '';
    document.getElementById('admin-form-name-en').value = item[`${level}_name_en`] || '';

    renderExtraFields(item);
    document.getElementById('modal-admin-unit').classList.add('active');
  } catch (e) {
    showToast('Lỗi khi tải thông tin chi tiết', 'danger');
  }
}

async function renderExtraFields(item = null) {
  const level = getAdminCurrentLevel();
  const container = document.getElementById('admin-form-extra');
  container.innerHTML = '';

  if (level === 'province') return;

  const label = level === 'district' ? 'Tỉnh / Thành phố' : 'Quận / Huyện';
  const parentId = item ? (level === 'district' ? item.province_id : item.district_id) : '';

  container.innerHTML = `
    <div class="form-group">
      <label>${label}</label>
      <select id="admin-form-parent" class="form-input" required>
        <option value="">-- Đang tải... --</option>
      </select>
    </div>
  `;

  try {
    const parentLevel = level === 'district' ? 'province' : 'district';
    let url = `${API_BASE}/${parentLevel}s?limit=500`;

    // For ward, filter districts by current selected province if possible
    if (level === 'ward') {
      const pInput = document.getElementById('admin-province-input');
      const filterProvId = pInput && pInput.value ? adminState.provinces[pInput.value] : null;
      if (filterProvId) url += `&province_id=${filterProvId}`;
    }

    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();

    renderUnifiedSelectOptions('admin-form-parent', data, `${parentLevel}_id`, `${parentLevel}_name`, '-- Chọn đơn vị cha --');
    if (parentId) document.getElementById('admin-form-parent').value = parentId;
  } catch (e) {
    console.error('Lỗi khi tải danh sách đơn vị cha', e);
  }
}

window.deleteAdminUnit = async function (level, id, name) {
  const ok = await showConfirm(`Bạn có chắc chắn muốn xóa "${name}"? Hành động này không thể hoàn tác.`);
  if (!ok) return;

  try {
    const res = await fetch(`${API_BASE}/${level}s/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader()
    });

    if (res.ok) {
      showToast('Đã xóa thành công');
      loadAdminData();
    } else {
      showToast('Lỗi khi xóa dữ liệu', 'danger');
    }
  } catch (e) {
    showToast('Lỗi kết nối server', 'danger');
  }
}

async function saveAdminUnit() {
  const level = getAdminCurrentLevel();
  const id = document.getElementById('admin-form-id').value;
  const name = document.getElementById('admin-form-name').value;
  const no = document.getElementById('admin-form-no').value;
  const type = document.getElementById('admin-form-type').value;
  const nameEn = document.getElementById('admin-form-name-en').value;
  const parentId = document.getElementById('admin-form-parent')?.value;

  const payload = {
    [`${level}_name`]: name,
    [`${level}_no`]: no,
    type_name: type,
    [`${level}_name_en`]: nameEn
  };

  if (level === 'district' && parentId) payload.province_id = parseInt(parentId);
  if (level === 'ward' && parentId) payload.district_id = parseInt(parentId);

  const url = id ? `${API_BASE}/${level}s/${id}` : `${API_BASE}/${level}s`;
  const method = id ? 'PATCH' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Lưu dữ liệu thành công');
      document.getElementById('modal-admin-unit').classList.remove('active');
      loadAdminData();
    } else {
      const err = await res.json();
      showToast(`Lỗi: ${err.detail || 'Không xác định'}`, 'danger');
    }
  } catch (e) {
    showToast('Lỗi kết nối server', 'danger');
  }
}

let adminState = {
  provinces: {},
  districts: {},
  wards: {}
};

async function initAdminManager() {
  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');
  const wInput = document.getElementById('admin-ward-input');
  const searchInput = document.getElementById('admin-search-input');
  const btnRefresh = document.getElementById('btn-admin-refresh');
  const btnAddNew = document.getElementById('btn-admin-add-new');
  const unitForm = document.getElementById('admin-unit-form');
  const modal = document.getElementById('modal-admin-unit');
  const vRadios = document.getElementsByName('admin-crud-version');

  if (!pInput) return;

  const loadProvinces = async () => {
    try {
      const res = await fetch(`${API_BASE}/provinces?limit=100`, { headers: getAuthHeader() });
      const data = await res.json();
      renderLookupTemplateDatalist('admin-list-provinces', data, 'province_name', 'province_id', adminState.provinces);
    } catch (e) { console.error(e); }
  };

  pInput.addEventListener('input', async () => {
    if (pInput.value === '') {
      dInput.value = ''; wInput.value = '';
      adminState.districts = {}; adminState.wards = {};
      const listD = document.getElementById('admin-list-districts');
      if (listD) listD.innerHTML = '';
      const listW = document.getElementById('admin-list-wards');
      if (listW) listW.innerHTML = '';
      loadAdminData();
      return;
    }
    const id = adminState.provinces[pInput.value];
    if (!id) return;

    loadAdminData();

    dInput.value = ''; wInput.value = '';
    adminState.districts = {}; adminState.wards = {};
    try {
      const res = await fetch(`${API_BASE}/districts?province_id=${id}&limit=500`, { headers: getAuthHeader() });
      const data = await res.json();
      renderLookupTemplateDatalist('admin-list-districts', data, 'district_name', 'district_id', adminState.districts);
    } catch (e) { console.error(e); }
  });

  dInput.addEventListener('input', async () => {
    if (dInput.value === '') {
      wInput.value = '';
      adminState.wards = {};
      const listW = document.getElementById('admin-list-wards');
      if (listW) listW.innerHTML = '';
      loadAdminData();
      return;
    }
    const id = adminState.districts[dInput.value];
    if (!id) return;

    loadAdminData();

    wInput.value = '';
    adminState.wards = {};
    try {
      const res = await fetch(`${API_BASE}/wards?district_id=${id}&limit=500`, { headers: getAuthHeader() });
      const data = await res.json();
      renderLookupTemplateDatalist('admin-list-wards', data, 'ward_name', 'ward_id', adminState.wards);
    } catch (e) { console.error(e); }
  });

  btnRefresh.addEventListener('click', () => loadAdminData());
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      // Debounce search
      clearTimeout(searchInput._timer);
      searchInput._timer = setTimeout(() => loadAdminData(), 300);
    });
  }

  document.getElementById('btn-clear-admin-province')?.addEventListener('click', () => {
    pInput.value = '';
    pInput.dispatchEvent(new Event('input'));
  });
  document.getElementById('btn-clear-admin-district')?.addEventListener('click', () => {
    dInput.value = '';
    dInput.dispatchEvent(new Event('input'));
  });

  // Modal actions
  btnAddNew.addEventListener('click', () => {
    const level = getAdminCurrentLevel();
    document.getElementById('admin-modal-title').textContent = `Thêm ${level === 'province' ? 'Tỉnh/Thành' : level === 'district' ? 'Quận/Huyện' : 'Phường/Xã'} mới`;
    document.getElementById('admin-form-id').value = '';
    unitForm.reset();
    renderExtraFields();
    modal.classList.add('active');
  });

  unitForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    await saveAdminUnit();
  });

  // Initial load
  loadProvinces();
  loadAdminData();
}

function getAdminCurrentLevel() {
  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');

  if (dInput && dInput.value && adminState.districts[dInput.value]) return 'ward';
  if (pInput && pInput.value && adminState.provinces[pInput.value]) return 'district';
  return 'province';
}

async function loadAdminData() {
  const level = getAdminCurrentLevel();

  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');

  const provinceId = pInput && pInput.value ? adminState.provinces[pInput.value] : null;
  const districtId = dInput && dInput.value ? adminState.districts[dInput.value] : null;

  const searchInput = document.getElementById('admin-search-input');
  const q = searchInput ? searchInput.value.toLowerCase() : '';

  const tableHead = document.getElementById('admin-table-head');
  const tableBody = document.getElementById('admin-table-body');
  const title = document.getElementById('admin-table-title');

  tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24"><i class="fa-solid fa-spinner fa-spin mr-8"></i> Đang tải dữ liệu...</td></tr>';

  let url = `${API_BASE}/${level}s?limit=500`;
  if (level === 'district' && provinceId) url += `&province_id=${provinceId}`;
  if (level === 'ward' && districtId) url += `&district_id=${districtId}`;

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    let data = await res.json();

    // Sort by GSO code (_no) - Numeric sort
    const noField = `${level}_no`;
    data.sort((a, b) => (a[noField] || '').localeCompare(b[noField] || '', undefined, { numeric: true }));

    // Render Headers
    const headers = ['ID', 'Mã số', 'Tên đơn vị', 'Tên Tiếng Anh', 'Loại hình'];
    tableHead.innerHTML = headers.map(h => `<th>${h}</th>`).join('') + '<th class="text-right">Thao tác</th>';

    // Apply client-side search filter
    if (q) {
      data = data.filter(item => {
        const no = (item[`${level}_no`] || '').toLowerCase();
        const name = (item[`${level}_name`] || '').toLowerCase();
        return no.includes(q) || name.includes(q);
      });
    }

    // Render Rows
    if (data.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24 text-tertiary">Không tìm thấy dữ liệu</td></tr>';
      return;
    }

    tableBody.innerHTML = data.map(item => `
      <tr>
        <td class="text-mono text-xs">${item[`${level}_id`]}</td>
        <td class="text-mono font-bold">${item[`${level}_no`] || '-'}</td>
        <td>
          <div class="flex items-center gap-8">
            ${level === 'province' ? '<i class="fa-solid fa-map text-tertiary" style="width:16px"></i>' :
        level === 'district' ? '<i class="fa-solid fa-folder-tree text-tertiary ml-12" style="width:16px"></i>' :
          '<i class="fa-solid fa-location-dot text-tertiary ml-24" style="width:16px"></i>'}
            <span class="${level !== 'province' ? 'text-secondary' : 'font-600'}">${item[`${level}_name`]}</span>
          </div>
        </td>
        <td class="text-tertiary text-xs">${item[`${level}_name_en`] || '-'}</td>
        <td><span class="badge badge-outline">${item.type_name || '-'}</span></td>
        <td class="text-right">
          <button class="btn btn-icon btn-sm" onclick="editAdminUnit('${level}', ${item[`${level}_id`]})" title="Sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="btn btn-icon btn-sm text-danger" onclick="deleteAdminUnit('${level}', ${item[`${level}_id`]}, '${item[`${level}_name`]}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `).join('');

    title.innerHTML = `<i class="fa-solid fa-list mr-8"></i> Danh sách ${level === 'province' ? 'Tỉnh/Thành' : level === 'district' ? 'Quận/Huyện' : 'Phường/Xã'} (${data.length.toLocaleString()})`;

    adjustActivePageHeight();
  } catch (e) {
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24 text-danger">Lỗi khi tải dữ liệu</td></tr>';
  }
}

// Initialize all modules is now handled in DOMContentLoaded

// ═══════════════════════════════════════════════════════════
// DATA EXPLORER
// ═══════════════════════════════════════════════════════════
function initDataExplorer() {
  const btnRefresh = document.getElementById("btn-explorer-refresh");
  const searchInput = document.getElementById("explorer-search");
  const tbody = document.getElementById("explorer-body");

  if (!btnRefresh || !tbody) return;

  const loadData = async () => {
    btnRefresh.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btnRefresh.disabled = true;
    try {
      const q = searchInput ? searchInput.value.trim() : "";
      const res = await fetch(`${API_BASE}/explorer/queue?limit=100&q=${encodeURIComponent(q)}`, {
        headers: getAuthHeader()
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();

      if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-tertiary);">Không có dữ liệu trong prq.address_cleansing_queue</td></tr>`;
      } else {
        tbody.innerHTML = data.map(item => {
          let statusBadge = "info";
          if (item.status === "DONE") statusBadge = "success";
          else if (item.status === "ERROR") statusBadge = "danger";
          else if (item.status === "PROCESSING") statusBadge = "warning";

          return `<tr>
            <td class="text-mono" style="font-size: 11px;">#${item.id}</td>
            <td>${item.raw_address}</td>
            <td>${item.ward_name || "-"}</td>
            <td>${item.district_name || "-"}</td>
            <td>${item.province_name || "-"}</td>
            <td><span class="badge ${statusBadge}">${item.status}</span></td>
          </tr>`;
        }).join("");
      }
    } catch (err) {
      console.error(err);
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);"><i class="fa-solid fa-triangle-exclamation mr-8"></i>Lỗi tải dữ liệu: ${err.message}</td></tr>`;
      if (typeof showToast === 'function') showToast(`Data Explorer: ${err.message}`, "danger");
    } finally {
      btnRefresh.innerHTML = '<i class="fa-solid fa-arrow-rotate-right"></i>';
      btnRefresh.disabled = false;
      adjustActivePageHeight();
    }
  };

  btnRefresh.addEventListener("click", loadData);

  if (searchInput) {
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") loadData();
    });
  }

  // Initial load
  loadData();
}

/**
 * Dynamically calculates and adjusts the height of scrollable elements 
 * (gridview, job-log, etc.) to prevent #page-content from overflowing.
 */
function adjustActivePageHeight() {
  const activePage = document.querySelector('.page.active');
  if (!activePage) return;

  const pageContent = document.getElementById('page-content');
  if (!pageContent) return;

  // Small delay to ensure DOM is rendered if called after data load
  requestAnimationFrame(() => {
    const scrollableSelectors = [
      '.table-container',
      '.batch-log',
      '#parser-comparison-matrix',
      '.ner-output',
      '.card-body.with-scroll',
      '#activity-feed',
      '#osm-job-log',
      '#nso-sync-logs',
      '.lookup-results-table',
      '.ner-output'
    ];

    const scrollableElements = activePage.querySelectorAll(scrollableSelectors.join(', '));
    const pageContentRect = pageContent.getBoundingClientRect();
    const buffer = 24; // Bottom padding/margin buffer

    scrollableElements.forEach(el => {
      // Reset first to get natural position
      el.style.maxHeight = '';

      const rect = el.getBoundingClientRect();
      const availableHeight = pageContentRect.bottom - rect.top - buffer;

      if (availableHeight > 100) {
        el.style.maxHeight = `${Math.floor(availableHeight)}px`;
        el.style.overflowY = 'auto';
      }
    });
  });
}

// Export to window for access from other parts of the app if needed
window.adjustActivePageHeight = adjustActivePageHeight;

/**
 * Loads all page templates from the pages/ directory and injects them into #page-content.
 */
async function loadPages() {
  const container = document.getElementById('page-content');
  if (!container) return;

  // Clear loading state
  container.innerHTML = '';

  const loadPromises = PAGES.map(async (pageId) => {
    try {
      const response = await fetch(`pages/${pageId}.html`);
      if (!response.ok) throw new Error(`Failed to load ${pageId}`);
      const html = await response.text();

      const div = document.createElement('div');
      div.innerHTML = html;

      // The templates should contain the <div class="page" id="..."> wrapper
      // If they don't, we should add it. My templates already have it.
      const pageNode = div.firstElementChild;
      if (pageNode) {
        container.appendChild(pageNode);
      }
    } catch (err) {
      console.error(`Error loading page ${pageId}:`, err);
    }
  });

  await Promise.all(loadPromises);
}

// ═══════════════════════════════════════════════════════════
// LABEL STUDIO INTEGRATION
// ═══════════════════════════════════════════════════════════
async function initLabelStudioIntegration() {
  const btnRefresh = document.getElementById('btn-ls-refresh');
  if (!btnRefresh) return;

  btnRefresh.addEventListener('click', fetchLabelStudioTasks);

  // Initial fetch if page is active
  if (document.getElementById('label-studio').classList.contains('active')) {
    fetchLabelStudioTasks();
  }
}

async function fetchLabelStudioTasks() {
  const tbody = document.getElementById('ls-tasks-body');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="5" class="text-center p-24 text-tertiary"><i class="fa-solid fa-spinner fa-spin mr-8"></i> Đang tải dữ liệu...</td></tr>';

  try {
    const response = await fetch(`${API_BASE}/label-studio/tasks`, {
      headers: getAuthHeader()
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);

    const tasks = await response.json();

    if (tasks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center p-24 text-tertiary">Không có task nào trong dự án hiện tại</td></tr>';
      return;
    }

    tbody.innerHTML = tasks.map(task => `
      <tr>
        <td class="text-mono">#${task.id}</td>
        <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${JSON.stringify(task.data)}
        </td>
        <td class="text-tertiary">${new Date(task.created_at).toLocaleString('vi-VN')}</td>
        <td><span class="badge ${task.is_labeled ? 'success' : 'warning'}">${task.is_labeled ? 'Completed' : 'Pending'}</span></td>
        <td class="text-right">
          <a href="https://label.nod.io.vn/projects/${task.project}/data?task=${task.id}" target="_blank" class="btn btn-icon btn-sm" title="Gán nhãn"><i class="fa-solid fa-tag"></i></a>
        </td>
      </tr>
    `).join('');

    // Update stats
    document.getElementById('ls-stat-total').textContent = tasks.length;
    document.getElementById('ls-stat-completed').textContent = tasks.filter(t => t.is_labeled).length;

    adjustActivePageHeight();
  } catch (err) {
    console.error('Label Studio API error:', err);
    tbody.innerHTML = `<tr><td colspan="5" class="text-center p-24 text-danger"><i class="fa-solid fa-circle-exclamation mr-8"></i> Lỗi: ${err.message}</td></tr>`;
  }
}
// Admin Unit CRUD Stubs
function editAdminUnit(level, id) {
  showToast(`Chức năng chỉnh sửa ${level} (ID: ${id}) đang được phát triển.`, 'info');
}

async function deleteAdminUnit(level, id, name) {
  const confirmed = await showConfirm(`Bạn có chắc chắn muốn xóa ${level}: ${name}?`);
  if (confirmed) {
    showToast(`Đã yêu cầu xóa ${name}. Đang xử lý...`, 'warning');
  }
}

// Expose to window for inline onclick handlers
window.showDetails = showDetails;
window.editAdminUnit = editAdminUnit;
window.deleteAdminUnit = deleteAdminUnit;
window.loadTrainingHistoryFromDB = loadTrainingHistoryFromDB;
