function styleCells(row) {
    const $row = $(row);

    // Evita filas responsive "child"
    if ($row.hasClass('child')) return;

    // ---- Índices fijos según tu THEAD ----
    const IDX = {
        folio: 1,
        status: 2,
        cancel: 3,
        folioFiscal: 4,
        total: 6,
        tipo: 7
    };

    // 0) Booleans → badges
    $row.children('td').each(function () {
        const v = $(this).text().trim().toLowerCase();
        if (v === 'true') {
            $(this).html('<span class="badge bg-success"><i class="bi bi-check-lg me-1"></i>Sí</span>')
                   .addClass('text-center');
        } else if (v === 'false') {
            $(this).html('<span class="badge bg-danger"><i class="bi bi-x-lg me-1"></i>No</span>')
                   .addClass('text-center');
        }
    });

    // 1) Status → badge + (opcional) color de fila
    const $cStatus = $row.children().eq(IDX.status);
    if ($cStatus.length) {
        const raw = $cStatus.text().trim().toLowerCase();
        let badge = 'secondary', label = raw;

        if (['valid', 'vigente'].includes(raw)) {
            badge = 'success'; label = 'Vigente';
        } else if (['canceled', 'cancelado'].includes(raw)) {
            badge = 'danger'; label = 'Cancelado'; $row.addClass('table-danger');
        } else if (['pending', 'pendiente'].includes(raw)) {
            badge = 'warning'; label = 'Pendiente';
        } else if (['stamped', 'emitida', 'timbrada'].includes(raw)) {
            badge = 'primary'; label = 'Timbrada';
        }

        $cStatus.html(`<span class="badge bg-${badge}">${label}</span>`).addClass('text-center');
    }

    // 2) Cancelación → badge simple
    const $cCancel = $row.children().eq(IDX.cancel);
    if ($cCancel.length) {
        const raw = $cCancel.text().trim().toLowerCase();
        let badge = 'secondary', label = raw || '—';
        if (raw === 'none' || raw === '') { badge = 'secondary'; label = '—'; }
        else if (raw === 'requested' || raw === 'solicitada') { badge = 'warning'; label = 'Solicitada'; }
        else if (raw === 'accepted' || raw === 'aceptada') { badge = 'success'; label = 'Aceptada'; }
        else if (raw === 'rejected' || raw === 'rechazada') { badge = 'danger'; label = 'Rechazada'; }
        $cCancel.html(`<span class="badge bg-${badge}">${label}</span>`).addClass('text-center');
    }

    // 3) Tipo → badge con tooltip
    const $cTipo = $row.children().eq(IDX.tipo);
    if ($cTipo.length) {
        const raw = $cTipo.text().trim().toUpperCase();
        let badge = 'secondary', tooltip = raw;
        switch (raw) {
            case 'I':  badge = 'primary';  tooltip = 'Ingreso';         break;
            case 'P':  badge = 'info';     tooltip = 'Pago';            break;
            case 'E':  badge = 'warning';  tooltip = 'Egreso';          break;
            case 'NC': badge = 'dark';     tooltip = 'Nota de crédito'; break;
            case 'T':  badge = 'secondary';tooltip = 'Traslado';        break;
        }
        $cTipo.html(`<span class="badge bg-${badge}" data-bs-toggle="tooltip" title="${tooltip}">${raw}</span>`)
              .addClass('text-center');
    }

    // 4) Total → formato MXN + derecha
    const $cTotal = $row.children().eq(IDX.total);
    if ($cTotal.length) {
        const n = Number($cTotal.text().replace(/[^0-9.-]/g, ''));
        if (!Number.isNaN(n)) {
            const f = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', minimumFractionDigits: 2 });
            $cTotal.text(f.format(n)).addClass('text-end fw-semibold');
        } else {
            $cTotal.addClass('text-end');
        }
    }

    // 5) Folio fiscal → monospace + truncado
    const $cFolioFiscal = $row.children().eq(IDX.folioFiscal);
    if ($cFolioFiscal.length) {
        const full = $cFolioFiscal.text().trim();
        $cFolioFiscal.addClass('font-monospace');
    }

    // 6) Folio numérico → derecha
    const $cFolio = $row.children().eq(IDX.folio);
    if ($cFolio.length) $cFolio.addClass('text-end');

    // Inicializa tooltips del row
    $row.find('[data-bs-toggle="tooltip"]').each(function () {
        try { new bootstrap.Tooltip(this); } catch (e) {}
    });

    // 7) Fecha → mostrar solo YYYY-MM-DD
    const $cFecha = $row.children().eq(0); // Columna 0 = Fecha
    if ($cFecha.length) {
        const raw = $cFecha.text().trim();
        // Intenta detectar formato con hora
        if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
            const soloFecha = raw.slice(0, 10); // yyyy-mm-dd
            $cFecha.text(soloFecha);
        }
    }
}




console.log('row_callback.js');
styleCells(row);