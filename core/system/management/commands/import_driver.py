import csv
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from core.operations_panel.models import Driver


class Command(BaseCommand):
    help = "MIGRA LOS REGISTROS DE DRIVERS.CSV AL MODELO DRIVER."

    def handle(self, *args, **options):
        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/operator.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
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

                name = clean(row.get("name"))
                last_name = clean(row.get("last_name"))
                mother_last_name = clean(row.get("mother_last_name"))
                rfc = clean(row.get("rfc"))
                license_number = clean(row.get("licence_number"))
                license_type = clean(row.get("licence_type"))
                notes = None  # No hay campo equivalente en CSV

                # Fecha de vencimiento (licence_validity o licence_expiration)
                expiration = datetime.now().date()
                for key in ["licence_validity", "licence_expiration"]:
                    date_val = clean(row.get(key))
                    if date_val:
                        try:
                            expiration = datetime.strptime(date_val, "%Y-%m-%d").date()
                            break
                        except Exception:
                            pass


                try:
                    obj, was_created = Driver.objects.get_or_create(
                        old_id=int(row["id"]),
                        defaults={
                            "name": name or "",
                            "last_name": last_name or "",
                            "mother_last_name": mother_last_name or "",
                            "rfc": rfc or "",
                            "license_number": license_number or "",
                            "license_type": license_type or "",
                            "license_expiration": expiration,
                            "notes": notes,
                        },
                    )
                    print(obj, was_created)

                    if was_created:
                        created += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN DRIVER ID {row['id']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} CONDUCTORES IMPORTADOS."))
