import os
import json
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from apps.facturapi.models import FacturapiInvoice, FacturapiInvoiceItem, FacturapiProduct, FacturapiInvoicePayment
from ikigai2025.settings import FACTURAPI_API_KEY

FACTURAPI_BASE_URL = 'https://www.facturapi.io/v2'
DEFAULT_TIMEOUT = 10  # segundos
D2 = Decimal('0.01')
D4 = Decimal('0.0001')
ONE = Decimal('1')


def q2(v):  # 2 decimales (dinero)
    return Decimal(str(v or '0')).quantize(D2, rounding=ROUND_HALF_UP)


def q4(v):  # 4 decimales (tasas)
    return Decimal(str(v or '0')).quantize(D4, rounding=ROUND_HALF_UP)


def get_facturapi_key():
    """
    Get the FacturAPI key from settings.
    """
    api_key = FACTURAPI_API_KEY
    if not api_key:
        print("FACTURAPI_KEY not set in env")
        raise ValueError("FACTURAPI_KEY not set in env")
    return api_key


def get_headers(extra=None):
    """
    Get the headers for FacturAPI requests.
    """
    headers = {
        'Authorization': f'Bearer {get_facturapi_key()}',
        'Content-Type': 'application/json',
    }
    if extra:
        headers.update(extra)
    return headers


def _clean_payload(d):
    """Elimina claves con None o listas vacías/strings vacíos (opcional)."""
    return {k: v for k, v in d.items() if v not in (None, '', [], {})}


def cancel_invoice(invoice: FacturapiInvoice, motive=None, substitute_uuid=None):
    data = {}
    data["motive"] = motive
    data["substitution"] = substitute_uuid
    url = FACTURAPI_BASE_URL + "/invoices/" + invoice.facturapi_id + '?motive=' + str(motive)
    if motive == '01' or motive == '04':
        url += "&substitution=" + str(substitute_uuid)
    headers = get_headers()
    resp = requests.delete(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(resp.content)
    s = json.loads(resp.content)

    invoice.status = s.get('status') or invoice.status  # 'valid' | 'canceled' | 'pending' | 'draft'
    invoice.cancellation_status = s.get(
        'cancellation_status') or invoice.cancellation_status  # 'none' | 'pending' | 'accepted' | 'rejected' | 'expired'

    invoice.facturapi_response = s
    invoice.save()


def bill_type_i(invoice: FacturapiInvoice):
    data = _set_facturapi_invoice_base_data(invoice)
    data["payment_form"] = invoice.payment_method
    data["payment_method"] = invoice.payment_form
    data["use"] = invoice.use
    data = _set_facturapi_invoice_cfdi_relation(invoice, data)
    data["items"] = []
    for invoice_item in invoice.items.all():
        item = _set_facturapi_invoice_item(invoice_item)
        data["items"].append(item)
    data["pdf_custom_section"] = invoice.pdf_custom_section
    _send_invoice_to_facturapi(invoice, data)


def bill_type_e(invoice: FacturapiInvoice):
    data = _set_facturapi_invoice_base_data(invoice)
    data["payment_form"] = invoice.payment_method
    data["payment_method"] = invoice.payment_form
    data["use"] = invoice.use
    data = _set_facturapi_invoice_cfdi_relation(invoice, data)
    data["items"] = []
    for invoice_item in invoice.items.all():
        item = _set_facturapi_invoice_item(invoice_item)
        data["items"].append(item)
    data["pdf_custom_section"] = invoice.pdf_custom_section
    _send_invoice_to_facturapi(invoice, data)


def bill_type_p(invoice: FacturapiInvoice):
    data = _set_facturapi_invoice_base_data(invoice)
    data = _set_facturapi_invoice_cfdi_relation(invoice, data)

    data.setdefault("complements", [])
    complement = {"type": "pago", "data": []}

    # Prefetch para evitar N+1
    payments = invoice.payments.prefetch_related('taxes').all()

    for pay in payments:
        pago_node = _set_facturapi_invoice_payment(pay)
        # Asegura la moneda real del invoice
        if pago_node["related_documents"]:
            pago_node["related_documents"][0]["currency"] = invoice.currency

        # Si manejas forma de pago a nivel factura:
        if getattr(invoice, "payment_form", None):
            pago_node["payment_form"] = invoice.payment_method

        complement["data"].append(pago_node)

    if complement["data"]:
        data["complements"].append(complement)

    data["pdf_custom_section"] = invoice.pdf_custom_section
    _send_invoice_to_facturapi(invoice, data)


def get_invoice(invoice_id):
    url = f"{FACTURAPI_BASE_URL}/invoices/{invoice_id}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("obtener factura", e)
        raise


def list_invoices(limit=50, page=1, **filters):
    """
    Lista facturas con filtros (usa params para URL-encode correcto).
    Ejemplos de filters: status='valid', customer='cus_...', date={'gte': '2024-01-01', 'lte': '2024-12-31'}
    """
    url = f"{FACTURAPI_BASE_URL}/invoices"
    params = {"limit": limit, "page": page}
    # aplanado básico de filtros anidados (p.ej. date[gte]=..., date[lte]=...)
    for k, v in (filters or {}).items():
        if isinstance(v, dict):
            for subk, subv in v.items():
                params[f"{k}[{subk}]"] = subv
        else:
            params[k] = v

    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("listar facturas", e)
        raise


# Invoice download functions
def download_invoice_cancellation_pdf(invoice_id):
    url = f"{FACTURAPI_BASE_URL}/invoices/{invoice_id}/cancellation_receipt/pdf"
    try:
        resp = requests.get(url, headers=get_headers({"Accept": "application/pdf"}), stream=True,
                            timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.content, _filename_from_disposition(resp.headers, fallback=f"{invoice_id}.pdf")
    except requests.exceptions.RequestException as e:
        _log_http_error("descargar PDF", e)
        raise


# Invoice download functions
def download_invoice_pdf(invoice_id):
    url = f"{FACTURAPI_BASE_URL}/invoices/{invoice_id}/pdf"
    try:
        resp = requests.get(url, headers=get_headers({"Accept": "application/pdf"}), stream=True,
                            timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.content, _filename_from_disposition(resp.headers, fallback=f"{invoice_id}.pdf")
    except requests.exceptions.RequestException as e:
        _log_http_error("descargar PDF", e)
        raise


def download_invoice_xml(invoice_id):
    url = f"{FACTURAPI_BASE_URL}/invoices/{invoice_id}/xml"
    try:
        resp = requests.get(url, headers=get_headers({"Accept": "application/xml"}), stream=True,
                            timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.content, _filename_from_disposition(resp.headers, fallback=f"{invoice_id}.xml")
    except requests.exceptions.RequestException as e:
        _log_http_error("descargar XML", e)
        raise


def download_invoice_zip(invoice_id):
    url = f"{FACTURAPI_BASE_URL}/invoices/{invoice_id}/zip"
    try:
        resp = requests.get(url, headers=get_headers({"Accept": "application/zip"}), stream=True,
                            timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.content, _filename_from_disposition(resp.headers, fallback=f"{invoice_id}.zip")
    except requests.exceptions.RequestException as e:
        _log_http_error("descargar ZIP", e)
        raise


# ------------------------
# Helpers
# ------------------------

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # o float(obj) si prefieres
        return super().default(obj)


def _filename_from_disposition(headers, fallback):
    cd = headers.get("Content-Disposition", "")
    # intento simple: attachment; filename="..."
    if "filename=" in cd:
        try:
            return cd.split("filename=")[1].strip('"; ')
        except Exception:
            pass
    return fallback


def _log_http_error(what, e: requests.exceptions.RequestException):
    msg = f"Error al {what}: {str(e)}"
    if getattr(e, "response", None) is not None:
        try:
            payload = e.response.json()
            print("%s | status=%s | detail=%s", msg, e.response.status_code, payload)
        except Exception:
            print("%s | status=%s | body=%s", msg, e.response.status_code, getattr(e.response, "text", ""))
    else:
        print(msg)


def _set_facturapi_invoice_base_data(invoice: FacturapiInvoice):
    if not invoice.customer:
        raise Exception("La factura no tiene cliente. Asignalo antes de enviar a FacturAPI.")
    data = {"type": invoice.type, "customer": {}}
    data["customer"]["legal_name"] = invoice.customer.business_name
    data["customer"]["email"] = invoice.customer.email.split(',')[0]
    data["customer"]["tax_id"] = invoice.customer.rfc
    data["customer"]["tax_system"] = invoice.customer.tax_regime
    data["customer"]["address"] = {}
    data["customer"]["address"]["zip"] = invoice.customer.address.zip_code
    return data


def _set_facturapi_invoice_cfdi_relation(invoice: FacturapiInvoice, data: dict):
    if invoice.relation_type:
        data["related_documents"] = []
        rel_doc = {
            "documents": [],
            "relationship": ""
        }
        for i in invoice.related_uuids.split(','):
            if i != "":
                rel_doc["documents"].append(i)
        rel_doc["relationship"] = invoice.relation_type
        data["related_documents"].append(rel_doc)
    return data


def _set_facturapi_invoice_item(invoice_item: FacturapiInvoiceItem):
    item_data = {"quantity": invoice_item.quantity, "discount": str(invoice_item.discount), "product": {}}
    product = FacturapiProduct.objects.get(pk=invoice_item.product.id)
    item_data["product"]['description'] = product.description
    item_data["product"]['product_key'] = product.product_key
    item_data["product"]['price'] = float(invoice_item.unit_price)
    item_data["product"]['sku'] = product.sku
    item_data["product"]['unit_key'] = product.unit_key
    # item_data["product"]['unit_name'] = product.unit_code.split(':')[1]
    item_data["product"]['tax_included'] = False
    item_data["product"]['taxes'] = []
    for tax in product.taxes.all():
        tax_data = {
            'type': tax.type,
            'factor': tax.factor,
            'withholding': tax.withholding,
            'rate': float(tax.rate),
        }
        item_data["product"]['taxes'].append(tax_data)
    return item_data


def _set_facturapi_invoice_payment(invoice_payment: FacturapiInvoicePayment):
    related_doc = _serialize_related_document_from_payment(invoice_payment,
                                                           currency="MXN")  # ajusta si tu invoice tiene otra moneda
    return {
        "date": invoice_payment.payment_day.isoformat(),
        "related_documents": [related_doc]
        # "payment_form": "PUE/PPD"  # si quieres incluirla por pago, agrega un campo en el modelo y rellénalo aquí
    }


def _send_invoice_to_facturapi(invoice: FacturapiInvoice, data: dict):
    url = FACTURAPI_BASE_URL + "/invoices"
    headers = get_headers()
    json_data = json.dumps(data, cls=DecimalEncoder)
    resp = requests.post(url, headers=headers, data=json_data, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(resp.content)
    s = json.loads(resp.content)

    stamp = s.get('stamp') or {}

    # Asignaciones directas del nivel raíz
    invoice.facturapi_id = s.get('id') or invoice.facturapi_id
    invoice.status = s.get('status') or invoice.status  # 'valid' | 'canceled' | 'pending' | 'draft'
    invoice.cancellation_status = s.get(
        'cancellation_status') or invoice.cancellation_status  # 'none' | 'pending' | 'accepted' | 'rejected' | 'expired'
    invoice.verification_url = s.get('verification_url') or invoice.verification_url

    invoice.uuid = s.get('uuid') or invoice.uuid
    invoice.series = s.get('series') or invoice.series
    invoice.folio_number = s.get('folio_number') or invoice.folio_number

    if s.get('total') is not None:
        invoice.total = Decimal(str(s['total']))  # evita problemas binarios

    # Ambiente
    invoice.is_live = s.get('livemode', invoice.is_live)

    # TIMBRE (objeto stamp)
    # OJO: el campo 'date' al nivel raíz es fecha de expedición; la fecha de timbrado viene en stamp.date
    if stamp.get('date'):
        invoice.stamp_date = parse_datetime(stamp['date'])  # guarda timezone-aware si viene con 'Z'
    invoice.sat_cert_number = stamp.get('sat_cert_number') or invoice.sat_cert_number
    invoice.sat_signature = stamp.get('sat_signature') or invoice.sat_signature
    invoice.signature = stamp.get('signature') or invoice.signature

    # Guarda la respuesta completa para auditoría/depuración
    invoice.facturapi_response = s

    invoice.save()

    # Si es CFDI de Pago, dispara lógica adicional
    # if invoice.type == 'P':
    #     invoice.get_facturapi_payments()


def _serialize_related_document_from_payment(pay, currency: str) -> dict:
    """
    Convierte un FacturapiInvoicePayment + sus impuestos M2M a un related_document
    para el Complemento de Pagos.
    - Calcula base a partir del monto total con impuestos.
    - Usa is_retained para 'withholding'.
    """
    amount = q2(pay.amount)
    # Suma neta de tasas (negativas si son retenciones)
    tasa_neta = Decimal('0')
    taxes = list(pay.taxes.all())
    for t in taxes:
        rate = q4(getattr(t, 'rate', 0))
        tasa_neta += (-rate if getattr(t, 'withholding', False) else rate)

    # Base: si el monto incluye impuestos, dividir entre (1 + tasa_neta)
    base = amount if tasa_neta == 0 else (amount / (ONE + tasa_neta)).quantize(D2, rounding=ROUND_HALF_UP)

    taxes_payload = []
    for t in taxes:
        taxes_payload.append({
            "type": getattr(t, "type", ""),  # IVA | ISR | IEPS
            "factor": getattr(t, "factor", ""),  # Tasa | Cuota | Exento
            "base": float(base),  # número
            "withholding": bool(getattr(t, "withholding", False)),
            "rate": float(q4(getattr(t, "rate", 0))),  # número con 4 dp
        })

    # 'installment' (parcialidad) suele ser entero; si lo guardas decimal, casteamos seguro.
    try:
        installment_int = int(Decimal(pay.installment))
    except Exception:
        installment_int = 1

    return {
        "uuid": str(pay.uuid).upper(),
        "amount": float(amount),
        "installment": installment_int,
        "last_balance": float(q2(pay.last_balance)),
        "currency": currency,
        "taxability": "02",  # objeto de impuesto en pagos
        "taxes": taxes_payload,  # puede ser []
    }
