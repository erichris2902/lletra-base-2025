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

