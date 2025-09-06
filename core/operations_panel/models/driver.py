from django.db import models

from core.system.models import BaseModel

class Driver(BaseModel):
    """
    Modelo para conductores.
    """
    name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido paterno")
    mother_last_name = models.CharField(max_length=100, verbose_name="Apellido materno")
    rfc = models.CharField(max_length=13, verbose_name="RFC")
    license_number = models.CharField(max_length=20, verbose_name="Número de licencia")
    license_type = models.CharField(max_length=20, verbose_name="Tipo de licencia")
    license_expiration = models.DateField(verbose_name="Vencimiento de licencia")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    def __str__(self):
        return f"{self.name} {self.last_name} {self.mother_last_name}"

    class Meta:
        verbose_name = "Conductor"
        verbose_name_plural = "Conductores"