from django.db import models
from django.utils.text import slugify

from core.operations_panel.models.address import Address

from apps.facturapi.choices import TaxRegime
from core.system.functions import extract_best_coincidence_from_field_in_model
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

    @staticmethod
    def get_or_create_by_str(name: str = None):
        if not name:
            return None

        # Try exact match first
        try:
            return Client.objects.get(name__iexact=name)
        except Client.DoesNotExist:
            pass

        # Try fuzzy matching
        best_coincidence = extract_best_coincidence_from_field_in_model(Client, 'name', name)

        if best_coincidence:
            return best_coincidence

        # Create new client if no match found
        # First create a default address
        address = Address.objects.create(
            street="Default Street",
            exterior_number="S/N",
            colony="Default Colony",
            city="Default City",
            state="Ciudad de México",  # Valid choice from MEXICAN_STATES
            zip_code="00000"
        )

        return Client.objects.create(
            name=name,
            business_name=name,
            email=f"{slugify(name)}@example.com",  # Default email
            phone="0000000000",  # Default phone
            tax_regime="601",  # Default tax regime
            address=address
        )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

