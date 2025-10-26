import csv

from dateutil import parser
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, is_naive

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.choices import OperationStatus, ShipmentType
from core.operations_panel.models import Client, Driver, Vehicle, Route, Operation


class Command(BaseCommand):
    help = "MIGRA LAS OPERACIONES DESDE operationclosed.csv Y operation.csv"

    def handle(self, *args, **options):
        #op_closed_file = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/operationclosed.csv"
        op_file = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/operation.csv"
        transported_products_file = "C:/Users/erich/Desktop/MIGRACION LLETRA 241025/transportedproduct.csv"

        # ===== 3️⃣ PROCESAR operation.csv =====
        created = 0
        total = 0

        def clean(value):
            if value in [None, "", "NULL", "null"]:
                return None
            return str(value).strip()

        with open(op_file, newline='', encoding='utf-8') as csvfile:
            reader = list(csv.DictReader(csvfile))
            for row in reversed(reader):
                total += 1
                try:
                    vehicular_control = clean(row.get("vehicular_control"))

                    # === INVOICE ===
                    invoice_id = (row.get("cartaporte_folio") or "").strip().upper()
                    shipment_invoice = FacturapiInvoice.objects.exclude(type="P").exclude(type="E").filter(status="valid").exclude(complements__isnull=True).exclude(complements={}).get(folio_number=invoice_id) if invoice_id and invoice_id != "NULL" else None

                    # === CLIENT ===
                    client_id = (row.get("client_id") or "").strip().upper()
                    client = Client.objects.get(old_id=client_id) if client_id and client_id != "NULL" else None

                    # === DRIVER ===
                    operator_id = (row.get("operator_id") or "").strip().upper()
                    driver = Driver.objects.get(old_id=operator_id) if operator_id and operator_id != "NULL" else None

                    # === VEHÍCULO ===
                    vehicle_id = (row.get("unit_id") or "").strip().upper()
                    vehicle = Vehicle.objects.get(old_id=vehicle_id) if vehicle_id and vehicle_id != "NULL" else None

                    # === CAJA ===
                    vehicle_box_id = (row.get("caja_id") or "").strip().upper()
                    vehicle_box = Vehicle.objects.get(old_id=vehicle_box_id) if vehicle_box_id and vehicle_box_id != "NULL" else None

                    # === RUTA ===
                    route = None
                    route_id = clean(row.get("route_id"))
                    if route_id:
                        route = Route.objects.get(old_id=int(route_id)) if route_id and route_id != "NULL" else None


                    cargo_app = clean(row.get("cargo_appointment"))
                    download_app = clean(row.get("download_appointment"))
                    scheduled_dep = clean(row.get("scheduled_departure_time"))

                    def parse_dt(v):
                        """
                        Convierte una cadena de texto a datetime aware (UTC).
                        Acepta múltiples formatos:
                        - 2023-04-03 13:00:00
                        - 2023-04-03 13:00:00Z
                        - 2023-04-03 13:00:00+00
                        - 2023-04-03 13:00:00+00:00
                        """
                        if not v:
                            return None
                        try:
                            dt = parser.parse(v)
                            # Solo aplicar make_aware si es naive
                            if is_naive(dt):
                                print("is_naive")
                                return make_aware(dt)
                            return dt
                        except Exception as e:
                            print(f"[WARN] No se pudo parsear fecha {v}: {e}")
                            return None

                    cargo_appointment = parse_dt(cargo_app)
                    download_appointment = parse_dt(download_app)
                    scheduled_departure_time = parse_dt(scheduled_dep)

                    notes = clean(row.get("commentaries"))

                    status = OperationStatus.APPROVED

                    if shipment_invoice:
                        status = OperationStatus.INVOICED
                        if shipment_invoice.status == "canceled":
                            status = OperationStatus.CANCELLED

                    if client.rfc == "TTB040915CY9":
                        shipment_type = ShipmentType.THREE_B
                    elif client.rfc == "AEM151124N36" or client.rfc == "CAS230914GM9":
                        shipment_type = ShipmentType.ASTURIANO
                    elif client.rfc == "CTC861104I92":
                        shipment_type = ShipmentType.CHEM
                    else:
                        shipment_type = ShipmentType.GENERAL

                    # === CREACIÓN / ACTUALIZACIÓN ===
                    obj, created_flag = Operation.objects.get_or_create(
                        old_id=int(row["id"]),
                        defaults={
                            "shipment_invoice" : shipment_invoice,
                            "pre_folio": vehicular_control,
                            "folio": vehicular_control,
                            "client": client,
                            "driver": driver,
                            "vehicle": vehicle,
                            "vehicle_box": vehicle_box,
                            "route": route,
                            "operation_date": cargo_appointment.date() if cargo_appointment else None,
                            "shipment_type": shipment_type,
                            "status": status,
                            "notes": notes,
                            "is_rent": False,
                            "is_packing_ready": False,
                            "cargo_appointment": cargo_appointment,
                            "download_appointment": download_appointment,
                            "scheduled_departure_time": scheduled_departure_time,
                            #vehicle_type
                        },
                    )



                    if created_flag:
                        created += 1
                        if obj.status == OperationStatus.INVOICED:
                            obj.upload_invoice_to_drive()

                        self.stdout.write(self.style.SUCCESS(f"OPERACIÓN {row.get('id')} ({vehicular_control})({status}): CREADA CON EXITO"))
                    else:
                        self.stdout.write(self.style.SUCCESS(f"OPERACIÓN {row.get('id')} ({vehicular_control})({status}): YA EXISTE"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ ERROR EN OPERACIÓN {row.get('id')} ({vehicular_control}): {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"✅ MIGRACIÓN COMPLETADA: {created}/{total} OPERACIONES CREADAS O ACTUALIZADAS.")
        )
