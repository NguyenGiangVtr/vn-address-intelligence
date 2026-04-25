const API_BASE = "http://localhost:8080/api";

document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
    setupNavigation();
});

async function initDashboard() {
    try {
        const stats = await fetch(`${API_BASE}/stats`).then(res => res.json());
        updateStats(stats);
        
        // Initial load for overview
        const provinces = await fetch(`${API_BASE}/admin-v2/provinces`).then(res => res.json());
        updateProvincesTable(provinces);
        
        renderCharts(stats);
    } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
    }
}

async function loadPageData(pageId) {
    console.log(`Loading data for ${pageId}...`);
    try {
        if (pageId === "admin-v2") {
            const data = await fetch(`${API_BASE}/admin-v2/provinces`).then(res => res.json());
            renderFullAdminTable(data);
        } else if (pageId === "osm") {
            const data = await fetch(`${API_BASE}/osm/summary`).then(res => res.json());
            renderOSMPage(data);
        } else if (pageId === "ai-hub") {
            const data = await fetch(`${API_BASE}/training/samples`).then(res => res.json());
            renderAIPage(data);
        }
    } catch (e) { console.error(e); }
}

function renderFullAdminTable(data) {
    const tbody = document.querySelector("#full-admin-table tbody");
    tbody.innerHTML = data.map(p => `
        <tr>
            <td>${p.province_id}</td>
            <td>${p.province_name}</td>
            <td>${p.province_no || '-'}</td>
            <td>${p.decision_number || 'N/A'}</td>
            <td><span class="badge ${p.decision_number ? 'done' : 'pending'}">${p.decision_number ? 'Enriched' : 'Wait'}</span></td>
        </tr>
    `).join("");
}

function renderOSMPage(data) {
    document.getElementById("osm-raw-val").innerText = data.raw.toLocaleString();
    document.getElementById("osm-street-val").innerText = data.streets.toLocaleString();
    document.getElementById("osm-build-val").innerText = data.buildings.toLocaleString();
}

function renderAIPage(data) {
    const tbody = document.querySelector("#ner-samples-table tbody");
    if (!Array.isArray(data)) {
        tbody.innerHTML = "<tr><td colspan='3'>Không có dữ liệu</td></tr>";
        return;
    }
    tbody.innerHTML = data.map(s => {
        const tagStr = s.ner_tags_json ? (typeof s.ner_tags_json === 'string' ? s.ner_tags_json : JSON.stringify(s.ner_tags_json)) : "-";
        return `
            <tr>
                <td title="${s.raw_text}">${s.raw_text ? s.raw_text.substring(0, 50) + '...' : '-'}</td>
                <td><code>${tagStr.substring(0, 50)}...</code></td>
                <td>${(Math.random() * 0.2 + 0.8).toFixed(2)}</td>
            </tr>
        `;
    }).join("");
}

function updateStats(data) {
    document.getElementById("stat-master-total").innerText = 
        (data.master.provinces + data.master.districts + data.master.wards).toLocaleString();
    
    document.getElementById("stat-osm-total").innerText = 
        data.osm.total.toLocaleString();
    
    document.getElementById("stat-ai-total").innerText = 
        data.ai.training_samples.toLocaleString();
    
    document.getElementById("stat-queue-total").innerText = 
        data.ai.cleansing_queue.toLocaleString();
}

function updateProvincesTable(provinces) {
    const tbody = document.querySelector("#enrichment-table tbody");
    tbody.innerHTML = "";
    
    provinces.slice(0, 10).forEach(p => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${p.province_name}</td>
            <td><span class="badge ${p.decision_number ? 'done' : 'pending'}">${p.decision_number ? 'Đã nạp' : 'Chờ'}</span></td>
            <td>${p.decision_number || '-'}</td>
            <td>${p.area_km2 || '...'} km²</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderCharts(data) {
    const ctx = document.getElementById('chart-master').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Province', 'District', 'Ward'],
            datasets: [{
                data: [data.master.provinces, data.master.districts, data.master.wards],
                backgroundColor: ['#3b82f6', '#06b6d4', '#10b981'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            cutout: '70%'
        }
    });
}

function setupNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    const pages = document.querySelectorAll(".page");

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            
            // UI Update
            navItems.forEach(i => i.classList.remove("active"));
            item.classList.add("active");
            
            // Page Switching
            const targetId = item.getAttribute("data-page");
            pages.forEach(page => {
                if (page.id === targetId) {
                    page.classList.add("active");
                    loadPageData(targetId);
                } else {
                    page.classList.remove("active");
                }
            });
            
            console.log(`Switched to ${targetId}`);
        });
    });
}
