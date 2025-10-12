# apps/facturapi/client.py
import os
import logging
import requests
from typing import Dict, Any
from django.conf import settings

from .mappers import (
    client_to_facturapi_payload,
    product_to_facturapi_payload,
    invoice_to_facturapi_payload,
)

logger = logging.getLogger(__name__)

FACTURAPI_BASE_URL = "https://www.facturapi.io/v2"
DEFAULT_TIMEOUT = 25

def _get_key():
    key = os.environ.get("FACTURAPI_TEST_KEY") if settings.DEBUG else os.environ.get("FACTURAPI_LIVE_KEY")
    if not key:
        raise RuntimeError("Llave de FacturAPI no configurada (FACTURAPI_TEST_KEY / FACTURAPI_LIVE_KEY)")
    return key

def _headers(extra=None):
    h = {
        "Authorization": f"Bearer {_get_key()}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h

def _log_http_error(what: str, e: requests.exceptions.RequestException):
    msg = f"Error al {what}: {e}"
    if getattr(e, "response", None) is not None:
        try:
            print("%s | status=%s | json=%s", msg, e.response.status_code, e.response.json())
        except Exception:
            print("%s | status=%s | text=%s", msg, e.response.status_code, getattr(e.response, "text", ""))
    else:
        print(msg)

# ----------------- Customers -----------------

def create_customer(client_model) -> Dict[str, Any]:
    url = f"{FACTURAPI_BASE_URL}/customers"
    payload = client_to_facturapi_payload(client_model)
    try:
        r = requests.post(url, json=payload, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("crear cliente", e)
        raise

def update_customer(customer_id: str, client_model) -> Dict[str, Any]:
    url = f"{FACTURAPI_BASE_URL}/customers/{customer_id}"
    payload = client_to_facturapi_payload(client_model)
    try:
        r = requests.put(url, json=payload, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("actualizar cliente", e)
        raise

# ----------------- Products -----------------

def create_product(product_model) -> Dict[str, Any]:
    url = f"{FACTURAPI_BASE_URL}/products"
    payload = product_to_facturapi_payload(product_model)
    try:
        r = requests.post(url, json=payload, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("crear producto", e)
        raise

def update_product(product_id: str, product_model) -> Dict[str, Any]:
    url = f"{FACTURAPI_BASE_URL}/products/{product_id}"
    payload = product_to_facturapi_payload(product_model)
    try:
        r = requests.put(url, json=payload, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("actualizar producto", e)
        raise

# ----------------- Invoices -----------------

def create_invoice(invoice_model, *, payment_method: str = None, force_inline_customer: bool = False) -> Dict[str, Any]:
    url = f"{FACTURAPI_BASE_URL}/invoices"
    payload = invoice_to_facturapi_payload(
        invoice_model,
        payment_method=payment_method,
        force_inline_customer=force_inline_customer,
    )
    try:
        r = requests.post(url, json=payload, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        _log_http_error("crear factura", e)
        raise
