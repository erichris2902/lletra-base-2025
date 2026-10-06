from django.conf import settings
from django.db import models

from core.system.models import BaseModel
from core.operations_panel.models.operation import Operation


def external_upload_to(instance, filename: str) -> str:
    try:
        d = instance.date
    except Exception:
        d = None
    if d:
        return f"external_entries/{d:%Y/%m}/{filename}"
    return f"external_entries/{filename}"


class ExternalFinanceCategory(BaseModel):
    name = models.CharField(max_length=80, unique=True, verbose_name="Categoría")
    active = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        verbose_name = "Categoría de ingreso/egreso externo"
        verbose_name_plural = "Categorías de ingresos/egresos externos"

    def __str__(self):
        return self.name


class ExternalFinanceEntry(BaseModel):
    class EntryType(models.TextChoices):
        INCOME = "INCOME", "Ingreso"
        EXPENSE = "EXPENSE", "Egreso"

    concept = models.CharField(max_length=255, verbose_name="Concepto")
    entry_type = models.CharField(max_length=7, choices=EntryType.choices, verbose_name="Tipo")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (IVA incluido)")
    date = models.DateField(verbose_name="Fecha limite para pago", blank=True, null=True)
    paid = models.BooleanField(default=False, verbose_name="Pagado", blank=True)
    paid_date = models.DateField(blank=True, null=True, verbose_name="Fecha de pago")

    invoice_pdf = models.FileField(upload_to=external_upload_to, blank=True, null=True, verbose_name="Factura PDF")
    invoice_xml = models.FileField(upload_to=external_upload_to, blank=True, null=True, verbose_name="Factura XML")

    category = models.ForeignKey(ExternalFinanceCategory, on_delete=models.SET_NULL, blank=True, null=True,
                                 verbose_name="Categoría")
    operation = models.ForeignKey(Operation, on_delete=models.SET_NULL, blank=True, null=True,
                                  verbose_name="Operación (opcional)")
    comments = models.TextField(blank=True, null=True, verbose_name="Comentarios")

    created_by = models.ForeignKey(getattr(settings, "AUTH_USER_MODEL", "system.SystemUser"),
                                   on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = "Ingreso/Egreso externo"
        verbose_name_plural = "Ingresos/Egresos externos"
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["entry_type"]),
            models.Index(fields=["paid"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.amount is None or self.amount <= 0:
            raise ValidationError({"amount": "El monto debe ser mayor a 0."})
        if self.paid and not self.paid_date:
            raise ValidationError({"paid_date": "Si está marcado como pagado, ingresa la fecha de pago."})

    def __str__(self):
        return f"{self.get_entry_type_display()} - {self.concept} - ${self.amount}"