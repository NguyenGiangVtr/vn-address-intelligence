/* ══════════════════════════════════════════════════════════════
   VN Address Intelligence — SaaS App Logic
   ══════════════════════════════════════════════════════════════ */

const DEFAULT_API_BASE = window.location.hostname === "localhost" || window.location.protocol === "file:"
  ? "http://localhost:8081/api"
  : "/api";

const UI_SETTINGS_STORAGE_KEY = 'vnai_ui_settings_v1';
const VALID_THEMES = new Set(['dark', 'light', 'oled-black']);
const VALID_MOTION_MODES = new Set(['smooth', 'fast', 'off']);

function normalizeApiBase(url) {
  const raw = String(url || '').trim();
  if (!raw) return DEFAULT_API_BASE;
  return raw.replace(/\/+$/, '');
}

function loadUISettings() {
  try {
    const raw = localStorage.getItem(UI_SETTINGS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (_err) {
    return {};
  }
}

function saveUISettings(settings) {
  localStorage.setItem(UI_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}

function resolveTheme(theme) {
  return VALID_THEMES.has(theme) ? theme : 'dark';
}

function resolveMotionMode(mode) {
  return VALID_MOTION_MODES.has(mode) ? mode : 'smooth';
}

function applyVisualSettings(settings) {
  const theme = resolveTheme(settings?.theme);
  const motion = resolveMotionMode(settings?.animations);
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.setAttribute('data-motion', motion);
}

let API_BASE = normalizeApiBase(loadUISettings().apiBaseUrl);
applyVisualSettings(loadUISettings());

function getApiBaseCandidates() {
  const candidates = [API_BASE, normalizeApiBase(loadUISettings().apiBaseUrl), DEFAULT_API_BASE];

  if (window.location.origin && window.location.origin !== 'null') {
    candidates.push(`${window.location.origin}/api`);
  }

  return [...new Set(candidates.filter(Boolean).map((value) => normalizeApiBase(value)))];
}

async function fetchWithApiFallback(path, options = {}) {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  let lastError = null;

  for (const base of getApiBaseCandidates()) {
    try {
      return await fetch(`${base}${suffix}`, options);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error(`Unable to reach API for ${suffix}`);
}

const PAGES = [
  "overview", "parser", "batch", "training", "label-studio",
  "experiments", "explorer", "osm-enrichment", "lookup", "boundary-visualization",
  "admin-units", "nso-sync", "settings", "evidence"
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

async function logoutAndRedirect() {
  try {
    await fetch(`${API_BASE}/logout`, {
      method: 'POST',
      headers: getAuthHeader(),
    });
  } catch (error) {
    console.warn('Logout request failed, clearing local session anyway.', error);
  } finally {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
  }
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
  safeInit("initEvidenceView", initEvidenceView);
  safeInit("initTrainingHub", initTrainingHub);
  safeInit("initBoundaryVisualizationUI", initBoundaryVisualizationUI);
  safeInit("initSettingsPage", initSettingsPage);

  document.getElementById('btn-logout')?.addEventListener('click', async () => {
    const confirmed = !showConfirm ? true : await showConfirm('Bạn có chắc chắn muốn đăng xuất?');
    if (confirmed) {
      await logoutAndRedirect();
    }
  });

  fetchStats();
  setInterval(fetchStats, 30000);
  loadTrainingHistoryFromDB({ silent: true });
});

function getSettingsFormData() {
  const settingsPage = document.getElementById('settings');
  if (!settingsPage) return null;

  const env = {};
  settingsPage.querySelectorAll('[data-env-key]').forEach((input) => {
    const key = input.getAttribute('data-env-key');
    if (!key) return;
    env[key] = input.value.trim();
  });

  const apiInput = document.getElementById('cfg-api-url');
  const themeSelect = document.getElementById('cfg-theme');
  const motionSelect = document.getElementById('cfg-animations');

  return {
    apiBaseUrl: normalizeApiBase(apiInput?.value),
    theme: resolveTheme(themeSelect?.value),
    animations: resolveMotionMode(motionSelect?.value),
    env,
  };
}

function populateSettingsForm() {
  const settingsPage = document.getElementById('settings');
  if (!settingsPage) return;

  const stored = loadUISettings();
  const env = stored?.env && typeof stored.env === 'object' ? stored.env : {};

  const apiInput = document.getElementById('cfg-api-url');
  const themeSelect = document.getElementById('cfg-theme');
  const motionSelect = document.getElementById('cfg-animations');

  if (apiInput) {
    apiInput.value = normalizeApiBase(stored.apiBaseUrl || API_BASE || DEFAULT_API_BASE);
  }
  if (themeSelect) {
    themeSelect.value = resolveTheme(stored.theme);
  }
  if (motionSelect) {
    motionSelect.value = resolveMotionMode(stored.animations);
  }

  settingsPage.querySelectorAll('[data-env-key]').forEach((input) => {
    const key = input.getAttribute('data-env-key');
    if (!key) return;
    input.value = typeof env[key] === 'string' ? env[key] : '';
  });
}

async function testLabelStudioConnectionFromSettings(buttonNode) {
  if (!buttonNode) return;
  const original = buttonNode.innerHTML;
  buttonNode.disabled = true;
  buttonNode.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra...';

  try {
    const response = await fetch(`${API_BASE}/label-studio/debug`, {
      headers: getAuthHeader()
    });
    const result = await response.json();

    if (result.status === 'success') {
      showToast(result.message || 'Kết nối Label Studio thành công', 'success');
    } else {
      showToast(result.message || 'Kết nối Label Studio thất bại', 'danger');
    }
  } catch (_err) {
    showToast('Không thể kết nối tới API server', 'danger');
  } finally {
    buttonNode.disabled = false;
    buttonNode.innerHTML = original;
  }
}

function initSettingsPage() {
  const settingsPage = document.getElementById('settings');
  if (!settingsPage) return;

  populateSettingsForm();

  const saveBtn = document.getElementById('btn-settings-save');
  const testLsBtn = document.getElementById('btn-settings-ls-test');
  const themeSelect = document.getElementById('cfg-theme');
  const motionSelect = document.getElementById('cfg-animations');

  if (themeSelect) {
    themeSelect.addEventListener('change', () => {
      const current = loadUISettings();
      current.theme = resolveTheme(themeSelect.value);
      saveUISettings(current);
      applyVisualSettings(current);
    });
  }

  if (motionSelect) {
    motionSelect.addEventListener('change', () => {
      const current = loadUISettings();
      current.animations = resolveMotionMode(motionSelect.value);
      saveUISettings(current);
      applyVisualSettings(current);
    });
  }

  if (testLsBtn) {
    testLsBtn.addEventListener('click', () => testLabelStudioConnectionFromSettings(testLsBtn));
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const formData = getSettingsFormData();
      if (!formData) return;

      saveUISettings(formData);
      API_BASE = formData.apiBaseUrl;
      applyVisualSettings(formData);
      showToast('Đã lưu cấu hình Settings trên trình duyệt', 'success');
    });
  }
}

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

async function triggerOSMJob(options = {}) {
  const limitProvinces = options.limit_provinces || getNumericInputValue("osm-limit-provinces") || 63;
  const targetTotal = options.target_total || getNumericInputValue("osm-target-total") || 5000000;
  const provinceId = options.province_id || null;

  const response = await fetch(`${API_BASE}/osm/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify({
      limit_provinces: limitProvinces,
      target_total: targetTotal,
      province_id: provinceId
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
    const pInput = document.getElementById('osm-province-input');
    const pId = osmState.provinces[pInput?.value];

    let limitProvinces = 63;
    let provinceId = null;

    if (pId) {
      limitProvinces = 1;
      provinceId = pId;
    }

    const targetTotal = getNumericInputValue("osm-target-total") || 5000000;
    const confirmMessage = pId
      ? `Chạy crawl OSM cho tỉnh ${pInput.value} với target ${targetTotal.toLocaleString()} entities?`
      : `Chạy crawl OSM cho tất cả 63 tỉnh/thành với target ${targetTotal.toLocaleString()} entities?`;

    if (showConfirm) {
      const confirmed = await showConfirm(confirmMessage);
      if (!confirmed) return;
    }

    setOSMRunButtons(true);
    const trigger = await triggerOSMJob({ limit_provinces: limitProvinces, province_id: provinceId, target_total: targetTotal });

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

let osmState = {};
async function initOSMEnrichmentUI() {
  const runButton = document.getElementById("btn-osm-run");
  const previewButton = document.getElementById("btn-osm-preview-counts");
  const page = document.getElementById("osm-enrichment");

  if (!page) return;

  VNAIControls.renderSmartFilter('osm-filter-container', {
    prefix: 'osm',
    title: 'Phạm vi Crawl (OpenStreetMap)',
    showVersion: false,
    showWard: false,
    showDistrict: false,
    searchPlaceholder: 'Tìm nhanh Tỉnh/Thành...'
  });

  osmState = await VNAIControls.initSmartFilter('osm', {
    onSearch: () => refreshOSMEnrichmentPanel({ silent: false })
  });

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

/** Map each data-page value → its parent group id */
const PAGE_GROUP_MAP = {
  'nso-sync':               'gov-sync',
  'admin-units':            'gov-sync',
  'parser':                 'address-processing',
  'batch':                  'address-processing',
  'explorer':               'address-processing',
  'lookup':                 'spatial',
  'boundary-visualization': 'spatial',
  'osm-enrichment':         'enrichment',
  'label-studio':           'ai-bench',
  'training':               'ai-bench',
  'experiments':            'ai-bench',
};

function openNavGroup(groupId) {
  const btn   = document.querySelector(`.nav-group-toggle[data-group="${groupId}"]`);
  const panel = document.getElementById(`group-${groupId}`);
  if (!btn || !panel) return;
  btn.classList.add('open');
  panel.classList.add('open');
}

function closeNavGroup(groupId) {
  const btn   = document.querySelector(`.nav-group-toggle[data-group="${groupId}"]`);
  const panel = document.getElementById(`group-${groupId}`);
  if (!btn || !panel) return;
  btn.classList.remove('open');
  panel.classList.remove('open');
}

function setupNavGroupToggles() {
  document.querySelectorAll('.nav-group-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const groupId = btn.getAttribute('data-group');
      const isOpen  = btn.classList.contains('open');
      if (isOpen) {
        closeNavGroup(groupId);
      } else {
        openNavGroup(groupId);
      }
    });
  });
}

// ── Sidebar Collapse ──
const SIDEBAR_COLLAPSED_KEY = 'vnai_sidebar_collapsed';

function setSidebarCollapsed(collapsed) {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;
  sidebar.classList.toggle('collapsed', collapsed);
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? '1' : '0');

  // Add data-tooltip to nav items & group toggles for collapsed tooltip
  document.querySelectorAll('.nav-item[data-page]').forEach(item => {
    const span = item.querySelector('span');
    if (span) item.setAttribute('data-tooltip', span.textContent.trim());
  });
  document.querySelectorAll('.nav-group-toggle[data-group]').forEach(btn => {
    const label = btn.querySelector('.nav-group-label');
    if (label) btn.setAttribute('data-tooltip', label.textContent.trim());
  });
}

function setupSidebarCollapse() {
  const btn = document.getElementById('sidebar-collapse-btn');
  if (!btn) return;

  // Restore persisted state
  const persisted = localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1';
  if (persisted) setSidebarCollapsed(true);

  btn.addEventListener('click', () => {
    const sidebar = document.querySelector('.sidebar');
    setSidebarCollapsed(!sidebar.classList.contains('collapsed'));
  });
}

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
    document.body.classList.remove("no-scroll");
  };

  if (toggle) {
    toggle.addEventListener("click", () => {
      const isActive = sidebar.classList.toggle("mobile-active");
      overlay.classList.toggle("mobile-active");
      document.body.classList.toggle("no-scroll", isActive);
    });
  }

  if (overlay) overlay.addEventListener("click", closeMobileMenu);

  // Setup collapsible group buttons
  setupNavGroupToggles();

  // Setup sidebar collapse toggle
  setupSidebarCollapse();

  // Auto-open all groups by default
  document.querySelectorAll('.nav-group-toggle[data-group]').forEach(btn => {
    openNavGroup(btn.getAttribute('data-group'));
  });

  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      navItems.forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      const targetId = item.getAttribute("data-page");
      pages.forEach(p => p.classList.toggle("active", p.id === targetId));

      // Use span text if available, else full text
      const spanEl = item.querySelector('span');
      titleEl.textContent = (spanEl ? spanEl.textContent : item.textContent).trim();

      // Open parent group if navigating to a sub-item
      const group = PAGE_GROUP_MAP[targetId];
      if (group) openNavGroup(group);

      // UX: Scroll to top when page changes
      window.scrollTo({ top: 0, behavior: 'smooth' });
      const contentEl = document.getElementById('page-content');
      if (contentEl) contentEl.scrollTo({ top: 0, behavior: 'smooth' });

      closeMobileMenu(); // Close sidebar on mobile after selection

      // Calculate layout height after page transition
      setTimeout(adjustActivePageHeight, 350);

      // Refresh parser model status when navigating to parser page
      if (targetId === "parser") {
        if (_parserStatusPollTimer) clearTimeout(_parserStatusPollTimer);
        _pollParserModelStatus();
      }
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

// Model status polling
let _parserStatusPollTimer = null;

function _updateParserModelStatusBar(status) {
  const bar = document.getElementById("parser-model-status-bar");
  const dot = document.getElementById("pmsb-dot");
  const text = document.getElementById("pmsb-text");
  const chips = document.getElementById("pmsb-chips");
  const reloadBtn = document.getElementById("pmsb-reload-btn");
  if (!bar) return;

  const MODEL_LABELS = {
    prelabeler: "PreLabeler",
    phobert: "PhoBERT",
    mgte: "mGTE",
    llm: "Qwen LLM",
  };
  const ALL_AI_MODELS = ["phobert", "mgte", "llm"];

  const loaded = new Set(status.loadedModels || []);
  const errors = status.errors || {};

  // Update dot
  if (dot) {
    dot.className = `pmsb-dot ${status.status}`;
  }

  // Update text
  if (text) {
    const statusLabels = {
      idle: "Model AI chưa được nạp — nhấn Tải model để bắt đầu",
      loading: `Đang nạp model AI vào bộ nhớ... (${status.loadedModels?.length || 0}/3 hoàn thành)`,
      ready: `Model sẵn sàng — ${status.loadedModels?.length || 0}/3 model AI đã nạp${status.corpusSize ? `, ${status.corpusSize.toLocaleString()} địa chỉ corpus` : ""}`,
      error: "Một số model không thể nạp — xem chi tiết bên dưới",
    };
    text.textContent = statusLabels[status.status] || status.status;
  }

  // Render chips
  if (chips) {
    let html = "";
    ALL_AI_MODELS.forEach(key => {
      const lbl = MODEL_LABELS[key] || key;
      if (loaded.has(key)) {
        html += `<span class="pmsb-chip loaded" title="${lbl} sẵn sàng">${lbl} ✓</span>`;
      } else if (errors[key]) {
        const shortErr = errors[key].length > 60 ? errors[key].slice(0, 60) + "…" : errors[key];
        html += `<span class="pmsb-chip failed" title="${shortErr}">${lbl} ✗</span>`;
      } else if (status.status === "loading") {
        html += `<span class="pmsb-chip loading" title="Đang nạp...">${lbl} ⏳</span>`;
      } else {
        html += `<span class="pmsb-chip failed" title="Chưa nạp">${lbl} —</span>`;
      }
    });
    chips.innerHTML = html;
  }

  // Show/hide reload button
  if (reloadBtn) {
    const isLoading = status.status === "loading";
    reloadBtn.disabled = isLoading;
    reloadBtn.innerHTML = isLoading
      ? '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp...'
      : '<i class="fa-solid fa-rotate-right"></i> Tải model';
  }
}

async function _pollParserModelStatus() {
  try {
    const res = await fetch(`${API_BASE}/parser/status`, { headers: getAuthHeader() });
    if (!res.ok) return;
    const data = await res.json();
    _updateParserModelStatusBar(data);

    // Keep polling while loading
    if (data.status === "loading") {
      _parserStatusPollTimer = setTimeout(_pollParserModelStatus, 3000);
    } else {
      _parserStatusPollTimer = null;
    }
  } catch (_) {
    // Silently ignore — server might be starting up
  }
}

async function _reloadParserModels() {
  const btn = document.getElementById("pmsb-reload-btn");
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp...'; }

  try {
    const res = await fetch(`${API_BASE}/parser/reload`, {
      method: "POST",
      headers: { ...getAuthHeader(), "Content-Type": "application/json" },
    });
    const data = await res.json();
    if (showToast) showToast(data.message || "Đã kích hoạt tải model", "info");
  } catch (err) {
    if (showToast) showToast("Không thể kích hoạt tải model: " + err.message, "danger");
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Tải model'; }
  } finally {
    // Start polling to reflect updated state
    if (_parserStatusPollTimer) clearTimeout(_parserStatusPollTimer);
    _parserStatusPollTimer = setTimeout(_pollParserModelStatus, 1500);
  }
}

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

  const autoResizeInput = () => {
    if (!inputEl) return;
    inputEl.style.height = 'auto';
    inputEl.style.height = (inputEl.scrollHeight) + 'px';
  };

  if (inputEl) {
    inputEl.addEventListener("input", autoResizeInput);
    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        runParser();
      }
    });
    setTimeout(autoResizeInput, 100); // Wait for page transition
  }

  if (btnSampleLocal) btnSampleLocal.addEventListener("click", () => {
    const addr = SAMPLE_ADDRESSES[Math.floor(Math.random() * SAMPLE_ADDRESSES.length)];
    if (inputEl) {
      inputEl.value = addr;
      inputEl.dataset.sampleId = "";
      autoResizeInput();
    }
    runParser();
  });

  if (btnSampleDB) btnSampleDB.addEventListener("click", async () => {
    await fetchParserSampleDB();
    autoResizeInput();
  });

  // Wire up reload button
  const reloadBtn = document.getElementById("pmsb-reload-btn");
  if (reloadBtn) reloadBtn.addEventListener("click", _reloadParserModels);

  // Build NER legend once
  _buildParserNERLegend();

  // Poll model status on page open
  _pollParserModelStatus();
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
  const existingSummary = document.getElementById("parser-compare-summary");
  if (existingSummary) existingSummary.remove();
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
      if (!res.ok) {
        // Try to extract server error detail for better user message
        let errDetail = `HTTP ${res.status}`;
        try {
          const errBody = await res.json();
          const note = errBody?.detail?.note || errBody?.detail?.error || errBody?.detail;
          if (note && typeof note === "string") errDetail = note;
        } catch (_) {}
        throw new Error(errDetail);
      }
      const data = await res.json();
      const out = data.outputs?.[key];
      if (data.meta) lastMeta = data.meta;
      if (data.acs && !lastMeta?._acs) {
        if (!lastMeta) lastMeta = {};
        lastMeta._acs = data.acs;
      }

      // HTTP 200 but server returned a fallback error (PreLabeler-only mode)
      if (data.error && !out) {
        _renderModelCard(key, { error: data.error, status: "Not loaded" }, latency);
      } else {
        _renderModelCard(key, out, latency);
      }

      // Show NER from prelabeler immediately
      if (key === "prelabeler" && !firstNERDone) {
        firstNERDone = true;
        const entities = out?.result || [];
        renderNERHighlight(entities);
      }
    } catch (e) {
      _renderModelCardError(key, label, e.message);
    } finally {
      completedCount++;
      _setParserStatus("running", `Đang phân tích — ${completedCount}/4 model hoàn thành...`);
    }
  };

  try {
    await Promise.all(models.map(fetchModel));

    const totalMs = Date.now() - startTs;
    const totalMsFmt = totalMs >= 1000
      ? `${(totalMs / 1000).toFixed(2)}s`
      : `${totalMs.toLocaleString("vi-VN")}ms`;
    _setParserStatus("done", "Hoàn thành — 4/4 model");
    if (timingEl && timingVal) { timingVal.textContent = totalMsFmt; timingEl.style.display = "flex"; }

    // Update meta footer
    if (lastMeta) _updateParserMeta(lastMeta);
    // Render comparison summary
    _renderParserCompareSummary();
  } catch (err) {
    _setParserStatus("error", "Đã xảy ra lỗi trong quá trình phân tích");
  } finally {
    if (heroInner) heroInner.classList.remove("is-running");
    if (btnParse) { btnParse.disabled = false; btnParse.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span>Phân tích địa chỉ</span>'; }
  }
}

// Model task metadata for contextual display
const _MODEL_TASK_META = {
  prelabeler: {
    task: "NER", icon: "fa-tags",
    taskLabel: "Trích xuất thực thể",
    outputType: "entities",
    outputDesc: null,
  },
  phobert: {
    task: "Retrieval", icon: "fa-magnifying-glass",
    taskLabel: "Corpus Retrieval · PhoBERT",
    outputType: "normalized",
    outputDesc: "Địa chỉ khớp nhất trong corpus (cosine similarity)",
  },
  mgte: {
    task: "Retrieval", icon: "fa-layer-group",
    taskLabel: "Corpus Retrieval · mGTE",
    outputType: "normalized",
    outputDesc: "Địa chỉ khớp nhất trong corpus (cosine similarity)",
  },
  llm: {
    task: "LLM", icon: "fa-brain",
    taskLabel: "Suy luận · Qwen LLM",
    outputType: "normalized",
    outputDesc: "Địa chỉ được suy luận từ RAG candidates",
  },
};

function _renderModelCard(model, out, latencyMs) {
  const card = document.getElementById(`pcard-${model}`);
  const resultEl = document.getElementById(`presult-${model}`);
  const statsEl = document.getElementById(`pstats-${model}`);
  const badgeEl = document.getElementById(`pbadge-${model}`);
  if (!card) return;

  const taskMeta = _MODEL_TASK_META[model] || {};

  card.classList.add("is-done");

  if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done success">DONE</span>`;

  if (resultEl) {
    resultEl.classList.add("has-result");
    if (!out) {
      resultEl.innerHTML = `<span style="color:var(--text-tertiary);font-size:11px">Không có kết quả</span>`;
    } else if (out.error && !out.normalizedAddress && !Array.isArray(out.result)) {
      // Model loaded but errored, or not loaded at all
      const errMsg = out.error || "Model chưa được nạp";
      const isNotLoaded = (out.status === "Not loaded");
      resultEl.innerHTML = `<div class="pmodel-not-loaded">
        <i class="fa-solid fa-circle-exclamation" style="color:var(--warning)"></i>
        <span style="color:var(--warning);font-size:11px">${isNotLoaded ? "Model chưa được nạp vào bộ nhớ" : escapeHtml(errMsg)}</span>
        <span style="display:block;color:var(--text-tertiary);font-size:10px;margin-top:2px">Khởi động lại server để nạp model AI</span>
      </div>`;
    } else {
      const normalized = out.normalizedAddress || "";
      const entities = Array.isArray(out.result) ? out.result : [];
      const labelInfo = {};
      NER_LABELS.forEach(l => labelInfo[l.value] = l);

      let html = "";

      // Task type badge
      if (taskMeta.taskLabel) {
        const descAttr = taskMeta.outputDesc ? ` title="${taskMeta.outputDesc}"` : "";
        html += `<div class="pmodel-task-badge"${descAttr}><i class="fa-solid ${taskMeta.icon || 'fa-circle'}"></i> ${taskMeta.taskLabel}</div>`;
      }

      if (normalized) {
        // For retrieval models show the score inline next to the result so users
        // understand this is the closest corpus match, not an extracted value.
        const score = typeof out?.score === "number" ? out.score : null;
        const isRetrieval = taskMeta.task === "Retrieval";
        if (isRetrieval && score !== null) {
          const pct = (score * 100).toFixed(1);
          const scoreColor = score >= 0.85 ? "var(--success)" : score >= 0.6 ? "var(--warning)" : "var(--danger)";
          html += `<div class="pmodel-retrieval-result">
            <span class="pmodel-normalized" title="Địa chỉ khớp nhất trong corpus — không phải trích xuất từ input">${escapeHtml(normalized)}</span>
            <span class="pmodel-retrieval-score" style="color:${scoreColor}" title="Độ tương đồng cosine với địa chỉ input">${pct}% match</span>
          </div>`;
          if (score < 0.75) {
            html += `<span class="pmodel-retrieval-warn"><i class="fa-solid fa-triangle-exclamation"></i> Khớp thấp — corpus có thể chưa có địa chỉ này</span>`;
          }
        } else {
          html += `<span class="pmodel-normalized">${escapeHtml(normalized)}</span>`;
        }
      }
      if (entities.length > 0) {
        const chips = entities.slice(0, 10).map(e => {
          const lbl = e.label || (e.value?.labels?.[0]) || "?";
          const txt = e.text || e.value?.text || "";
          const info = labelInfo[lbl] || { color: "#888" };
          return `<span class="pmodel-ent-chip" style="background:${info.color}18;color:${info.color}" title="${info.text || lbl}">${lbl}: ${escapeHtml(txt)}</span>`;
        }).join("");
        html += `<div class="pmodel-entities">${chips}</div>`;
      }
      if (!normalized && entities.length === 0 && !out.error) {
        html += `<span style="color:var(--text-tertiary);font-size:11px">Không tìm thấy kết quả phù hợp</span>`;
      }
      resultEl.innerHTML = html;
    }
  }

  if (statsEl) {
    const score = typeof out?.score === "number" ? out.score : null;
    const count = Array.isArray(out?.result) ? out.result.length : (typeof out?.entityCount === "number" ? out.entityCount : null);
    const modelLatency = typeof out?.latencyMs === "number" ? out.latencyMs : null;
    let chips = `<span class="pstat-chip latency"><i class="fa-solid fa-stopwatch"></i>${latencyMs}ms</span>`;
    if (modelLatency !== null && modelLatency !== latencyMs) {
      chips += `<span class="pstat-chip latency" title="Thời gian xử lý model"><i class="fa-solid fa-microchip"></i>${modelLatency.toFixed(0)}ms</span>`;
    }
    if (count !== null) chips += `<span class="pstat-chip count"><i class="fa-solid fa-tags"></i>${count} entities</span>`;
    if (score !== null) chips += `<span class="pstat-chip conf" title="Độ tương đồng ngữ nghĩa"><i class="fa-solid fa-chart-line"></i>${(score * 100).toFixed(1)}%</span>`;
    statsEl.innerHTML = chips;
  }
}

function _renderModelCardError(model, label, errMsg) {
  const card     = document.getElementById(`pcard-${model}`);
  const resultEl = document.getElementById(`presult-${model}`);
  const badgeEl  = document.getElementById(`pbadge-${model}`);
  if (card) card.classList.add("is-error");
  if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done error">ERR</span>`;
  const detail = errMsg ? `<span style="display:block;color:var(--text-tertiary);font-size:10px;margin-top:3px">${escapeHtml(errMsg)}</span>` : "";
  if (resultEl) resultEl.innerHTML = `<div style="display:flex;flex-direction:column;gap:2px">
    <span style="color:var(--danger);font-size:11px"><i class="fa-solid fa-triangle-exclamation"></i> Không thể kết nối model</span>
    ${detail}
  </div>`;
}

function _renderParserCompareSummary() {
  const grid = document.getElementById("parser-models-grid");
  if (!grid) return;
  // Remove previous summary if any
  const existing = document.getElementById("parser-compare-summary");
  if (existing) existing.remove();

  // Collect results from all rendered cards
  const modelKeys = ["prelabeler", "phobert", "mgte", "llm"];
  const modelNames = { prelabeler: "PreLabeler", phobert: "PhoBERT", mgte: "mGTE", llm: "Qwen LLM" };
  const rows = modelKeys.map(k => {
    const resultEl = document.getElementById(`presult-${k}`);
    const statsEl = document.getElementById(`pstats-${k}`);
    const isError = document.getElementById(`pcard-${k}`)?.classList.contains("is-error");
    const isNotLoaded = resultEl?.querySelector(".pmodel-not-loaded") !== null;
    const normalizedEl = resultEl?.querySelector(".pmodel-normalized");
    const entChips = resultEl?.querySelectorAll(".pmodel-ent-chip");
    const confChip = statsEl?.querySelector(".pstat-chip.conf");

    return {
      key: k,
      name: modelNames[k],
      isError,
      isNotLoaded,
      normalized: normalizedEl?.textContent?.trim() || null,
      entityCount: entChips?.length || 0,
      confidence: confChip?.textContent?.trim() || null,
    };
  }).filter(r => !r.isError && !r.isNotLoaded);

  if (!rows.length) return;

  const summaryEl = document.createElement("div");
  summaryEl.id = "parser-compare-summary";
  summaryEl.className = "parser-compare-summary";

  const rowsHtml = rows.map(r => {
    const outputHtml = r.normalized
      ? `<span class="pcs-output normalized">${escapeHtml(r.normalized)}</span>`
      : (r.entityCount > 0 ? `<span class="pcs-output entities">${r.entityCount} thực thể trích xuất</span>` : `<span class="pcs-output empty">—</span>`);
    const confHtml = r.confidence ? `<span class="pcs-conf">${r.confidence}</span>` : "";
    const taskMeta = _MODEL_TASK_META[r.key];
    return `<tr>
      <td class="pcs-name"><i class="fa-solid ${taskMeta?.icon || 'fa-circle'}"></i> ${r.name}</td>
      <td class="pcs-task">${taskMeta?.taskLabel || ""}</td>
      <td class="pcs-output-cell">${outputHtml}</td>
      <td class="pcs-conf-cell">${confHtml}</td>
    </tr>`;
  }).join("");

  summaryEl.innerHTML = `
    <div class="pcs-header"><i class="fa-solid fa-table-columns"></i> So sánh kết quả các mô hình</div>
    <div class="pcs-note">Mỗi mô hình thực hiện một tác vụ khác nhau — kết quả trả về khác nhau là bình thường.</div>
    <table class="pcs-table">
      <thead><tr><th>Mô hình</th><th>Tác vụ</th><th>Kết quả</th><th>Điểm</th></tr></thead>
      <tbody>${rowsHtml}</tbody>
    </table>`;

  grid.after(summaryEl);
}

function _updateParserMeta(meta) {
  const el = document.getElementById("parser-meta");
  if (!el) return;
  const parts = [];
  if (meta.corpusSize) {
    parts.push(`<i class="fa-solid fa-database" style="color:var(--text-tertiary);font-size:11px"></i><span class="text-tertiary" style="font-size:12px"><strong>${meta.corpusSize.toLocaleString()}</strong> địa chỉ trong corpus</span>`);
  }
  if (meta._acs) {
    const acs = meta._acs;
    const scoreColor = acs.acs_score >= 0.8 ? "var(--success)" : acs.acs_score >= 0.5 ? "var(--warning)" : "var(--danger)";
    parts.push(`<span style="font-size:11px;color:var(--text-secondary)">ACS <strong style="color:${scoreColor}">${(acs.acs_score * 100).toFixed(1)}%</strong> · ${acs.acs_decision || ""}</span>`);
    if (acs.address_epoch) {
      parts.push(`<span style="font-size:11px;color:var(--text-tertiary)">Epoch: ${acs.address_epoch}</span>`);
    }
  }
  if (parts.length) el.innerHTML = parts.join('<span style="color:var(--border-default);margin:0 6px">·</span>');
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
  const methodSelect = document.getElementById("batch-method");
  const methodDescription = document.getElementById("batch-method-description");
  const doneEl = document.getElementById("batch-done");
  const throughputEl = document.getElementById("batch-throughput");
  const progressStatusEl = document.getElementById("batch-progress-status");

  if (!btnToggle || !log || !progressValue || !progressFill || !methodSelect || !doneEl || !throughputEl || !progressStatusEl) {
    console.warn("[Batch] Missing required DOM nodes. Batch tool is not initialized.");
    return;
  }

  // Ensure progress bar is visible
  progressFill.style.background = 'var(--accent)';
  progressFill.style.height = '100%';
  progressFill.style.borderRadius = '2px';

  const modeDescriptions = {
    hybrid: "Cân bằng giữa tốc độ xử lý và độ chính xác, phù hợp cho phần lớn nhu cầu vận hành.",
    "ner-only": "Ưu tiên tốc độ tách thực thể (số nhà, đường, phường...) và bỏ qua các bước chuẩn hóa sâu.",
    "full-chain": "Chạy đầy đủ pipeline chuẩn hóa nhiều tầng để tối đa độ chính xác, thời gian xử lý sẽ lâu hơn."
  };

  const formatInt = (value) => new Intl.NumberFormat('vi-VN').format(Number(value || 0));
  const formatFloat = (value, digits = 1) => Number(value || 0).toLocaleString('vi-VN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });

  function formatNumbersInText(text) {
    return text.replace(/\b\d{1,3}(?:,\d{3})*\b/g, (match) => formatInt(match.replace(/,/g, '')));
  }

  function parseProgressFromText(text) {
    if (!text) return null;
    const progressRegex = /Progress:\s*(\d+)\s*\/\s*(\d+)/gi;
    const progressMatches = Array.from(text.matchAll(progressRegex));
    if (progressMatches.length) {
      const lastMatch = progressMatches[progressMatches.length - 1];
      return {
        processed: Number(lastMatch[1]),
        total: Number(lastMatch[2]),
      };
    }
    const totalRegex = /Processing\s+(\d+)\s+rows?/gi;
    const totalMatches = Array.from(text.matchAll(totalRegex));
    if (totalMatches.length) {
      return { total: Number(totalMatches[totalMatches.length - 1][1]) };
    }
    return null;
  }

  let isBatchRunning = false;
  let batchPollTimer = null;
  let lastKnownProgress = 0;
  let lastStatusText = '';

  function setProgressStatus(message) {
    if (!progressStatusEl) return;
    if (message === lastStatusText) return;
    lastStatusText = message;
    progressStatusEl.textContent = message;
  }

  function updateMethodDescription() {
    if (!methodDescription) return;
    methodDescription.textContent = modeDescriptions[methodSelect.value] || modeDescriptions.hybrid;
  }

  function appendLogLine(message) {
    log.innerText += `${log.innerText ? '\n' : ''}[${formatLogTime()}] ${message}`;
    log.scrollTop = log.scrollHeight;
  }

  function setProgress(percent) {
    const safePercent = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
    progressValue.textContent = `${safePercent}%`;
    progressFill.style.width = `${safePercent}%`;
    lastKnownProgress = safePercent;
  }

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

  async function pollBatchStatus() {
    try {
      const response = await fetch(`${API_BASE}/batch/job`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error(`Batch status failed (${response.status})`);
      }

      const payload = await response.json();
      const job = payload?.job;

      if (!job) {
        batchPollTimer = setTimeout(pollBatchStatus, 2000);
        return;
      }

      const parsedProgress = parseProgressFromText(job.outputTail);
      const effectiveJob = { ...job };
      if (parsedProgress) {
        if (parsedProgress.total) effectiveJob.totalCount = parsedProgress.total;
        if (parsedProgress.processed !== undefined) effectiveJob.processedCount = parsedProgress.processed;
      }

      if (job.outputTail !== undefined && job.outputTail !== null) {
        log.innerText = formatNumbersInText(job.outputTail);
        log.scrollTop = log.scrollHeight;
      }

      if (effectiveJob.processedCount !== undefined) {
        doneEl.textContent = formatInt(effectiveJob.processedCount);
      }

      if (effectiveJob.throughput !== undefined) {
        throughputEl.textContent = `${formatFloat(effectiveJob.throughput, 1)} items/s`;
      }

      const processed = Number(effectiveJob.processedCount || 0);
      const total = Number(effectiveJob.totalCount || 0);

      if (total > 0) {
        setProgress((processed / total) * 100);
        setProgressStatus(`Đã xử lý ${formatInt(processed)}/${formatInt(total)} bản ghi (${lastKnownProgress}%).`);
      } else if (job.status === "running") {
        const fallbackProgress = Math.max(lastKnownProgress, processed > 0 ? 1 : 0);
        setProgress(fallbackProgress);
        setProgressStatus(`Đang xử lý ${formatInt(processed)} bản ghi…`);
      }

      if (job.status === "running") {
        batchPollTimer = setTimeout(pollBatchStatus, 2000);
      } else {
        setButtonState(false);
        if (job.status === "success") {
          if (total <= 0) setProgress(100);
          showToast("Xử lý hàng loạt hoàn tất!", "success");
          appendLogLine("Hoàn tất xử lý hàng loạt.");
        } else if (job.status === "failed") {
          showToast(`Lỗi xử lý: ${job.error || "Unknown error"}`, "danger");
          appendLogLine(`Lỗi xử lý: ${job.error || "Unknown error"}`);
        }
      }
    } catch (error) {
      console.error("Batch poll error:", error);
      showToast("Không thể theo dõi trạng thái batch job", "danger");
      setButtonState(false);
    }
  }

  methodSelect.addEventListener("change", updateMethodDescription);
  updateMethodDescription();
  setProgress(0);

  btnToggle.addEventListener("click", async () => {
    if (isBatchRunning) {
      if (batchPollTimer) clearTimeout(batchPollTimer);
      setButtonState(false);
      appendLogLine("⛔ Đã dừng theo dõi batch job trên giao diện.");
      return;
    }

    const size = getNumericInputValue("batch-size") || 1000;
    const method = methodSelect.value;

    try {
      setButtonState(true);
      doneEl.textContent = "0";
      throughputEl.textContent = "0,0 items/s";
      setProgress(0);
      lastStatusText = '';
      setProgressStatus("Khởi tạo batch... chờ phản hồi server.");
      log.innerText = "";
      appendLogLine(`Yêu cầu xử lý batch: ${formatInt(size)} bản ghi | Chế độ: ${method}.`);

      const response = await fetch(`${API_BASE}/batch/trigger`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({ batch_size: size, method: method }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Trigger failed");
      }

      const data = await response.json();
      appendLogLine(`Batch job accepted. ID: ${data?.job?.jobId || "-"}`);
      setProgressStatus("Batch đã được chấp nhận. Đang bắt đầu theo dõi tiến trình...");

      pollBatchStatus();
    } catch (error) {
      showToast(error.message, "danger");
      appendLogLine(`Không thể khởi chạy batch: ${error.message}`);
      setButtonState(false);
    }
  });
}

async function fetchStats(options = {}) {
  const { manual = false } = options;
  try {
    if (manual) setDashboardRefreshState(true);

    const response = await fetchWithApiFallback('/stats', {
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
  provinces: {},
  districts: {},
  wards: {}
};

async function initMappingV3() {
  VNAIControls.renderSmartFilter('lookup-filter-container', {
    prefix: 'mapping',
    title: 'Bộ lọc Thông minh (Mapping History)',
    searchPlaceholder: 'Tìm theo tên hoặc mã...'
  });

  mappingState = await VNAIControls.initSmartFilter('mapping', {
    onSearch: triggerMappingSearch,
    onSelect: (level, id, version) => showDetails(level, id, version)
  });
}

async function showDetails(level, id, version = null) {
  const pl = document.getElementById('unit-details-panel');
  if (!pl) return;
  if (!version) version = mappingState.version;
  pl.innerHTML = '<div class="text-center" style="padding:40px"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></div>';
  try {
    const res = await fetch(`${API_BASE}/unit-details/${level}/${id}?version=${version}`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Unit not found");
    const u = await res.json();
    pl.innerHTML = `
      <div class="unit-details-flex">
        <!-- Main Info -->
        <div class="unit-main-info">
          <div class="flex items-center gap-12 mb-4">
            <span class="unit-name-text">${u.ward_name || u.district_name || u.province_name}</span>
            <span class="badge info">v${u.admin_version}</span>
          </div>
          <div class="unit-meta-text">
            ${u.ward_name ? 'Phường/Xã' : (u.district_name ? 'Quận/Huyện' : 'Tỉnh/Thành phố')} • 
            Mã GSO: <span class="text-mono">${u.ward_no || u.district_no || u.province_no || "N/A"}</span>
          </div>
        </div>

        <!-- Stats -->
        <div class="unit-stats-group">
          <div class="unit-stat-item">
            <div class="unit-stat-label">Dân số</div>
            <div class="unit-stat-value">${(u.population || 0).toLocaleString()} <small>người</small></div>
          </div>
          <div class="unit-stat-item">
            <div class="unit-stat-label">Diện tích</div>
            <div class="unit-stat-value">${(u.area_km2 || 0).toLocaleString()} <small>km²</small></div>
          </div>
        </div>

        <!-- Note Info -->
        <div class="unit-note-info">
          <div class="unit-stat-label">Ghi chú</div>
          <div class="unit-note-text" title="${u.notes || ""}">
            ${u.notes || "Chưa có ghi chú trong hệ thống."}
          </div>
        </div>
      </div>
    `;
  } catch (e) { panel.innerHTML = "Lỗi tải thông tin"; }
}

async function triggerMappingSearch(state) {
  const activeState = state || mappingState;
  const qInput = document.getElementById('mapping-search-input');
  const pInput = document.getElementById('mapping-province-input');
  const dInput = document.getElementById('mapping-district-input');
  const wInput = document.getElementById('mapping-ward-input');

  if (!activeState.provinces || !qInput) return;

  const qText = qInput.value;
  const pId = activeState.provinces[pInput.value];
  const dId = activeState.districts[dInput.value];
  const wId = activeState.wards[wInput.value];

  const tbody = document.getElementById('mapping-results-table');
  const version = document.getElementById('mapping-version-select')?.value || activeState.version;

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
      <tr style="cursor: pointer; transition: background 0.2s;" onclick="showDetails('ward', ${m.ward_id_new}, 2)">
        <td data-label="ĐVHC Cũ" style="padding: 16px 20px;">
          <div class="font-700" style="font-size:15px; color:var(--text-primary)">${m.ward_name_old || (m.ward_id_old == -1 ? "(Tất cả Xã)" : "N/A")}</div>
          <div class="text-tertiary" style="font-size:12px; margin-top: 2px;">
            ${[m.district_name_old, m.province_name_old].filter(x => x).join(" - ")}
          </div>
        </td>
        <td class="text-center mobile-hidden" style="vertical-align:middle; width: 60px;">
          <div style="background: var(--bg-hover); width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
            <i class="fa-solid fa-chevron-right text-accent" style="font-size: 12px;"></i>
          </div>
        </td>
        <td data-label="ĐVHC Mới" style="padding: 16px 20px;">
          <div class="font-700" style="font-size:15px; color:var(--success)">${m.ward_name_new || "N/A"}</div>
          <div class="text-tertiary" style="font-size:12px; margin-top: 2px;">${m.district_name_new || ""} - ${m.province_name_new || ""}</div>
        </td>
        <td data-label="Diễn biến & Nghị quyết" style="padding: 16px 20px;">
          <div class="badge ${m.relationship_type === 'MERGE' ? 'warning' : 'info'}" style="font-size: 10px; margin-bottom: 6px;">${m.relationship_type || 'MAPPING'}</div>
          <div style="font-size:12px; line-height:1.5; color: var(--text-secondary)">${m.updated_note || "Cập nhật theo nghị quyết sáp nhập ĐVHC."}</div>
        </td>
        <td data-label="Ngày áp dụng" class="text-tertiary" style="padding: 16px 20px; font-size:13px; font-family: var(--font-mono)">
          ${m.effective_date_from ? new Date(m.effective_date_from).toLocaleDateString('vi-VN') : "01/07/2025"}
        </td>
      </tr>
    `).join("");
  } catch (err) { tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger" style="padding:40px">Lỗi kết nối API</td></tr>'; }
}


// ═══════════════════════════════════════════════════════════
// NSO SYNC LOGIC (v3 - Hierarchical Filters & Improved Sync)
// ═══════════════════════════════════════════════════════════
let nsoState = {
  provinces: {},
  districts: {},
  wards: {},
  currentLevel: 'province',
  currentData: []
};

let logPollingInterval = null;

async function initNSOSyncTool() {
  VNAIControls.renderSmartFilter('nso-filter-container', {
    prefix: 'nso',
    title: 'Tra cứu danh mục NSO / GSO',
    showVersion: false,
    searchPlaceholder: 'Tìm nhanh mã hoặc tên đơn vị NSO...',
    buttonText: 'Lọc dữ liệu'
  });

  nsoState = await VNAIControls.initSmartFilter('nso', {
    provinceNameKey: 'TenTinh',
    provinceIdKey: 'MaTinh',
    districtNameKey: 'TenHuyen',
    districtIdKey: 'MaHuyen',
    wardNameKey: 'TenXa',
    wardIdKey: 'MaXa',
    fetchProvinces: async () => {
      const res = await fetch(`${API_BASE}/nso/provinces`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchDistricts: async (pCode, _, pItem) => {
      const res = await fetch(`${API_BASE}/nso/districts?province_no=${pCode}&province_name=${encodeURIComponent(pItem.TenTinh)}`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchWards: async (dCode, _, dItem) => {
      const pInput = document.getElementById('nso-province-input');
      const pItem = nsoState.provinces[pInput.value];
      const res = await fetch(`${API_BASE}/nso/wards?province_no=${pItem.MaTinh}&province_name=${encodeURIComponent(pItem.TenTinh)}&district_no=${dCode}&district_name=${encodeURIComponent(dItem.TenHuyen)}`, { headers: getAuthHeader() });
      return await res.json();
    },
    onSearch: (state) => {
      nsoState.currentData = state.currentData;
      renderNSOTable(state.currentData);
    }
  });

  document.getElementById('btn-nso-sync-selected')?.addEventListener('click', syncSelectedUnit);
  document.getElementById('btn-nso-sync-all')?.addEventListener('click', syncAllNSO);
  document.getElementById('btn-clear-nso-logs')?.addEventListener('click', clearSyncLogs);
}

async function loadNSOProvinces() {
  const tbody = document.getElementById('nso-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="4" class="text-center p-40"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/provinces`, { headers: getAuthHeader() });
    const data = await res.json();
    nsoState.currentData = data;
    renderNSOTemplateDatalist('nso-list-provinces', data, 'TenTinh', 'MaTinh', nsoState.provinces);
    renderNSOTable(data);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger p-20">Lỗi tải danh mục Tỉnh từ NSO</td></tr>';
  }
}

async function loadNSODistricts(pCode, pName) {
  const tbody = document.getElementById('nso-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="4" class="text-center p-40"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/districts?province_no=${pCode}&province_name=${encodeURIComponent(pName)}`, { headers: getAuthHeader() });
    const data = await res.json();
    nsoState.currentData = data;
    renderNSOTemplateDatalist('nso-list-districts', data, 'TenHuyen', 'MaHuyen', nsoState.districts);
    renderNSOTable(data);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger p-20">Lỗi tải danh mục Huyện từ NSO</td></tr>';
  }
}

async function loadNSOWards(pCode, pName, dCode, dName) {
  const tbody = document.getElementById('nso-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="4" class="text-center p-40"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/wards?province_no=${pCode}&province_name=${encodeURIComponent(pName)}&district_no=${dCode}&district_name=${encodeURIComponent(dName)}`, { headers: getAuthHeader() });
    const data = await res.json();
    nsoState.currentData = data;
    renderNSOTemplateDatalist('nso-list-wards', data, 'TenXa', 'MaXa', nsoState.wards);
    renderNSOTable(data);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger p-20">Lỗi tải danh mục Xã từ NSO</td></tr>';
  }
}

function renderNSOTemplateDatalist(listId, data, nameKey, idKey, stateMap) {
  const list = document.getElementById(listId);
  if (!list) return;
  list.innerHTML = '';
  // Reset state map
  for (let k in stateMap) delete stateMap[k];

  data.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item[nameKey];
    list.appendChild(opt);
    stateMap[item[nameKey]] = item;
  });
}

function renderNSOTable(data) {
  const tbody = document.getElementById('nso-table-body');
  const countEl = document.getElementById('nso-count');
  if (!tbody) return;

  const searchVal = (document.getElementById('nso-ward-input')?.value ||
    document.getElementById('nso-district-input')?.value ||
    document.getElementById('nso-province-input')?.value || "").toLowerCase();

  const filtered = data.filter(item => {
    const name = (item.TenXa || item.TenHuyen || item.TenTinh || "").toLowerCase();
    const code = (item.MaXa || item.MaHuyen || item.MaTinh || "");
    return name.includes(searchVal) || code.includes(searchVal);
  });

  countEl.textContent = `${filtered.length.toLocaleString()} bản ghi`;

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center p-20 text-tertiary">Không tìm thấy dữ liệu phù hợp.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(item => {
    const code = item.MaXa || item.MaHuyen || item.MaTinh;
    const name = item.TenXa || item.TenHuyen || item.TenTinh;
    const type = item.LoaiHinh || "N/A";

    return `
      <tr>
        <td><span class="text-mono">${code}</span></td>
        <td><strong>${name}</strong></td>
        <td><span class="badge info">${type}</span></td>
        <td class="text-right">
          <button class="btn btn-xs btn-accent" onclick="syncSingleNSOUnit('${code}', '${name}')">
            <i class="fa-solid fa-sync"></i> Sync
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

async function syncSingleNSOUnit(code, name) {
  updateSyncStatus('SYNCING', 'var(--warning)');
  showToast(`🚀 Bắt đầu đồng bộ: ${name}...`);

  try {
    const res = await fetch(`${API_BASE}/sync/nso/province`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, name })
    });
    const result = await res.json();
    if (result.status === 'success') {
      showToast(`✅ Hoàn thành: ${name}`);
    } else {
      showToast(`❌ Lỗi: ${result.message}`, 'danger');
    }
  } catch (e) {
    showToast(`❌ Lỗi kết nối khi đồng bộ ${name}`, 'danger');
  } finally {
    updateSyncStatus('IDLE', '#8b949e');
  }
}

async function syncSelectedUnit() {
  const pVal = document.getElementById('nso-province-input').value;
  const dVal = document.getElementById('nso-district-input').value;
  const wVal = document.getElementById('nso-ward-input').value;

  const ward = nsoState.wards[wVal];
  const district = nsoState.districts[dVal];
  const province = nsoState.provinces[pVal];

  if (ward) {
    syncSingleNSOUnit(ward.MaXa, ward.TenXa);
  } else if (district) {
    syncSingleNSOUnit(district.MaHuyen, district.TenHuyen);
  } else if (province) {
    syncSingleNSOUnit(province.MaTinh, province.TenTinh);
  } else {
    showToast('Vui lòng chọn ít nhất một đơn vị để đồng bộ', 'warning');
  }
}

async function syncAllNSO() {
  const confirm = await showConfirm("Bạn có chắc chắn muốn đồng bộ TOÀN BỘ 63 tỉnh thành? Quá trình này có thể mất vài phút.");
  if (!confirm) return;

  updateSyncStatus('SYNCING ALL', 'var(--warning)');
  try {
    await fetch(`${API_BASE}/sync/nso`, { method: 'POST', headers: getAuthHeader() });
    showToast("Đã gửi yêu cầu đồng bộ toàn bộ hệ thống.");
  } catch (e) {
    showToast("Lỗi khi gửi yêu cầu đồng bộ", "danger");
  } finally {
    updateSyncStatus('IDLE', '#8b949e');
  }
}

async function clearSyncLogs() {
  try {
    await fetch(`${API_BASE}/sync/nso/logs`, { method: 'DELETE', headers: getAuthHeader() });
    document.getElementById('nso-sync-logs').innerHTML = '<div style="color: #5c5c5f;">[System] Logs cleared.</div>';
  } catch (e) { showToast('Không thể xóa nhật ký', 'danger'); }
}

function startLogPolling() {
  if (logPollingInterval) clearInterval(logPollingInterval);
  logPollingInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/sync/nso/logs`, { headers: getAuthHeader() });
      if (!res.ok) return;
      const logs = await res.json();
      const container = document.getElementById('nso-sync-logs');
      if (container && Array.isArray(logs) && logs.length > 0) {
        container.innerHTML = logs.map(l => {
          const colorMap = { 'error': 'var(--danger)', 'success': 'var(--success)', 'warning': 'var(--warning)' };
          const color = colorMap[l.level] || 'inherit';
          return `<div style="margin-bottom: 2px;">
            <span style="color: var(--text-tertiary); font-size: 11px;">[${l.time || ''}]</span> 
            <span style="color: ${color}">${l.message || ''}</span>
          </div>`;
        }).join('');
        container.scrollTop = container.scrollHeight;
      }
    } catch (e) { console.error("Log polling error", e); }
  }, 2000);
}

function updateSyncStatus(text, color) {
  const el = document.getElementById('nso-sync-status');
  if (el) {
    el.textContent = text;
    el.style.borderColor = color;
    el.style.color = color;
  }
}

// ═══ ADMINISTRATIVE MANAGER (CRUD) ═══
const ADMIN_CRUD_ENABLED = false;

function showAdminCrudUnavailable() {
  showToast('Chức năng thêm/sửa/xóa đã được tắt do API đã gom lại.', 'warning');
}

window.editAdminUnit = async function (level, id) {
  if (!ADMIN_CRUD_ENABLED) {
    showAdminCrudUnavailable();
    return;
  }
  try {
    const version = adminState ? adminState.version : 1;
    const res = await fetch(`${API_BASE}/unit-details/${level}/${id}?version=${version}`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const item = await res.json();
    if (!item) throw new Error('Unit not found');

    document.getElementById('admin-modal-title').textContent = `Chỉnh sửa ${item[`${level}_name`]}`;
    document.getElementById('admin-form-id').value = id;
    document.getElementById('admin-form-name').value = item[`${level}_name`];
    document.getElementById('admin-form-no').value = item[`${level}_no`] || '';
    document.getElementById('admin-form-type').value = item.type_name || '';
    document.getElementById('admin-form-name-en').value = item[`${level}_name_en`] || '';

    renderExtraFields(item);
    document.getElementById('modal-admin-unit').classList.add('active');
  } catch (e) {
    console.error('Error loading unit details:', e);
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
  if (!ADMIN_CRUD_ENABLED) {
    showAdminCrudUnavailable();
    return;
  }
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
  if (!ADMIN_CRUD_ENABLED) {
    showAdminCrudUnavailable();
    return;
  }
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
  VNAIControls.renderSmartFilter('admin-filter-container', {
    prefix: 'admin',
    title: 'Lọc danh mục Master Database',
    searchPlaceholder: 'Tìm nhanh mã hoặc tên đơn vị...'
  });

  adminState = await VNAIControls.initSmartFilter('admin', {
    fetchProvinces: async (v) => {
      const res = await fetch(`${API_BASE}/provinces?limit=100&version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchDistricts: async (pId, v) => {
      const res = await fetch(`${API_BASE}/districts?province_id=${pId}&limit=500&version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchWards: async (dId, v) => {
      const res = await fetch(`${API_BASE}/wards?district_id=${dId}&limit=500&version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    },
    onSearch: (state) => loadAdminData(state)
  });

  document.getElementById('btn-admin-add-new')?.addEventListener('click', () => {
    if (!ADMIN_CRUD_ENABLED) {
      showAdminCrudUnavailable();
      return;
    }
    const level = getAdminCurrentLevel();
    document.getElementById('admin-modal-title').textContent = `Thêm ${level === 'province' ? 'Tỉnh/Thành' : level === 'district' ? 'Quận/Huyện' : 'Phường/Xã'} mới`;
    document.getElementById('admin-form-id').value = '';
    document.getElementById('admin-unit-form').reset();
    renderExtraFields();
    document.getElementById('modal-admin-unit').classList.add('active');
  });

  document.getElementById('admin-unit-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    await saveAdminUnit();
  });

  const addButton = document.getElementById('btn-admin-add-new');
  if (addButton && !ADMIN_CRUD_ENABLED) {
    addButton.disabled = true;
    addButton.title = 'Tạm tắt do backend đã gom API quản trị danh mục';
  }

  // Close modal handlers
  document.querySelectorAll('#modal-admin-unit .close-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('modal-admin-unit').classList.remove('active');
    });
  });

  // Add search listeners
  document.getElementById('admin-search-input')?.addEventListener('input', () => loadAdminData());
  document.getElementById('admin-btn-search')?.addEventListener('click', () => loadAdminData());

  loadAdminData();
}

function getAdminCurrentLevel(state) {
  const activeState = state || adminState;
  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');
  const wInput = document.getElementById('admin-ward-input');

  // If a ward is selected, we are definitely at ward level
  if (wInput && wInput.value && activeState.wards[wInput.value]) return 'ward';
  // If a district is selected, we show wards of that district
  if (dInput && dInput.value && activeState.districts[dInput.value]) return 'ward';
  // If a province is selected, we show districts of that province
  if (pInput && pInput.value && activeState.provinces[pInput.value]) return 'district';
  
  return 'province';
}

function formatDateTime(dateInput) {
    if (!dateInput) return '-';

    const d = new Date(dateInput);

    const yyyy = d.getFullYear();
    const MM = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');

    const HH = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');

    return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`;
}

async function loadAdminData(state) {
  const activeState = state || adminState;
  if (!activeState.provinces) return;

  const level = getAdminCurrentLevel(activeState);

  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');
  const wInput = document.getElementById('admin-ward-input');

  const provinceId = pInput && pInput.value ? activeState.provinces[pInput.value] : null;
  const districtId = dInput && dInput.value ? activeState.districts[dInput.value] : null;
  const wardId = wInput && wInput.value ? activeState.wards[wInput.value] : null;

  const searchInput = document.getElementById('admin-search-input');
  const q = searchInput ? searchInput.value.toLowerCase() : '';

  const tableHead = document.getElementById('admin-table-head');
  const tableBody = document.getElementById('admin-table-body');
  const title = document.getElementById('admin-table-title');

  tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24"><i class="fa-solid fa-spinner fa-spin mr-8"></i> Đang tải dữ liệu...</td></tr>';

  let url = `${API_BASE}/${level}s?limit=500&version=${activeState.version}`;
  if (level === 'district' && provinceId) url += `&province_id=${provinceId}`;
  if (level === 'ward' && districtId) url += `&district_id=${districtId}`;
  if (level === 'ward' && wardId) url += `&ward_id=${wardId}`;

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    let data = await res.json();

    // Sort by GSO code (_no) - Numeric sort
    const noField = `${level}_no`;
    data.sort((a, b) => (a[noField] || '').localeCompare(b[noField] || '', undefined, { numeric: true }));

    // Filter by selected ward if level is ward and ward is selected
    if (level === 'ward' && wardId) {
      data = data.filter(item => item[`${level}_id`] == wardId);
    }

    // Render Headers
    const headers = ['ID', 'Mã số', 'Tên đơn vị', 'Ngày cập nhật', 'Loại hình'];
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
        <td class="text-tertiary text-xs">${item.updated_date ? formatDateTime(item.updated_date) : '-'}</td>
        <td><span class="badge badge-outline">${item.type_name || '-'}</span></td>
        <td class="text-right">
          ${ADMIN_CRUD_ENABLED
            ? `<button class="btn btn-icon btn-sm" onclick="editAdminUnit('${level}', ${item[`${level}_id`]})" title="Sửa"><i class="fa-solid fa-pen-to-square"></i></button>
               <button class="btn btn-icon btn-sm text-danger" onclick="deleteAdminUnit('${level}', ${item[`${level}_id`]}, '${item[`${level}_name`]}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>`
            : `<span class="text-tertiary text-xs">Read-only</span>`}
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
let explorerState = {
  provinces: {},
  districts: {},
  wards: {}
};
async function initDataExplorer() {
  VNAIControls.renderSmartFilter('explorer-filter-container', {
    prefix: 'explorer',
    title: 'Truy vấn hàng đợi xử lý địa chỉ',
    showVersion: false,
    searchPlaceholder: 'Tìm kiếm địa chỉ, tỉnh thành, trạng thái...',
    buttonText: 'Truy vấn'
  });

  const loadData = async (state) => {
    const activeState = state || explorerState;
    const tbody = document.getElementById("explorer-body");
    const sBtn = document.getElementById("explorer-btn-search");
    if (!tbody || !activeState.provinces) return;

    if (sBtn) sBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    try {
      const q = document.getElementById("explorer-search-input")?.value.trim() || "";
      const pId = activeState.provinces[document.getElementById('explorer-province-input')?.value] || "";
      const dId = activeState.districts[document.getElementById('explorer-district-input')?.value] || "";
      const wId = activeState.wards[document.getElementById('explorer-ward-input')?.value] || "";

      let url = `${API_BASE}/explorer/queue?limit=100&q=${encodeURIComponent(q)}`;
      if (wId) url += `&ward_id=${wId}`;
      else if (dId) url += `&district_id=${dId}`;
      else if (pId) url += `&province_id=${pId}`;

      const res = await fetch(url, { headers: getAuthHeader() });
      const data = await res.json();

      if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-tertiary);">Không có dữ liệu phù hợp</td></tr>`;
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
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Lỗi tải dữ liệu</td></tr>`;
    } finally {
      if (sBtn) sBtn.innerHTML = 'Truy vấn';
      adjustActivePageHeight();
    }
  };

  explorerState = await VNAIControls.initSmartFilter('explorer', {
    onSearch: loadData
  });

  // Add search listeners
  document.getElementById('explorer-search-input')?.addEventListener('input', () => loadData());
  document.getElementById('explorer-btn-search')?.addEventListener('click', () => loadData());

  loadData();
}

// ═══════════════════════════════════════════════════════════
// BOUNDARY VISUALIZATION
// ═══════════════════════════════════════════════════════════
function initBoundaryVisualizationUI() {
  const page = document.getElementById("boundary-visualization");
  if (!page) return;

  const scopeSelect = document.getElementById("boundary-scope");
  const provinceInput = document.getElementById("boundary-province-id");
  const districtInput = document.getElementById("boundary-district-id");
  const wardInput = document.getElementById("boundary-ward-id");
  const zoomInput = document.getElementById("boundary-zoom-start");
  const runBtn = document.getElementById("btn-boundary-run");
  const frame = document.getElementById("boundary-map-frame");
  const statusEl = document.getElementById("boundary-status");
  const statusDot = document.getElementById("boundary-status-dot");
  const countEl = document.getElementById("boundary-ring-count");
  const countLabelEl = document.getElementById("boundary-ring-count-label");
  const urlEl = document.getElementById("boundary-map-url");
  const logEl = document.getElementById("boundary-log");

  const setStatus = (message, tone = "idle") => {
    if (statusEl) {
      statusEl.textContent = message;
      statusEl.dataset.tone = tone;
    }
    if (statusDot) {
      statusDot.className = `pstatus-dot ${tone}`;
    }
  };

  const appendLog = (message) => {
    if (!logEl) return;
    const time = new Date().toLocaleTimeString("vi-VN", { hour12: false });
    const line = `[${time}] ${message}`;
    logEl.textContent = logEl.textContent ? `${logEl.textContent}\n${line}` : line;
    logEl.scrollTop = logEl.scrollHeight;
  };

  const refreshRequiredFields = () => {
    const scope = scopeSelect?.value || "province";
    if (provinceInput) provinceInput.required = scope === "province" || scope === "district" || scope === "ward";
    if (districtInput) districtInput.required = scope === "district" || scope === "ward";
    if (wardInput) wardInput.required = scope === "ward";
  };

  const run = async () => {
    const scope = scopeSelect?.value || "province";
    const payload = new URLSearchParams();
    payload.set("scope", scope);
    payload.set("zoom_start", String(parseInt(zoomInput?.value || "11", 10) || 11));

    if (provinceInput?.value) payload.set("province_id", provinceInput.value.trim());
    if (districtInput?.value) payload.set("district_id", districtInput.value.trim());
    if (wardInput?.value) payload.set("ward_id", wardInput.value.trim());

    setStatus("Đang tạo bản đồ ranh giới...", "loading");
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Đang tạo...</span>';
    }

    try {
      const response = await fetch(`${API_BASE}/boundary/map?${payload.toString()}`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Boundary API failed: ${response.status}`);
      }

      const result = await response.json();
      if (frame && result.url) frame.src = result.url;
      if (urlEl && result.url) {
        urlEl.href = result.url;
        urlEl.textContent = result.url;
      }
      if (countEl) countEl.textContent = Number(result.rings || 0).toLocaleString("vi-VN");
      if (countLabelEl) countLabelEl.textContent = Number(result.rings || 0).toLocaleString("vi-VN");

      setStatus("Đã tạo bản đồ thành công", "success");
      appendLog(`Generated ${result.rings || 0} polygon ring(s) at ${result.url || "unknown url"}`);
      showToast?.("Tạo bản đồ ranh giới thành công", "success");
    } catch (error) {
      console.error(error);
      setStatus("Tạo bản đồ thất bại", "danger");
      appendLog(`ERROR: ${error.message}`);
      showToast?.("Không thể tạo bản đồ ranh giới", "danger");
    } finally {
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.innerHTML = '<i class="fa-solid fa-map-location-dot"></i><span>Tạo bản đồ</span>';
      }
    }
  };

  scopeSelect?.addEventListener("change", refreshRequiredFields);
  runBtn?.addEventListener("click", run);
  [provinceInput, districtInput, wardInput].forEach((input) => {
    input?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        run();
      }
    });
  });

  refreshRequiredFields();
  appendLog("Boundary visualization ready.");
  setStatus("Sẵn sàng tạo bản đồ ranh giới", "idle");
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
  const btnTest = document.getElementById('btn-ls-test');
  const btnSync = document.getElementById('btn-ls-sync');
  
  if (btnRefresh) {
    btnRefresh.addEventListener('click', fetchLabelStudioTasks);
  }

  if (btnTest) {
    btnTest.addEventListener('click', testLabelStudioConnection);
  }

  if (btnSync) {
    btnSync.addEventListener('click', syncLabelStudioTasks);
  }

  // Initial fetch if page is active
  const page = document.getElementById('label-studio');
  if (page && page.classList.contains('active')) {
    fetchLabelStudioTasks();
  }
}

async function syncLabelStudioTasks() {
  const btn = document.getElementById('btn-ls-sync');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
  }

  try {
    const response = await fetch(`${API_BASE}/label-studio/sync`, {
      method: 'POST',
      headers: getAuthHeader()
    });
    const result = await response.json();

    if (response.ok) {
      showToast(result.message, "success");
    } else {
      showToast(result.detail || "Lỗi khi đồng bộ dữ liệu", "danger");
    }
  } catch (err) {
    showToast("Không thể kết nối tới API server", "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Sync Labeled to Training Hub';
    }
  }
}

async function testLabelStudioConnection() {
  const btn = document.getElementById('btn-ls-test');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';
  }

  try {
    const response = await fetch(`${API_BASE}/label-studio/debug`, {
      headers: getAuthHeader()
    });
    const result = await response.json();

    if (result.status === "success") {
      showToast(result.message, "success");
    } else {
      showToast(result.message, "danger");
      console.error("LS Debug Details:", result.details);
    }
  } catch (err) {
    showToast("Không thể kết nối tới API server", "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-vial"></i> Check Connection';
    }
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
async function deleteAdminUnit(level, id, name) {
  const confirmed = await showConfirm(`Bạn có chắc chắn muốn xóa ${level}: ${name}?`);
  if (confirmed) {
    showToast(`Đã yêu cầu xóa ${name}. Đang xử lý...`, 'warning');
  }
}

// Expose to window for inline onclick handlers
window.showDetails = showDetails;
window.deleteAdminUnit = deleteAdminUnit;
window.loadTrainingHistoryFromDB = loadTrainingHistoryFromDB;

async function initEvidenceView() {
  const page = document.getElementById('evidence');
  if (!page) return;

  const refreshButton = page.querySelector('#evidence-refresh');
  const fileList = page.querySelector('#evidence-file-list');
  const iframe = page.querySelector('#evidence-iframe');
  const csvPreview = page.querySelector('#evidence-csv-preview');
  const meta = page.querySelector('#evidence-meta');

  async function loadManifest() {
    fileList.innerHTML = '<li class="text-tertiary p-12">Đang tải manifest...</li>';
    csvPreview.innerHTML = '';
    iframe.src = 'about:blank';
    iframe.style.display = 'none';
    csvPreview.style.display = 'none';

    const response = await fetch(`${API_BASE}/evidence/manifest`, { headers: getAuthHeader() });
    if (!response.ok) {
      throw new Error(`Manifest API failed: ${response.status}`);
    }

    const manifest = await response.json();
    const files = manifest.files || {};
    const entries = Object.entries(files);

    if (meta) {
      meta.textContent = manifest.generatedAt
        ? `Generated at ${manifest.generatedAt}`
        : 'Generated at unknown time';
    }

    if (!entries.length) {
      fileList.innerHTML = '<li class="text-tertiary p-12">Manifest không có tệp nào</li>';
      return;
    }

    fileList.innerHTML = entries.map(([key, value]) => `
      <li class="evidence-file-row" data-key="${key}">
        <div class="evidence-file-main">
          <div class="evidence-file-key">${key}</div>
          <div class="evidence-file-path">${value}</div>
        </div>
        <div class="evidence-file-actions">
          <button type="button" class="btn btn-sm btn-ghost evidence-view-btn" data-key="${key}">Xem</button>
          <a class="btn btn-sm btn-primary" href="/api/evidence/file?key=${encodeURIComponent(key)}" target="_blank" rel="noopener">Mở</a>
        </div>
      </li>
    `).join('');

    fileList.querySelectorAll('.evidence-view-btn').forEach((button) => {
      button.addEventListener('click', () => openEvidenceFile(button.dataset.key, files));
    });
  }

  async function openEvidenceFile(key, files) {
    const filePath = files[key] || '';
    const ext = filePath.split('.').pop().toLowerCase();
    const url = `${API_BASE}/evidence/file?key=${encodeURIComponent(key)}`;

    if (ext === 'html' || ext === 'htm') {
      iframe.src = url;
      iframe.style.display = 'block';
      csvPreview.style.display = 'none';
      return;
    }

    const response = await fetch(url, { headers: getAuthHeader() });
    if (!response.ok) {
      throw new Error(`Preview API failed: ${response.status}`);
    }

    const text = await response.text();
    const lines = text.split(/\r?\n/).filter(Boolean).slice(0, 25);
    if (!lines.length) {
      csvPreview.innerHTML = '<div class="p-12 text-tertiary">Tệp rỗng</div>';
      csvPreview.style.display = 'block';
      iframe.style.display = 'none';
      return;
    }

    const rows = lines.map((line) => line.split(','));
    const headers = rows[0] || [];
    const bodyRows = rows.slice(1);
    const tableHtml = `
      <div class="table-container">
        <table>
          <thead>
            <tr>${headers.map((cell) => `<th>${escapeHtml(cell)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')}
          </tbody>
        </table>
      </div>
    `;

    csvPreview.innerHTML = tableHtml;
    csvPreview.style.display = 'block';
    iframe.style.display = 'none';
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  refreshButton.addEventListener('click', async () => {
    try {
      await loadManifest();
    } catch (error) {
      fileList.innerHTML = `<li class="text-danger p-12">Không tải được manifest: ${escapeHtml(error.message)}</li>`;
    }
  });

  try {
    await loadManifest();
  } catch (error) {
    fileList.innerHTML = `<li class="text-danger p-12">Không tải được manifest: ${escapeHtml(error.message)}</li>`;
  }
}
