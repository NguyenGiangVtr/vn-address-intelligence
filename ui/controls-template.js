/* Shared UI control template: dropdown, notify, confirm */
(function () {
  const UI_CONTROL_TEMPLATE = Object.freeze({
    dropdownClass: 'control-template-dropdown',
    notifyDurationMs: 4000,
    icons: {
      success: 'fa-circle-check',
      danger: 'fa-circle-xmark',
      warning: 'fa-triangle-exclamation',
      info: 'fa-circle-info'
    }
  });

  function applyUnifiedControlTemplate() {
    document.querySelectorAll('select.form-input, input[list].form-input').forEach((el) => {
      el.classList.add(UI_CONTROL_TEMPLATE.dropdownClass);
    });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderLookupTemplateDatalist(listId, rows, labelKey, idKey, stateMap) {
    const list = document.getElementById(listId);
    if (!list) return;

    Object.keys(stateMap).forEach((k) => delete stateMap[k]);
    list.innerHTML = rows.map((item) => {
      const label = item[labelKey];
      const id = item[idKey];
      if (label != null && id != null) stateMap[label] = id;
      return `<option value="${escapeHtml(String(label || ''))}" data-id="${id}"></option>`;
    }).join('');
  }

  function renderUnifiedSelectOptions(selectId, rows, valueKey, labelKey, placeholder) {
    const select = document.getElementById(selectId);
    if (!select) return;

    const baseOption = `<option value="">${escapeHtml(placeholder)}</option>`;
    const optionHtml = rows.map((item) => (
      `<option value="${item[valueKey]}">${escapeHtml(String(item[labelKey] || ''))}</option>`
    )).join('');

    select.innerHTML = baseOption + optionHtml;
    select.classList.add(UI_CONTROL_TEMPLATE.dropdownClass);
  }

  function removeToast(toast) {
    toast.classList.add('hiding');
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = UI_CONTROL_TEMPLATE.icons[type] || UI_CONTROL_TEMPLATE.icons.info;

    toast.innerHTML = `
      <i class="fa-solid ${icon} toast-icon"></i>
      <div class="toast-content">${message}</div>
      <div class="toast-close"><i class="fa-solid fa-xmark"></i></div>
    `;

    container.appendChild(toast);

    const timer = setTimeout(() => {
      removeToast(toast);
    }, UI_CONTROL_TEMPLATE.notifyDurationMs);

    toast.querySelector('.toast-close').addEventListener('click', () => {
      clearTimeout(timer);
      removeToast(toast);
    });
  }

  function showConfirm(message) {
    return new Promise((resolve) => {
      const overlay = document.getElementById('modal-overlay');
      const msgEl = document.getElementById('confirm-message');
      const btnOk = document.getElementById('btn-confirm-ok');
      const btnCancel = document.getElementById('btn-confirm-cancel');

      if (!overlay || !msgEl || !btnOk || !btnCancel) {
        console.error('Unified confirm modal is missing in DOM.');
        resolve(false);
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

  /**
   * Render the Smart Filter HTML into a container
   * @param {string} containerId - ID of the container element
   * @param {object} options - Configuration options
   */
  function renderSmartFilter(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const prefix = options.prefix || 'sf';
    const showVersion = options.showVersion !== false;
    const showProvince = options.showProvince !== false;
    const showDistrict = options.showDistrict !== false;
    const showWard = options.showWard !== false;
    const showSearch = options.showSearch !== false;
    const searchPlaceholder = options.searchPlaceholder || "Tìm nhanh theo tên hoặc mã hành chính...";
    const buttonText = options.buttonText || "Tra cứu ngay";
    const title = options.title || "Bộ lọc Thông minh";

    let html = `
      <div class="card smart-filter-card shadow-lg">
        <div class="card-header">
            <span class="card-title"><i class="fa-solid fa-filter mr-8"></i> ${title}</span>
        </div>
        <div class="card-body">
            <div class="smart-filter-grid">
    `;

    if (showVersion) {
      html += `
                <div class="form-group smart-filter-item">
                    <label class="form-label">Phiên bản danh mục</label>
                    <select id="${prefix}-version-select" class="form-input">
                        <option value="1" selected>Trước 01/07/2025</option>
                        <option value="2">Sau 01/07/2025</option>
                    </select>
                </div>
      `;
    }

    if (showProvince) {
      html += `
                <div class="form-group smart-filter-item">
                    <label class="form-label">Tỉnh/Thành phố</label>
                    <div class="input-wrapper">
                        <input list="${prefix}-list-provinces" id="${prefix}-province-input" class="form-input has-clear"
                            placeholder="Chọn Tỉnh/Thành...">
                        <button type="button" class="btn-clear-input" id="${prefix}-btn-clear-province" title="Xóa"><i class="fa-solid fa-xmark"></i></button>
                    </div>
                    <datalist id="${prefix}-list-provinces"></datalist>
                </div>
      `;
    }

    if (showDistrict) {
      html += `
                <div class="form-group smart-filter-item">
                    <label class="form-label">Quận/Huyện/Thị xã</label>
                    <div class="input-wrapper">
                        <input list="${prefix}-list-districts" id="${prefix}-district-input" class="form-input has-clear"
                            placeholder="Chọn Quận/Huyện...">
                        <button type="button" class="btn-clear-input" id="${prefix}-btn-clear-district" title="Xóa"><i class="fa-solid fa-xmark"></i></button>
                    </div>
                    <datalist id="${prefix}-list-districts"></datalist>
                </div>
      `;
    }

    if (showWard) {
      html += `
                <div class="form-group smart-filter-item">
                    <label class="form-label">Phường/Xã/Thị trấn</label>
                    <div class="input-wrapper">
                        <input list="${prefix}-list-wards" id="${prefix}-ward-input" class="form-input has-clear"
                            placeholder="Chọn Phường/Xã...">
                        <button type="button" class="btn-clear-input" id="${prefix}-btn-clear-ward" title="Xóa"><i class="fa-solid fa-xmark"></i></button>
                    </div>
                    <datalist id="${prefix}-list-wards"></datalist>
                </div>
      `;
    }

    html += `
            </div>
    `;

    if (showSearch) {
      html += `
            <div class="search-box-unified">
                <i class="fa-solid fa-search search-icon"></i>
                <input type="text" id="${prefix}-search-input" class="search-input"
                    placeholder="${searchPlaceholder}">
                <button class="btn-search" id="${prefix}-btn-search">${buttonText}</button>
            </div>
      `;
    }

    html += `
        </div>
      </div>
    `;

    container.innerHTML = html;
  }

  /**
   * Initialize hierarchical logic for a Smart Filter
   * @param {string} prefix - ID prefix used during render
   * @param {object} config - Configuration and callbacks
   */
  async function initSmartFilter(prefix, config = {}) {
    const state = {
      version: 1,
      provinces: {},
      districts: {},
      wards: {},
      currentData: [] // For local filtering
    };

    const pInput = document.getElementById(`${prefix}-province-input`);
    const dInput = document.getElementById(`${prefix}-district-input`);
    const wInput = document.getElementById(`${prefix}-ward-input`);
    const vSelect = document.getElementById(`${prefix}-version-select`);
    const sInput = document.getElementById(`${prefix}-search-input`);
    const sBtn = document.getElementById(`${prefix}-btn-search`);

    const onSearch = config.onSearch || (() => { });
    const onSelect = config.onSelect || (() => { });

    // Custom fetchers
    const fetchProvinces = config.fetchProvinces || (async (v) => {
      const res = await fetch(`${API_BASE}/provinces?version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    });

    const fetchDistricts = config.fetchDistricts || (async (pId, v) => {
      const res = await fetch(`${API_BASE}/districts/${pId}?version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    });

    const fetchWards = config.fetchWards || (async (dId, v) => {
      const res = await fetch(`${API_BASE}/wards/${dId}?version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    });

    if (vSelect) state.version = parseInt(vSelect.value);

    // Clear buttons logic
    ['province', 'district', 'ward'].forEach(level => {
      const btn = document.getElementById(`${prefix}-btn-clear-${level}`);
      const input = document.getElementById(`${prefix}-${level}-input`);
      if (btn && input) {
        btn.addEventListener('click', () => {
          input.value = '';
          input.dispatchEvent(new Event('input'));
        });
      }
    });

    const loadProvinces = async () => {
      try {
        const data = await fetchProvinces(state.version);
        state.currentData = data;
        renderLookupTemplateDatalist(`${prefix}-list-provinces`, data, config.provinceNameKey || 'province_name', config.provinceIdKey || 'province_id', state.provinces);
        onSearch(state);
      } catch (e) { console.error(e); }
    };

    vSelect?.addEventListener('change', () => {
      state.version = parseInt(vSelect.value);
      if (pInput) pInput.value = '';
      if (dInput) dInput.value = '';
      if (wInput) wInput.value = '';
      state.provinces = {}; state.districts = {}; state.wards = {};
      const listP = document.getElementById(`${prefix}-list-provinces`); if (listP) listP.innerHTML = '';
      const listD = document.getElementById(`${prefix}-list-districts`); if (listD) listD.innerHTML = '';
      const listW = document.getElementById(`${prefix}-list-wards`); if (listW) listW.innerHTML = '';
      loadProvinces();
    });

    pInput?.addEventListener('input', async () => {
      if (pInput.value === '') {
        if (dInput) dInput.value = '';
        if (wInput) wInput.value = '';
        state.districts = {}; state.wards = {};
        const listD = document.getElementById(`${prefix}-list-districts`); if (listD) listD.innerHTML = '';
        const listW = document.getElementById(`${prefix}-list-wards`); if (listW) listW.innerHTML = '';
        loadProvinces(); // Reload top level if cleared
        return;
      }

      const val = state.provinces[pInput.value];
      if (!val) return;

      const id = typeof val === 'object' ? (val[config.provinceIdKey || 'province_id'] || val.MaTinh) : val;

      if (dInput) dInput.value = '';
      if (wInput) wInput.value = '';
      state.districts = {}; state.wards = {};

      onSelect('province', id, state.version, val);

      try {
        const data = await fetchDistricts(id, state.version, val);
        state.currentData = data;
        renderLookupTemplateDatalist(`${prefix}-list-districts`, data, config.districtNameKey || 'district_name', config.districtIdKey || 'district_id', state.districts);
        onSearch(state);
      } catch (e) { console.error(e); }
    });

    dInput?.addEventListener('input', async () => {
      if (dInput.value === '') {
        if (wInput) wInput.value = '';
        state.wards = {};
        const listW = document.getElementById(`${prefix}-list-wards`); if (listW) listW.innerHTML = '';
        // Reload districts
        const pVal = state.provinces[pInput.value];
        const pId = typeof pVal === 'object' ? (pVal[config.provinceIdKey || 'province_id'] || pVal.MaTinh) : pVal;
        const data = await fetchDistricts(pId, state.version, pVal);
        state.currentData = data;
        onSearch(state);
        return;
      }

      const val = state.districts[dInput.value];
      if (!val) return;

      const id = typeof val === 'object' ? (val[config.districtIdKey || 'district_id'] || val.MaHuyen) : val;

      if (wInput) wInput.value = '';
      state.wards = {};

      onSelect('district', id, state.version, val);

      try {
        const data = await fetchWards(id, state.version, val);
        state.currentData = data;
        renderLookupTemplateDatalist(`${prefix}-list-wards`, data, config.wardNameKey || 'ward_name', config.wardIdKey || 'ward_id', state.wards);
        onSearch(state);
      } catch (e) { console.error(e); }
    });

    wInput?.addEventListener('input', () => {
      const val = state.wards[wInput.value];
      if (val) {
        const id = typeof val === 'object' ? (val[config.wardIdKey || 'ward_id'] || val.MaXa) : val;
        onSelect('ward', id, state.version, val);
      }
      onSearch(state);
    });

    sBtn?.addEventListener('click', () => onSearch(state));
    sInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') onSearch(state);
    });

    if (pInput) await loadProvinces();

    return state;
  }

  window.VNAIControls = Object.freeze({
    UI_CONTROL_TEMPLATE,
    applyUnifiedControlTemplate,
    escapeHtml,
    renderLookupTemplateDatalist,
    renderUnifiedSelectOptions,
    showToast,
    showConfirm,
    renderSmartFilter,
    initSmartFilter
  });
})();
