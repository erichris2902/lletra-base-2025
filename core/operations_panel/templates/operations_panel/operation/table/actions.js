

$('#main_datatable tbody').on('click', 'a[rel="invoice_i"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_invoice_i");
});

$('#main_datatable tbody').on('click', 'a[rel="invoice_t"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_invoice_t");
});

$('#main_datatable tbody').on('click', 'a[rel="update"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
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