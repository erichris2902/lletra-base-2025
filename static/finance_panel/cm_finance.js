/* Finance CM quick-edit page (/finance/cm/) */
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

  const $tbody = document.getElementById('tbody');
  const $btnApply = document.getElementById('btn-apply');
  const $btnClear = document.getElementById('btn-clear');
  const $pageInfo = document.getElementById('page-info');
  const $prev = document.getElementById('prev');
  const $next = document.getElementById('next');

  const $fDateFrom = document.getElementById('filter-date-from');
  const $fDateTo = document.getElementById('filter-date-to');
  const $fClient = document.getElementById('filter-client');
  const $fSupplier = document.getElementById('filter-supplier');
  const $fFolio = document.getElementById('filter-folio');

  let currentPage = 1;
  const pageSize = 25;

  function fmtMoney(v){
    if (v == null || v === '') return '';
    const n = Number(String(v).replace(/[\s,]/g, m => (m === ',' ? '.' : '')));
    return isFinite(n) ? n.toLocaleString('es-MX', {style: 'currency', currency: 'MXN'}) : v;
  }
  function fmtDateISO(d){
    if (!d) return '';
    try {
      const dt = new Date(d);
      if (!isNaN(dt)){
        const yyyy = dt.getFullYear();
        const mm = String(dt.getMonth()+1).padStart(2,'0');
        const dd = String(dt.getDate()).padStart(2,'0');
        return `${dd}-${mm}-${yyyy}`;
      }
    } catch(_){/*ignore*/}
    // if already string like YYYY-MM-DD
    const m = String(d).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) return `${m[3]}-${m[2]}-${m[1]}`;
    return String(d);
  }
  function isValidDDMMYYYY(s){
    if (!s) return true;
    const m = String(s).match(/^(\d{2})-(\d{2})-(\d{4})$/);
    if (!m) return false;
    const dd = +m[1], mm = +m[2], yyyy = +m[3];
    const dt = new Date(yyyy, mm-1, dd);
    return dt.getFullYear()===yyyy && dt.getMonth()===mm-1 && dt.getDate()===dd;
  }
  function latinDecimalToCanonical(value){
    if (value == null) return '';
    const s = String(value).trim();
    if (s === '') return '';
    // Remove thousands separators (.) and unify decimal separator to .
    const t = s.replace(/\./g, '').replace(/,/g, '.');
    const n = Number(t);
    if (!isFinite(n)) return null;
    return n.toFixed(2);
  }

  function normalizeForCompare(field, value){
    const numeric = ['collected_amount_reported','supplier_paid_amount_reported'];
    if (numeric.includes(field)){
      const canon = latinDecimalToCanonical(value);
      return canon === '' ? '' : (canon ?? '__INVALID__');
    }
    const dateFields = ['expected_collection_date','supplier_invoice_date','scheduled_supplier_payment_date'];
    if (dateFields.includes(field)){
      if (!value) return '';
      if (!isValidDDMMYYYY(value)) return '__INVALID__';
      // normalize to YYYY-MM-DD for comparison
      const [dd,mm,yyyy] = value.split('-');
      return `${yyyy}-${mm}-${dd}`;
    }
    return (value ?? '').trim();
  }

  function buildRow(r){
    const tr = document.createElement('tr');
    tr.dataset.id = r.id;

    const hasPO = !!r.has_purchase_order;
    const ingresoDisplay = hasPO ? (r.purchase_order_total ? fmtMoney(r.purchase_order_total) : '—') : fmtMoney(r.sale_amount);
    const costoDisplay = fmtMoney(r.cost_amount);

    tr.innerHTML = `
      <td class="nowrap">${r.folio ?? ''}</td>
      <td class="nowrap">${r.date ?? ''}</td>
      <td>${r.client ?? ''}</td>
      <td>${r.unit ?? ''}</td>
      <td>${hasPO ? (r.purchase_order_folio || 'Sí') : '—'}</td>
      <td class="text-end">${ingresoDisplay}</td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="collected_amount_reported" placeholder="0.00" value="${r.collected_amount_reported ?? ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="expected_collection_date" placeholder="DD-MM-YYYY" value="${fmtDateISO(r.expected_collection_date) || ''}">
      </td>
      <td class="text-end">${costoDisplay}</td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="supplier_paid_amount_reported" placeholder="0.00" value="${r.supplier_paid_amount_reported ?? ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="supplier_invoice_number" value="${r.supplier_invoice_number ?? ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="supplier_invoice_date" placeholder="DD-MM-YYYY" value="${fmtDateISO(r.supplier_invoice_date) || ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="scheduled_supplier_payment_date" placeholder="DD-MM-YYYY" value="${fmtDateISO(r.scheduled_supplier_payment_date) || ''}">
      </td>
      <td>
        <textarea class="form-control form-control-sm edit" data-field="notes" rows="1">${r.notes ?? ''}</textarea>
      </td>
    `;

    // mark original values for change detection
    tr.querySelectorAll('.edit').forEach(el => {
      const field = el.dataset.field;
      const val = el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' ? el.value : (el.value || '');
      el.dataset.orig = normalizeForCompare(field, val) || '';
    });

    tr.querySelectorAll('.edit').forEach(el => {
      el.addEventListener('blur', () => trySave(el));
      el.addEventListener('keydown', (ev)=>{
        if (ev.key === 'Enter' && el.tagName === 'INPUT') {
          ev.preventDefault();
          el.blur();
        }
      });
    });

    return tr;
  }

  async function trySave(el){
    const tr = el.closest('tr');
    const id = tr?.dataset?.id;
    const field = el.dataset.field;
    let value = (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') ? el.value.trim() : el.value;

    const allowed = [
      'collected_amount_reported',
      'supplier_paid_amount_reported',
      'expected_collection_date',
      'supplier_invoice_number',
      'supplier_invoice_date',
      'scheduled_supplier_payment_date',
      'notes'
    ];
    if (!id || !field || !allowed.includes(field)) return;

    // Early exit: no change
    const currentNorm = normalizeForCompare(field, value);
    const origNorm = el.dataset.orig || '';
    if (currentNorm !== '__INVALID__' && currentNorm === origNorm) return;

    // Validate
    if (['supplier_invoice_date','scheduled_supplier_payment_date','expected_collection_date'].includes(field)){
      if (value && !isValidDDMMYYYY(value)){
        await Swal.fire({icon:'error', title:'Fecha inválida', text:'Usa el formato DD-MM-YYYY'});
        return;
      }
    }
    if (['collected_amount_reported','supplier_paid_amount_reported'].includes(field)){
      const canon = latinDecimalToCanonical(value);
      if (value && !canon){
        await Swal.fire({icon:'error', title:'Número inválido', text:'Usa formato latino (1.234,56) o decimal (1234.56).'});
        return;
      }
      value = canon ?? '';
    }

    const payload = { control_id: id, field, value };
    tr.classList.add('saving');

    try {
      const res = await fetch(window.OP_CTRL.apiUpdateFinance, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken, 'Accept': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok){
        const errText = await res.text();
        throw new Error(errText || ('HTTP ' + res.status));
      }
      const data = await res.json();
      // On success, update orig
      el.dataset.orig = currentNorm || '';
    } catch (e){
      console.error(e);
      await Swal.fire({icon:'error', title:'No se guardó', text: String(e.message || e)});
    } finally {
      tr.classList.remove('saving');
    }
  }

  async function loadPage(page){
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', pageSize);
    if ($fDateFrom.value) params.set('date_from', $fDateFrom.value);
    if ($fDateTo.value) params.set('date_to', $fDateTo.value);
    if ($fClient.value) params.set('client', $fClient.value);
    if ($fSupplier.value) params.set('supplier', $fSupplier.value);
    if ($fFolio && $fFolio.value) params.set('folio', $fFolio.value);

    const url = OP_CTRL.apiList + '?' + params.toString();
    const res = await fetch(url, {headers: {'Accept': 'application/json'}});
    if (!res.ok) {
      await Swal.fire({icon:'error', title:'Error cargando lista', text: 'HTTP ' + res.status});
      return;
    }
    const data = await res.json();

    $tbody.innerHTML = '';
    (data.results || []).forEach(r => $tbody.appendChild(buildRow(r)));

    currentPage = data.page || page;
    $pageInfo.textContent = `Página ${currentPage} de ${data.num_pages || 1} (Total: ${data.count || 0})`;
    $prev.disabled = currentPage <= 1;
    $next.disabled = currentPage >= (data.num_pages || 1);
  }

  $btnApply.addEventListener('click', () => loadPage(1));
  $btnClear.addEventListener('click', () => {
    $fDateFrom.value = '';
    $fDateTo.value = '';
    $fClient.value = '';
    $fSupplier.value = '';
    if ($fFolio) $fFolio.value = '';
    loadPage(1);
  });
  $prev.addEventListener('click', () => { if (currentPage > 1) loadPage(currentPage - 1); });
  $next.addEventListener('click', () => loadPage(currentPage + 1));

  // init
  loadPage(1);
})();
