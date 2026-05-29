from django.conf import settings
from django.db import models

from core.system.models import BaseModel
from .operation import Operation


class OperationEvidence(BaseModel):
    class FileKind(models.TextChoices):
        PHOTO = "PHOTO", "Foto"
        PDF = "PDF", "PDF"

    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        related_name="evidences",
        verbose_name="Operación"
    )
    file = models.FileField(
        upload_to="operations/evidence/%Y/%m/",
        verbose_name="Archivo de evidencia"
    )
    file_kind = models.CharField(
        max_length=10,
        choices=FileKind.choices,
        verbose_name="Tipo de archivo"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Descripción"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_operation_evidences",
        verbose_name="Subido por"
    )

    def __str__(self):
        return f"Evidencia {self.file.name} ({self.file_kind}) de {self.operation}"

    class Meta:
        verbose_name = "Evidencia de Operación"
        verbose_name_plural = "Evidencias de Operación"
