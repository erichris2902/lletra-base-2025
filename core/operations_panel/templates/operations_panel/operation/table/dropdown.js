function dropdown(data, type, row) {
    // Toma el identificador de la fila (ajusta si tu campo es otro)




    let dropdown = '<div class="dropdown">';

    if (row.invoice_id) {
        const invId = row.invoice_id;
        const isDisabled = !invId;

        // Ajusta estas rutas a tus endpoints reales
        const base = '/system/facturapi/invoices'; // p.ej: '/system/invoices' o '/facturapi/invoices'
        const hrefXML = `${base}/${invId}/download/xml/`;
        const hrefPDF = `${base}/${invId}/download/pdf/`;
        const hrefZIP = `${base}/${invId}/download/zip/`;
        const hrefACUSE = `${base}/${invId}/download/acuse/`;
        dropdown += `
            <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
                ${isDisabled ? 'href="#"' : `href="${hrefXML}"`} title="Descargar XML" target="_blank" rel="noopener">
                <i class="bi bi-filetype-xml"></i> XML
            </a>
        `;
        dropdown += `
        <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
            ${isDisabled ? 'href="#"' : `href="${hrefPDF}"`} title="Descargar PDF" target="_blank" rel="noopener">
            <i class="bi bi-filetype-pdf"></i> PDF
        </a>
        `;
        dropdown += `
        <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
             ${isDisabled ? 'href="#"' : `href="${hrefZIP}"`} title="Descargar ZIP" target="_blank" rel="noopener">
            <i class="bi bi-file-zip"></i> ZIP
        </a>
        `;
    }

    dropdown += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';

    dropdown += '<div class="dropdown-menu">';
    dropdown += '<a rel="update" class="dropdown-item" type="button">Actualizar</a>';
    dropdown += `<a href="/operations/generate_invoice/i/${row.id}/" target="_blank" class="dropdown-item">Cartaporte</a>`;
    dropdown += `<a href="/operations/generate_invoice/t/${row.id}/" target="_blank" class="dropdown-item">Translado</a>`;
    dropdown += `<a href="/operations/generate_invoice/local/${row.id}/" target="_blank" class="dropdown-item">Local</a>`;
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