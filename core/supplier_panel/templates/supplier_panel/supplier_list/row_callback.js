

function styleCells(row) {
    $('td', row).each(function () {
        const value = $(this).text().trim();
        if (value === "true" || value === "True") {
            $(this).css('background-color', 'rgb(200, 255, 200)').text("✔");
        } else if (value === "false" || value === "False") {
            $(this).css('background-color', 'rgb(255, 200, 200)').text("✘");
        }
    });
}

styleCells(row);