from django.core.management.base import BaseCommand

from core.operations_panel.models.address import Address


class Command(BaseCommand):
    help = "ELIMINA TODAS LAS DIRECCIONES DE LA BASE DE DATOS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Elimina todas las direcciones sin pedir confirmación.",
        )

    def handle(self, *args, **options):
        if not options["force"]:
            confirm = input("⚠ ¿ESTÁS SEGURO DE QUE DESEAS ELIMINAR TODAS LAS DIRECCIONES? (S/N): ").strip().upper()
            if confirm != "S":
                self.stdout.write(self.style.WARNING("❎ OPERACIÓN CANCELADA."))
                return

        count = Address.objects.count()
        Address.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"✅ {count} DIRECCIONES ELIMINADAS CORRECTAMENTE."))