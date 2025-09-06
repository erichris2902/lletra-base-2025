# apps/facturapi/mappers.py
from typing import Dict, Any, List, Optional

from .models import (
    FacturapiClient,
    FacturapiProduct,
    FacturapiTax,
    FacturapiInvoice,
    FacturapiInvoiceItem,
)

def client_to_facturapi_payload(client: FacturapiClient) -> Dict[str, Any]:
    """
    Convierte FacturapiClient -> payload para customers.create/update.
    Mapea:
      - legal_name (razón social), tax_id (RFC), tax_system (régimen)
      - email, phone
      - address minimalista (si sólo tienes CP), expandelo cuando modeles domicilio.
    """
    payload = {
        "legal_name": client.business_name,
        "tax_id": client.rfc,
        "tax_system": client.regimen_fiscal,  # 3 dígitos SAT (ej. "601")
        "email": client.email or None,
        "phone": client.tel or None,
    }
    # Domicilio fiscal (opcional). Con lo que tienes, al menos zip:
    if getattr(client, "cp", None):
        payload["address"] = {"zip": client.cp}

    # Si en el futuro agregas default_invoice_use, inclúyelo:
    if hasattr(client, "default_invoice_use") and client.default_invoice_use:
        payload["default_invoice_use"] = client.default_invoice_use

    # Limpia None
    return {k: v for k, v in payload.items() if v not in (None, "", {}, [])}


def _tax_to_payload(tax: FacturapiTax) -> Dict[str, Any]:
    """
    Convierte FacturapiTax -> dict usado por FacturAPI en product.taxes o line_item.taxes.
    FacturAPI espera:
      - type: 'IVA'|'ISR'|'IEPS'
      - rate: decimal (e.g. 0.1600 para 16% o 0.1600/16.0 dependiendo de tu convención)
      - withholding: bool (retención)
    NOTA: En tus modelos usas 'is_retained'. Lo mapeamos a 'withholding'.
    """
    # Si guardas 'rate' como 0.1600 (fracción), déjalo así.
    # Si lo guardas como 16.0 (porcentaje), convierte a fracción (tax.rate / 100).
    # Asumiré que ya lo guardas como fracción (0.1600). Ajusta si no es así.
    return {
        "type": tax.type,
        "rate": float(tax.rate),
        "withholding": bool(getattr(tax, "withholding", False)),
    }


def product_to_facturapi_payload(product: FacturapiProduct) -> Dict[str, Any]:
    """
    Convierte FacturapiProduct -> payload para products.create/update.
    """
    payload = {
        "description": product.description,
        "product_key": product.product_key,
        "unit_key": product.unit_key,
        "price": float(product.price),
        "tax_included": bool(product.tax_included),
    }

    # Impuestos desde M2M
    taxes = []
    for t in product.taxes.all():
        taxes.append(_tax_to_payload(t))
    if taxes:
        payload["taxes"] = taxes

    # Campos opcionales si algún día los agregas al modelo:
    for opt in ("unit_name", "sku", "taxability", "local_taxes"):
        if hasattr(product, opt) and getattr(product, opt):
            payload[opt] = getattr(product, opt)

    return payload


def invoice_item_to_payload(item: FacturapiInvoiceItem) -> Dict[str, Any]:
    """
    Convierte FacturapiInvoiceItem -> payload para un concepto en invoices.create.
    Si el producto tiene facturapi_id -> enviamos referencia por 'product'.
    Si no -> enviamos descripción y claves SAT inline (product_key, unit_key, unit_price).
    """
    base = {
        "quantity": float(item.quantity),
        "discount": float(item.discount or 0),
    }

    product = item.product
    # Si tienes product.facturapi_id en tu modelo, úsalo.
    facturapi_id = getattr(product, "facturapi_id", None)
    if facturapi_id:
        base["product"] = facturapi_id
    else:
        base.update({
            "description": item.description or product.description,
            "product_key": item.product_key or product.product_key,
            "unit_key": item.unit_key or product.unit_key,
            "unit_price": float(item.unit_price),
        })

        # (Opcional) Impuestos a nivel concepto (si difieren de los del producto)
        if hasattr(item, "item_taxes") and item.item_taxes:
            base["taxes"] = item.item_taxes

    return base


def invoice_to_facturapi_payload(
    invoice: FacturapiInvoice,
    items: Optional[List[FacturapiInvoiceItem]] = None,
    *,
    payment_method: Optional[str] = None,  # 'PUE' | 'PPD'
    force_inline_customer: bool = False    # manda objeto cliente en lugar de ID
) -> Dict[str, Any]:
    """
    Convierte FacturapiInvoice (+ items) -> payload para invoices.create.
    customer: si tu FacturapiClient tiene facturapi_id úsalo; si no o force_inline_customer=True, manda objeto inline.
    """
    customer_obj: FacturapiClient = invoice.customer

    # Resolver customer
    customer_payload: Any
    client_ext_id = getattr(customer_obj, "facturapi_id", None)
    if client_ext_id and not force_inline_customer:
        customer_payload = client_ext_id
    else:
        customer_payload = client_to_facturapi_payload(customer_obj)

    payload = {
        "customer": customer_payload,
        "items": [invoice_item_to_payload(i) for i in (items or list(invoice.items.all()))],
        "payment_form": invoice.payment_form,  # '03' etc.
        "type": invoice.type or "I",
        "currency": invoice.currency or "MXN",
        "use": invoice.use or None,
        "series": invoice.series or None,
        "folio_number": invoice.folio_number or None,
        "payment_method": payment_method,  # si tu modelo aún no lo guarda
    }

    # Campos opcionales que tienes en el modelo:
    optionals = {
        "pdf_custom_section": invoice.pdf_custom_section,
        "related_documents": invoice.related_documents,
        "complements": invoice.complements,
        "target_invoice_ids": invoice.target_invoice_ids,
        "received_payment_ids": invoice.received_payment_ids,
    }
    for k, v in optionals.items():
        if v not in (None, "", [], {}):
            payload[k] = v

    # Limpia None/empty
    return {k: v for k, v in payload.items() if v not in (None, "", [], {})}
