from django.core.management.base import BaseCommand
from django.db import transaction

from core.operations_panel.models import Operation, Route


class Command(BaseCommand):
    help = "Duplica rutas en operaciones desde un folio dado"

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-folio",
            type=str,
            required=True,
            help="Folio inicial (ej: G1240)"
        )

    def handle(self, *args, **options):
        from_folio = options["from_folio"]

        # Extraer número
        try:
            prefix = from_folio[0]
            start_number = int(from_folio[1:])
        except Exception:
            self.stdout.write(self.style.ERROR("Formato de folio inválido"))
            return

        operations = Operation.objects.exclude(route__isnull=True)

        total = operations.count()
        processed = 0
        print(total)

        for op in operations:
            if not op.folio:
                continue

            try:
                op_prefix = op.folio[0]
                op_number = int(op.folio[1:])
            except Exception:
                continue

            # Filtrar desde G1240 en adelante
            if op_prefix != prefix or op_number < start_number:
                continue

            with transaction.atomic():
                print(op.folio)
                original_route = op.route

                # Guardar stops
                stops = list(original_route.route_stops.all())

                # Clonar ruta
                new_route = Route.objects.get(pk=original_route.pk)
                new_route.pk = None
                new_route.id = None
                new_route.name = f"{op.folio}"
                new_route.published = False
                new_route.save()

                # Copiar M2M
                new_route.route_stops.set(stops)

                # Asignar nueva ruta a la operación
                op.route = new_route
                op.save(update_fields=["route"])

                processed += 1

                self.stdout.write(
                    self.style.SUCCESS(f"Operación {op.folio} actualizada")
                )

        self.stdout.write(
            self.style.WARNING(f"\nProcesadas: {processed} de {total}")
        )