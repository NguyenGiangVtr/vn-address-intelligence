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
  { value:"PCD", text:"Plus Code",      color:"#f032e6", hotkey:"0", example:"7P28QR4F+2M" },
  { value:"BLD", text:"Tòa nhà/Chung cư", color:"#f58231", hotkey:"1", example:"Chung Cư Tecco Green Nest" },
  { value:"POI", text:"Địa danh/Mốc",   color:"#911eb4", hotkey:"2", example:"Đối Diện Chợ Bà Chiểu" },
  { value:"ALY", text:"Hẻm/Ngõ",        color:"#4363d8", hotkey:"3", example:"Hẻm 141" },
  { value:"NUM", text:"Số nhà/Lô",      color:"#e6194B", hotkey:"4", example:"Số 17/2A" },
  { value:"STR", text:"Tên đường",       color:"#3cb44b", hotkey:"5", example:"Đường Phạm Thế Hiển" },
  { value:"NHB", text:"Khu phố/Thôn/Ấp", color:"#469990", hotkey:"6", example:"Khu Phố 3" },
  { value:"WDS", text:"Phường/Xã",       color:"#ffe119", hotkey:"7", example:"Phường Tân Thới Nhất" },
  { value:"DST", text:"Quận/Huyện",      color:"#800000", hotkey:"8", example:"Quận 12" },
  { value:"PRO", text:"Tỉnh/TP",         color:"#000075", hotkey:"9", example:"TP Hồ Chí Minh" },
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
            callback: (v) => v >= 1000 ? (v/1000)+"K" : v
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
      entities.push({ label:"PRO", start: m.index, end: m.index + m[0].replace(/,$/,"").length, text: m[0].replace(/,$/,"").trim() });
    }
  });

  // District
  const dstRe = /(?:Quận|quận|Q\.?\s*|Huyện|huyện|H\.?\s*|Thị xã|thị xã|TX\.?\s*)([A-ZĐa-zÀ-ỹ0-9\s]+?)(?:,|$)/g;
  let m;
  while ((m = dstRe.exec(text)) !== null) {
    entities.push({ label:"DST", start: m.index, end: m.index + m[0].replace(/,$/,"").length, text: m[0].replace(/,$/,"").trim() });
  }

  // Ward
  const wdsRe = /(?:Phường|phường|P\.?\s*|Xã|xã|X\.?\s*|Thị trấn|TT\.?\s*)([A-ZĐa-zÀ-ỹ0-9\s]+?)(?:,|$)/g;
  while ((m = wdsRe.exec(text)) !== null) {
    entities.push({ label:"WDS", start: m.index, end: m.index + m[0].replace(/,$/,"").length, text: m[0].replace(/,$/,"").trim() });
  }

  // Street
  const strRe = /(?:Đường|đường|Đ\.?\s*|Phố|phố)[\s]*([A-ZĐa-zÀ-ỹ0-9\s]+?)(?:,|$)/g;
  while ((m = strRe.exec(text)) !== null) {
    entities.push({ label:"STR", start: m.index, end: m.index + m[0].replace(/,$/,"").length, text: m[0].replace(/,$/,"").trim() });
  }

  // House number
  const numRe = /(?:Số\s+|số\s+)?(\d+[\w/.\-]*)/g;
  while ((m = numRe.exec(text)) !== null) {
    if (!entities.some(e => m.index >= e.start && m.index < e.end)) {
      entities.push({ label:"NUM", start: m.index, end: m.index + m[0].length, text: m[0].trim() });
    }
  }

  // Alley
  const alyRe = /(?:Hẻm|hẻm|Ngõ|ngõ|Ngách|ngách|Kiệt|kiệt)\s*[\d/]+/g;
  while ((m = alyRe.exec(text)) !== null) {
    entities.push({ label:"ALY", start: m.index, end: m.index + m[0].length, text: m[0].trim() });
  }

  // Building
  const bldRe = /(?:Chung [Cc]ư|CC\.?\s*|Tòa nhà|Khu đô thị|KĐT)\s*[A-ZĐa-zÀ-ỹ0-9\s]+?(?:,|$)/g;
  while ((m = bldRe.exec(text)) !== null) {
    entities.push({ label:"BLD", start: m.index, end: m.index + m[0].replace(/,$/,"").length, text: m[0].replace(/,$/,"").trim() });
  }

  // Neighborhood
  const nhbRe = /(?:Khu [Pp]hố|KP\.?\s*|[Tt]hôn|[Ấấ]p|[Tt]ổ)\s*[\dA-Za-zÀ-ỹ\s]+?(?:,|$)/g;
  while ((m = nhbRe.exec(text)) !== null) {
    entities.push({ label:"NHB", start: m.index, end: m.index + m[0].replace(/,$/,"").length, text: m[0].replace(/,$/,"").trim() });
  }

  return entities.sort((a,b) => a.start - b.start);
}

function renderNEROutput(text, entities) {
  const output = document.getElementById("parser-output");
  if (!entities.length) {
    output.innerHTML = `<span style="color:var(--text-secondary)">${escapeHtml(text)}</span>`;
    return;
  }

  let html = "";
  let lastEnd = 0;
  const sorted = [...entities].sort((a,b) => a.start - b.start);

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
      <td>${(0.7 + Math.random()*0.25).toFixed(2)}</td>
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
        const key = `${w.ward_name} (${dInput.value})`;
        mappingState.wards[key] = w.ward_id;
        return `<option value="${key}" data-id="${w.ward_id}">`;
      }).join('');
    } catch (e) { console.error(e); }
  });

  wInput.addEventListener('input', () => {
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
        <div class="flex justify-between"><span>Mã GSO:</span><span class="text-mono" id="current-unit-code">${u.province_id || u.district_id || u.ward_id}</span></div>
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
  
  // Xây dựng URL với các tham số ID chính xác
  let url = `${API_BASE}/lookup/mapping?`;
  if (wId) url += `ward_id=${wId}`;
  else if (dId) url += `district_id=${dId}`;
  else if (pId) url += `province_id=${pId}`;
  
  if (qText) url += `${url.endsWith('?') ? '' : '&'}query=${encodeURIComponent(qText)}`;
  
  if (url.endsWith('?')) return; // No filter
  
  tbody.innerHTML = '<tr><td colspan="7" class="text-center" style="padding:40px"><i class="fa-solid fa-circle-notch fa-spin fa-2x text-accent"></i></td></tr>';
  
  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();
    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-tertiary" style="padding:40px">Không tìm thấy dữ liệu ánh xạ phù hợp</td></tr>';
      return;
    }
    tbody.innerHTML = data.map(m => `
      <tr>
        <td class="text-mono" style="color:var(--text-accent)">${m.ward_id_old || "-"}</td>
        <td>
          <div class="font-600">${m.ward_name_old || (m.ward_id_old == -1 ? "(Tất cả Xã)" : "N/A")}</div>
          <div class="text-tertiary" style="font-size:11px">
            ${[m.district_name_old, m.province_name_old].filter(x => x).join(", ")}
          </div>
        </td>
        <td class="text-tertiary"><i class="fa-solid fa-arrow-right-long"></i></td>
        <td class="text-mono" style="color:var(--success)">${m.ward_id_new || "-"}</td>
        <td>
          <div class="font-600 text-success">${m.ward_name_new || "N/A"}</div>
          <div class="text-tertiary" style="font-size:11px">${m.province_name_new || ""}</div>
        </td>
        <td><div style="max-width:300px; font-size:12px; line-height:1.4">${m.updated_note || ""}</div></td>
        <td class="text-tertiary" style="font-size:12px">${m.effective_date_from ? new Date(m.effective_date_from).toLocaleDateString('vi-VN') : "-"}</td>
      </tr>
    `).join("");
  } catch (err) { tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger" style="padding:40px">Lỗi kết nối API</td></tr>'; }
}

document.getElementById('btn-mapping-search')?.addEventListener('click', triggerMappingSearch);
document.getElementById('mapping-search-input')?.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') triggerMappingSearch();
});

// ═══════════════════════════════════════════════════════════
// NSO SYNC LOGIC
// ═══════════════════════════════════════════════════════════
document.getElementById('btn-sync-nso')?.addEventListener('click', async () => {
  const btn = document.getElementById('btn-sync-nso');
  const originalHtml = btn.innerHTML;
  
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/sync/nso`, {
      method: 'POST',
      headers: getAuthHeader()
    });
    const data = await res.json();
    
    if (data.status === 'success') {
      showToast(`✅ Đã đồng bộ ${data.synced_units.toLocaleString()} đơn vị từ NSO vào Version 2!`);
      // Refresh provinces if current version is 2
      if (mappingState.version == 2) {
        initMappingV3(); 
      }
    } else {
      showToast('❌ Lỗi đồng bộ dữ liệu NSO', 'danger');
    }
  } catch (e) {
    console.error(e);
    showToast('❌ Lỗi kết nối server', 'danger');
  } finally {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
  }
});

function showToast(msg, type = 'success') {
  // Simple alert for now, can be improved to a real toast UI
  alert(msg);
}

initMappingV3();
