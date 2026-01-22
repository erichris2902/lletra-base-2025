$('#main_datatable tbody').on('click', 'a[rel]', function () {

    if (!tblClient) {
        console.error('DataTable no inicializado');
        return;
    }

    const action = this.getAttribute('rel');
    const tr = this.closest('tr');
    const data = tblClient.row(tr).data();

    if (!data) {
        console.error('No se pudo obtener la fila');
        return;
    }

    console.log('Acción:', action, 'Fila:', data);


    switch (action) {
        case 'delete':
            deleteRow(data.id);
            break;
        case 'update':
            updateRow(data.id);
            break;
        default:
            LoadForm(data.id, action);
            break;
    }
});

function updateRow(id) {
    //const tr = tblClient.cell($(this).closest('td, li')).index();
    //const data = tblClient.row(tr.row).data();
    LoadForm(id);
}

function deleteRow(id) {
    const parameters = new FormData();
    parameters.append('action', 'Delete');
    parameters.append('id', id);
    parameters.append('csrfmiddlewaretoken', csrfToken);

    submit_with_ajax(window.location.pathname, parameters,
        function () {
            Swal.fire({
                icon: 'success',
                title: 'Éxito',
                text: 'Se eliminó exitosamente',
            });
            tblClient.ajax.reload(null, false);
        },
        function (data) {
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                html: data.error,
            });
        }
    );
}