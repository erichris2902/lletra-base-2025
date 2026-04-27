import json
import unicodedata
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from core.operations_panel.models import Operation


def normalize(value):
    if value is None:
        return ""
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.split())


def parse_json_date(value):
    if not value:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


class Command(BaseCommand):
    help = "Actualiza cantidad de repartos en operaciones usando JSON externo"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str)

    def handle(self, *args, **options):
        json_path = options["json_path"]

        with open(json_path, "r", encoding="utf-8") as file:
            records = json.load(file)

        updated = 0
        not_found = 0
        ambiguous = 0

        with transaction.atomic():
            for item in records:
                destino = normalize(item.get("destino"))
                proveedor = normalize(item.get("proveedor"))
                fecha = parse_json_date(item.get("fecha"))
                repartos = item.get("cantidad_de_repartos")

                if not destino or not proveedor or not fecha:
                    not_found += 1
                    self.stdout.write(
                        self.style.WARNING(f"Registro incompleto: {item}")
                    )
                    continue

                qs = Operation.objects.filter(
                    client__name='CHEM-TREND COMERCIAL',
                    operation_date=fecha,
                )

                matches = []

                for operation in qs:
                    payload = operation.raw_payload or {}

                    op_destino = normalize(payload.get("destino"))
                    op_proveedor = normalize(payload.get("proveedor"))

                    if op_destino == destino and op_proveedor == proveedor:
                        matches.append(operation)

                if len(matches) == 1:
                    operation = matches[0]
                    old_value = operation.deliveries_amount

                    operation.deliveries_amount = repartos
                    operation.save(update_fields=["deliveries_amount"])

                    updated += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"OK Operation {operation.id}: "
                            f"{old_value} -> {repartos}"
                        )
                    )

                elif len(matches) > 1:
                    ambiguous += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Ambiguo: {fecha} | {destino} | {proveedor} "
                            f"coincide con {[op.id for op in matches]}"
                        )
                    )

                else:
                    not_found += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"No encontrado: {fecha} | {destino} | {proveedor} -> {repartos}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write(f"Actualizados: {updated}")
        self.stdout.write(f"No encontrados: {not_found}")
        self.stdout.write(f"Ambiguos: {ambiguous}")