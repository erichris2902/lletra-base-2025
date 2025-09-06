import csv
from django.core.management.base import BaseCommand
from django.db import transaction

from core.operations_panel.models import DeliveryLocation
from core.operations_panel.models.address import Address


def parse_value(value):
    return value.strip() if value and value.strip().upper() != "NULL" else ""


class Command(BaseCommand):
    help = 'Importa direcciones y ubicaciones de entrega desde CSV'

    def add_arguments(self, parser):
        parser.add_argument('--addresses', type=str, help='Ruta al CSV de direcciones')
        parser.add_argument('--locations', type=str, help='Ruta al CSV de ubicaciones de entrega')

    def handle(self, *args, **options):
        address_file = options['addresses']
        location_file = options['locations']

        if address_file:
            self.import_addresses(address_file)

        if location_file:
            self.import_locations(location_file)

    @transaction.atomic
    def import_addresses(self, file_path):
        self.stdout.write(self.style.WARNING(f"📦 Importando direcciones desde {file_path}"))

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                address, created = Address.objects.update_or_create(
                    id=int(row['id']),
                    defaults={
                        "street": parse_value(row["street"]),
                        "exterior_number": parse_value(row["exterior_number"]),
                        "interior_number": parse_value(row["interior_number"]),
                        "colony": parse_value(row["colony"]),
                        "city": parse_value(row["city"]),
                        "state": parse_value(row["state"]),
                        "zip_code": parse_value(row["cp"]),
                    }
                )
                self.stdout.write(self.style.SUCCESS(
                    f"{'✅ Creado' if created else '♻️ Actualizado'} Address ID {address.id}"
                ))

    @transaction.atomic
    def import_locations(self, file_path):
        self.stdout.write(self.style.WARNING(f"🏬 Importando ubicaciones desde {file_path}"))

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                print(row)
                direction_id = int(row["direction_id"])
                try:
                    address = Address.objects.get(id=direction_id)
                    location, created = DeliveryLocation.objects.get_or_create(
                        name=parse_value(row["name"]),
                        rfc=parse_value(row["rfc"]),
                        defaults={
                            "business_name": parse_value(row["bussines_name"]),
                            "address": address,
                            "notes": parse_value(row["comments_on_delivery"]),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"{'✅ Creado' if created else '♻️ Existente'} DeliveryLocation: {location}"
                    ))
                except Address.DoesNotExist:
                    self.stderr.write(self.style.ERROR(
                        f"❌ No se encontró Address con ID {direction_id} para DeliveryLocation: {row['name']}"
                    ))
