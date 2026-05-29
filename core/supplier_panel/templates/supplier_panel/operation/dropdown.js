function dropdown(data, type, row) {
    let html = '<div class="dropdown">';
    html += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';
    html += '<div class="dropdown-menu">';

    // Subir evidencia (abre modal con el form)
    html += '<a rel="Get" class="dropdown-item" type="button">Subir evidencia (Fotos/PDF)</a>';

    html += '</div></div>';
    return html;
}
