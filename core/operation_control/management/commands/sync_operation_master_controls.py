from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.models import F, Q

from core.operations_panel.models.operation import Operation
from core.operation_control.models import OperationMasterControl


class Command(BaseCommand):
    help = (
        "Crea registros faltantes de OperationMasterControl para operaciones existentes.\n"
        "Por defecto procesa las últimas 20 operaciones (por fecha de operación desc, luego id desc)\n"
        "que aún no tienen su control maestro. Usa --limit para cambiar el número.\n"
        "Opcionalmente filtra por --since YYYY-MM-DD. Soporta --dry-run.\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=2,
            help="Número máximo de operaciones a procesar (default: 20)",
        )
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Fecha mínima (YYYY-MM-DD) para filtrar por operation_date",
        )
        parser.add_argument(
            "--created-by",
            type=int,
            dest="created_by",
            default=None,
            help="User ID para usar como 'created_by' si la operación no lo tiene",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que haría sin escribir cambios",
        )

    def handle(self, *args, **options):
        limit: int = options["limit"]
        since_str: Optional[str] = options.get("since")
        created_by_id: Optional[int] = options.get("created_by")
        dry_run: bool = options.get("dry_run", False)

        if limit <= 0:
            raise CommandError("--limit debe ser mayor que 0")

        fallback_user = None
        if created_by_id is not None:
            User = get_user_model()
            try:
                fallback_user = User.objects.get(pk=created_by_id)
            except User.DoesNotExist:
                raise CommandError(f"No existe el usuario con id={created_by_id}")

        # Construir queryset base
        qs = Operation.objects.all()

        # Filtro opcional por fecha mínima
        if since_str:
            try:
                since_dt = datetime.strptime(since_str, "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("--since debe tener el formato YYYY-MM-DD")
            qs = qs.filter(operation_date__gte=since_dt)

        # Ordenar por fecha desc (nulls_last) y luego por id desc
        qs = qs.order_by(F("operation_date").desc(nulls_last=True), "-id")

        # Excluir operaciones que ya tienen control
        qs = qs.filter(~Q(master_control__isnull=False))

        # Limitar a N candidatos
        candidates = list(qs[:limit])

        if not candidates:
            self.stdout.write(self.style.WARNING("No hay operaciones candidatas para crear control maestro."))
            return

        created = 0
        skipped = 0
        errors = 0

        for op in candidates:
            # Idempotencia adicional
            if hasattr(op, "master_control") and getattr(op, "master_control_id", None):
                skipped += 1
                continue

            defaults = {"created_by": getattr(op, "created_by", None) or fallback_user}

            self.stdout.write(f"Procesando operación id={op.id} folio={getattr(op, 'folio', None)}…")
            if dry_run:
                self.stdout.write("  DRY-RUN: se crearía OperationMasterControl(...) con defaults=" + str(defaults))
                continue

            try:
                obj, was_created = OperationMasterControl.objects.get_or_create(
                    operation=op,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"  Creado control maestro id={obj.id}"))
                else:
                    skipped += 1
                    self.stdout.write(self.style.WARNING("  Ya existía, omitido"))
            except Exception as exc:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  Error: {exc}"))

        if dry_run:
            self.stdout.write(self.style.NOTICE if hasattr(self.style, 'NOTICE') else self.style.WARNING)(
                f"DRY-RUN finalizado. Candidatos: {len(candidates)} (no se crearon registros)."
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Finalizado. Creados={created}, Omitidos={skipped}, Errores={errors}"))
