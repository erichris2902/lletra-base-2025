function dropdown(data, type, row) {
    // Toma el identificador de la fila (ajusta si tu campo es otro)
    const invId = row.id;
    const isDisabled = !invId;

    // Ajusta estas rutas a tus endpoints reales
    const base = '/system/facturapi/invoices'; // p.ej: '/system/invoices' o '/facturapi/invoices'
    const hrefXML = `${base}/${invId}/download/xml/`;
    const hrefPDF = `${base}/${invId}/download/pdf/`;
    const hrefZIP = `${base}/${invId}/download/zip/`;
    const hrefACUSE = `${base}/${invId}/download/acuse/`;


    var html = "<div class=\"btn-group btn-group-sm\" role=\"group\" aria-label=\"Acciones\">";
    html += `
        <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
            ${isDisabled ? 'href="#"' : `href="${hrefXML}"`} title="Descargar XML" target="_blank" rel="noopener">
            <i class="bi bi-filetype-xml"></i> XML
        </a>
    `;
    html += `
        <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
            ${isDisabled ? 'href="#"' : `href="${hrefPDF}"`} title="Descargar PDF" target="_blank" rel="noopener">
            <i class="bi bi-filetype-pdf"></i> PDF
        </a>
    `;
    html += `
        <a class="btn btn-outline-primary ${isDisabled ? 'disabled' : ''}" 
             ${isDisabled ? 'href="#"' : `href="${hrefZIP}"`} title="Descargar ZIP" target="_blank" rel="noopener">
            <i class="bi bi-file-zip"></i> ZIP
        </a>
    `;
    if (row.cancellation_status == "none" || row.cancellation_status == "rejected") {
        html += `
            <a rel="getcancelinvoice" class="btn btn-outline-danger" type="button" 
                data-action="cancel-invoice" data-id="${invId}" ${isDisabled ? 'disabled' : ''} title="Cancelar factura">
                <i class="bi bi-x-circle"></i> Cancelar
            </a>
        `;
    } else {
        html += `
            <a class="btn btn-outline-primary" type="button" ${isDisabled ? 'href="#"' : `href="${hrefACUSE}"`} 
                title="Acuse de cancelacion" target="_blank" rel="noopener">
                <i class="bi bi-x-circle"></i> Acuse
            </a>
        `;
    }

    html += `
        </div>
    `;

    // Nota: <a disabled> no deshabilita por defecto; marcamos clase 'disabled' si no hay ID
    return html;
}