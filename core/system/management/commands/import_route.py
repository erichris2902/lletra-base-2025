import csv
import uuid
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime

from core.operations_panel.models import DeliveryLocation, Route


class Command(BaseCommand):
    help = "MIGRA LAS RUTAS DESDE ROUTES.CSV AL MODELO ROUTE."

    def handle(self, *args, **options):
        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/route.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
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

                system = clean(row.get("system"))
                name = f"{system or 'OLD'}-{row['id']}"
                kms = clean(row.get("kilometros"))
                try:
                    kms = int(float(kms)) if kms else -1
                except Exception:
                    kms = -1

                # BUSCAR UBICACIONES DE ENTREGA (origen y destino)
                origin = None
                destiny = None

                origin_id = clean(row.get("origin_id"))
                if origin_id:
                    origin = DeliveryLocation.objects.filter(old_id=int(origin_id)).first()
                    if not origin:
                        self.stdout.write(
                            self.style.WARNING(f"⚠ NO SE ENCONTRÓ ORIGEN CON OLD_ID {origin_id} (ROUTE ID {row['id']})")
                        )

                destiny_id = clean(row.get("destiny_id"))
                if destiny_id:
                    destiny = DeliveryLocation.objects.filter(old_id=int(destiny_id)).first()
                    if not destiny:
                        self.stdout.write(
                            self.style.WARNING(f"⚠ NO SE ENCONTRÓ DESTINO CON OLD_ID {destiny_id} (ROUTE ID {row['id']})")
                        )

                try:
                    obj, was_created = Route.objects.get_or_create(
                        old_id=int(row["id"]),
                        defaults={
                            "name": name,
                            "initial_location": origin,
                            "destination_location": destiny,
                            "direct_distance": kms,
                            "optimized_distance": kms,
                            "published": False,
                            "notes": None,
                            "optimized_route": None,
                        },
                    )
                    print(obj, was_created)

                    if was_created:
                        created += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN ROUTE ID {row['id']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} RUTAS IMPORTADAS."))
