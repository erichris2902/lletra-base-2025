import csv
import uuid
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime

from core.operations_panel.models import Client
from core.operations_panel.models.address import Address


class Command(BaseCommand):
    help = "MIGRA LOS REGISTROS DE CLIENTES DESDE CLIENTS.CSV AL MODELO CLIENT."

    def handle(self, *args, **options):
        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/client.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
        total = 0
        created = 0

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total += 1

                def clean(value):
                    if value in [None, "", "NULL", "null"]:
                        return None
                    return value.strip().upper()

                comercial_name = clean(row.get("comercial_name"))
                business_name = clean(row.get("business_name"))
                tax_regime = clean(row.get("regimen_fiscal"))
                rfc = clean(row.get("rfc"))
                email = clean(row.get("email"))
                phone = clean(row.get("tel"))

                # BUSCAR DIRECCIÓN SEGÚN OLD_ID
                address = None
                direction_id = clean(row.get("direction_id"))
                if direction_id:
                    address = Address.objects.filter(old_id=int(direction_id)).first()
                    if not address:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠ NO SE ENCONTRÓ ADDRESS CON OLD_ID {direction_id} PARA CLIENTE ID {row['id']}")
                        )

                try:
                    obj = Client.objects.get_or_create(
                        old_id=int(row["id"]),
                        defaults={
                            "name": comercial_name or "",
                            "business_name": business_name or "",
                            "rfc": rfc,
                            "address": address,
                            "email": email or "",
                            "phone": phone or "",
                            "tax_regime": tax_regime or "601",
                        }

                    )
                    print(obj)

                    created += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN CLIENTE ID {row['id']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} CLIENTES IMPORTADOS."))
