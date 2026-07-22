from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from core.operation_control.models import OperationMasterControl, OperationControlChangeLog


@login_required
@require_GET
def master_list(request):
    """Render the main Operations Master Control page.
    The grid is populated via AJAX from api_list.
    """
    return render(request, "operation_control/master_list.html")


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

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 25))
    paginator = Paginator(qs, page_size)
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
        
        return {
            "id": c.id,
            "folio": getattr(op, "folio", None),
            "date": getattr(op, "operation_date", None),
            "client": getattr(op.client, "name", None) if op and op.client else None,
            "origin": origin,
            "destination": destination,
            "unit": unit_display,
            "sale_amount": str(c.sale_amount),
            "cost_amount": str(c.cost_amount),
            "factoring_cost": str(c.factoring_cost),
            "profit": str(c.profit),
            "profit_percentage": str(c.profit_percentage),
            "counter_receipt": c.counter_receipt,
            "counter_receipt_date": c.counter_receipt_date,
            "customer_invoice_code": c.customer_invoice_code,
            "customer_invoice_date": c.customer_invoice_date,
            "expected_collection_date": c.expected_collection_date,
            "supplier_invoice_number": c.supplier_invoice_number,
            "supplier_invoice_date": c.supplier_invoice_date,
            "scheduled_supplier_payment_date": c.scheduled_supplier_payment_date,
            "purchase_order": c.purchase_order,
            "has_factoring": c.has_factoring,
            "notes": c.notes,
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
