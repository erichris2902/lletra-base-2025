from django.db import models

from apps.facturapi.choices import TaxRegime
from core.operations_panel.models.address import Address

from core.operations_panel.choices import SupplierStatus
from core.system.models import BaseModel

class Supplier(BaseModel):
    """
    Modelo para proveedores.
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="Código")
    business_name = models.CharField(max_length=100, verbose_name="Razón social")
    tax_regime = models.CharField(
        max_length=3,
        choices=TaxRegime.choices,
        verbose_name="Régimen fiscal"
    )
    rfc = models.CharField(max_length=13, verbose_name="RFC")
    email = models.EmailField(verbose_name="Correo electrónico")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    bank = models.CharField(max_length=100, verbose_name="Banco")
    clabe = models.CharField(max_length=18, verbose_name="CLABE interbancaria")
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, verbose_name="Dirección")

    status = models.CharField(
        max_length=20,
        choices=SupplierStatus.choices,
        default=SupplierStatus.ACTIVO,
        verbose_name="Estatus"
    )

    def __str__(self):
        return f"{self.business_name} ({self.code})"

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"