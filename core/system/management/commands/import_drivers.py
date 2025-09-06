import csv
from django.core.management.base import BaseCommand
from datetime import datetime

from core.operations_panel.models import Driver


class Command(BaseCommand):
    help = 'Importa choferes desde un archivo CSV, omitiendo duplicados por RFC'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        created = 0
        skipped = 0

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    rfc = row['rfc'].strip().upper()

                    try:
                        expiration = row['licence_validity']
                        license_expiration = datetime.strptime(expiration, '%Y-%m-%d').date() if expiration else None
                    except Exception:
                        license_expiration = datetime.now().date()

                    driver, _created = Driver.objects.get_or_create(
                        name=row['name'].strip(),
                        last_name=row['last_name'].strip(),
                        mother_last_name=row['mother_last_name'].strip(),
                        rfc=rfc,
                        license_number=row['licence_number'].strip(),
                        license_type=row['licence_type'].strip(),
                        license_expiration=license_expiration,
                        notes=None  # Puedes cambiarlo si deseas guardar algo aquí
                    )
                    if _created:
                        created += 1
                except Exception as e:
                    print(f"Error al procesar el chofer {row['name']} {row['last_name']} {row['rfc']}: {str(e)}")
                    skipped += 1
                    continue

        self.stdout.write(self.style.SUCCESS(
            f'✅ Importación completada: {created} choferes creados, {skipped} omitidos.'
        ))
