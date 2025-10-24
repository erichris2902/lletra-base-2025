from django.db import models

from core.system.models import BaseModel

class TransportedProduct(BaseModel):
    transported_product_key = models.CharField(max_length=100, verbose_name="Bienes transportados")
    unit_key = models.CharField(max_length=100, verbose_name="Clave SAT")
    description = models.CharField(max_length=100, verbose_name="Descripcion del bien")
    currency = models.CharField(default="MXN", max_length=100, verbose_name="Moneda")
    is_danger = models.BooleanField(default=False, verbose_name='¿Es material peligroso del tipo 0,1?')

    weight = models.FloatField(verbose_name="Peso en Kg")
    amount = models.IntegerField(verbose_name="Cantidad")

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = "Producto transportado"
        verbose_name_plural = "Productos transportados"


class OperationTransportedProduct(BaseModel):
    operation = models.ForeignKey(
        "Operation",
        on_delete=models.CASCADE,
        related_name="transported_products_operation",
        verbose_name="Operación"
    )
    transported_product = models.ForeignKey(
        TransportedProduct,
        on_delete=models.CASCADE,
        verbose_name="Producto base"
    )
    weight = models.FloatField(verbose_name="Peso en Kg")
    amount = models.IntegerField(verbose_name="Cantidad")

    def __str__(self):
        return f"{self.transported_product.description} ({self.amount}x) - {self.operation.folio}"
