import csv
from django.core.management.base import BaseCommand

from apps.facturapi.choices import VehicleConfig
from core.operations_panel.choices import UnitStatus, UnitType
from core.operations_panel.models import Vehicle


class Command(BaseCommand):
    help = 'Importa vehículos desde un archivo CSV, omitiendo duplicados por número de serie'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        created = 0
        skipped = 0

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                serial = row['serial_number'].strip()

                try:
                    vehicle_config = row['conf_vehicular'].strip()
                    if vehicle_config not in VehicleConfig.values:
                        raise ValueError(f"Conf. vehicular inválida: {vehicle_config}")
                except Exception:
                    vehicle_config = VehicleConfig.UNSPECIFIED if hasattr(VehicleConfig, 'UNSPECIFIED') else ''  # Asume que tienes una opción genérica

                try:
                    status = row['status'].strip()
                    if status not in UnitStatus.values:
                        raise ValueError(f"Estado inválido: {status}")
                except Exception:
                    status = UnitStatus.PENDING if hasattr(UnitStatus, 'PENDING') else 'PENDIENTE'

                try:
                    unit_type = row['unit_type'].strip()
                    if unit_type not in UnitType.values:
                        raise ValueError(f"Tipo de unidad inválido: {unit_type}")
                except Exception:
                    unit_type = UnitType.OTHER if hasattr(UnitType, 'OTHER') else 'OTRO'

                vehicle, _created  =Vehicle.objects.get_or_create(
                    econ_number=row['econ_number'].strip(),
                    model=row['model'].strip(),
                    brand=row['brand'].strip(),
                    circulation_card_number=row['circulation_card_number'] or '',
                    insurance_company=row['insurance_company'].strip(),
                    insurance_code=row['insurance_code'].strip(),
                    serial_number=serial,
                    license_plate=row['license_plate'].strip(),
                    year=int(row['year']) if row['year'] and row['year'] != "NULL" else 0,
                    sct_permit=row['permiso_sct'] or '',
                    vehicle_config=vehicle_config,
                    status=status,
                    unit_type=unit_type,
                )
                if _created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f'🚚 Vehículos importados: {created} creados, {skipped} omitidos por duplicado o error.'
        ))
