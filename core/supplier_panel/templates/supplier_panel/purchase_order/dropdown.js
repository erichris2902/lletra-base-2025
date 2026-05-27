function dropdown(data, type, row) {
    let html = '<div class="dropdown">';
    html += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';
    html += '<div class="dropdown-menu">';

    // Subir factura (abre modal con el form)
    html += '<a rel="Get" class="dropdown-item" type="button">Subir factura (XML/PDF)</a>';

    // Descargar OC (usa la vista existente en admin_panel)
    const downloadUrl = `/purchase-orders/${row.id}/pdf/`;
    html += `<a class="dropdown-item" href="${downloadUrl}" target="_blank">Descargar orden de compra</a>`;

    html += '</div></div>';
    return html;
}
