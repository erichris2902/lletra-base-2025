

$('#main_datatable tbody').on('click', 'a[rel="update"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    console.log(data);
    console.log(data.id);
    console.log(tr);
    LoadForm(data.id);
});

$('#main_datatable tbody').on('click', 'a[rel="delete"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();

    const parameters = new FormData();
    parameters.append('action', 'Delete');
    parameters.append('id', data.id);
    parameters.append('csrfmiddlewaretoken', csrfToken);

    submit_with_ajax(window.location.pathname, parameters, function (data) {
        Swal.fire({
            icon: 'success',
            title: 'Éxito',
            text: 'Se eliminó exitosamente',
        });
        tblClient.ajax.reload(null, false);
    }, function (data) {
        Swal.fire({
            icon: 'error',
            title: 'Oops...',
            text: data.error,
        });
    });
});