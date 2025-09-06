// --- CONFIG/Refs ---
let productIndex = 0;
const productsContainer = document.getElementById('products');

// --- Helpers de UI ---
function ensureSummaryRow() {
    let summary = document.getElementById('products-summary');
    if (!summary) {
        summary = document.createElement('div');
        summary.id = 'products-summary';
        summary.className = 'd-flex justify-content-end mt-2';
        summary.innerHTML = `
      <div class="text-end">
        <strong>Total:</strong> <span id="grand-total">0.00</span>
      </div>`;
        // Insertamos al final del contenedor padre de #products
        const parent = productsContainer.parentElement || document.getElementById('product_form') || document.body;
        parent.appendChild(summary);
    }
}

function renderProductCard(idx, data) {
    // data: { id, product, description, price, tax }
    const prod = data || {};
    const price = Number(prod.price || 0);
    const tax = Number(prod.tax || 0);
    const qty = 1;
    const discount = 0;
    const base = Math.max(0, (price * qty) - discount);
    const total = base + base * tax;

    return `
    <div class="card mb-3 product-group" data-index="${idx}">
      <div class="card-header py-2 d-flex justify-content-between align-items-center">
        <span>Producto #<span class="product-seq">${idx + 1}</span></span>
        <button type="button" class="btn btn-sm btn-outline-danger" data-action="remove-product" title="Eliminar">
          <i class="bi bi-trash"></i> Eliminar
        </button>
      </div>

      <div class="card-body pt-3">
        <div class="row g-3">
          <input type="hidden"
                 data-field="id"
                 name="products[${idx}][id]"
                 id="product-id-${idx}"
                 value="${prod.id ?? ''}">

          <div class="col-12 col-md-6">
            <label class="form-label">Producto</label>
            <input type="text"
                   class="form-control"
                   data-field="product"
                   name="products[${idx}][product]"
                   id="product-${idx}"
                   value="${(prod.product ?? '').toString().replace(/"/g, '&quot;')}"
                   readonly>
          </div>

          <div class="col-12 col-md-6">
            <label class="form-label">Descripción</label>
            <input type="text"
                   class="form-control"
                   data-field="description"
                   name="products[${idx}][description]"
                   id="description-${idx}"
                   value="${(prod.description ?? '').toString().replace(/"/g, '&quot;')}">
          </div>

          <div class="col-6 col-md-3">
            <label class="form-label">Precio</label>
            <input type="number" step="0.01" min="0"
                   class="form-control product-calc text-end"
                   data-field="price"
                   name="products[${idx}][price]"
                   id="precio-${idx}"
                   value="${price.toFixed(2)}">
          </div>

          <div class="col-6 col-md-3">
            <label class="form-label">Cantidad</label>
            <input type="number" step="0.01" min="0"
                   class="form-control product-calc text-end"
                   data-field="quantity"
                   name="products[${idx}][quantity]"
                   id="id_quantity-${idx}"
                   value="${qty}">
          </div>

          <div class="col-6 col-md-3">
            <label class="form-label">Descuento</label>
            <input type="number" step="0.01" min="0"
                   class="form-control product-calc text-end"
                   data-field="discount"
                   name="products[${idx}][discount]"
                   id="id_discount-${idx}"
                   value="${discount.toFixed(2)}">
          </div>

          <div class="col-6 col-md-3">
            <label class="form-label">Impuesto (tasa)</label>
            <input type="number" step="0.0001" min="0"
                   class="form-control text-end"
                   data-field="tax"
                   name="products[${idx}][tax]"
                   id="id_tax-${idx}"
                   value="${tax}"
                   readonly>
            <small class="text-muted">Ej: 0.16 para 16%</small>
          </div>

          <div class="col-12 col-md-3 ms-auto">
            <label class="form-label">Total</label>
            <input type="text"
                   class="form-control text-end fw-semibold"
                   data-field="total"
                   name="products[${idx}][total]"
                   id="total-${idx}"
                   value="${total.toFixed(2)}"
                   readonly>
          </div>
        </div>
      </div>
    </div>
  `;
}

function recalcCardTotal(cardEl) {
    const getVal = (selector, fallback = 0) =>
        parseFloat(cardEl.querySelector(selector)?.value) || fallback;

    const price = getVal('[data-field="price"]', 0);
    const qty = getVal('[data-field="quantity"]', 0);
    const discount = getVal('[data-field="discount"]', 0);
    const tax = getVal('[data-field="tax"]', 0); // readonly, viene del server

    let base = (price * qty) - discount;
    if (base < 0) base = 0;

    const total = base + base * tax;
    cardEl.querySelector('[data-field="total"]').value = total.toFixed(2);

    recalcGrandTotal();
}

function recalcGrandTotal() {
    ensureSummaryRow();
    const totals = productsContainer.querySelectorAll('[data-field="total"]');
    let sum = 0;
    totals.forEach(inp => sum += (parseFloat(inp.value) || 0));
    const grand = document.getElementById('grand-total');
    if (grand) grand.textContent = sum.toFixed(2);
}

function reindexProducts() {
    const groups = productsContainer.querySelectorAll('.product-group');
    groups.forEach((group, newIdx) => {
        group.dataset.index = newIdx;
        const seq = group.querySelector('.product-seq');
        if (seq) seq.textContent = newIdx + 1;

        const inputs = group.querySelectorAll('[data-field]');
        inputs.forEach((inp) => {
            const field = inp.getAttribute('data-field');
            inp.name = `products[${newIdx}][${field}]`;
            switch (field) {
                case 'id':
                    inp.id = `product-id-${newIdx}`;
                    break;
                case 'product':
                    inp.id = `product-${newIdx}`;
                    break;
                case 'description':
                    inp.id = `description-${newIdx}`;
                    break;
                case 'price':
                    inp.id = `precio-${newIdx}`;
                    break;
                case 'quantity':
                    inp.id = `id_quantity-${newIdx}`;
                    break;
                case 'discount':
                    inp.id = `id_discount-${newIdx}`;
                    break;
                case 'tax':
                    inp.id = `id_tax-${newIdx}`;
                    break;
                case 'total':
                    inp.id = `total-${newIdx}`;
                    break;
            }
        });
    });

    productIndex = groups.length;
    recalcGrandTotal();
}

// --- API add product (desde select2) ---
function addProductFromApi(payload) {
    const idx = productIndex;
    productsContainer.insertAdjacentHTML('beforeend', renderProductCard(idx, payload));
    productIndex += 1;
    reindexProducts();
}

// --- Listeners ---
// 1) Selección desde Select2 en #id_product -> fetch + add
$('#id_product').on('select2:select', function () {
    const selected = $("#id_product").val();
    $.post('/system/catalog', {
        action: "SelectProduct",
        csrfmiddlewaretoken: csrfToken,
        selected: selected
    }, function (data) {
        addProductFromApi(data); // {id, product, description, price, tax}
    });
});

// 2) Delegación para eliminar tarjetas
productsContainer.addEventListener('click', function (ev) {
    const btn = ev.target.closest('[data-action="remove-product"]');
    if (!btn) return;
    const card = btn.closest('.product-group');
    if (card) {
        card.remove();
        reindexProducts();
    }
});

// 3) Recalcular cuando cambian inputs relevantes (precio/cantidad/descuento)
productsContainer.addEventListener('input', function (ev) {
    const target = ev.target;
    if (!target.classList.contains('product-calc')) return;
    const card = target.closest('.product-group');
    if (card) recalcCardTotal(card);
});

// 4) Recalcular también al perder foco
productsContainer.addEventListener('change', function (ev) {
    const target = ev.target;
    if (!target.classList.contains('product-calc')) return;
    const card = target.closest('.product-group');
    if (card) recalcCardTotal(card);
});

// Inicializar fila resumen si ya hay productos renderizados del lado servidor
ensureSummaryRow();
recalcGrandTotal();
