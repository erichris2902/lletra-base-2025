# tu_app/management/commands/create_drive_folder_in_facturacion.py

from django.core.management.base import BaseCommand

from apps.google_drive.services import check_folder_exists_with_service_account, create_folder_with_service_account

class Command(BaseCommand):
    help = "Crea una carpeta llamada 'prueba' dentro de la carpeta 'Facturacion' en Google Drive usando la cuenta de servicio."

    def add_arguments(self, parser):
        parser.add_argument(
            '--parent',
            type=str,
            default='1YPzEEXIGOj2Rs-lpLrd0Z94llJNoiaRF',
            help='ID de la carpeta raíz donde se buscará la carpeta Facturacion.'
        )
        parser.add_argument(
            '--name',
            type=str,
            default='prueba',
            help='Nombre de la carpeta a crear dentro de Facturacion.'
        )

    def handle(self, *args, **options):
        parent_root = options['parent']
        new_folder_name = options['name']

        self.stdout.write(self.style.NOTICE(f"🔍 Buscando carpeta 'Facturacion' dentro de {parent_root}..."))

        # Buscar carpeta Facturacion dentro del parent root
        facturacion_id = check_folder_exists_with_service_account("Facturacion", parent_root)

        if not facturacion_id:
            self.stdout.write(self.style.ERROR("❌ No se encontró la carpeta 'Facturacion'."))
            return

        self.stdout.write(self.style.SUCCESS(f"📁 Carpeta 'Facturacion' encontrada con ID: {facturacion_id}"))
        self.stdout.write(self.style.NOTICE(f"🚀 Creando carpeta '{new_folder_name}' dentro de 'Facturacion'..."))

        # Crear carpeta de prueba dentro de Facturacion
        new_folder_id = create_folder_with_service_account(new_folder_name, facturacion_id)

        if new_folder_id:
            self.stdout.write(self.style.SUCCESS(f"✅ Carpeta '{new_folder_name}' creada con ID: {new_folder_id}"))
        else:
            self.stdout.write(self.style.ERROR("❌ No se pudo crear la carpeta."))
