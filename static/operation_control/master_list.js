/* Operations Master - List UI Enhancements */
(function(){
  // CSRF helper
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie('csrftoken');

  // Elements
  const $tbody = document.querySelector('#grid tbody');
  const $form = document.querySelector('#filters');
  const $loading = document.getElementById('loading');
  const toastEl = document.getElementById('toast');
  const toastBody = document.getElementById('toast-body');
  const toast = toastEl ? new bootstrap.Toast(toastEl, {delay: 2500}) : null;
  const btnQuick7d = document.getElementById('btn-quick-7d');
  const btnQuickMonth = document.getElementById('btn-quick-month');
  const btnReset = document.getElementById('btn-reset');
  const btnExport = document.getElementById('btn-export');
  const $chips = document.getElementById('active-filters');

  // Formatters
  function fmtMoney(v) {
    if (v === null || v === undefined || v === '') return '';
    const n = Number(v);
    if (Number.isFinite(n)) return n.toLocaleString('es-MX', {style: 'currency', currency: 'MXN'});
    // Attempt Decimal string like '1234.56'
    const parsed = Number(String(v).replace(/[^\d.-]/g, ''));
    return Number.isFinite(parsed) ? parsed.toLocaleString('es-MX', {style:'currency', currency:'MXN'}) : String(v);
  }
  const fmtPercent = v => (v==null||v==='')? '' : `${Number(v).toFixed(2)}%`;

  // Row builder
  function buildRow(r) {
    const tr = document.createElement('tr');
    tr.dataset.id = r.id;
    tr.innerHTML = `
      <td class="col-date nowrap">${r.date ?? ''}</td>
      <td class="col-folio nowrap">${r.folio ?? ''}</td>
      <td class="col-client">${r.client ?? ''}</td>
      <td class="col-origin">${r.origin ?? ''}</td>
      <td class="col-destination">${r.destination ?? ''}</td>
      <td class="text-end col-money">${fmtMoney(r.sale_amount)}</td>
      <td class="text-end col-money">${fmtMoney(r.cost_amount)}</td>
      <td class="text-end col-money">${fmtMoney(r.factoring_cost)}</td>
      <td class="text-end col-money">${fmtMoney(r.profit)}</td>
      <td class="text-end col-percent">${fmtPercent(r.profit_percentage)}</td>
      <td contenteditable class="cell-editable" data-field="counter_receipt">${r.customer_invoice_code ? '' : (r.counter_receipt || '')}</td>
      <td contenteditable class="cell-editable" data-field="counter_receipt_date">${r.counter_receipt_date || ''}</td>
      <td contenteditable class="cell-editable" data-field="customer_invoice_code">${r.customer_invoice_code || ''}</td>
      <td contenteditable class="cell-editable" data-field="customer_invoice_date">${r.customer_invoice_date || ''}</td>
      <td contenteditable class="cell-editable" data-field="expected_collection_date">${r.expected_collection_date || ''}</td>
      <td contenteditable class="cell-editable" data-field="supplier_invoice_date">${r.supplier_invoice_date || ''}</td>
      <td contenteditable class="cell-editable" data-field="supplier_invoice_number">${r.supplier_invoice_number || ''}</td>
      <td contenteditable class="cell-editable" data-field="scheduled_supplier_payment_date">${r.scheduled_supplier_payment_date || ''}</td>
      <td contenteditable class="cell-editable" data-field="purchase_order">${r.purchase_order || ''}</td>
      <td>
        <select class="form-select form-select-sm bool-select" data-field="missing_approval">
          <option value="n" ${r.missing_approval ? '' : 'selected'}>No</option>
          <option value="y" ${r.missing_approval ? 'selected' : ''}>Sí</option>
        </select>
      </td>
      <td>
        <select class="form-select form-select-sm bool-select" data-field="has_factoring">
          <option value="n" ${r.has_factoring ? '' : 'selected'}>No</option>
          <option value="y" ${r.has_factoring ? 'selected' : ''}>Sí</option>
        </select>
      </td>
      <td contenteditable class="cell-editable" data-field="notes">${r.notes || ''}</td>
    `;
    return tr;
  }

  // Loading
  function setLoading(isLoading){
    if(!$loading) return;
    $loading.classList.toggle('d-none', !isLoading);
  }

  // Load data
  async function loadData(page=1) {
    const params = new URLSearchParams(new FormData($form));
    params.set('page', page);
    params.set('page_size', 50);
    setLoading(true);
    try {
      const res = await fetch(`${location.pathname}api/list/?` + params.toString(), {headers: {'Accept': 'application/json'}});
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      renderTable(data.results || []);
      updateKpis(data.results || []);
      buildActiveFilterChips();
    } catch (err) {
      console.error(err);
      showToast('No se pudo cargar la información', true);
    } finally {
      setLoading(false);
    }
  }

  function renderTable(rows){
    $tbody.innerHTML = '';
    rows.forEach(r => $tbody.appendChild(buildRow(r)));
  }

  function updateKpis(rows){
    // Using available fields only (Phase 1): sale, cost, profit. Collected/pending placeholders.
    const sum = (arr, sel) => arr.reduce((acc, it)=>acc + (Number(it[sel]) || 0), 0);
    const sales = sum(rows, 'sale_amount');
    const costs = sum(rows, 'cost_amount');
    const profit = sum(rows, 'profit');
    const pending = Math.max(0, sales - 0); // no collected amount yet in Phase 1
    setText('kpi-sales', fmtMoney(sales));
    setText('kpi-costs', fmtMoney(costs));
    setText('kpi-profit', fmtMoney(profit));
    setText('kpi-collected', fmtMoney(0));
    setText('kpi-pending', fmtMoney(pending));
    const margin = sales ? (profit * 100 / sales) : 0;
    setText('kpi-margin', `${margin.toFixed(2)}%`);
  }

  function setText(id, text){
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  // Save cell inline
  async function saveCell(td){
    const tr = td.closest('tr');
    const controlId = tr?.dataset?.id;
    const field = td.dataset.field;
    const value = td.innerText.trim();
    if(!controlId || !field) return;
    td.dataset.saving = '1';
    td.style.opacity = '.6';
    try {
      const res = await fetch(`${location.pathname}api/update-field/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ control_id: controlId, field, value })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      // Update recalculated values
      if (data.recalc) {
        const cells = tr.querySelectorAll('td');
        // Indices according to the row template
        cells[5].innerText = fmtMoney(data.recalc.sale_amount);
        cells[6].innerText = fmtMoney(data.recalc.cost_amount);
        cells[7].innerText = fmtMoney(data.recalc.factoring_cost);
        cells[8].innerText = fmtMoney(data.recalc.profit);
        cells[9].innerText = fmtPercent(data.recalc.profit_percentage);
      }
      showToast('Cambios guardados ✓');
    } catch (err) {
      console.error(err);
      showToast('No se pudo guardar el cambio', true);
    } finally {
      td.dataset.saving = '0';
      td.style.opacity = '';
    }
  }

  // Save boolean select inline (Vo.Bo. / Factoraje)
  async function saveSelect(selectEl){
    const tr = selectEl.closest('tr');
    const controlId = tr?.dataset?.id;
    const field = selectEl.dataset.field;
    const value = selectEl.value; // 'y' or 'n'
    if(!controlId || !field) return;
    const prevDisabled = selectEl.disabled;
    selectEl.disabled = true;
    try {
      const res = await fetch(`${location.pathname}api/update-field/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ control_id: controlId, field, value })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      // Update recalculated values (e.g., factoraje cambia utilidad)
      if (data.recalc) {
        const cells = tr.querySelectorAll('td');
        cells[5].innerText = fmtMoney(data.recalc.sale_amount);
        cells[6].innerText = fmtMoney(data.recalc.cost_amount);
        cells[7].innerText = fmtMoney(data.recalc.factoring_cost);
        cells[8].innerText = fmtMoney(data.recalc.profit);
        cells[9].innerText = fmtPercent(data.recalc.profit_percentage);
      }
      showToast('Cambios guardados ✓');
    } catch (err) {
      console.error(err);
      showToast('No se pudo guardar el cambio', true);
    } finally {
      selectEl.disabled = prevDisabled;
    }
  }

  function showToast(message, isError=false){
    if (!toast) return alert(message);
    toastEl.classList.toggle('text-bg-danger', !!isError);
    toastEl.classList.toggle('text-bg-primary', !isError);
    toastBody.textContent = message;
    toast.show();
  }

  // Active filter chips
  function buildActiveFilterChips(){
    if (!$chips) return;
    $chips.innerHTML = '';
    const fd = new FormData($form);
    for (const [key, val] of fd.entries()){
      if (!val) continue;
      const chip = document.createElement('span');
      chip.className = 'filter-chip';
      chip.innerHTML = `${labelFor(key)}: <strong>${escapeHtml(val)}</strong> <button class="btn-clear" aria-label="Quitar">✕</button>`;
      chip.querySelector('.btn-clear').addEventListener('click', ()=>{
        const el = $form.querySelector(`[name="${cssEscape(key)}"]`);
        if (el){ el.value = ''; $form.dispatchEvent(new Event('submit')); }
      });
      $chips.appendChild(chip);
    }
  }

  function labelFor(name){
    switch(name){
      case 'date_from': return 'Desde';
      case 'date_to': return 'Hasta';
      case 'client': return 'Cliente';
      case 'supplier': return 'Proveedor';
      case 'invoiced': return 'Facturado';
      case 'missing_approval': return 'Vo.Bo.';
      case 'has_factoring': return 'Factoraje';
      default: return name;
    }
  }

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c])); }
  function cssEscape(s){ return CSS && CSS.escape ? CSS.escape(s) : s.replace(/[^a-z0-9_-]/ig, '_'); }

  // Events
  $form.addEventListener('submit', (ev) => { ev.preventDefault(); loadData(1); });

  document.querySelector('#grid tbody').addEventListener('blur', (ev) => {
    const td = ev.target;
    if (td.matches('.cell-editable')) saveCell(td);
  }, true);

  // Delegate change for boolean selects (Vo.Bo. / Factoraje)
  document.querySelector('#grid tbody').addEventListener('change', (ev) => {
    const el = ev.target;
    if (el.matches('select.bool-select')) {
      saveSelect(el);
    }
  });

  if (btnQuick7d){
    btnQuick7d.addEventListener('click', ()=>{
      const to = new Date();
      const from = new Date(Date.now() - 6*24*60*60*1000);
      setDate('date_from', from);
      setDate('date_to', to);
      loadData(1);
    });
  }
  if (btnQuickMonth){
    btnQuickMonth.addEventListener('click', ()=>{
      const now = new Date();
      const from = new Date(now.getFullYear(), now.getMonth(), 1);
      const to = new Date(now.getFullYear(), now.getMonth()+1, 0);
      setDate('date_from', from);
      setDate('date_to', to);
      loadData(1);
    });
  }
  if (btnReset){
    btnReset.addEventListener('click', ()=>{
      $form.reset();
      loadData(1);
    });
  }
  if (btnExport){
    btnExport.addEventListener('click', ()=>{
      const params = new URLSearchParams(new FormData($form));
      // TODO: point to real export endpoint once available
      const url = `${location.pathname}export/?` + params.toString();
      window.open(url, '_blank');
    });
  }

  function setDate(field, date){
    const el = $form.querySelector(`[name="${field}"]`);
    if (!el) return;
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth()+1).padStart(2,'0');
    const dd = String(date.getDate()).padStart(2,'0');
    el.value = `${yyyy}-${mm}-${dd}`;
  }

  // Initial load
  loadData().catch(console.error);
})();
