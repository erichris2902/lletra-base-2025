function dropdown(data, type, row) {
    let dropdown = '<div class="dropdown">';
    dropdown += '<button class="btn btn-primary dropdown-toggle btn-sm rounded-pill" type="button" data-bs-toggle="dropdown">Acciones</button>';
    dropdown += '<div class="dropdown-menu">';
    dropdown += '<a rel="update" class="dropdown-item" type="button">Actualizar</a>';
    dropdown += '<a href="/rh/employee/' + row.id + '" class="dropdown-item" type="button">Registrar biometrico</a>';
    dropdown += '<hr class="dropdown-divider">';
    dropdown += '<a rel="delete" class="dropdown-item" type="button">Eliminar</a>';
    dropdown += '</div></div>';
    //var buttons = '';
    //buttons += dropdown;
    //return buttons;
    return dropdown;
}