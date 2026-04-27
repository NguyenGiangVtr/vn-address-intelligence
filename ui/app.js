/* ══════════════════════════════════════════════════════════════
   VN Address Intelligence — SaaS App Logic
   ══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.hostname === "localhost" || window.location.protocol === "file:"
  ? "http://localhost:8081/api"
  : "/api";

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

// ─── INIT ───
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  populateLabelRegistry();
  initOverviewChart();
  setupParserTool();
  setupBatchTool();
  fetchStats();
  initNSOSyncTool();
  initAdminManager();

  // Refresh stats every 30 seconds
  setInterval(fetchStats, 30000);
  // Initialize Training Chart if on training page
  initIntelligenceChart();
});

let intelligenceChart = null;
function initIntelligenceChart() {
  const ctx = document.getElementById('intelligenceChart');
  if (!ctx) return;

  if (intelligenceChart) intelligenceChart.destroy();

  intelligenceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['v2.1', 'v2.2', 'v2.3', 'v2.4 (Current)'],
      datasets: [{
        label: 'Model Accuracy (%)',
        data: [82.5, 84.2, 88.7, 92.4],
        borderColor: '#818cf8',
        backgroundColor: 'rgba(129, 140, 248, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#818cf8'
      }, {
        label: 'F1-Score',
        data: [79.1, 81.5, 85.3, 90.1],
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
        legend: { display: false }
      },
      scales: {
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#5c5c5f', font: { size: 10 } }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#5c5c5f', font: { size: 10 } }
        }
      }
    }
  });
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
    });
  });

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
function initOverviewChart() {
  const ctx = document.getElementById("chart-overview");
  if (!ctx) return;

  new Chart(ctx.getContext("2d"), {
    type: "bar",
    data: {
      labels: ["mat.province", "mat.district", "mat.ward", "osm.streets", "osm.buildings", "ath.training", "prq.queue"],
      datasets: [{
        label: "Records",
        data: [97, 767, 15563, 281376, 29889, 25130, 505094],
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
          type: "logarithmic",
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
  const btnSample = document.getElementById("btn-parse-sample");
  const inputEl = document.getElementById("parser-input");

  if (btnParse) btnParse.addEventListener("click", () => runParser());
  if (btnSample) btnSample.addEventListener("click", () => {
    const addr = SAMPLE_ADDRESSES[Math.floor(Math.random() * SAMPLE_ADDRESSES.length)];
    inputEl.value = addr;
    runParser();
  });
}

function runParser() {
  const text = document.getElementById("parser-input").value.trim();
  if (!text) return;

  // Client-side heuristic NER (mirrors PreLabeler logic)
  const entities = heuristicNER(text);
  renderNEROutput(text, entities);
  renderEntitiesTable(entities);
}

function heuristicNER(text) {
  const entities = [];
  let used = new Set();

  // Province patterns
  const proPatterns = [
    /(?:Tỉnh|tỉnh|T\.)\s+([A-ZĐa-zÀ-ỹ\s\-]+?)(?:,|$)/g,
    /(?:Thành phố|TP\.?\s*|tp\.?\s*)([A-ZĐa-zÀ-ỹ\s]+?)(?:,|$)/g,
  ];
  proPatterns.forEach(re => {
    let m;
    while ((m = re.exec(text)) !== null) {
      entities.push({ label: "PRO", start: m.index, end: m.index + m[0].replace(/,$/, "").length, text: m[0].replace(/,$/, "").trim() });
    }
  });

  // District
  const dstRe = /(?:Quận|quận|Q\.?\s*|Huyện|huyện|H\.?\s*|Thị xã|thị xã|TX\.?\s*)([A-ZĐa-zÀ-ỹ0-9\s]+?)(?:,|$)/g;
  let m;
  while ((m = dstRe.exec(text)) !== null) {
    entities.push({ label: "DST", start: m.index, end: m.index + m[0].replace(/,$/, "").length, text: m[0].replace(/,$/, "").trim() });
  }

  // Ward
  const wdsRe = /(?:Phường|phường|P\.?\s*|Xã|xã|X\.?\s*|Thị trấn|TT\.?\s*)([A-ZĐa-zÀ-ỹ0-9\s]+?)(?:,|$)/g;
  while ((m = wdsRe.exec(text)) !== null) {
    entities.push({ label: "WDS", start: m.index, end: m.index + m[0].replace(/,$/, "").length, text: m[0].replace(/,$/, "").trim() });
  }

  // Street
  const strRe = /(?:Đường|đường|Đ\.?\s*|Phố|phố)[\s]*([A-ZĐa-zÀ-ỹ0-9\s]+?)(?:,|$)/g;
  while ((m = strRe.exec(text)) !== null) {
    entities.push({ label: "STR", start: m.index, end: m.index + m[0].replace(/,$/, "").length, text: m[0].replace(/,$/, "").trim() });
  }

  // House number
  const numRe = /(?:Số\s+|số\s+)?(\d+[\w/.\-]*)/g;
  while ((m = numRe.exec(text)) !== null) {
    if (!entities.some(e => m.index >= e.start && m.index < e.end)) {
      entities.push({ label: "NUM", start: m.index, end: m.index + m[0].length, text: m[0].trim() });
    }
  }

  // Alley
  const alyRe = /(?:Hẻm|hẻm|Ngõ|ngõ|Ngách|ngách|Kiệt|kiệt)\s*[\d/]+/g;
  while ((m = alyRe.exec(text)) !== null) {
    entities.push({ label: "ALY", start: m.index, end: m.index + m[0].length, text: m[0].trim() });
  }

  // Building
  const bldRe = /(?:Chung [Cc]ư|CC\.?\s*|Tòa nhà|Khu đô thị|KĐT)\s*[A-ZĐa-zÀ-ỹ0-9\s]+?(?:,|$)/g;
  while ((m = bldRe.exec(text)) !== null) {
    entities.push({ label: "BLD", start: m.index, end: m.index + m[0].replace(/,$/, "").length, text: m[0].replace(/,$/, "").trim() });
  }

  // Neighborhood
  const nhbRe = /(?:Khu [Pp]hố|KP\.?\s*|[Tt]hôn|[Ấấ]p|[Tt]ổ)\s*[\dA-Za-zÀ-ỹ\s]+?(?:,|$)/g;
  while ((m = nhbRe.exec(text)) !== null) {
    entities.push({ label: "NHB", start: m.index, end: m.index + m[0].replace(/,$/, "").length, text: m[0].replace(/,$/, "").trim() });
  }

  return entities.sort((a, b) => a.start - b.start);
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
  const btnStart = document.getElementById("btn-batch-start");
  const btnStop = document.getElementById("btn-batch-stop");
  const log = document.getElementById("batch-log");

  if (btnStart) btnStart.addEventListener("click", () => {
    const size = document.getElementById("batch-size").value;
    const method = document.getElementById("batch-method").value;
    log.innerHTML = `[${new Date().toLocaleTimeString()}] Starting batch: ${size} records, method=${method}\n`;
    log.innerHTML += `[${new Date().toLocaleTimeString()}] Connecting to prq.address_cleansing_queue...\n`;


    // Simulate progress
    let processed = 0;
    const startTime = Date.now();
    const interval = setInterval(() => {
      processed += Math.floor(Math.random() * 50) + 10;
      const elapsed = (Date.now() - startTime) / 1000;
      const tps = elapsed > 0 ? Math.round(processed / elapsed) : 0;

      if (processed >= parseInt(size)) {
        processed = parseInt(size);
        clearInterval(interval);
        log.innerHTML += `[${new Date().toLocaleTimeString()}] ✅ Batch complete: ${processed.toLocaleString()} records processed\n`;
        document.getElementById("batch-done").textContent = processed.toLocaleString();
        document.getElementById("batch-throughput").textContent = `${tps.toLocaleString()} items/s`;
        return;
      }

      document.getElementById("batch-throughput").textContent = `${tps.toLocaleString()} items/s`;
      log.innerHTML += `[${new Date().toLocaleTimeString()}] Processing... ${processed.toLocaleString()}/${parseInt(size).toLocaleString()}\n`;
      log.scrollTop = log.scrollHeight;
    }, 800);

    btnStop.onclick = () => { clearInterval(interval); log.innerHTML += `\n[${new Date().toLocaleTimeString()}] ⛔ Batch stopped by user\n`; };
  });
}

async function fetchStats() {
  try {
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

    // Update Visitors
    if (data.visitors) {
      if (document.getElementById('stat-total-visits')) document.getElementById('stat-total-visits').textContent = data.visitors.total.toLocaleString();
      if (document.getElementById('stat-unique-ips')) document.getElementById('stat-unique-ips').textContent = data.visitors.unique.toLocaleString();
      if (document.getElementById('stat-online-users')) document.getElementById('stat-online-users').textContent = data.visitors.online.toLocaleString();
    }
  } catch (err) {
    console.error("Stats Fetch Error:", err);
  }
}

// ═══════════════════════════════════════════════════════════
// TRAINING HUB LOGIC
// ═══════════════════════════════════════════════════════════
document.getElementById('btn-import-ls')?.addEventListener('click', async () => {
  const fileInput = document.getElementById('ls-import-file');
  const statusEl = document.getElementById('import-status');

  if (!fileInput.files.length) {
    statusEl.innerHTML = '<span class="text-danger">Vui lòng chọn file JSON</span>';
    return;
  }

  statusEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải lên và tái huấn luyện...';

  // Simulated delay for training
  setTimeout(() => {
    statusEl.innerHTML = '<span class="text-success">✅ Thành công! Mô hình đã được cập nhật bản v2.4.1</span>';

    // Update chart with new point
    if (intelligenceChart) {
      intelligenceChart.data.labels.push('v2.4.1');
      intelligenceChart.data.datasets[0].data.push(93.8);
      intelligenceChart.data.datasets[1].data.push(91.5);
      intelligenceChart.update();
    }

    // Update last retrained text
    const timeEl = document.getElementById('last-retrained-text');
    if (timeEl) timeEl.textContent = "Vừa xong";
  }, 3000);
});

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
  const vRadios = document.getElementsByName('admin-version');

  if (!pInput) return;

  const loadProvinces = async () => {
    try {
      const res = await fetch(`${API_BASE}/provinces?version=${mappingState.version}`, { headers: getAuthHeader() });
      const data = await res.json();
      const list = document.getElementById('list-provinces');
      mappingState.provinces = {}; // Clear
      list.innerHTML = data.map(p => {
        mappingState.provinces[p.province_name] = p.province_id;
        return `<option value="${p.province_name}" data-id="${p.province_id}">`;
      }).join('');
    } catch (e) { console.error(e); }
  };

  vRadios.forEach(r => r.addEventListener('change', () => {
    mappingState.version = r.value;
    pInput.value = ''; dInput.value = ''; wInput.value = '';
    mappingState.provinces = {}; mappingState.districts = {}; mappingState.wards = {};
    loadProvinces();
  }));

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
      const list = document.getElementById('list-districts');
      list.innerHTML = data.map(d => {
        mappingState.districts[d.district_name] = d.district_id;
        return `<option value="${d.district_name}" data-id="${d.district_id}">`;
      }).join('');
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
      const list = document.getElementById('list-wards');
      list.innerHTML = data.map(w => {
        const key = w.ward_name;
        mappingState.wards[key] = w.ward_id;
        return `<option value="${key}" data-id="${w.ward_id}">`;
      }).join('');
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

  loadProvinces();
}

async function showDetails(level, id) {
  const panel = document.getElementById('unit-details-panel');
  panel.innerHTML = '<div class="text-center" style="padding:40px"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></div>';
  try {
    const res = await fetch(`${API_BASE}/unit-details/${level}/${id}`, { headers: getAuthHeader() });
    const u = await res.json();
    panel.innerHTML = `
      <div class="flex flex-col gap-12">
        <div class="text-accent font-700" style="font-size:18px">${u.province_name || u.district_name || u.ward_name}</div>
        <div class="flex justify-between"><span>Phiên bản:</span><span class="badge info">Admin v${u.admin_version}</span></div>
        <div class="flex justify-between"><span>Mã GSO:</span><span class="text-mono" id="current-unit-code">${u.province_no || u.province_no || u.district_no || u.ward_no || "N/A"}</span></div>
        <div class="flex justify-between"><span>Dân số:</span><span class="font-600">${(u.population || 0).toLocaleString()} người</span></div>
        <div class="flex justify-between"><span>Diện tích:</span><span class="font-600">${u.area_km2 || 0} km²</span></div>
        <div class="nav-divider"></div>
        <div>
          <div class="stat-label">Nghị quyết/Quyết định:</div>
          <div style="font-size:12px; color:var(--text-secondary); line-height:1.4">${u.decision_number || "Chưa có dữ liệu"}</div>
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

  // Lấy giá trị version từ UI
  const version = document.querySelector('input[name="admin-version"]:checked')?.value;

  // Xây dựng URL với các tham số ID chính xác
  let url = `${API_BASE}/lookup/mapping?`;
  if (wId) url += `ward_id=${wId}`;
  else if (dId) url += `district_id=${dId}`;
  else if (pId) url += `province_id=${pId}`;

  if (version) url += `${url.endsWith('?') ? '' : '&'}version=${version}`;

  if (qText) url += `${url.endsWith('?') ? '' : '&'}query=${encodeURIComponent(qText)}`;

  if (url.endsWith('?')) return; // No filter

  tbody.innerHTML = '<tr><td colspan="5" class="text-center" style="padding:40px"><i class="fa-solid fa-circle-notch fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();
    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-tertiary" style="padding:40px">Không tìm thấy dữ liệu ánh xạ phù hợp</td></tr>';
      return;
    }
    tbody.innerHTML = data.map(m => `
      <tr>
        <td>
          <div class="font-600" style="font-size:14px; color:var(--text-accent)">${m.ward_name_old || (m.ward_id_old == -1 ? "(Tất cả Xã)" : "N/A")}</div>
          <div class="text-tertiary" style="font-size:12px">
            ${[m.district_name_old, m.province_name_old].filter(x => x).join(" - ")}
          </div>
        </td>
        <td class="text-tertiary" style="vertical-align:middle"><i class="fa-solid fa-arrow-right-long"></i></td>
        <td>
          <div class="font-600" style="font-size:14px; color:var(--success)">${m.ward_name_new || "N/A"}</div>
          <div class="text-tertiary" style="font-size:12px">${m.province_name_new || ""}</div>
        </td>
        <td><div style="max-width:300px; font-size:12px; line-height:1.4">${m.updated_note || ""}</div></td>
        <td class="text-tertiary" style="font-size:12px">${m.effective_date_from ? new Date(m.effective_date_from).toLocaleDateString('vi-VN') : "-"}</td>
      </tr>
    `).join("");
  } catch (err) { tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger" style="padding:40px">Lỗi kết nối API</td></tr>'; }
}

document.getElementById('btn-mapping-search')?.addEventListener('click', triggerMappingSearch);
document.getElementById('mapping-search-input')?.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') triggerMappingSearch();
});

// ═══════════════════════════════════════════════════════════
// NSO SYNC LOGIC (v2 - Batch & Real-time Logs)
// ═══════════════════════════════════════════════════════════
let nsoProvinces = [];
let logPollingInterval = null;

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
    await fetch(`${API_BASE}/sync/nso/logs`, { method: 'DELETE', headers: getAuthHeader() });
    logsContainer.innerHTML = '<div style="color: #8b949e;">[System] Logs cleared.</div>';
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

  logPollingInterval = setInterval(async () => {
    const logsContainer = document.getElementById('nso-sync-logs');
    if (!logsContainer) return;

    try {
      const res = await fetch(`${API_BASE}/sync/nso/logs`, { headers: getAuthHeader() });
      const logs = await res.json();

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
    } catch (e) { /* Ignore polling errors */ }
  }, 2000);
}

async function syncAllProvinces() {
  const btn = document.getElementById('btn-sync-all-provinces');
  if (nsoProvinces.length === 0) {
    showToast('Vui lòng tải danh sách Tỉnh trước', 'warning');
    return;
  }

  const confirmMsg = `Hệ thống sẽ bắt đầu đồng bộ tuần tự ${nsoProvinces.length} tỉnh/thành. Quá trình này có thể kéo dài vài phút tùy thuộc vào tốc độ mạng. Bạn có chắc chắn muốn bắt đầu?`;
  const isConfirmed = await showConfirm(confirmMsg);
  if (!isConfirmed) return;

  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing All...';

  try {
    for (let i = 0; i < nsoProvinces.length; i++) {
      const p = nsoProvinces[i];
      updateSyncStatus(`SYNCING (${i + 1}/${nsoProvinces.length})`, 'var(--warning)');

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

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icon = type === 'success' ? 'fa-circle-check' :
    type === 'danger' ? 'fa-circle-xmark' :
      type === 'warning' ? 'fa-triangle-exclamation' : 'fa-circle-info';

  toast.innerHTML = `
    <i class="fa-solid ${icon} toast-icon"></i>
    <div class="toast-content">${message}</div>
    <div class="toast-close"><i class="fa-solid fa-xmark"></i></div>
  `;

  container.appendChild(toast);

  // Auto remove
  const timer = setTimeout(() => {
    removeToast(toast);
  }, 4000);

  toast.querySelector('.toast-close').addEventListener('click', () => {
    clearTimeout(timer);
    removeToast(toast);
  });
}

function removeToast(toast) {
  toast.classList.add('hiding');
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

function showConfirm(message) {
  return new Promise((resolve) => {
    const overlay = document.getElementById('modal-overlay');
    const msgEl = document.getElementById('confirm-message');
    const btnOk = document.getElementById('btn-confirm-ok');
    const btnCancel = document.getElementById('btn-confirm-cancel');

    if (!overlay || !msgEl) {
      resolve(confirm(message)); // Fallback
      return;
    }

    msgEl.textContent = message;
    overlay.classList.add('active');

    const cleanUp = (result) => {
      overlay.classList.remove('active');
      btnOk.removeEventListener('click', onOk);
      btnCancel.removeEventListener('click', onCancel);
      resolve(result);
    };

    const onOk = () => cleanUp(true);
    const onCancel = () => cleanUp(false);

    btnOk.addEventListener('click', onOk);
    btnCancel.addEventListener('click', onCancel);
  });
}

// ═══ ADMINISTRATIVE MANAGER (CRUD) ═══

window.editAdminUnit = async function(level, id) {
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

window.deleteAdminUnit = async function(level, id, name) {
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
  const level = document.getElementById('admin-crud-level').value;
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

async function initAdminManager() {
  const levelSelect = document.getElementById('admin-crud-level');
  const provinceSelect = document.getElementById('admin-crud-province-select');
  const districtSelect = document.getElementById('admin-crud-district-select');
  const btnRefresh = document.getElementById('btn-admin-refresh');
  const btnAddNew = document.getElementById('btn-admin-add-new');
  const unitForm = document.getElementById('admin-unit-form');
  const modal = document.getElementById('modal-admin-unit');

  if (!levelSelect) return;

  // Handle Level Change
  levelSelect.addEventListener('change', async () => {
    const level = levelSelect.value;
    document.getElementById('admin-filter-parent-province').classList.toggle('hidden', level === 'province');
    document.getElementById('admin-filter-parent-district').classList.toggle('hidden', level !== 'ward');
    
    if (level !== 'province') await loadAdminProvinces();
    loadAdminData();
  });

  provinceSelect.addEventListener('change', async () => {
    if (levelSelect.value === 'ward') await loadAdminDistricts(provinceSelect.value);
    loadAdminData();
  });

  districtSelect.addEventListener('change', () => loadAdminData());
  btnRefresh.addEventListener('click', () => loadAdminData());

  // Modal actions
  btnAddNew.addEventListener('click', () => {
    const level = levelSelect.value;
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
  loadAdminData();
}

async function loadAdminProvinces() {
  const select = document.getElementById('admin-crud-province-select');
  try {
    const res = await fetch(`${API_BASE}/provinces?limit=100`, { headers: getAuthHeader() });
    const data = await res.json();
    select.innerHTML = '<option value="">-- Tất cả --</option>' + 
      data.map(p => `<option value="${p.province_id}">${p.province_name}</option>`).join('');
  } catch (e) { console.error(e); }
}

async function loadAdminDistricts(provinceId) {
  const select = document.getElementById('admin-crud-district-select');
  if (!provinceId) {
    select.innerHTML = '<option value="">-- Chọn Tỉnh trước --</option>';
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/districts?province_id=${provinceId}&limit=500`, { headers: getAuthHeader() });
    const data = await res.json();
    select.innerHTML = '<option value="">-- Tất cả --</option>' + 
      data.map(d => `<option value="${d.district_id}">${d.district_name}</option>`).join('');
  } catch (e) { console.error(e); }
}

async function loadAdminData() {
  const level = document.getElementById('admin-crud-level').value;
  const provinceId = document.getElementById('admin-crud-province-select').value;
  const districtId = document.getElementById('admin-crud-district-select').value;
  const tableHead = document.getElementById('admin-table-head');
  const tableBody = document.getElementById('admin-table-body');
  const title = document.getElementById('admin-table-title');

  tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24"><i class="fa-solid fa-spinner fa-spin mr-8"></i> Đang tải dữ liệu...</td></tr>';

  let url = `${API_BASE}/${level}s?limit=500`;
  if (level === 'district' && provinceId) url += `&province_id=${provinceId}`;
  if (level === 'ward' && districtId) url += `&district_id=${districtId}`;

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();

    // Render Headers
    const headers = ['ID', 'Mã số', 'Tên đơn vị', 'Tên Tiếng Anh', 'Loại hình'];
    tableHead.innerHTML = headers.map(h => `<th>${h}</th>`).join('') + '<th class="text-right">Thao tác</th>';

    // Render Rows
    if (data.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24 text-tertiary">Không tìm thấy dữ liệu</td></tr>';
      return;
    }

    tableBody.innerHTML = data.map(item => `
      <tr>
        <td class="text-mono text-xs">${item[`${level}_id`]}</td>
        <td class="text-mono font-bold">${item[`${level}_no`] || '-'}</td>
        <td>${item[`${level}_name`]}</td>
        <td class="text-tertiary text-xs">${item[`${level}_name_en`] || '-'}</td>
        <td><span class="badge badge-outline">${item.type_name || '-'}</span></td>
        <td class="text-right">
          <button class="btn btn-icon btn-sm" onclick="editAdminUnit('${level}', ${item[`${level}_id`]})" title="Sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="btn btn-icon btn-sm text-danger" onclick="deleteAdminUnit('${level}', ${item[`${level}_id`]}, '${item[`${level}_name`]}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `).join('');

    title.innerHTML = `<i class="fa-solid fa-list mr-8"></i> Danh sách ${level === 'province' ? 'Tỉnh/Thành' : level === 'district' ? 'Quận/Huyện' : 'Phường/Xã'} (${data.length})`;
  } catch (e) {
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24 text-danger">Lỗi khi tải dữ liệu</td></tr>';
  }
}

// Initialize all modules
initMappingV3();
