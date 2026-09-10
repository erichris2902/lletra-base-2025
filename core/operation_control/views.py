from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from core.operation_control.models import OperationMasterControl, OperationControlChangeLog
from core.admin_panel.models.purchase_order import PurchaseOrderOperation
from decimal import Decimal
import re


@login_required
@require_GET
def master_list(request):
    """Render the main Operations Master Control page.
    The grid is populated via AJAX from api_list.
    """
    return render(request, "operation_control/master_list.html")


@login_required
@permission_required('operation_control.change_operationmastercontrol', raise_exception=True)
@require_GET
def master_edit_finance(request):
    """Render the Finance Edit page similar to master_list but with inline editing.
    """
    return render(request, "operation_control/master_edit_finance.html")


@login_required
@require_GET
def api_list(request):
    """Return a JSON list of master controls with basic filters and pagination.

    Query params:
    - page, page_size
    - date_from, date_to (filter by operation.operation_date if available; fallback to id)
    - client (substring case-insensitive on client name)
    - supplier (substring case-insensitive on supplier name)
    - collected_status / supplier_status (reserved for Phase 2)
    - invoiced (y/n) based on customer_invoice_code presence
    - missing_approval (y/n)
    - has_factoring (y/n)
    """
    qs = (
        OperationMasterControl.objects
        .select_related(
            "operation",
            "operation__client",
            "operation__supplier",
            "operation__route",
            "operation__vehicle",
        )
        .all().order_by("-operation__folio")
    )

    # Aplicar filtros antes de decidir qué filas mostrar (esto permite que una "B" huérfana aparezca
    # cuando la base no califica en los filtros actuales).
    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    if date_from:
        qs = qs.filter(operation__operation_date__gte=date_from)
    if date_to:
        qs = qs.filter(operation__operation_date__lte=date_to)

    client = request.GET.get("client")
    if client:
        qs = qs.filter(operation__client__name__icontains=client)

    supplier = request.GET.get("supplier")
    if supplier:
        qs = qs.filter(operation__supplier__name__icontains=supplier)

    invoiced = request.GET.get("invoiced")
    if invoiced in ("y", "n"):
        condition = Q(customer_invoice_code__isnull=False) & ~Q(customer_invoice_code="")
        qs = qs.filter(condition if invoiced == "y" else ~condition)

    missing_approval = request.GET.get("missing_approval")
    if missing_approval in ("y", "n"):
        qs = qs.filter(missing_approval=(missing_approval == "y"))

    factoring = request.GET.get("has_factoring")
    if factoring in ("y", "n"):
        qs = qs.filter(has_factoring=(factoring == "y"))

    # Construir la lista final a mostrar:
    # - Incluir todas las operaciones cuyo folio NO termina en 'B'.
    # - Incluir también aquellas con folio terminado en 'B' SOLO si su base (folio sin 'B') no está presente en el queryset filtrado.
    # Esto asegura que si sólo existe la B (o la base quedó fuera por filtros), se muestre como fila representativa.
    # Primero, recolectar el set de folios base presentes (sin sufijo 'B').
    base_folios = set()
    folios_by_id = {}
    for c in qs:
        f = getattr(getattr(c, "operation", None), "folio", None)
        folios_by_id[c.id] = f
        if f and not str(f).upper().endswith("B"):
            base_folios.add(str(f))

    display_controls = []
    for c in qs:
        f = folios_by_id.get(c.id)
        if not f:
            display_controls.append(c)
            continue
        fs = str(f).upper()
        if fs.endswith("B"):
            base = str(f)[:-1]
            if base in base_folios:
                # Hay base presente en el conjunto filtrado; ocultar la B (se sumará a la base)
                continue
            # No hay base en el conjunto filtrado; incluir la B como fila representativa
            display_controls.append(c)
        else:
            display_controls.append(c)

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 25))
    paginator = Paginator(display_controls, page_size)
    page_obj = paginator.get_page(page)

    def serialize_row(c: OperationMasterControl):
        op = c.operation
        
        # Helper to safely stringify complex objects (e.g., DeliveryLocation, Route, Vehicle)
        def safe_str(obj):
            try:
                return str(obj) if obj is not None else None
            except Exception:
                return None
        
        origin = None
        destination = None
        if op and getattr(op, "route", None):
            try:
                origin = safe_str(getattr(op.route, "initial_location", None))
            except Exception:
                origin = None
            try:
                destination = safe_str(getattr(op.route, "destination_location", None))
            except Exception:
                destination = None
        
        unit_display = None
        if op and getattr(op, "vehicle", None):
            unit_display = safe_str(op.vehicle)
        
        # Encontrar si existe operación hermana con sufijo 'B' y agregar sus valores a esta fila base
        b_control = None
        try:
            base_folio = getattr(op, "folio", None)
            if base_folio:
                b_control = OperationMasterControl.objects.select_related(
                    "operation",
                    "operation__client",
                    "operation__supplier",
                    "operation__route",
                    "operation__vehicle",
                ).filter(operation__folio=str(base_folio) + "B").first()
        except Exception:
            b_control = None
        
        # Ingresos por OC (individual por operación) y folios de OC (posiblemente múltiples)
        def po_info(ctrl: OperationMasterControl):
            has_po = False
            folio = None
            total = None
            try:
                if ctrl and getattr(ctrl, "operation", None):
                    link = PurchaseOrderOperation.objects.select_related('purchase_order').filter(operation=ctrl.operation).first()
                    if link and link.purchase_order:
                        has_po = True
                        folio = link.purchase_order.folio
                        try:
                            total = ctrl.get_purchase_order_operation_total()
                        except Exception:
                            total = None
            except Exception:
                has_po = False
                folio = None
                total = None
            return has_po, folio, total
        
        has_po_a, po_folio_a, po_total_a = po_info(c)
        has_po_b, po_folio_b, po_total_b = po_info(b_control) if b_control else (False, None, None)
        has_po = bool(has_po_a or has_po_b)
        # Folio puede ser uno o ambos separados por coma si existen
        po_folio = None
        if po_folio_a and po_folio_b and po_folio_a != po_folio_b:
            po_folio = f"{po_folio_a}, {po_folio_b}"
        else:
            po_folio = po_folio_a or po_folio_b
        # Total de OC agregado (cuando aplica)
        po_total = None
        if po_total_a is not None or po_total_b is not None:
            from decimal import Decimal as _D
            po_total = (po_total_a or _D("0.00")) + (po_total_b or _D("0.00"))
        
        # Agregación de montos base + B
        from decimal import Decimal as _D
        sale_a = c.sale_amount or _D("0.00")
        cost_a = c.cost_amount or _D("0.00")
        fact_a = c.factoring_cost or _D("0.00")
        profit_a = c.profit or _D("0.00")
        
        sale_b = (b_control.sale_amount if b_control else _D("0.00")) or _D("0.00")
        cost_b = (b_control.cost_amount if b_control else _D("0.00")) or _D("0.00")
        fact_b = (b_control.factoring_cost if b_control else _D("0.00")) or _D("0.00")
        profit_b = (b_control.profit if b_control else _D("0.00")) or _D("0.00")
        
        sale_sum = sale_a + sale_b
        cost_sum = cost_a + cost_b
        fact_sum = fact_a + fact_b
        profit_sum = profit_a + profit_b  # equivalente a sale_sum - cost_sum - fact_sum
        margin = _D("0.00") if sale_sum == _D("0.00") else (profit_sum * _D("100")) / sale_sum

        # Build customer invoice display with '-C' if canceled
        customer_invoice_display = c.customer_invoice_code
        try:
            inv = getattr(op, "shipment_invoice", None)
            if inv:
                base_code = None
                series = getattr(inv, "series", None)
                folio_num = getattr(inv, "folio_number", None)
                if series and folio_num is not None:
                    base_code = f"{series}-{folio_num}"
                else:
                    base_code = getattr(inv, "uuid", None) or (c.customer_invoice_code or "")
                is_canceled = (getattr(inv, "status", None) == "canceled") or (str(getattr(inv, "cancellation_status", "") or "").lower() in ("canceled", "cancelado", "cancelled", "cancelada"))
                if base_code:
                    customer_invoice_display = str(base_code) + ("-C" if is_canceled and not str(base_code).upper().endswith("-C") else "")
        except Exception:
            pass

        return {
            "id": c.id,
            "folio": getattr(op, "folio", None),
            "date": getattr(op, "operation_date", None),
            "client": getattr(op.client, "name", None) if op and op.client else None,
            "origin": origin,
            "destination": destination,
            "unit": unit_display,
            "sale_amount": str(sale_sum),
            "cost_amount": str(cost_sum),
            "factoring_cost": str(fact_sum),
            "profit": str(profit_sum),
            "profit_percentage": str(margin),
            "counter_receipt": c.counter_receipt,
            "counter_receipt_date": c.counter_receipt_date,
            "customer_invoice_code": customer_invoice_display,
            "customer_invoice_date": c.customer_invoice_date,
            "expected_collection_date": c.expected_collection_date,
            "supplier_invoice_number": (
                (c.supplier_invoice_number or "") + (
                    (", " + (getattr(b_control, "supplier_invoice_number", "") or "")) if (b_control and getattr(b_control, "supplier_invoice_number", "")) and c.supplier_invoice_number else (getattr(b_control, "supplier_invoice_number", "") or "")
                )
            ).strip(', ').strip() if True else c.supplier_invoice_number,
            "supplier_invoice_date": c.supplier_invoice_date,
            "scheduled_supplier_payment_date": c.scheduled_supplier_payment_date,
            "purchase_order": c.purchase_order,
            "has_factoring": c.has_factoring,
            "notes": c.notes,
            # Finanzas adicionales para la pantalla de edición
            "has_purchase_order": has_po,
            "purchase_order_folio": po_folio,
            "purchase_order_total": str(po_total) if po_total is not None else None,
            "sale_amount_override": str(c.sale_amount_override) if c.sale_amount_override is not None else None,
            "cost_amount_override": str(c.cost_amount_override) if c.cost_amount_override is not None else None,
            "factoring_amount": str(c.factoring_amount) if c.factoring_amount is not None else None,
            "factoring_percentage": str(c.factoring_percentage) if c.factoring_percentage is not None else None,
        }

    data = [serialize_row(c) for c in page_obj.object_list]
    return JsonResponse({
        "count": paginator.count,
        "num_pages": paginator.num_pages,
        "page": page_obj.number,
        "results": data,
    })


EDITABLE_FIELDS = {
    # field_name: python_cast
    "missing_approval": lambda v: v in (True, "true", "True", "1", 1, "y", "Y", "yes", "si", "sí"),
    "counter_receipt": str,
    "counter_receipt_date": parse_date,
    "customer_invoice_code": str,
    "customer_invoice_date": parse_date,
    "expected_collection_date": parse_date,
    "supplier_invoice_date": parse_date,
    "supplier_invoice_number": str,
    "scheduled_supplier_payment_date": parse_date,
    "purchase_order": str,
    "sale_amount_override": lambda v: None if v in ("", None) else v,
    "cost_amount_override": lambda v: None if v in ("", None) else v,
    "has_factoring": lambda v: v in (True, "true", "True", "1", 1, "y", "Y", "yes", "si", "sí"),
    "factoring_amount": str,
    "factoring_percentage": str,
    "notes": str,
    "is_reviewed": lambda v: v in (True, "true", "True", "1", 1, "y", "Y", "yes", "si", "sí"),
}


@login_required
@require_POST
def api_update_field(request):
    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON body")

    control_id = payload.get("control_id")
    field = payload.get("field")
    value = payload.get("value")

    if not control_id or not field or field not in EDITABLE_FIELDS:
        return HttpResponseBadRequest("Invalid parameters or field not editable")

    control = get_object_or_404(OperationMasterControl, pk=control_id)

    caster = EDITABLE_FIELDS[field]
    cast_value = caster(value)

    # For decimal fields, rely on Django model to validate; strings are fine if properly formatted.
    previous = getattr(control, field, None)

    setattr(control, field, cast_value)
    control.updated_by = getattr(request, "user", None)
    control.save(update_fields=[field, "updated_by", "updated_at"])

    OperationControlChangeLog.objects.create(
        control=control,
        field_name=field,
        previous_value=str(previous) if previous is not None else "",
        new_value=str(getattr(control, field, "")) or "",
        changed_by=getattr(request, "user", None),
    )

    # Minimal recalculated values to update UI quickly
    recalc = {
        "sale_amount": str(control.sale_amount),
        "cost_amount": str(control.cost_amount),
        "factoring_cost": str(control.factoring_cost),
        "profit": str(control.profit),
        "profit_percentage": str(control.profit_percentage),
    }

    return JsonResponse({"ok": True, "updated": {"field": field, "value": cast_value}, "recalc": recalc})


# ===================== Finance update (with Latin decimal and DD-MM-YYYY parsing) =====================
LATIN_DECIMAL_RE = re.compile(r"^\s*[-+]?\d{1,3}(?:[\.\s]\d{3})*(?:,\d+)?\s*$|^\s*[-+]?\d+(?:,\d+)?\s*$")


def parse_latin_decimal(value):
    if value in (None, ""):  # allow nulls
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    s = str(value).strip()
    # normalize thousand separators and decimal comma
    if not LATIN_DECIMAL_RE.match(s):
        # Try also dot-decimal format as fallback
        try:
            return Decimal(s)
        except Exception:
            raise ValueError("Formato numérico inválido")
    s = s.replace(".", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except Exception:
        raise ValueError("Formato numérico inválido")


DATE_DDMMYYYY_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")


def parse_ddmmyyyy(value):
    if value in (None, ""):
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value
    s = str(value).strip()
    m = DATE_DDMMYYYY_RE.match(s)
    if not m:
        raise ValueError("Formato de fecha inválido (usa DD-MM-YYYY)")
    dd, mm, yyyy = map(int, m.groups())
    from datetime import date
    try:
        return date(yyyy, mm, dd)
    except Exception:
        raise ValueError("Fecha inválida")


FINANCE_FIELDS = {
    # Ingresos (solo si no hay OC):
    "sale_amount_override": parse_latin_decimal,
    "expected_collection_date": parse_ddmmyyyy,
    # Egresos:
    "cost_amount_override": parse_latin_decimal,
    "supplier_invoice_number": str,
    "supplier_invoice_date": parse_ddmmyyyy,
    "scheduled_supplier_payment_date": parse_ddmmyyyy,
    "has_factoring": lambda v: v in (True, "true", "True", "1", 1, "y", "Y", "yes", "si", "sí"),
    "factoring_amount": parse_latin_decimal,
    "factoring_percentage": parse_latin_decimal,
    "notes": str,
}


@login_required
@permission_required('operation_control.change_operationmastercontrol', raise_exception=True)
@require_POST
def api_update_finance(request):
    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    control_id = payload.get("control_id")
    field = payload.get("field")
    value = payload.get("value")

    if not control_id or not field or field not in FINANCE_FIELDS:
        return HttpResponseBadRequest("Parámetros inválidos o campo no editable")

    control = get_object_or_404(OperationMasterControl, pk=control_id)

    # Regla de ingresos: si hay OC, no permitir editar sale_amount_override ni expected_collection_date
    if field in ("sale_amount_override", "expected_collection_date"):
        op = getattr(control, "operation", None)
        has_po = False
        if op is not None:
            link = PurchaseOrderOperation.objects.filter(operation=op).first()
            has_po = bool(link)
        if has_po:
            return HttpResponseBadRequest("La operación tiene una Orden de Compra; los ingresos se toman de la OC y no son editables aquí.")

    caster = FINANCE_FIELDS[field]
    try:
        cast_value = caster(value)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))

    previous = getattr(control, field, None)

    setattr(control, field, cast_value)
    control.updated_by = getattr(request, "user", None)
    # Persist only the changed field + audit fields
    control.save(update_fields=[field, "updated_by", "updated_at"])

    OperationControlChangeLog.objects.create(
        control=control,
        field_name=field,
        previous_value=str(previous) if previous is not None else "",
        new_value=str(getattr(control, field, "")) or "",
        changed_by=getattr(request, "user", None),
    )

    # Recalcular totales derivados
    op = control.operation
    po_total = None
    po_folio = None
    has_po = False
    try:
        if op:
            link = PurchaseOrderOperation.objects.select_related('purchase_order').filter(operation=op).first()
            if link and link.purchase_order:
                has_po = True
                po_folio = link.purchase_order.folio
                try:
                    po_total = control.get_purchase_order_operation_total()
                except Exception:
                    po_total = None
    except Exception:
        has_po = False
        po_total = None
        po_folio = None

    # Agregación con posible operación hermana con sufijo 'B' para devolver totales consistentes en UI
    from decimal import Decimal as _D
    b_control = None
    try:
        base_folio = getattr(op, "folio", None)
        if base_folio:
            b_control = OperationMasterControl.objects.select_related(
                "operation",
                "operation__client",
                "operation__supplier",
                "operation__route",
                "operation__vehicle",
            ).filter(operation__folio=str(base_folio) + "B").first()
    except Exception:
        b_control = None

    sale_sum = (control.sale_amount or _D("0.00")) + ((b_control.sale_amount or _D("0.00")) if b_control else _D("0.00"))
    cost_sum = (control.cost_amount or _D("0.00")) + ((b_control.cost_amount or _D("0.00")) if b_control else _D("0.00"))
    fact_sum = (control.factoring_cost or _D("0.00")) + ((b_control.factoring_cost or _D("0.00")) if b_control else _D("0.00"))
    profit_sum = sale_sum - cost_sum - fact_sum
    margin = _D("0.00") if sale_sum == _D("0.00") else (profit_sum * _D("100")) / sale_sum

    recalc = {
        "sale_amount": str(sale_sum),
        "cost_amount": str(cost_sum),
        "factoring_cost": str(fact_sum),
        "profit": str(profit_sum),
        "profit_percentage": str(margin),
        "has_purchase_order": has_po,
        "purchase_order_folio": po_folio,
        "purchase_order_total": str(po_total) if po_total is not None else None,
    }

    return JsonResponse({"ok": True, "updated": {"field": field, "value": value}, "recalc": recalc})
