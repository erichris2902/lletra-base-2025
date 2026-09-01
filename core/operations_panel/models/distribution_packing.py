from django.db import models
from packaging.utils import _

from core.operations_panel.models.operation import Operation

from core.operations_panel.models.delivery_location import DeliveryLocation

from core.operations_panel.choices import AsturianoPacking
from core.system.models import BaseModel

class DistributionPacking(BaseModel):
    """
    Model for cargo (load). A cargo can have multiple transported products.
    """
    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    delivery_shop = models.ForeignKey(
        DeliveryLocation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    distribution = models.CharField(
        _("Distribucion"),
        max_length=20,
        choices=AsturianoPacking.choices,
        default=AsturianoPacking.CVZ_AB
    )
    weight = models.FloatField(verbose_name="Peso en Kg")
    amount = models.IntegerField(verbose_name="Cantidad")

    cajas_ab = models.IntegerField(verbose_name="Cajas de abarrotes", default=0)
    bolsas_ab = models.IntegerField(verbose_name="Bolsas de abarrotes", default=0)
    weight_ab = models.FloatField(verbose_name="Peso en Kg de abarrotes", default=0)

    cajas_cvz = models.IntegerField(verbose_name="Cajas de cerveza", default=0)
    bolsas_cvz = models.IntegerField(verbose_name="Bolsas de cerveza", default=0)
    weight_cvz = models.FloatField(verbose_name="Peso en Kg de cerveza", default=0)

    def __str__(self):
        return f"{self.operation or 'Sin operación'} - {self.delivery_shop or 'Sin tienda'}"

