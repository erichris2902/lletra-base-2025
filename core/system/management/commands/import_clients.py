import csv
from django.core.management.base import BaseCommand

from core.operations_panel.models import Client


class Command(BaseCommand):
    help = 'Importa clientes desde un archivo CSV, evitando duplicados por RFC'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        created = 0
        skipped = 0

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                rfc = row['rfc'].strip().upper()
                if Client.objects.filter(rfc=rfc).exists():
                    skipped += 1
                    continue

                Client.objects.create(
                    name=row['comercial_name'].strip(),
                    business_name=row['business_name'].strip(),
                    rfc=rfc,
                    email=row['email'].strip(),
                    phone=row['tel'].strip(),
                    tax_regime=row['regimen_fiscal'].strip()
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {created} clientes creados, {skipped} omitidos.'
        ))
