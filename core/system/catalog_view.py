import json

import requests
from django.http import JsonResponse
from django.views.generic import FormView

from apps.facturapi.models import FacturapiProduct, FacturapiInvoice, FacturapiInvoicePayment
from apps.facturapi.services import get_headers
from core.operations_panel.models import TransportedProduct, Operation


def getCatalogProductsURL():
    return "https://www.facturapi.io/v2/catalogs/products?q="

def getCatalogUnitsURL():
    return "https://www.facturapi.io/v2/catalogs/units?q="

class CatalogView(FormView):
    def post(self, request, *args, **kwargs):
        data = {}
        print(request.POST)
        try:
            action = request.POST['action']
            if action == 'Search':
                catalog = request.POST['catalog']
                if catalog == 'TransportedProducts':
                    products = TransportedProduct.objects.filter(description__icontains=request.POST['term'])
                    data["results"] = []
                    for i in range(0, len(products)):
                        element = {}
                        element['id'] = products[i].id
                        element['text'] = products[i].description + ": " + products[i].unit_key
                        data["results"].append(element)
                    data["pagination"] = {"more": True}
                elif catalog == 'ProductAndServiceCatalog':
                    url = getCatalogProductsURL() + request.POST['term']
                    headers = get_headers()
                    resp = requests.get(url, headers=headers)
                    if (resp.status_code != 200):
                        raise Exception(resp.content)
                    s = json.loads(resp.content)
                    dict_data = s["data"]
                    data["results"] = []
                    for i in range(0, len(dict_data)):
                        element = {}
                        element['id'] = dict_data[i]['key']
                        element['text'] = dict_data[i]['key'] + ": " + dict_data[i]['description']
                        data["results"].append(element)
                    data["pagination"] = {"more": True}
                elif catalog == 'UnitSat':
                    url = getCatalogUnitsURL() + request.POST['term']
                    headers = get_headers()
                    resp = requests.get(url, headers=headers)
                    if (resp.status_code != 200):
                        raise Exception(resp.content)
                    s = json.loads(resp.content)
                    dict_data = s["data"]
                    data["results"] = []
                    for i in range(0, len(dict_data)):
                        element = {}
                        element['id'] = dict_data[i]['key']
                        element['text'] = dict_data[i]['key'] + ": " + dict_data[i]['description']
                        data["results"].append(element)
                    data["pagination"] = {"more": True}
            elif action == 'SelectProduct':
                product = FacturapiProduct.objects.get(pk=request.POST['selected'])
                data["price"] = str(product.price)
                data["product"] = str(product.name)
                data["description"] = str(product.description)
                data["id"] = str(product.id)
                i = 0
                for tax in product.taxes.all():
                    if tax.withholding:
                        i -= tax.rate
                    else:
                        i += tax.rate
                data["tax"] = str(i)
            elif action == 'SelectConglomerado':
                invoice = FacturapiInvoice.objects.get(pk=request.POST['selected'])
                print(invoice)
                print(invoice.shipment_invoice)
                print(invoice.shipment_invoice.get())
                operation = invoice.shipment_invoice.get()

                description = operation.folio
                description += " RUTA"
                description += ", ".join(
                    [delivery.name for delivery in operation.route.route_stops.all()])
                description += " " + operation.route.destination_location.name
                description += " " + operation.cargo_appointment.strftime('%d/%m/%Y')

                product = FacturapiProduct.objects.get(name="Traslado")
                data["price"] = str(product.price)
                data["product"] = str(product.name)
                data["description"] = str(description)
                data["id"] = str(product.id)
                i = 0
                for tax in product.taxes.all():
                    if tax.withholding:
                        i -= tax.rate
                    else:
                        i += tax.rate
                data["tax"] = str(i)
                data["related_uuid"] = str(invoice.uuid)
            elif action == 'SelectPayment':
                invoice = FacturapiInvoice.objects.get(pk=request.POST['selected'])
                payments = FacturapiInvoicePayment.objects.filter(uuid=invoice.uuid)
                debt = invoice.total
                total_payments = 0
                payment_number = 1
                for payment in payments:
                    payment_number += 1
                    total_payments += payment.amount
                    debt -= payment.amount
                data["uuid"] = str(invoice.uuid)
                data["payment_number"] = str(payment_number)
                data["payment_amount"] = str(total_payments)
                data["debt_before"] = str(debt)
            else:
                data['error'] = "No se ingreso ninguna accion."
        except Exception as e:
            print(e)
            data['error'] = str(e)
        print(data)
        return JsonResponse(data)