from django.db import models

from core.operations_panel.models.transported_product import TransportedProduct
from core.system.models import BaseModel


class Cargo(BaseModel):
    """
    Model for cargo (load). A cargo can have multiple transported products.
    """
    identifier = models.CharField(max_length=255, verbose_name="Identificador")
    products = models.ManyToManyField(TransportedProduct, related_name="cargos", verbose_name="Productos transportados")

    def __str__(self):
        return f"Carga: {self.identifier}"

    class Meta:
        verbose_name = "Carga"
        verbose_name_plural = "Cargas"

    def toJSON(self):
        return {
            "id": self.id,
            "identifier": self.identifier,
            "products": ", ".join(product.description for product in self.products.all()),
        }