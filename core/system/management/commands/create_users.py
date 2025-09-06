import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password

from core.system.enums import SystemEnum
from core.system.models import SystemUser


class Command(BaseCommand):
    help = 'Importa usuarios del sistema desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Ruta al archivo CSV')

    def handle(self, *args, **options):
        path = options['csv_path']

        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                email = row['Correo'].strip()
                password = row['Pass'].strip()
                telegram_username = row['Telegram'].strip() or None
                area = row['Area'].strip().capitalize()
                calendario = row['Calendario'].strip().lower() == 'si'

                nombre = row['Nombre de la persona'].strip()
                telefono = row['Telefono'].strip()
                contacto_email = row['Correo de contacto'].strip()
                cargo = row['Cargo'].strip()

                user, created = SystemUser.objects.get_or_create(
                    username=email,
                    defaults={
                        'email': email,
                        'password': make_password(password),
                        'telegram_username': telegram_username,
                        'system': SystemEnum.ADMINISTRACION,
                        'calendar_url': f'https://calendar.google.com/calendar/embed?src={email}' if calendario else None,
                        'doc_nombre': nombre,
                        'doc_tel': telefono,
                        'doc_mail': contacto_email,
                        'doc_cargo': cargo,
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Usuario creado: {email}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Usuario ya existía: {email}"))
