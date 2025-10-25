import csv
from django.core.management.base import BaseCommand

from core.operations_panel.models import Supplier
from core.operations_panel.models.address import Address


class Command(BaseCommand):
    help = "MIGRA LOS REGISTROS DE SUPPLIERS.CSV AL MODELO SUPPLIER."

    def handle(self, *args, **options):
        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/supplier.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
        total = 0
        created = 0

        with open(file_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total += 1

                def clean(value):
                    if value in [None, "", "NULL", "null"]:
                        return None
                    return value.strip().upper()

                code = clean(row.get("comercial_name"))
                business_name = clean(row.get("business_name"))
                tax_regime = clean(row.get("regimen_fiscal"))
                rfc = clean(row.get("rfc"))
                email = clean(row.get("email"))
                phone = clean(row.get("tel"))
                bank = clean(row.get("banco"))
                clabe = clean(row.get("clave_interbancaria"))
                status = clean(row.get("status")) or "ACTIVO"

                # DIRECCIÓN
                address = None
                direction_id = clean(row.get("direction_id"))
                if direction_id:
                    address = Address.objects.filter(old_id=int(direction_id)).first()
                    if not address:
                        self.stdout.write(
                            self.style.WARNING(f"⚠ NO SE ENCONTRÓ ADDRESS CON OLD_ID {direction_id} PARA SUPPLIER ID {row['id']}")
                        )


                try:
                    obj, was_created = Supplier.objects.get_or_create(
                        old_id=int(row["id"]),
                        defaults={
                            "code": code or f"EQ-{row['id']}",
                            "business_name": business_name or "",
                            "tax_regime": tax_regime or "601",
                            "rfc": rfc or "",
                            "email": email or "",
                            "phone": phone or "",
                            "bank": bank or "",
                            "clabe": clabe.replace(" ", "")[:18] if clabe else  "",
                            "address": address,
                            "status": status,
                        },
                    )

                    if was_created:
                        created += 1

                    print(obj)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN SUPPLIER ID {row['id']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} PROVEEDORES IMPORTADOS."))
