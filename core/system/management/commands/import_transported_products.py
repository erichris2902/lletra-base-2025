import csv
from django.core.management.base import BaseCommand

from core.operations_panel.models import TransportedProduct


class Command(BaseCommand):
    help = 'Importa productos transportados desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        created = 0
        skipped = 0

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = row['BienesTransp']

                TransportedProduct.objects.create(
                    transported_product_key=key,
                    unit_key=row['ClaveUnidad'],
                    description=row['Descripcion'],
                    currency=row['Moneda'],
                    weight=float(row['PesoEnKg']),
                    amount=int(row['Cantidad']),
                    is_danger=row['MaterialPeligroso'].strip().lower() in ['true', '1']
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Importación completada: {created} creados, {skipped} omitidos por clave repetida.'
        ))
