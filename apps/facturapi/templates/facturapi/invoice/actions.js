


$('#main_datatable tbody').on('click', 'a[rel="getcancelinvoice"]', function () {
    const tr = tblClient.cell($(this).closest('td, li')).index();
    const data = tblClient.row(tr.row).data();
    LoadForm(data.id, "getcancelinvoice");
});
