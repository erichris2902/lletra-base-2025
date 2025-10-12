from datetime import datetime

from django.db import models

from apps.facturapi.choices import VehicleConfig
from core.operations_panel.choices import UnitStatus, UnitType
from core.system.functions import extract_best_coincidence_from_field_in_model
from core.system.models import BaseModel


class Vehicle(BaseModel):
    """
    Modelo para vehículos.
    """
    econ_number = models.CharField(max_length=20, verbose_name="Número económico")
    model = models.CharField(max_length=50, verbose_name="Modelo")
    brand = models.CharField(max_length=50, verbose_name="Marca")
    year = models.PositiveIntegerField(verbose_name="Año")

    circulation_card_number = models.CharField(max_length=50, verbose_name="Tarjeta de circulación")
    serial_number = models.CharField(max_length=50, verbose_name="Número de serie")
    license_plate = models.CharField(max_length=20, verbose_name="Placas")
    sct_permit = models.CharField(max_length=50, verbose_name="Permiso SCT")

    insurance_company = models.CharField(max_length=50, verbose_name="Aseguradora")
    insurance_code = models.CharField(max_length=50, verbose_name="Póliza de seguro")
    vehicle_config = models.CharField(
        max_length=20,
        choices=VehicleConfig.choices,
        verbose_name="Configuración vehicular"
    )
    status = models.CharField(
        max_length=20,
        choices=UnitStatus.choices,
        default=UnitStatus.PENDING,
        verbose_name="Estatus"
    )
    supplier = models.ForeignKey(
        "Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Proveedor"
    )
    unit_type = models.CharField(
        max_length=30,
        choices=UnitType.choices,
        verbose_name="Tipo de unidad"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    @staticmethod
    def get_or_create_by_plate(plates, unit_type=None):
        if not plates:
            return None

        # Try exact match first
        try:
            return Vehicle.objects.get(license_plate__iexact=plates)
        except Vehicle.DoesNotExist:
            pass

        # Try fuzzy matching
        best_coincidence = extract_best_coincidence_from_field_in_model(Vehicle, 'license_plate', plates, 80)
        if best_coincidence:
            return best_coincidence

        # Determine unit type
        vehicle_type = get_vehicle_type(unit_type)

        # Create new vehicle if no match found
        return Vehicle.objects.create(
            econ_number=f"ECO-{plates}",
            model="DEFAULT",
            brand="DEFAULT",
            circulation_card_number="DEFAULT",
            insurance_company="DEFAULT",
            insurance_code="DEFAULT",
            serial_number="DEFAULT",
            license_plate=plates,
            year=datetime.now().year,
            sct_permit="DEFAULT",
            vehicle_config="C2",  # Default vehicle config
            unit_type=vehicle_type
        )

    def __str__(self):
        return f"{self.econ_number} - {self.license_plate}"

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"


def get_vehicle_type(unit_description):
    """
    Map a unit description to a UnitType choice.

    Args:
        unit_description (str): Description of the unit

    Returns:
        str: UnitType choice
    """
    if not unit_description:
        return UnitType.TORTON  # Default as per issue description

    unit_description = unit_description.upper()

    # Map common descriptions to UnitType choices
    if "TORTON" in unit_description:
        return UnitType.TORTON
    elif "TRACTO" in unit_description or "TRAILER" in unit_description:
        return UnitType.TRAILER
    elif "CAJA" in unit_description:
        if "40" in unit_description:
            return UnitType.BOX_40
        elif "48" in unit_description:
            return UnitType.BOX_48
        elif "53" in unit_description:
            return UnitType.BOX_53
        else:
            return UnitType.BOX
    elif "1 TN" in unit_description or "1TN" in unit_description:
        return UnitType.UNIT_1TN
    elif "2.5 TN" in unit_description or "2.5TN" in unit_description:
        return UnitType.UNIT_25TN
    elif "3.5 TN" in unit_description or "3.5TN" in unit_description:
        return UnitType.UNIT_35TN
    elif "5 TN" in unit_description or "5TN" in unit_description:
        return UnitType.UNIT_5TN
    elif "RABON" in unit_description:
        return UnitType.RABON
    elif "PLATAFORMA" in unit_description:
        if "40" in unit_description:
            return UnitType.PLATFORM_40
        elif "48" in unit_description:
            return UnitType.PLATFORM_48
        else:
            return UnitType.PLATFORM_40
    elif "PIPA" in unit_description:
        return UnitType.TANKER
    elif "TOLVA" in unit_description:
        return UnitType.HOPPER
    elif "MADRINA" in unit_description:
        return UnitType.CARRIER
    elif "UTILITARIO" in unit_description:
        return UnitType.UTILITY
    else:
        return UnitType.TORTON  # Default
