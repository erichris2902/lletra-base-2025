function dropdown(data, type, row) {
    let dropdown = '<div class="dropdown">' ;
    dropdown += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';
    dropdown += '<div class="dropdown-menu">';
    if (row.is_ready_to_invoice === 'True') {
        dropdown += '<a rel="confirm" class="dropdown-item" type="button">Confirmar packing</a>';
    }
    dropdown += '<a rel="update" class="dropdown-item" type="button">Editar viaje</a>';
    dropdown += '<a rel="update_cargo" class="dropdown-item" type="button">Asignar carga</a>';
    dropdown += '<a rel="update_route" class="dropdown-item" type="button">Verificar ruta</a>';
    if (row.shipment_type === 'ASTURIANO') {
        dropdown += '<a rel="update_packing" class="dropdown-item" type="button">Distribuir packing</a>';
    }
    dropdown += '<hr class="dropdown-divider">';
    dropdown += '<a rel="delete" class="dropdown-item" type="button">Eliminar</a>';
    dropdown += '</div></div>';
    //var buttons = '';
    //buttons += dropdown;
    //return buttons;

    return dropdown;
}