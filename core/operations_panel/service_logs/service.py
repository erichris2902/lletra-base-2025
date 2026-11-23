from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.operations_panel.models.operation import Operation
from core.operations_panel.models.route import Route
from core.operations_panel.models.service_log import (
    ServiceLog,
    ServiceLogEvent,
    ServiceLogActivity,
    ServiceLogEventType,
    ServiceLogActivityType,
)

# Centralized mapping: Event → Activity category (or None if marker only)
EVENT_TO_ACTIVITY: Dict[str, Optional[str]] = {
    ServiceLogEventType.TRIP_START: ServiceLogActivityType.DRIVING,
    ServiceLogEventType.UNLOADING: ServiceLogActivityType.AUXILIARY,
    ServiceLogEventType.BREAKDOWN: ServiceLogActivityType.EXCEPTION,
    ServiceLogEventType.MEAL: ServiceLogActivityType.PAUSE,
    ServiceLogEventType.REST: ServiceLogActivityType.REST,
    ServiceLogEventType.CHECKPOINT: ServiceLogActivityType.EXCEPTION,
    ServiceLogEventType.TRIP_END: None,  # pure marker
}


def snap_to_30(dt: datetime) -> datetime:
    if dt is None:
        return dt
    minute = 0 if dt.minute < 30 else 30
    return dt.replace(minute=minute, second=0, microsecond=0)


def ensure_grid(start: datetime, end: Optional[datetime] = None):
    s = snap_to_30(start)
    e = snap_to_30(end) if end else None
    if e and e <= s:
        raise ValidationError("Fin debe ser posterior a inicio en bloques de 30 minutos.")
    return s, e


def open_or_create_log_by_folio(folio: str) -> ServiceLog:
    if not folio:
        raise ValidationError("Debes capturar un folio de operación.")
    op = Operation.objects.filter(folio__iexact=folio.strip()).select_related(
        "driver", "vehicle", "route", "route__initial_location", "route__destination_location"
    ).first()
    if not op:
        raise ValidationError("No existe una operación con ese folio.")
    log, _created = ServiceLog.objects.get_or_create(operation=op)
    return log


@transaction.atomic
def add_event_and_activity(
    *,
    service_log: ServiceLog,
    event_type: str,
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    notes: str = "",
):
    started_at, ended_at = ensure_grid(started_at, ended_at)

    event = ServiceLogEvent.objects.create(
        service_log=service_log,
        event_type=event_type,
        started_at=started_at,
        ended_at=ended_at,
        notes=notes or "",
    )

    activity_type = EVENT_TO_ACTIVITY.get(event_type)
    activity = None

    # Only create activity if mapping exists and we have an interval
    if activity_type and ended_at:
        # Validate non-overlap (clean handles it)
        activity = ServiceLogActivity(
            service_log=service_log,
            event=event,
            activity_type=activity_type,
            started_at=started_at,
            ended_at=ended_at,
            notes=notes or "",
        )
        activity.full_clean()
        activity.save()

    # Update status heuristics
    if event_type == ServiceLogEventType.TRIP_START and not service_log.departure_datetime:
        service_log.departure_datetime = started_at
        service_log.status = service_log.status or "IN_PROGRESS"
        service_log.save(update_fields=["departure_datetime", "status", "updated_at"])
    elif event_type == ServiceLogEventType.TRIP_END:
        service_log.arrival_datetime = ended_at or started_at
        service_log.status = "COMPLETED"
        service_log.closed_at = timezone.now()
        service_log.save(update_fields=["arrival_datetime", "status", "closed_at", "updated_at"])

    return event, activity


def serialize_operation_for_header(op: Operation) -> Dict:
    driver = getattr(op, "driver", None)
    vehicle = getattr(op, "vehicle", None)
    route: Optional[Route] = getattr(op, "route", None)
    origin = getattr(route, "initial_location", None) if route else None
    destination = getattr(route, "destination_location", None) if route else None
    stops = list(route.route_stops.all()) if route else []

    def dl_str(dl):
        return str(dl) if dl else ""

    return {
        "folio": op.folio,
        "operation_date": op.operation_date.isoformat() if getattr(op, "operation_date", None) else None,
        "shipment_type": op.shipment_type,
        "vehicle": str(vehicle) if vehicle else "",
        "vehicle_brand": getattr(vehicle, "brand", "") if vehicle else "",
        "vehicle_model": getattr(vehicle, "model", "") if vehicle else "",
        "vehicle_plates": getattr(vehicle, "license_plate", "") if vehicle else "",
        "driver_name": str(driver) if driver else "",
        "license_number": getattr(driver, "license_number", "") if driver else "",
        "license_expiration": getattr(driver, "license_expiration", None).isoformat() if driver and getattr(driver, "license_expiration", None) else None,
        "origin": dl_str(origin),
        "destination": dl_str(destination),
        "stops": [dl_str(s) for s in stops],
        "scheduled_departure_time": op.scheduled_departure_time.isoformat() if getattr(op, "scheduled_departure_time", None) else None,
    }


def serialize_log(log: ServiceLog) -> Dict:
    op = log.operation
    header = serialize_operation_for_header(op)

    events = [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "started_at": e.started_at.isoformat(),
            "ended_at": e.ended_at.isoformat() if e.ended_at else None,
            "notes": e.notes or "",
        }
        for e in log.events.all().order_by("started_at", "created_at")
    ]

    activities = [
        {
            "id": str(a.id),
            "event_id": str(a.event_id) if a.event_id else None,
            "activity_type": a.activity_type,
            "started_at": a.started_at.isoformat(),
            "ended_at": a.ended_at.isoformat(),
            "notes": a.notes or "",
        }
        for a in log.activities.all().order_by("started_at", "created_at")
    ]

    from .calculation_service import calculate_totals
    totals = calculate_totals(log)

    return {
        "id": str(log.id),
        "status": log.status,
        "departure_datetime": log.departure_datetime.isoformat() if log.departure_datetime else None,
        "arrival_datetime": log.arrival_datetime.isoformat() if log.arrival_datetime else None,
        "notes": log.notes or "",
        "header": header,
        "events": events,
        "activities": activities,
        "totals": totals,
    }
