from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from core.system.models import BaseModel
from core.operations_panel.models.operation import Operation


# --- Choices -----------------------------------------------------------------

class ServiceLogStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    IN_PROGRESS = "IN_PROGRESS", "En progreso"
    COMPLETED = "COMPLETED", "Completada"


class ServiceLogEventType(models.TextChoices):
    TRIP_START = "TRIP_START", "Inicio de viaje"
    UNLOADING = "UNLOADING", "Descarga"
    BREAKDOWN = "BREAKDOWN", "Descompostura"
    MEAL = "MEAL", "Comida"
    REST = "REST", "Descanso"
    CHECKPOINT = "CHECKPOINT", "Retén"
    TRIP_END = "TRIP_END", "Cierre de viaje"


class ServiceLogActivityType(models.TextChoices):
    DRIVING = "DRIVING", "Conduciendo"
    PAUSE = "PAUSE", "Pausa"
    AUXILIARY = "AUXILIARY", "Actividades auxiliares"
    EXCEPTION = "EXCEPTION", "Casos de excepción"
    REST = "REST", "Descanso"


# --- Validators ---------------------------------------------------------------

def _validate_30_minute_grid(dt):
    if dt is None:
        return
    minutes = dt.minute
    if minutes not in (0, 30):
        raise ValidationError("Los horarios deben alinearse a bloques de 30 minutos (mm = 00 o 30).")


def _validate_positive_interval(start, end):
    if start and end and end <= start:
        raise ValidationError("La hora final debe ser posterior a la hora inicial.")


# --- Models -------------------------------------------------------------------

class ServiceLog(BaseModel):
    """Bitácora principal asociada 1:1 a la Operation."""

    operation = models.OneToOneField(Operation, on_delete=models.PROTECT, related_name="service_log")

    departure_datetime = models.DateTimeField(null=True, blank=True)
    arrival_datetime = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=ServiceLogStatus.choices, default=ServiceLogStatus.DRAFT)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # Optimistic concurrency simple version field
    version = models.PositiveIntegerField(default=0)

    def clean(self):
        if self.departure_datetime and self.arrival_datetime:
            if self.arrival_datetime < self.departure_datetime:
                raise ValidationError("La llegada no puede ser anterior a la salida.")
        _validate_30_minute_grid(self.departure_datetime or timezone.now().replace(minute=0, second=0, microsecond=0))
        # arrival puede estar vacío durante el viaje; si existe, valida grid
        if self.arrival_datetime:
            _validate_30_minute_grid(self.arrival_datetime)

    def mark_completed(self):
        self.status = ServiceLogStatus.COMPLETED
        self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at", "updated_at"])

    class Meta:
        verbose_name = "Bitácora de servicio"
        verbose_name_plural = "Bitácoras de servicio"


class ServiceLogEvent(BaseModel):
    """Eventos puntuales o de intervalo asociados a la bitácora."""

    service_log = models.ForeignKey(ServiceLog, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=ServiceLogEventType.choices)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def clean(self):
        _validate_30_minute_grid(self.started_at)
        if self.ended_at:
            _validate_30_minute_grid(self.ended_at)
            _validate_positive_interval(self.started_at, self.ended_at)

    class Meta:
        verbose_name = "Evento de bitácora"
        verbose_name_plural = "Eventos de bitácora"
        ordering = ["started_at", "created_at"]


class ServiceLogActivity(BaseModel):
    """Intervalos de actividad categorizados; base de los cálculos."""

    service_log = models.ForeignKey(ServiceLog, on_delete=models.CASCADE, related_name="activities")
    event = models.ForeignKey(ServiceLogEvent, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")

    activity_type = models.CharField(max_length=20, choices=ServiceLogActivityType.choices)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    notes = models.TextField(null=True, blank=True)

    def clean(self):
        _validate_30_minute_grid(self.started_at)
        _validate_30_minute_grid(self.ended_at)
        _validate_positive_interval(self.started_at, self.ended_at)
        # Overlaps are allowed by business rule. No non-overlap validation.

    class Meta:
        verbose_name = "Actividad registrada"
        verbose_name_plural = "Actividades registradas"
        ordering = ["started_at", "created_at"]



class ServiceLogAudit(BaseModel):
    """Historial de cambios para bitácoras, eventos y actividades."""

    service_log = models.ForeignKey(ServiceLog, on_delete=models.CASCADE, related_name="audits")
    user = models.ForeignKey('system.SystemUser', null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    target_model = models.CharField(max_length=50)
    target_id = models.CharField(max_length=64)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Auditoría de bitácora"
        verbose_name_plural = "Auditorías de bitácora"
