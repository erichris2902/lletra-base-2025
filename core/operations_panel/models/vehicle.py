from django.db import models

from apps.facturapi.choices import VehicleConfig
from core.operations_panel.choices import UnitStatus, UnitType
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

    def __str__(self):
        return f"{self.econ_number} - {self.license_plate}"

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"