// --- CONFIG/Refs ---
let paymentIndex = 0;
const paymentsContainer = document.getElementById('payments');

const TAXES = JSON.parse(document.getElementById('taxes-json').textContent || '[]');

function renderPaymentCard(idx, data) {
    // data: { id, product, description, price, tax }
    const uuid = data.uuid || {};
    const payment_amount = Number(data.debt_before || 0);
    const payment_number = data.payment_number;
    const debt_before = data.debt_before;

    return `
    <div class="card mb-3 payment-group" data-index="${idx}">
      <div class="card-header py-2 d-flex justify-content-between align-items-center">
        <span>Pago #<span class="payment-seq">${idx + 1}</span></span>
        <button type="button" class="btn btn-sm btn-outline-danger" data-action="remove-payment" title="Eliminar">
          <i class="bi bi-trash"></i> Eliminar
        </button>
      </div>
      <div class="card-body pt-3">
        <div class="row g-3 align-items-end">
          <div class="col-12 col-md-8">
            <label class="form-label">Folio fiscal (UUID)</label>
            <input type="text" class="form-control"
                   name="payments[${idx}][uuid]"
                   placeholder="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
                   maxlength="36" autocomplete="off"
                   style="text-transform: uppercase;"
                   pattern="^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$"
                   value="${uuid}">
          </div>

          <!-- === Impuestos múltiples === -->
          <div class="col-12 col-md-4">
            <label class="form-label">Impuestos</label>
            <select class="form-select select2-tax"
                    name="payments[${idx}][tax_ids][]"
                    multiple
                    data-placeholder="Selecciona impuestos">
              <option></option>
            </select>
          </div>

          <div class="col-12 col-md-4">
            <label class="form-label">Cantidad pagada</label>
            <input type="number" step="0.01" min="0" class="form-control"
                   name="payments[${idx}][amount]" placeholder="0.00" value="${payment_amount}" required>
          </div>

          <div class="col-12 col-md-4">
            <label class="form-label">Número de pago</label>
            <input type="number" min="1" class="form-control"
                   name="payments[${idx}][number]" placeholder="1" value="${payment_number}" required>
          </div>

          <div class="col-12 col-md-4">
            <label class="form-label">Total adeudado antes del pago</label>
            <input type="number" step="0.01" min="0" class="form-control"
                   name="payments[${idx}][previous_balance]" placeholder="0.00" value="${debt_before}" required>
          </div>
        </div>
      </div>
    </div>`;
}

// --- API add product (desde select2) ---
function addPaymentFromApi(payload) {
    const idx = paymentIndex;
    paymentsContainer.insertAdjacentHTML('beforeend', renderPaymentCard(idx, payload));
    const lastGroup = paymentsContainer.querySelector('.payment-group:last-child');
    const taxSelect = lastGroup.querySelector('.select2-tax');
    populateTaxSelect(taxSelect);
    paymentIndex += 1;
    reindexPayments();
    recalcPaymentsTotal();
}

// --- Listeners ---
// 1) Selección desde Select2 en #id_product -> fetch + add
$('#id_payment_invoice').on('select2:select', function () {
    const selected = $("#id_payment_invoice").val();
    $.post('/system/catalog', {
        action: "SelectConglomerado",
        csrfmiddlewaretoken: csrfToken,
        selected: selected
    }, function (data) {
        addPaymentFromApi(data); // {id, product, description, price, tax}
    });
});

// 2) Delegación para eliminar tarjetas
paymentsContainer.addEventListener('click', function (ev) {
    const btn = ev.target.closest('[data-action="remove-payment"]');
    if (!btn) return;
    const card = btn.closest('.payment-group');
    if (card) {
        card.remove();
        //reindexpayments();
    }
});

// 3) Recalcular cuando cambian inputs relevantes (precio/cantidad/descuento)
paymentsContainer.addEventListener('input', function (ev) {
    const target = ev.target;
    //if (!target.classList.contains('product-calc')) return;
    //const card = target.closest('.product-group');
    //if (card) recalcCardTotal(card);
});

// 4) Recalcular también al perder foco
paymentsContainer.addEventListener('change', function (ev) {
    const target = ev.target;
    //if (!target.classList.contains('product-calc')) return;
    //const card = target.closest('.product-group');
    //if (card) recalcCardTotal(card);
});

function populateTaxSelect(selectEl, selectedId = null) {
    // Limpia y agrega placeholder
    selectEl.innerHTML = '<option></option>';
    // Rellena opciones
    const opts = TAXES.map(t => {
        const text = `${t.name} (${t.type}) - ${Number(t.rate).toFixed(4)}`;
        return `<option value="${t.id}">${text}</option>`;
    }).join('');
    selectEl.insertAdjacentHTML('beforeend', opts);

    // Activa Select2
    $(selectEl).select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: selectEl.dataset.placeholder || 'Selecciona impuesto',
        allowClear: true,
        dropdownParent: $('#InvoiceForm')
    });

    // Seleccion predefinida
    if (selectedId) {
        $(selectEl).val(selectedId).trigger('change', {skipRateSet: true});
    }

    // Cuando selecciona, llena la tasa oculta
    $(selectEl).on('select2:select', function (e) {
        const id = this.value;
        const tax = TAXES.find(x => String(x.id) === String(id));
        const group = this.closest('.payment-group');
        if (!group) return;
        const rateInput = group.querySelector('.tax-rate');
        if (rateInput && tax && !e.params?.skipRateSet) {
            rateInput.value = tax.rate; // ejemplo: 0.1600
        }
    });

    // Clear → borra la tasa
    $(selectEl).on('select2:clear', function () {
        const group = this.closest('.payment-group');
        const rateInput = group?.querySelector('.tax-rate');
        if (rateInput) rateInput.value = '';
    });
}

// Global para onclick del botón en plantilla
window.addPayment = function () {
    const container = document.getElementById('payments');
    container.insertAdjacentHTML('beforeend', renderPaymentGroup(paymentIndex));
    paymentIndex += 1;
    reindexPayments(); // asegura secuencia visible y nombres coherentes
    recalcPaymentsTotal();
};

// Delegación para eliminar
document.getElementById('payments').addEventListener('click', function (ev) {
    const btn = ev.target.closest('[data-action="remove-payment"]');
    if (!btn) return;
    const group = btn.closest('.payment-group');
    if (group) {
        group.remove();
        reindexPayments();
        recalcPaymentsTotal();
    }
});

window.addPayment = function () {
    const container = document.getElementById('payments');
    container.insertAdjacentHTML('beforeend', renderPaymentGroup(paymentIndex));
    const lastGroup = container.querySelector('.payment-group:last-child');
    const taxSelect = lastGroup.querySelector('.select2-tax');
    populateTaxSelect(taxSelect);
    paymentIndex += 1;
    reindexPayments();
    recalcPaymentsTotal();
};

function reindexPayments() {
    const groups = document.querySelectorAll('#payments .payment-group');
    groups.forEach((group, newIdx) => {
        group.dataset.index = newIdx;
        group.querySelector('.payment-seq').textContent = newIdx + 1;

        // Actualiza name= de inputs y selects
        const fields = group.querySelectorAll('input[name^="payments["], select[name^="payments["], textarea[name^="payments["]');
        fields.forEach((el) => {
            const parts = el.name.split(']');           // ["payments[0", "[field", ""]
            const field = parts[1].replace('[', '');     // field
            el.name = `payments[${newIdx}][${field}]`;
        });
    });
    paymentIndex = groups.length;
}

// Inicializar fila resumen si ya hay productos renderizados del lado servidor
//ensureSummaryRow();
//recalcGrandTotal();
