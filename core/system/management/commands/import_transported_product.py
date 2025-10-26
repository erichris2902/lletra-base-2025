import csv
import uuid
from django.core.management.base import BaseCommand

from core.operations_panel.models import TransportedProduct


class Command(BaseCommand):
    help = "MIGRA LOS PRODUCTOS TRANSPORTADOS DESDE TRANSPORTED_PRODUCTS.CSV AL MODELO TRANSPORTEDPRODUCT."

    def handle(self, *args, **options):
        file_path = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/transportedproduct.csv"  # AJUSTA LA RUTA SEGÚN DONDE ESTÉ TU ARCHIVO
        batch_size = 1000  # inserta en bloques de 1000 filas

        def clean(value):
            if value in [None, "", "NULL", "null"]:
                return None
            return value.strip().upper()

        total = 0
        objs = []

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total += 1

                try:
                    obj = TransportedProduct(
                        old_id=int(row["id"]),
                        transported_product_key=clean(row.get("BienesTransp")) or "",
                        unit_key=clean(row.get("ClaveUnidad")) or "",
                        description=clean(row.get("Descripcion")) or "",
                        currency=clean(row.get("Moneda")) or "MXN",
                        is_danger=str(row.get("MaterialPeligroso")).strip().lower() in ["true", "1", "yes"],
                        weight=float(row.get("PesoEnKg") or 0),
                        amount=int(float(row.get("Cantidad") or 0)),
                    )
                    objs.append(obj)

                    # Inserta en bloques
                    if len(objs) >= batch_size:
                        TransportedProduct.objects.bulk_create(objs, batch_size=batch_size)
                        self.stdout.write(self.style.NOTICE(f"💾 Insertadas {len(objs)} filas..."))
                        objs.clear()

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN FILA {row.get('id')}: {e}"))

            # Inserta las filas restantes
            if objs:
                TransportedProduct.objects.bulk_create(objs, batch_size=batch_size)
                self.stdout.write(self.style.NOTICE(f"💾 Último lote de {len(objs)} insertado."))

        self.stdout.write(self.style.SUCCESS(f"✅ MIGRACIÓN FINALIZADA ({total} REGISTROS IMPORTADOS)."))
