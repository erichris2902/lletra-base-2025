import json

import requests
from django.http import JsonResponse
from django.views.generic import FormView

from apps.facturapi.models import FacturapiProduct
from apps.facturapi.services import get_headers


def getCatalogProductsURL():
    return "https://www.facturapi.io/v2/catalogs/products?q="

def getCatalogUnitsURL():
    return "https://www.facturapi.io/v2/catalogs/units?q="

class CatalogView(FormView):
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'Search':
                catalog = request.POST['catalog']
                if catalog == 'ProductAndServiceCatalog':
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
            else:
                data['error'] = "No se ingreso ninguna accion."
        except Exception as e:
            print(e)
            data['error'] = str(e)
        return JsonResponse(data)