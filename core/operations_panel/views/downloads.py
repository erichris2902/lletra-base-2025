from django.shortcuts import render

from core.operations_panel.choices import ShipmentType
from core.operations_panel.models.operation import Operation
from core.operations_panel.models.shipment_facturapi_invoice import ShipmentFacturapiInvoice


def DownloadShipmentPDF(request, operation_id):
    shipment_invoice = ShipmentFacturapiInvoice()
    operation = Operation.objects.get(pk=operation_id)
    shipment_invoice.operation = operation
    shipment_invoice.client = operation.client
    context = {}
    shipment_invoice.departure_at = operation.cargo_appointment
    shipment_invoice.scheduled_arrival_at = operation.download_appointment
    context = shipment_invoice.custom_cartaporte_data()
    context["Cartaporte"]["Client"] = operation.client.to_dict()

    if operation.shipment_type == ShipmentType.ASTURIANO:
        context['is_asturiano'] = True
        context['asturiano_links'] = []
        for tienda in operation.deliveries.all():
            link = {}
            link["name"] = tienda.name
            context['asturiano_links'].append(link)
    if operation.shipment_type == ShipmentType.THREE_B:
        context['is_3b'] = True
        context['3b_links'] = []
        for tienda in operation.deliveries.all():
            link = {}
            link["name"] = tienda.name
            context['3b_links'].append(link)
    return render(request, 'operations_panel/cartaporte/cartaporte.html', context)