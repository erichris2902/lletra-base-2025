function styleCells(row) {
    // Convert boolean-like cells to check/cross with gentle background
    $('td', row).each(function () {
        const value = $(this).text().trim();
        if (value === "true" || value === "True") {
            $(this).css('background-color', 'rgb(200, 255, 200)').text("✔");
        } else if (value === "false" || value === "False") {
            $(this).css('background-color', 'rgb(255, 200, 200)').text("✘");
        }
    });

    // Colorize STATUS column specifically (index 7 in FolioOperationListView)
    try {
        const statusVal = (typeof data !== 'undefined' && data && data.status != null
            ? String(data.status)
            : $('td:eq(7)', row).text()
        ).trim().toUpperCase();
        const statusTd = $('td:eq(7)', row);
        if (statusTd && statusTd.length) {
            // reset previous coloring
            statusTd.css('background-color', '');
            if (statusVal === 'CANCELED' || statusVal === 'CANCELLED') {
                // Red for canceled
                statusTd.css('background-color', 'rgb(255, 200, 200)');
            } else if (statusVal === 'APPROVED') {
                // Green for approved
                statusTd.css('background-color', 'rgb(200, 255, 200)');
            } else if (statusVal) {
                // Yellow for any other non-empty status
                statusTd.css('background-color', 'rgb(255, 245, 200)');
            }
        }
    } catch (e) {
        // no-op
    }
}

styleCells(row);