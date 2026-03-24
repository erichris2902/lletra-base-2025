from django.http import Http404, HttpResponse
from django.shortcuts import render

from core.operations_panel.choices import ShipmentType
from core.operations_panel.models.operation import Operation
from core.operations_panel.models.shipment_facturapi_invoice import ShipmentFacturapiInvoice


def DownloadShipmentPDF(request, operation_id):
    try:
        operation = Operation.objects.get(pk=operation_id)
    except Operation.DoesNotExist:
        raise Http404("Operación no encontrada")

    html = operation.render_cartaporte_html()
    return HttpResponse(html)