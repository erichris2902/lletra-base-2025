

function styleCells(row) {
    $('td', row).each(function () {
        if (row.importancia_de_cotizacion === "ALTA") {
            $(this).css('background-color', 'rgb(255, 200, 200)')
        }
        if (row.importancia_de_cotizacion === "MEDIA") {
            $(this).css('background-color', 'rgb(200, 0, 255)')
        }
        if (row.importancia_de_cotizacion === "BAJA") {
            $(this).css('background-color', 'rgb(200, 255, 200)')
        }
        const value = $(this).text().trim();
        if (value === "true" || value === "True") {
            $(this).css('background-color', 'rgb(200, 255, 200)').text("✔");
        } else if (value === "false" || value === "False") {
            $(this).css('background-color', 'rgb(255, 200, 200)').text("✘");
        }
    });
}

styleCells(row);