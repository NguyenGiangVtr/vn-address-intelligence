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

  window.VNAIControls = Object.freeze({
    UI_CONTROL_TEMPLATE,
    applyUnifiedControlTemplate,
    escapeHtml,
    renderLookupTemplateDatalist,
    renderUnifiedSelectOptions,
    showToast,
    showConfirm
  });
})();
