/* Finance Edit - Inline grid with auto-save and SweetAlert validation */
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
  function fmtPercent(v){
    if (v == null || v === '') return '';
    const n = Number(v);
    return isFinite(n) ? n.toFixed(2) + '%' : v;
  }

  function buildRow(r){
    const tr = document.createElement('tr');
    tr.dataset.id = r.id;

    const ingresoReadOnly = !!r.has_purchase_order; // if true, ingreso/fecha cobro are read-only

    const ingresoValue = r.has_purchase_order ? r.purchase_order_total : (r.sale_amount_override ?? r.sale_amount);
    const ingresoDisplay = fmtMoney(ingresoValue);

    tr.innerHTML = `
      <td>${r.folio ?? ''}</td>
      <td>${r.date ?? ''}</td>
      <td>${r.client ?? ''}</td>
      <td>${r.unit ?? ''}</td>
      <td>${r.has_purchase_order ? (r.purchase_order_folio || 'Sí') : '—'}</td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="sale_amount_override" value="${r.sale_amount_override ?? ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="expected_collection_date" placeholder="DD-MM-YYYY" value="${formatDateDDMMYYYY(r.expected_collection_date) || ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="cost_amount_override" ${r.has_purchase_order?'disabled':''} value="${r.has_purchase_order ? '' : (r.cost_amount_override ?? '')}">
        ${r.has_purchase_order ? '<div class="small text-muted">Tomado de OC: '+ fmtMoney(r.purchase_order_total) +'</div>' : ''}
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="supplier_invoice_number" value="${r.supplier_invoice_number ?? ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="supplier_invoice_date" placeholder="DD-MM-YYYY" value="${formatDateDDMMYYYY(r.supplier_invoice_date) || ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="scheduled_supplier_payment_date" placeholder="DD-MM-YYYY" value="${formatDateDDMMYYYY(r.scheduled_supplier_payment_date) || ''}">
      </td>
      <td>
        <select class="form-select form-select-sm edit" data-field="has_factoring">
          <option value="n" ${r.has_factoring? '':'selected'}>No</option>
          <option value="y" ${r.has_factoring? 'selected':''}>Sí</option>
        </select>
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="factoring_amount" value="${r.factoring_amount ?? ''}">
      </td>
      <td>
        <input type="text" class="form-control form-control-sm edit" data-field="factoring_percentage" value="${r.factoring_percentage ?? ''}">
      </td>
      <td class="text-end">${fmtMoney(r.profit)}</td>
      <td class="text-end">${fmtPercent(r.profit_percentage)}</td>
      <td>
        <textarea class="form-control form-control-sm edit" data-field="notes" rows="1">${r.notes ?? ''}</textarea>
      </td>
    `;

    // initialize original values for change detection
    tr.querySelectorAll('.edit').forEach(el => {
      const field = el.dataset.field;
      const current = (el.tagName === 'SELECT') ? el.value : el.value;
      el.dataset.orig = normalizeForCompare(field, current) || '';
    });

    // attach listeners
    tr.querySelectorAll('.edit').forEach(el => {
      el.addEventListener('focus', () => {
        const field = el.dataset.field;
        const current = (el.tagName === 'SELECT') ? el.value : el.value;
        el.dataset.orig = normalizeForCompare(field, current) || '';
      });
      el.addEventListener('change', () => saveField(tr, el));
      el.addEventListener('blur', () => saveField(tr, el));
      el.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter' && !(el.tagName === 'TEXTAREA')) {
          ev.preventDefault();
          el.blur();
        }
      });
    });

    return tr;
  }

  function formatDateDDMMYYYY(isoDate){
    if (!isoDate) return '';
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return '';
    const dd = String(d.getDate()).padStart(2,'0');
    const mm = String(d.getMonth()+1).padStart(2,'0');
    const yyyy = d.getFullYear();
    return `${dd}-${mm}-${yyyy}`;
  }

  function isValidDDMMYYYY(s){
    return /^\d{2}-\d{2}-\d{4}$/.test(s);
  }

  function latinDecimalToCanonical(s){
    if (s == null || s === '') return s;
    s = String(s).trim();
    // allow 1.234,56 or 1234,56 or 1234.56
    const latin = /^[-+]?\d{1,3}(?:[\.\s]\d{3})*(?:,\d+)?$|^[-+]?\d+(?:,\d+)?$/;
    if (latin.test(s)){
      return s.replace(/[\.\s]/g, '').replace(',', '.');
    }
    const dot = /^[-+]?\d+(?:\.\d+)?$/;
    if (dot.test(s)) return s;
    return null;
  }

  function normalizeForCompare(field, value){
    if (value == null) return '';
    let v = String(value).trim();
    if (v === '') return '';
    if (["sale_amount_override","cost_amount_override","factoring_amount","factoring_percentage"].includes(field)){
      const canon = latinDecimalToCanonical(v);
      return canon == null ? '__INVALID__' : canon; // use canonical decimal string
    }
    if (["supplier_invoice_date","scheduled_supplier_payment_date","expected_collection_date"].includes(field)){
      // Normalize to YYYY-MM-DD for comparison
      if (/^\d{2}-\d{2}-\d{4}$/.test(v)){
        const [dd,mm,yyyy] = v.split('-');
        return `${yyyy}-${mm}-${dd}`;
      }
      if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return v;
      return v; // unknown format; compare raw
    }
    if (field === 'has_factoring'){
      const low = v.toLowerCase();
      if (['y','yes','si','sí','1','true'].includes(low)) return 'y';
      return 'n';
    }
    return v;
  }

  async function saveField(tr, el){
    // Do not attempt to save disabled inputs
    if (el.disabled) return;

    const id = tr.dataset.id;
    const field = el.dataset.field;
    let value = el.value;

    // Validate presence of required identifiers and allowed fields
    const allowed = [
      'sale_amount_override',
      'expected_collection_date',
      'cost_amount_override',
      'supplier_invoice_number',
      'supplier_invoice_date',
      'scheduled_supplier_payment_date',
      'has_factoring',
      'factoring_amount',
      'factoring_percentage',
      'notes'
    ];
    if (!id) {
      await Swal.fire({icon:'error', title:'No se guardó', text:'Falta el identificador de la fila (control_id).'});
      return;
    }
    if (!field || !allowed.includes(field)){
      // Silently ignore unknown fields to avoid unnecessary server calls
      return;
    }

    // Early exit: if value did not change (after normalization), do not call API
    const currentNorm = normalizeForCompare(field, value);
    const origNorm = el.dataset.orig || '';
    if (currentNorm !== '__INVALID__' && currentNorm === origNorm) {
      return; // no-op, silently skip
    }

    // client-side validation and normalization for payload
    if (["supplier_invoice_date","scheduled_supplier_payment_date","expected_collection_date"].includes(field)){
      if (value){
        if (!isValidDDMMYYYY(value)){
          await Swal.fire({icon:'error', title:'Fecha inválida', text:'Usa el formato DD-MM-YYYY'});
          return;
        }
      }
    }
    if (["sale_amount_override","cost_amount_override","factoring_amount","factoring_percentage"].includes(field)){
      const canon = latinDecimalToCanonical(value);
      if (value && !canon){
        await Swal.fire({icon:'error', title:'Número inválido', text:'Usa formato latino (e.g., 1.234,56) o punto decimal (1234.56).'});
        return;
      }
      value = canon ?? '';
    }

    // build payload
    const payload = { control_id: id, field, value };

    // optimistic UI: mark row saving
    tr.classList.add('saving');

    try {
      const res = await fetch(window.OP_CTRL.apiUpdateFinance, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok){
        const errText = await res.text();
        throw new Error(errText || ('HTTP ' + res.status));
      }
      const data = await res.json();
      // update computed columns
      if (data.recalc){
        const tds = tr.querySelectorAll('td');
        // profit and margin update (positions may change; instead select last two cells)
        tds[tds.length - 3].textContent = fmtMoney(data.recalc.profit);
        tds[tds.length - 2].textContent = fmtPercent(data.recalc.profit_percentage);
      }
      // on success, update original normalized value to avoid re-sending unchanged
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
