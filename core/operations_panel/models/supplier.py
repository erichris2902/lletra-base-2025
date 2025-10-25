from django.db import models
from django.utils.text import slugify

from apps.facturapi.choices import TaxRegime
from core.operations_panel.models.address import Address

from core.operations_panel.choices import SupplierStatus
from core.system.functions import extract_best_coincidence_from_field_in_model
from core.system.models import BaseModel

class Supplier(BaseModel):
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

    @staticmethod
    def get_or_create_by_str(name: str = None):
        if not name:
            return None

        # Try exact match first
        try:
            return Supplier.objects.get(business_name__iexact=name)
        except Supplier.DoesNotExist:
            pass

        # Try fuzzy matching
        best_coincidence = extract_best_coincidence_from_field_in_model(Supplier, 'code', name, 80)
        if best_coincidence:
            return best_coincidence

        best_coincidence = extract_best_coincidence_from_field_in_model(Supplier, 'business_name', name, 80)
        if best_coincidence:
            return best_coincidence

        # Create new supplier if no match found
        # First create a default address
        address = Address.objects.create(
            street="Default Street",
            exterior_number="S/N",
            colony="Default Colony",
            city="Default City",
            state="Ciudad de México",  # Valid choice from MEXICAN_STATES
            zip_code="00000"
        )

        code = generate_supplier_code(name)
        return Supplier.objects.create(
            code=code,
            business_name=name,
            rfc="XAXX010101000",  # Default RFC for Mexico
            email=f"{slugify(name)}@example.com",  # Default email
            phone="0000000000",  # Default phone
            bank="Default Bank",
            clabe="000000000000000000",
            tax_regime="601",  # Default tax regime
            address=address
        )

    def __str__(self):
        return f"{self.business_name} ({self.code})"

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

def generate_supplier_code(name):
    """
    Generate a unique supplier code based on the name.

    Args:
        name (str): Supplier name

    Returns:
        str: Generated code
    """
    # Create a base code from the first 3 letters of the name
    base_code = ''.join(c for c in name if c.isalnum())[:3].upper()

    # Add a number to make it unique
    existing_codes = Supplier.objects.filter(code__startswith=base_code).count()
    return f"{base_code}{existing_codes + 1:03d}"