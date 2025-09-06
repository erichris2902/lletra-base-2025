import csv
from django.core.management.base import BaseCommand
from core.operations_panel.models import Client
from core.operations_panel.models.address import Address


class Command(BaseCommand):
    help = 'Asigna direcciones a clientes existentes usando direction_id'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        updated = 0
        skipped = 0
        not_found = 0

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                rfc = row['rfc'].strip().upper()
                direction_id = row['direction_id'].strip()

                if not direction_id or direction_id.upper() == "NULL":
                    self.stdout.write(self.style.WARNING(f"⚠️ Cliente {rfc} sin dirección, se omite"))
                    skipped += 1
                    continue

                try:
                    client = Client.objects.get(rfc=rfc)
                    address = Address.objects.get(id=int(direction_id))
                    client.address = address
                    client.save()
                    updated += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ Dirección asignada a cliente {rfc}"))
                except Client.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"❌ Cliente con RFC {rfc} no encontrado"))
                    not_found += 1
                except Address.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"❌ Dirección con ID {direction_id} no encontrada"))
                    not_found += 1

        self.stdout.write(self.style.SUCCESS(
            f"🏁 Proceso terminado: {updated} actualizados, {skipped} sin dirección, {not_found} errores."
        ))
