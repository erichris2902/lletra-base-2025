function dropdown(data, type, row) {
    console.log(row);
    let dropdown = '<div class="dropdown">';
    dropdown += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';
    dropdown += '<div class="dropdown-menu">';
    dropdown += '<a rel="update" class="dropdown-item" type="button">Actualizar</a>';
    dropdown += `<a href="/operations/generate_invoice/i/${row.id}/" target="_blank" class="dropdown-item">Cartaporte</a>`;
    dropdown += `<a href="/operations/generate_invoice/t/${row.id}/" target="_blank" class="dropdown-item">Translado</a>`;
    dropdown += '<hr class="dropdown-divider">';
    if (!row.is_ready_to_invoice) {
        dropdown += `<a href="/operations/routes/shipment-invoice/${row.id}/pdf" target="_blank" class="dropdown-item">PDF</a>`;
        dropdown += `<a href="/operations/routes/shipment-invoice/${row.id}/xml" target="_blank" class="dropdown-item">XML</a>`;
    }
    dropdown += `<a href="/operations/download/shipment-invoice/${row.id}/no-signed" target="_blank" class="dropdown-item">Cartaporte (Sin timbre)</a>`;
    dropdown += '<hr class="dropdown-divider">';
    dropdown += `<a rel="release" target="_blank" class="dropdown-item">Liberar viaje</a>`;
    dropdown += '<hr class="dropdown-divider">';
    dropdown += '<a rel="delete" class="dropdown-item" type="button">Eliminar</a>';
    dropdown += '</div></div>';
    //var buttons = '';
    //buttons += dropdown;
    //return buttons;
    return dropdown;
}