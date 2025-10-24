

$('#main_datatable tbody').on('click', 'a[rel="get_assign_cargo_form"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_assign_cargo_form");
});

$('#main_datatable tbody').on('click', 'a[rel="get_assign_products_form"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_assign_products_form");
});

$('#main_datatable tbody').on('click', 'a[rel="update_cargo"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_cargo");
});

$('#main_datatable tbody').on('click', 'a[rel="update_packing"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_packing");
});

$('#main_datatable tbody').on('click', 'a[rel="update_route"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "get_route");
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

$('#main_datatable tbody').on('click', 'a[rel="confirm"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();

    const parameters = new FormData();
    parameters.append('action', 'confirm');
    parameters.append('id', data.id);
    parameters.append('csrfmiddlewaretoken', csrfToken);

    submit_with_ajax(window.location.pathname, parameters, function (data) {
        Swal.fire({
            icon: 'success',
            title: 'Éxito',
            text: 'Se confirmo exitosamente',
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