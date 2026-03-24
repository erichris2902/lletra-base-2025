import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Generator, Iterable, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.utils.dateparse import parse_date, parse_datetime

from apps.facturapi.choices import VehicleConfig
from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.choices import MEXICAN_STATES
from core.operations_panel.models import Client, Supplier, Vehicle, Driver, DeliveryLocation, Route, TransportedProduct, \
    Operation
from core.operations_panel.models.address import Address

BATCH_SIZE_DEFAULT = 1000


class Command(BaseCommand):
    help = "Migra datos de un dump SQL legacy de PostgreSQL hacia los modelos nuevos"

    def add_arguments(self, parser):
        parser.add_argument("sql_file", type=str, help="Ruta al archivo .sql")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=BATCH_SIZE_DEFAULT,
            help="Tamaño de lote para bulk_create",
        )
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Migrando Unit legacy -> Vehicle nuevo ..."))
        sql_file = options["sql_file"]

        try:
            with open(sql_file, "r", encoding="latin1") as f:
                sql_text = f.read()
        except FileNotFoundError:
            raise CommandError(f"No existe el archivo: {sql_file}")

        rows = list(self.extract_table_rows(sql_text, "operation"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'unit'."))
            return

        print(rows)
        dict = []
        for row in rows:
            dict.append({
                "vehicular_control": row["vehicular_control"],
                "cartaporte_folio": row["cartaporte_folio"],
            })
        print(dict)

        for item in dict:
            try:
                invoice = FacturapiInvoice.objects.get(folio_number=item["cartaporte_folio"])
                operation = Operation.objects.get(folio=item["vehicular_control"])
                #operation.ship
            except Exception as e:
                print(e)
                print(item["vehicular_control"])
                print("-------------------")
        raise Exception("Hola")

        supplier_map = {
            old_id: pk
            for pk, old_id in Supplier.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if True:
            existing_old_ids = set(
                Vehicle.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
            )

        processed_old_ids = set()

        to_create = []
        created = 0
        skipped = 0
        errors = 0

        for row in rows:
            try:
                old_id = self.to_int(row.get("id"))
                if old_id is None:
                    skipped += 1
                    continue

                if skip_existing and old_id in existing_old_ids:
                    skipped += 1
                    continue

                if old_id in processed_old_ids:
                    skipped += 1
                    continue

                processed_old_ids.add(old_id)

                legacy_supplier_id = self.to_int(row.get("supplier_id"))
                supplier_id = supplier_map.get(legacy_supplier_id)

                instance = Vehicle(
                    old_id=old_id,
                    econ_number=self.clean_str(row.get("econ_number")) or f"UNIT-{old_id}",
                    model=self.clean_str(row.get("model")) or "",
                    brand=self.clean_str(row.get("brand")) or "",
                    year=self.clean_positive_int(row.get("year"), default=2000),

                    circulation_card_number=self.clean_str(row.get("circulation_card_number")) or "",
                    serial_number=self.clean_str(row.get("serial_number")) or "",
                    license_plate=self.clean_str(row.get("license_plate")) or "",
                    sct_permit=self.clean_str(row.get("permiso_sct")) or "",

                    insurance_company=self.clean_str(row.get("insurance_company")) or "",
                    insurance_code=self.clean_str(row.get("insurance_code")) or "",

                    vehicle_config=self.map_vehicle_config(row.get("conf_vehicular")),
                    status=self.map_unit_status(row.get("status")),
                    supplier_id=supplier_id,
                    unit_type=self.map_unit_type(row.get("unit_type")),
                    notes=self.clean_str(row.get("observations")),

                    created_at=self.parse_legacy_datetime(
                        row.get("date_updated"),
                        fallback=datetime.now(),
                    ),
                    updated_at=self.parse_legacy_datetime(
                        row.get("date_created"),
                        fallback=datetime.now(),
                    ),
                )
                to_create.append(instance)

                if len(to_create) >= batch_size:
                    Vehicle.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"Vehicles creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Unit old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Vehicle.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Unit legacy -> Vehicle nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    def extract_table_rows(self, sql_text: str, table_name: str):
        copy_rows = list(self.extract_copy_rows(sql_text, table_name))
        if copy_rows:
            for row in copy_rows:
                yield row
            return

        insert_rows = list(self.extract_insert_rows(sql_text, table_name))
        for row in insert_rows:
            yield row

    def extract_copy_rows(self, sql_text: str, table_name: str):
        import re

        patterns = [
            rf'COPY\s+public\.{re.escape(table_name)}\s*\((.*?)\)\s+FROM\s+stdin;\s*\n(.*?)\n\\\.',
            rf'COPY\s+"public"\."{re.escape(table_name)}"\s*\((.*?)\)\s+FROM\s+stdin;\s*\n(.*?)\n\\\.',
            rf'COPY\s+(?:"public"\.)?"?{re.escape(table_name)}"?\s*\((.*?)\)\s+FROM\s+stdin;\s*\n(.*?)\n\\\.',
        ]

        for pattern_str in patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE | re.DOTALL)
            matches = pattern.findall(sql_text)

            for columns_str, data_block in matches:
                columns = [c.strip().strip('"') for c in columns_str.split(",")]

                for raw_line in data_block.splitlines():
                    if not raw_line.strip():
                        continue

                    values = raw_line.split("\t")
                    row = {}
                    for col, val in zip(columns, values):
                        row[col] = self.parse_copy_value(val)
                    yield row


    def parse_copy_value(self, value: str):
        if value == r"\N":
            return None
        return value
