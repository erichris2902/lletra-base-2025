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
        parser.add_argument(
            "--only",
            type=str,
            choices=[
                "address",
                "client",
                "delivery_location",
                "driver",
                "route",
                "supplier",
                "transported_product",
                "vehicle",
                "operation",
                "all",
            ],
            default="all",
            help="Migrar solo addresses, clients, suppliers, vehicles, drivers, delivery_locations, routes, transported_products o todo",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Omite registros que ya existan por old_id",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Limpia las tablas destino antes de importar",
        )

    def handle(self, *args, **options):
        flush = options["flush"]
        sql_file = options["sql_file"]
        batch_size = options["batch_size"]
        only = options["only"]
        skip_existing = options["skip_existing"]
        if flush:
            self.flush_target_tables(only=only)

        try:
            with open(sql_file, "r", encoding="latin1") as f:
                sql_text = f.read()
        except FileNotFoundError:
            raise CommandError(f"No existe el archivo: {sql_file}")

        self.stdout.write(self.style.NOTICE("Iniciando migración legacy..."))

        if only in ("address", "all"):
            self.migrate_addresses(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("client", "all"):
            self.migrate_clients(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("supplier", "all"):
            self.migrate_suppliers(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("vehicle", "all"):
            self.migrate_vehicles(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("driver", "all"):
            self.migrate_drivers(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("delivery_location", "all"):
            self.migrate_delivery_locations(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("route", "all"):
            self.migrate_routes(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("transported_product", "all"):
            self.migrate_transported_products(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        if only in ("operation", "all"):
            self.migrate_operations(
                sql_text=sql_text,
                batch_size=batch_size,
                skip_existing=skip_existing,
            )

        self.stdout.write(self.style.SUCCESS("Migración finalizada."))

    def flush_target_tables(self, only="all"):
        self.stdout.write(self.style.WARNING("Limpiando tablas destino..."))

        with transaction.atomic():
            with connection.cursor() as cursor:
                if only in ("supplier", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Supplier._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("Suppliers eliminados."))

                if only in ("client", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Client._meta.db_table}" RESTART IDENTITY;')
                    self.stdout.write(self.style.WARNING("Clients eliminados."))

                if only in ("address", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Address._meta.db_table}" RESTART IDENTITY;')
                    self.stdout.write(self.style.WARNING("Addresses eliminados."))

                if only in ("vehicle", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Vehicle._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("Vehicles eliminados."))

                if only in ("driver", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Driver._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("Drivers eliminados."))

                if only in ("delivery_location", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{DeliveryLocation._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("DeliveryLocations eliminados."))

                if only in ("route", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Route._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("Routes eliminadas."))

                if only in ("transported_product", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{TransportedProduct._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("TransportedProducts eliminados."))

                if only in ("operation", "all"):
                    cursor.execute(f'TRUNCATE TABLE "{Operation._meta.db_table}" RESTART IDENTITY CASCADE;')
                    self.stdout.write(self.style.WARNING("Operations eliminadas."))

        self.stdout.write(self.style.SUCCESS("Limpieza completada."))

    # =========================================================
    # OPERATION MIGRATION
    # =========================================================
    def migrate_operations(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Operation legacy -> Operation nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "operation"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'operation'."))
            return

        # Tabla auxiliar: OperationClosed
        operation_closed_rows = list(self.extract_table_rows(sql_text, "operationclosed"))

        operation_closed_map = self.build_operation_closed_map(operation_closed_rows)

        client_map = {
            old_id: pk
            for pk, old_id in Client.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        client_name_map = {
            pk: name
            for pk, name in Client.objects.values_list("pk", "name")
        }

        driver_map = {
            old_id: pk
            for pk, old_id in Driver.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        vehicle_map = {
            old_id: pk
            for pk, old_id in Vehicle.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        vehicle_supplier_map = {
            pk: supplier_id
            for pk, supplier_id in Vehicle.objects.values_list("pk", "supplier_id")
        }

        vehicle_unit_type_map = {
            pk: unit_type
            for pk, unit_type in Vehicle.objects.values_list("pk", "unit_type")
        }

        route_map = {
            old_id: pk
            for pk, old_id in Route.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                Operation.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
            )

        existing_folios = set(
            Operation.objects.exclude(folio__isnull=True).values_list("folio", flat=True)
        )

        existing_pre_folios = set(
            Operation.objects.exclude(pre_folio__isnull=True).values_list("pre_folio", flat=True)
        )

        processed_old_ids = set()
        processed_folios = set()
        processed_pre_folios = set()

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

                legacy_client_id = self.to_int(row.get("client_id"))
                legacy_operator_id = self.to_int(row.get("operator_id"))
                legacy_unit_id = self.to_int(row.get("unit_id"))
                legacy_caja_id = self.to_int(row.get("caja_id"))
                legacy_route_id = self.to_int(row.get("route_id"))

                client_id = client_map.get(legacy_client_id)
                driver_id = driver_map.get(legacy_operator_id)
                vehicle_id = vehicle_map.get(legacy_unit_id)
                vehicle_box_id = vehicle_map.get(legacy_caja_id)
                route_id = route_map.get(legacy_route_id)

                raw_vehicular_control = self.clean_str(row.get("vehicular_control"))
                raw_cartaporte = self.clean_str(row.get("cartaporte_folio"))

                folio = raw_vehicular_control[:10]

                closed_row = operation_closed_map.get((raw_vehicular_control or "").strip().lower())

                supplier_id = vehicle_supplier_map.get(vehicle_id)
                need_cartaporte = bool(raw_cartaporte)

                shipment_type = self.resolve_shipment_type(
                    client_id=client_id,
                    closed_row=closed_row,
                    client_name_map=client_name_map,
                )

                vehicle_type = self.resolve_operation_vehicle_type(
                    vehicle_id=vehicle_id,
                    closed_row=closed_row,
                    vehicle_unit_type_map=vehicle_unit_type_map,
                )

                status = self.resolve_operation_status(closed_row=closed_row)

                operation_date = self.parse_legacy_date(
                    row.get("date_joined"),
                    fallback=self.parse_legacy_date(
                        closed_row.get("date") if closed_row else None,
                        fallback=datetime.now().date(),
                    ),
                )

                instance = Operation(
                    old_id=old_id,
                    folio=folio,
                    pre_folio=folio,
                    client_id=client_id,
                    supplier_id=supplier_id,
                    driver_id=driver_id,
                    vehicle_id=vehicle_id,
                    vehicle_box_id=vehicle_box_id,
                    vehicle_type=vehicle_type,
                    operation_date=operation_date,
                    shipment_type=shipment_type,
                    status=status,
                    notes="",
                    need_cartaporte=need_cartaporte,
                    is_rent=self.to_bool(row.get("is_rent")),
                    is_packing_ready=False,
                    cargo_appointment=self.parse_legacy_datetime(row.get("cargo_appointment")),
                    download_appointment=self.parse_legacy_datetime(row.get("download_appointment")),
                    scheduled_departure_time=self.parse_legacy_datetime(row.get("scheduled_departure_time")),
                    cargo_id=None,
                    route_id=route_id,
                    total=self.to_decimal_value(closed_row.get("costo_sin_impuestos") if closed_row else None,
                                                default=0),
                    handling_amount=self.clean_positive_int(closed_row.get("maniobras") if closed_row else None,
                                                            default=0),
                    created_at=self.parse_legacy_datetime(
                        row.get("date_updated"),
                        fallback=self.parse_legacy_datetime(
                            closed_row.get("date_updated") if closed_row else None,
                            fallback=datetime.now(),
                        ),
                    ),
                    updated_at=self.parse_legacy_datetime(
                        row.get("date_created"),
                        fallback=self.parse_legacy_datetime(
                            closed_row.get("date_created") if closed_row else None,
                            fallback=datetime.now(),
                        ),
                    ),
                )
                to_create.append(instance)

                processed_old_ids.add(old_id)
                if folio:
                    processed_folios.add(folio)

                if len(to_create) >= batch_size:
                    try:
                        Operation.objects.bulk_create(to_create, batch_size=batch_size)
                        created += len(to_create)
                        self.stdout.write(f"Operations creadas: {created}")
                        to_create = []
                    except Exception as e:
                        print(e)

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Operation old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Operation.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Operation legacy -> Operation nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

        self.attach_operation_transported_products(sql_text=sql_text)

    # =========================================================
    # TRANSPORTED PRODUCT MIGRATION
    # =========================================================
    def migrate_transported_products(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando TransportedProduct legacy -> TransportedProduct nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "transportedproduct"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'transportedproduct'."))
            return

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                TransportedProduct.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
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

                instance = TransportedProduct(
                    old_id=old_id,
                    transported_product_key=(self.clean_str(row.get("BienesTransp")) or "")[:100],
                    unit_key=(self.clean_str(row.get("ClaveUnidad")) or "")[:100],
                    description=(self.clean_str(row.get("Descripcion")) or "")[:100],
                    currency=(self.clean_str(row.get("Moneda")) or "MXN")[:100],
                    is_danger=self.to_bool(row.get("MaterialPeligroso")),
                    weight=self.to_float(row.get("PesoEnKg"), default=0.0),
                    amount=self.clean_positive_int(row.get("Cantidad"), default=0),
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
                    TransportedProduct.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"TransportedProducts creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[TransportedProduct old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            TransportedProduct.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"TransportedProduct legacy -> TransportedProduct nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # ROUTE MIGRATION
    # =========================================================
    def migrate_routes(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Route legacy -> Route nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "route"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'route'."))
            return

        delivery_location_map = {
            old_id: pk
            for pk, old_id in DeliveryLocation.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                Route.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
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

                origin_old_id = self.to_int(row.get("origin_id"))
                destiny_old_id = self.to_int(row.get("destiny_id"))

                initial_location_id = delivery_location_map.get(origin_old_id)
                destination_location_id = delivery_location_map.get(destiny_old_id)

                # initial_location es requerido
                if not initial_location_id:
                    skipped += 1
                    continue

                processed_old_ids.add(old_id)

                direct_distance = self.to_int(row.get("kilometros")) or 0

                instance = Route(
                    old_id=old_id,
                    name=self.build_route_name(
                        old_id=old_id
                    ),
                    initial_location_id=initial_location_id,
                    destination_location_id=destination_location_id,
                    notes=None,
                    direct_distance=direct_distance,
                    optimized_distance=direct_distance,
                    published=False,
                    optimized_route=None,
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
                    Route.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"Routes creadas: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Route old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Route.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Route legacy -> Route nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # DELIVERY LOCATION MIGRATION
    # =========================================================
    def migrate_delivery_locations(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando DeliveryLocation legacy -> DeliveryLocation nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "deliverylocation"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'deliverylocation'."))
            return

        address_map = {
            old_id: pk
            for pk, old_id in Address.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                DeliveryLocation.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
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

                legacy_direction_id = self.to_int(row.get("direction_id"))
                address_id = address_map.get(legacy_direction_id)

                instance = DeliveryLocation(
                    old_id=old_id,
                    name=self.clean_str(row.get("name")) or f"DELIVERY-{old_id}",
                    business_name=self.clean_str(row.get("bussines_name")) or "",
                    rfc=self.clean_rfc(row.get("rfc")),
                    address_id=address_id,
                    notes=self.clean_str(row.get("comments_on_delivery")),
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
                    DeliveryLocation.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"DeliveryLocations creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[DeliveryLocation old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            DeliveryLocation.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"DeliveryLocation legacy -> DeliveryLocation nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # DRIVER MIGRATION
    # =========================================================
    def migrate_drivers(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Operator legacy -> Driver nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "operator"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'operator'."))
            return

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                Driver.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
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

                instance = Driver(
                    old_id=old_id,
                    name=self.clean_str(row.get("name")) or "",
                    last_name=self.clean_str(row.get("last_name")) or "",
                    mother_last_name=self.clean_str(row.get("mother_last_name")) or "",
                    rfc=self.clean_rfc(row.get("rfc")),
                    license_number=self.clean_license_number(row.get("licence_number")),
                    license_type=self.clean_license_type(row.get("licence_type")),
                    license_expiration=self.parse_legacy_date(
                        row.get("licence_expiration"),
                        fallback=self.default_license_expiration(),
                    ),
                    notes="",
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
                    Driver.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"Drivers creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Operator old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Driver.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Operator legacy -> Driver nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # VEHICLE MIGRATION
    # =========================================================
    def migrate_vehicles(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Unit legacy -> Vehicle nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "units"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'unit'."))
            return

        supplier_map = {
            old_id: pk
            for pk, old_id in Supplier.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if skip_existing:
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

    # =========================================================
    # SUPPLIER MIGRATION
    # =========================================================
    def migrate_suppliers(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Supplier legacy -> Supplier nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "supplier"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'supplier'."))
            return

        address_map = {
            old_id: pk
            for pk, old_id in Address.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                Supplier.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
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

                legacy_direction_id = self.to_int(row.get("direction_id"))
                address_id = address_map.get(legacy_direction_id)

                instance = Supplier(
                    old_id=old_id,
                    code=self.clean_str(row.get("comercial_name")) or f"SUP-{old_id}",
                    business_name=self.clean_str(row.get("business_name")) or "",
                    tax_regime=self.map_tax_regime(row.get("regimen_fiscal")),
                    rfc=self.clean_rfc(row.get("rfc")),
                    email=self.clean_email(row.get("email")),
                    phone=self.clean_str(row.get("tel")) or "",
                    bank=self.clean_str(row.get("banco")) or "",
                    clabe=self.clean_clabe(row.get("clave_interbancaria")),
                    address_id=address_id,
                    status=self.map_supplier_status(row.get("status")),
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
                    Supplier.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"Suppliers creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Supplier old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Supplier.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Supplier legacy -> Supplier nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # ADDRESS MIGRATION
    # =========================================================
    def migrate_addresses(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Direction -> Address ..."))

        rows = list(self.extract_table_rows(sql_text, "direction"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'direction'."))
            return

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                Address.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
            )

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

                instance = Address(
                    old_id=old_id,
                    street=self.clean_str(row.get("street")),
                    exterior_number=self.clean_str(row.get("exterior_number")),
                    interior_number=self.clean_str(row.get("interior_number")),
                    colony=self.clean_str(row.get("colony")),
                    city=self.clean_str(row.get("city")),
                    state=self.map_state(row.get("state")) or "Queretaro de Arteaga",
                    zip_code=self.clean_zip_code(row.get("cp")),
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
                    Address.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"Address creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Direction old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Address.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Direction -> Address completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # CLIENT MIGRATION
    # =========================================================
    def migrate_clients(self, sql_text: str, batch_size: int, skip_existing: bool):
        self.stdout.write(self.style.NOTICE("Migrando Client legacy -> Client nuevo ..."))

        rows = list(self.extract_table_rows(sql_text, "client"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron datos para la tabla legacy 'client'."))
            return

        address_map = {
            old_id: pk
            for pk, old_id in Address.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        existing_old_ids = set()
        if skip_existing:
            existing_old_ids = set(
                Client.objects.exclude(old_id__isnull=True).values_list("old_id", flat=True)
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

                legacy_direction_id = self.to_int(row.get("direction_id"))
                address_id = address_map.get(legacy_direction_id)

                instance = Client(
                    old_id=old_id,
                    name=self.clean_str(row.get("comercial_name")) or "",
                    business_name=self.clean_str(row.get("business_name")) or "",
                    rfc=self.clean_str(row.get("rfc")),
                    address_id=address_id,
                    email=self.clean_str(row.get("email")) or "",
                    phone=self.clean_str(row.get("tel")) or "",
                    tax_regime=self.map_tax_regime(row.get("regimen_fiscal")),
                    notes=None,
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
                    Client.objects.bulk_create(to_create, batch_size=batch_size)
                    created += len(to_create)
                    self.stdout.write(f"Clients creados: {created}")
                    to_create = []

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.WARNING(f"[Client old_id={row.get('id')}] Error: {exc}")
                )

        if to_create:
            Client.objects.bulk_create(to_create, batch_size=batch_size)
            created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Client legacy -> Client nuevo completado | creados={created}, omitidos={skipped}, errores={errors}"
            )
        )

    # =========================================================
    # SQL PARSING
    # =========================================================
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

    def extract_insert_rows(self, sql_text: str, table_name: str) -> Generator[Dict[str, object], None, None]:
        pattern = re.compile(
            rf"INSERT INTO\s+(?:public\.)?{re.escape(table_name)}\s*\((.*?)\)\s+VALUES\s*(.*?);",
            re.IGNORECASE | re.DOTALL,
        )
        matches = pattern.findall(sql_text)

        for columns_str, values_block in matches:
            columns = [c.strip().strip('"') for c in columns_str.split(",")]
            tuple_strings = self.split_sql_tuples(values_block)

            for tuple_str in tuple_strings:
                values = self.parse_sql_tuple(tuple_str)
                row = {}
                for col, val in zip(columns, values):
                    row[col] = val
                yield row

    def split_sql_tuples(self, values_block: str) -> List[str]:
        tuples_ = []
        current = []
        depth = 0
        in_string = False
        i = 0

        while i < len(values_block):
            ch = values_block[i]

            if ch == "'" and not self.is_escaped_quote(values_block, i):
                in_string = not in_string
                current.append(ch)
            elif not in_string:
                if ch == "(":
                    depth += 1
                    current.append(ch)
                elif ch == ")":
                    depth -= 1
                    current.append(ch)
                    if depth == 0:
                        tuples_.append("".join(current).strip())
                        current = []
                elif ch == "," and depth == 0:
                    pass
                else:
                    if depth > 0 or not ch.isspace():
                        current.append(ch)
            else:
                current.append(ch)

            i += 1

        return tuples_

    def parse_sql_tuple(self, tuple_str: str) -> List[object]:
        content = tuple_str.strip()
        if content.startswith("(") and content.endswith(")"):
            content = content[1:-1]

        reader = csv.reader(
            io.StringIO(content),
            delimiter=",",
            quotechar="'",
            escapechar="\\",
            skipinitialspace=True,
        )
        raw_values = next(reader)
        return [self.parse_insert_value(v) for v in raw_values]

    def parse_copy_value(self, value: str):
        if value == r"\N":
            return None
        return value

    def parse_insert_value(self, value: str):
        v = value.strip()

        if v.upper() == "NULL":
            return None

        if v.lower() in ("true", "false"):
            return v.lower() == "true"

        if re.fullmatch(r"-?\d+", v):
            try:
                return int(v)
            except ValueError:
                return v

        if re.fullmatch(r"-?\d+\.\d+", v):
            try:
                return Decimal(v)
            except Exception:
                return v

        return v

    def is_escaped_quote(self, text: str, index: int) -> bool:
        backslashes = 0
        j = index - 1
        while j >= 0 and text[j] == "\\":
            backslashes += 1
            j -= 1
        return backslashes % 2 == 1

    # =========================================================
    # HELPERS
    # =========================================================
    def clean_str(self, value) -> Optional[str]:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def clean_zip_code(self, value) -> str:
        value = self.clean_str(value)
        return value or "00000"

    def to_int(self, value) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def parse_legacy_datetime(self, value, fallback=None):
        if value in (None, ""):
            return fallback

        if isinstance(value, datetime):
            return value

        parsed = parse_datetime(str(value))
        if parsed:
            return parsed

        # fallback común para fechas sin timezone
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(str(value), fmt)
                return dt
            except ValueError:
                continue

        return fallback

    def map_state(self, legacy_state):
        default_state = "Queretaro de Arteaga"

        state = self.clean_str(legacy_state)
        if not state:
            return default_state

        # valores válidos exactos del modelo nuevo
        valid_states = {value for value, _label in MEXICAN_STATES if value}

        if state in valid_states:
            return state

        normalized = (
            state.strip()
            .lower()
            .replace(".", "")
        )

        alias_map = {
            "aguascalientes": "Aguascalientes",
            "baja california": "Baja California",
            "baja california sur": "Baja California Sur",
            "campeche": "Campeche",
            "chiapas": "Chiapas",
            "chihuahua": "Chihuahua",
            "coahuila": "Coahuila  de Zaragoza",
            "coahuila de zaragoza": "Coahuila  de Zaragoza",
            "colima": "Colima",
            "ciudad de mexico": "Ciudad de México",
            "ciudad de méxico": "Ciudad de México",
            "cdmx": "Cdmx",
            "dif": "Cdmx",
            "durango": "Durango",
            "guanajuato": "Guanajuato",
            "guerrero": "Guerrero",
            "hidalgo": "Hidalgo",
            "jalisco": "Jalisco",
            "mexico": "Mexico",
            "edo mexico": "Mexico",
            "estado de mexico": "Mexico",
            "edomex": "Mexico",
            "michoacan": "Michoacan de Ocampo",
            "michoacán": "Michoacan de Ocampo",
            "michoacan de ocampo": "Michoacan de Ocampo",
            "michoacán de ocampo": "Michoacan de Ocampo",
            "morelos": "Morelos",
            "nayarit": "Nayarit",
            "nuevo leon": "Nuevo Leon",
            "nuevo león": "Nuevo Leon",
            "oaxaca": "Oaxaca",
            "puebla": "Puebla",
            "queretaro": "Queretaro de Arteaga",
            "querétaro": "Queretaro de Arteaga",
            "queretaro de arteaga": "Queretaro de Arteaga",
            "querétaro de arteaga": "Queretaro de Arteaga",
            "quintana roo": "Quintana",
            "quintana": "Quintana",
            "san luis potosi": "San Luis Potosi",
            "san luis potosí": "San Luis Potosi",
            "sinaloa": "Sinaloa",
            "sonora": "Sonora",
            "tabasco": "Tabasco",
            "tamaulipas": "Tamaulipas",
            "tlaxcala": "Tlaxcala",
            "veracruz": "Veracruz",
            "yucatan": "Yucatan",
            "yucatán": "Yucatan",
            "zacatecas": "Zacatecas",
        }

        mapped = alias_map.get(normalized)
        if mapped in valid_states:
            return mapped

        return default_state

    def map_tax_regime(self, legacy_value: Optional[str]) -> str:
        """
        Aquí debes ajustar el mapeo real entre:
        RegimenFiscal (viejo) -> TaxRegime (nuevo)
        """
        value = self.clean_str(legacy_value)

        return value

    def clean_email(self, value) -> str:
        value = self.clean_str(value)
        if not value:
            return "sin-correo@example.com"

        # En legacy a veces vienen varios correos separados por coma
        first_email = value.split(",")[0].strip()

        # fallback muy básico para evitar romper EmailField
        if "@" not in first_email:
            return "sin-correo@example.com"

        return first_email[:254]

    def clean_rfc(self, value) -> str:
        value = self.clean_str(value)
        if not value:
            return "XAXX010101000"
        return value[:13]

    def clean_clabe(self, value) -> str:
        value = self.clean_str(value)
        if not value:
            return ""

        # deja solo dígitos
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits[:18]

    def map_supplier_status(self, legacy_value: Optional[str]) -> str:
        value = self.clean_str(legacy_value)

        return value

    def clean_positive_int(self, value, default=0) -> int:
        number = self.to_int(value)
        if number is None or number < 0:
            return default
        return number

    def map_vehicle_config(self, legacy_value: Optional[str]) -> str:
        value = self.clean_str(legacy_value)

        if not value:
            return VehicleConfig.PENDING

        return value

    def map_unit_status(self, legacy_value: Optional[str]) -> str:
        value = self.clean_str(legacy_value)

        return value

    def map_unit_type(self, legacy_value: Optional[str]) -> str:
        value = self.clean_str(legacy_value)

        return value

    def parse_legacy_date(self, value, fallback=None):
        if value in (None, ""):
            return fallback

        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            # date o datetime
            try:
                return value.date() if isinstance(value, datetime) else value
            except Exception:
                pass

        parsed = parse_date(str(value))
        if parsed:
            return parsed

        parsed_dt = parse_datetime(str(value))
        if parsed_dt:
            return parsed_dt.date()

        for fmt in (
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(str(value), fmt)
                return dt.date()
            except ValueError:
                continue

        return fallback

    def default_license_expiration(self):
        return datetime.now().date()

    def default_license_expiration(self):
        return datetime(2099, 12, 31).date()

    def clean_license_number(self, value) -> str:
        value = self.clean_str(value)
        if not value:
            return ""
        return value[:20]

    def clean_license_type(self, value) -> str:
        value = self.clean_str(value)
        if not value:
            return ""
        return value[:20]

    def build_route_name(self, old_id) -> str:
        name = f"{'OLD'}-{old_id}"
        return name

    def to_float(self, value, default=0.0) -> float:
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def to_bool(self, value) -> bool:
        if isinstance(value, bool):
            return value

        if value in (None, ""):
            return False

        normalized = str(value).strip().lower()
        return normalized in ("true", "1", "t", "yes", "y", "si", "sí")

    def infer_vehicle_type(self, vehicle_id):
        if not vehicle_id:
            return None

        try:
            vehicle = Vehicle.objects.filter(pk=vehicle_id).only("unit_type").first()
            return vehicle.unit_type if vehicle else None
        except Exception:
            return None

    def build_operation_closed_map(self, rows):
        result = {}

        for row in rows:
            key = self.clean_str(row.get("vehicular_control"))
            if not key:
                continue

            normalized_key = key.strip().lower()

            current = result.get(normalized_key)
            if current is None:
                result[normalized_key] = row
                continue

            current_dt = self.parse_legacy_datetime(current.get("date_created"))
            new_dt = self.parse_legacy_datetime(row.get("date_created"))

            if new_dt and (not current_dt or new_dt > current_dt):
                result[normalized_key] = row

        return result

    def resolve_shipment_type(self, client_id, closed_row, client_name_map: dict) -> str:
        candidates = []

        if closed_row:
            closed_client = self.clean_str(closed_row.get("cliente"))
            if closed_client:
                candidates.append(closed_client)

        if client_id:
            client_name = client_name_map.get(client_id)
            if client_name:
                candidates.append(client_name)

        for candidate in candidates:
            normalized = candidate.strip().lower()

            if "3b" in normalized:
                return "3B"
            if "astur" in normalized:
                return "ASTURIANO"
            if "chem" in normalized:
                return "CHEM"

        return "GENERAL"

    def resolve_operation_vehicle_type(self, vehicle_id, closed_row, vehicle_unit_type_map: dict):
        if closed_row:
            closed_unidad = self.clean_str(closed_row.get("unidad"))
            mapped = self.map_unit_type(closed_unidad)
            if mapped:
                return mapped

        return vehicle_unit_type_map.get(vehicle_id)

    def map_unit_type(self, legacy_value: Optional[str]) -> Optional[str]:
        value = self.clean_str(legacy_value)
        if not value:
            return None

        normalized = value.strip().lower()

        mapping = {
            "torton": "TORTON",
            "rabon": "RABON",
            "camioneta": "CAMIONETA",
            "pickup": "PICKUP",
            "tractor": "TRACTOR",
            "caja seca": "CAJA_SECA",
            "plataforma": "PLATAFORMA",
            "remolque": "REMOLQUE",
        }

        return mapping.get(normalized)

    def resolve_operation_status(self, closed_row) -> str:
        if not closed_row:
            return "PENDING"

        value = self.clean_str(closed_row.get("status"))
        if not value:
            return "PENDING"

        normalized = value.strip().lower()

        mapping = {
            "en espera": "PENDING",
            "aprobada": "APPROVED",
            "cancelada": "CANCELLED",
        }

        return mapping.get(normalized, "PENDING")

    def to_decimal_value(self, value, default=0):
        if value in (None, ""):
            return Decimal(default)

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(default)

    def attach_operation_transported_products(self, sql_text: str):
        self.stdout.write(self.style.NOTICE("Relacionando transported_products con operations..."))

        rows = list(self.extract_table_rows(sql_text, "transportedproduct"))
        if not rows:
            self.stdout.write(self.style.WARNING("No se encontraron transported products legacy para relacionar."))
            return

        operation_map = {
            old_id: pk
            for pk, old_id in Operation.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        transported_product_map = {
            old_id: pk
            for pk, old_id in TransportedProduct.objects.exclude(old_id__isnull=True).values_list("pk", "old_id")
        }

        linked = 0

        for row in rows:
            product_old_id = self.to_int(row.get("id"))
            operation_old_id = self.to_int(row.get("Operation_id"))

            if not product_old_id or not operation_old_id:
                continue

            operation_pk = operation_map.get(operation_old_id)
            product_pk = transported_product_map.get(product_old_id)

            if not operation_pk or not product_pk:
                continue

            try:
                operation = Operation.objects.get(pk=operation_pk)
                operation.transported_products.add(product_pk)
                linked += 1
            except Exception:
                continue

        self.stdout.write(self.style.SUCCESS(f"TransportedProducts relacionados con Operations: {linked}"))