from django.db import models

from core.operations_panel.models.address import Address

from apps.facturapi.choices import TaxRegime
from core.system.models import BaseModel


class Client(BaseModel):
    """
    Modelo para clientes.
    """
    name = models.CharField(max_length=100, verbose_name="Nombre comercial")
    business_name = models.CharField(max_length=100, verbose_name="Razón social")
    rfc = models.CharField(max_length=13, blank=True, null=True, verbose_name="RFC")
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, verbose_name="Dirección")
    email = models.EmailField(verbose_name="Correo electrónico")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    tax_regime = models.CharField(
        max_length=3,
        choices=TaxRegime.choices,
        default=TaxRegime.RF01,
        verbose_name="Régimen fiscal"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

