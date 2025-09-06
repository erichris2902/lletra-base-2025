from django.db import models

from core.operations_panel.models.address import Address

from core.operations_panel.choices import MEXICAN_STATES_KEY
from core.system.functions import extract_best_coincidence_from_field_in_model
from core.system.models import BaseModel

class DeliveryLocation(BaseModel):
    """
    Modelo para ubicaciones de entrega.
    """
    name = models.CharField(max_length=100, verbose_name="Nombre")
    business_name = models.CharField(max_length=100, verbose_name="Razón social")
    rfc = models.CharField(max_length=13, verbose_name="RFC")
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, verbose_name="Dirección")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    def get_or_create_by_str(self, name: str = None):
        if not name:
            return None

        try:
            return DeliveryLocation.objects.get(name__iexact=name)
        except DeliveryLocation.DoesNotExist:
            pass

        # Try fuzzy matching
        best_coincidence = extract_best_coincidence_from_field_in_model(DeliveryLocation, 'name', name, 90)

        if best_coincidence:
            return best_coincidence

        address = Address.objects.create(
            street="Default Street",
            exterior_number="S/N",
            colony="Default Colony",
            city="Default City",
            state="Ciudad de México",  # Valid choice from MEXICAN_STATES
            zip_code="00000"
        )

        return DeliveryLocation.objects.create(
            name=name,
            business_name=name,
            rfc="XAXX010101000",  # Default RFC for Mexico
            address=address
        )

    def generate_address_cartaporte(self):
        data = {
            'Calle': self.address.street or "Sin calle",
            'CodigoPostal': self.address.zip_code or "Sin CP",
            'Colonia': self.address.colony or "Sin colonia",
            'Estado': MEXICAN_STATES_KEY[self.address.state],
            'NumeroExterior': self.address.exterior_number or "Sin numero",
            'RFCRemitente': self.rfc,
        }
        return data

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Ubicación de Entrega"
        verbose_name_plural = "Ubicaciones de Entrega"
