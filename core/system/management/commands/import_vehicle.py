import csv
import uuid
from django.core.management.base import BaseCommand

from core.operations_panel.choices import UnitType, UnitStatus
from core.operations_panel.models import Supplier, Vehicle


class Command(BaseCommand):
    help = "MIGRA LOS VEHÍCULOS DESDE vehicles.csv AL MODELO VEHICLE"

    def handle(self, *args, **options):
        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/units.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
        total, created = 0, 0

        def clean(value):
            if value in [None, "", "NULL", "null"]:
                return None
            return str(value).strip().upper()

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total += 1
                try:
                    econ_number = clean(row.get("econ_number"))
                    model = clean(row.get("model"))
                    brand = clean(row.get("brand"))
                    year = int(2000)
                    circulation_card_number = clean(row.get("circulation_card_number")) or ""
                    serial_number = clean(row.get("serial_number")) or ""
                    license_plate = clean(row.get("license_plate")) or ""
                    sct_permit = clean(row.get("permiso_sct")) or ""
                    insurance_company = clean(row.get("insurance_company")) or ""
                    insurance_code = clean(row.get("insurance_code")) or ""
                    vehicle_config = clean(row.get("conf_vehicular")) or ""
                    unit_type = clean(row.get("unit_type")) or UnitType.OTHER
                    status = clean(row.get("status")) or "ACTIVA"
                    notes = clean(row.get("observations"))

                    # Relación con proveedor
                    supplier = None
                    supplier_id = row.get("supplier_id")
                    if supplier_id and supplier_id not in ["", "NULL", "null"]:
                        supplier = Supplier.objects.get(old_id=int(supplier_id))

                    # Normaliza estatus
                    if status in ["ACTIVA", "ACTIVE"]:
                        status = UnitStatus.ACTIVE
                    elif status in ["INACTIVA", "INACTIVE"]:
                        status = UnitStatus.INACTIVE
                    else:
                        status = UnitStatus.PENDING

                    # Crea o actualiza
                    obj, was_created = Vehicle.objects.get_or_create(
                        old_id=int(row["id"]),
                        defaults={
                            "econ_number": econ_number,
                            "model": model,
                            "brand": brand,
                            "year": year,
                            "circulation_card_number": circulation_card_number,
                            "serial_number": serial_number,
                            "license_plate": license_plate,
                            "sct_permit": sct_permit,
                            "insurance_company": insurance_company,
                            "insurance_code": insurance_code,
                            "vehicle_config": vehicle_config,
                            "unit_type": unit_type,
                            "status": status,
                            "supplier": supplier,
                            "notes": notes,
                        },
                    )

                    if was_created:
                        created += 1
                        self.stdout.write(self.style.ERROR(f"✅ VEHÍCULO ID {row.get('id')}"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN VEHÍCULO ID {row.get('id')}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} VEHÍCULOS CREADOS O ACTUALIZADOS.")
        )
