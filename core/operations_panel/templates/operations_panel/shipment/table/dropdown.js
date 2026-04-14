function dropdown(data, type, row) {
    let dropdown = '<div class="dropdown">' ;

    if (row.invoice_id) {
        const invId = row.invoice_id;
        const isDisabled = !invId;

        // Ajusta estas rutas a tus endpoints reales
        const base = '/system/facturapi/invoices'; // p.ej: '/system/invoices' o '/facturapi/invoices'
        const hrefPDF = `${base}/${invId}/download/pdf/`;
        dropdown += `
        <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
            ${isDisabled ? 'href="#"' : `href="${hrefPDF}"`} title="Descargar PDF" target="_blank" rel="noopener">
            <i class="bi bi-filetype-pdf"></i> PDF
        </a>
        `;
    }


    dropdown += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';
    dropdown += '<div class="dropdown-menu">';
    if (row.is_ready_to_invoice === 'True' && row.is_packing_ready === 'False') {
        dropdown += '<a rel="confirm" class="dropdown-item" type="button">Confirmar packing</a>';
        dropdown += '<hr class="dropdown-divider">';
    }
    else if (row.is_packing_ready === 'True' && !row.invoice_id) {
        dropdown += `<a href="/operations/generate_invoice/t/${row.id}/" target="_blank" class="dropdown-item">Timbrar translado</a>`;
        dropdown += '<hr class="dropdown-divider">';
    }
    dropdown += '<a rel="update" class="dropdown-item" type="button">Editar viaje</a>';
    dropdown += '<hr class="dropdown-divider">';
    dropdown += '<a rel="update_route" class="dropdown-item" type="button">Verificar ruta</a>';
    dropdown += '<a rel="update_route_select" class="dropdown-item" type="button">Cambiar ruta</a>';
    dropdown += '<a rel="update_stops" class="dropdown-item" type="button">Actualizar paradas</a>';
    dropdown += '<a rel="update_origin" class="dropdown-item" type="button">Editar origen</a>';
    dropdown += '<a rel="update_destiny" class="dropdown-item" type="button">Editar destino</a>';
    dropdown += '<hr class="dropdown-divider">';
    if (row.shipment_type === 'ASTURIANO') {
        dropdown += '<a rel="update_packing" class="dropdown-item" type="button">Distribuir packing</a>';
        dropdown += '<a rel="get_assign_products_form" class="dropdown-item" type="button">Asignar producto</a>';
    }else{
        //dropdown += '<a rel="get_assign_products_form_old" class="dropdown-item" type="button">Asignar producto (OLD)</a>';
        dropdown += '<a rel="update_cargo" class="dropdown-item" type="button">Asignar carga por archivo</a>';
        dropdown += '<a rel="get_assign_cargo_form" class="dropdown-item" type="button">Asignar carga precargada</a>';
        dropdown += '<a rel="get_assign_products_form" class="dropdown-item" type="button">Asignar producto</a>';
    }
    dropdown += '<hr class="dropdown-divider">';
    dropdown += '<a rel="delete" class="dropdown-item" type="button">Eliminar</a>';
    dropdown += '</div></div>';
    //var buttons = '';
    //buttons += dropdown;
    //return buttons;

    return dropdown;
}