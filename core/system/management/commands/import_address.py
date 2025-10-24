import csv
import uuid
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime

from core.operations_panel.models.address import Address


class Command(BaseCommand):
    help = "MIGRA LOS REGISTROS DE DIRECTION.CSV A ADDRESS."

    def handle(self, *args, **options):

        for address in Address.objects.all():
            print(address)
            address.delete()

        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/direction.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
        total = 0
        created = 0

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total += 1

                # IGNORAR NULL COMO TEXTO
                def clean(value):
                    if value in [None, "", "NULL", "null"]:
                        return None
                    return value.strip().upper()

                street = clean(row.get("street"))
                exterior_number = clean(row.get("exterior_number"))
                interior_number = clean(row.get("interior_number"))
                colony = clean(row.get("colony"))
                city = clean(row.get("city"))
                state = clean(row.get("state"))
                zip_code = clean(row.get("cp"))

                # CAMPOS QUE NO EXISTEN EN EL NUEVO MODELO
                municipy = clean(row.get("municipy"))
                # NOTIFICACIÓN
                if municipy:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ MUNICIPIO '{municipy}' (ID {row['id']}) NO TIENE CAMPO EN EL NUEVO MODELO.")
                    )

                # FECHAS (si se desean conservar, aunque BaseModel usa auto_now_add)
                try:
                    created_at = make_aware(datetime.fromisoformat(row.get("date_created").split("+")[0]))
                except Exception:
                    created_at = None

                try:
                    updated_at = make_aware(datetime.fromisoformat(row.get("date_updated").split("+")[0]))
                except Exception:
                    updated_at = None

                try:
                    obj = Address.objects.create(
                        id=uuid.uuid4(),
                        old_id=int(row["id"]),
                        street=street,
                        exterior_number=exterior_number,
                        interior_number=interior_number,
                        colony=colony,
                        city=city,
                        state=state or "QUERETARO DE ARTEAGA",
                        zip_code=zip_code,
                        latitude=None,
                        longitude=None,
                    )

                    # OPCIONAL: si quieres forzar created_at y updated_at iguales a los originales
                    if created_at:
                        Address.objects.filter(pk=obj.id).update(created_at=created_at)
                    if updated_at:
                        Address.objects.filter(pk=obj.id).update(updated_at=updated_at)

                    created += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN FILA ID {row['id']}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} REGISTROS CREADOS."))