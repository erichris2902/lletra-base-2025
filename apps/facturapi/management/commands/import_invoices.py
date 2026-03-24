import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.models import Client

FACTURAPI_BASE_URL = "https://www.facturapi.io/v2"
API_KEY = settings.FACTURAPI_API_KEY


def safe_parse_datetime(value):
    if not value:
        return None

    try:
        dt = parse_datetime(value.replace("Z", "+00:00"))
        if dt is None:
            return None
        return make_aware(dt) if dt.tzinfo is None else dt
    except Exception:
        return None


class Command(BaseCommand):
    help = "Descarga facturas de FacturAPI y las guarda de forma optimizada."

    def handle(self, *args, **options):
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        })

        page = 216
        limit = 100
        total_processed = 0
        total_created = 0

        while True:
            self.stdout.write(self.style.NOTICE(f"Descargando página {page}..."))

            response = session.get(
                f"{FACTURAPI_BASE_URL}/invoices",
                params={"page": page, "limit": limit},
                timeout=60,
            )

            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(f"Error HTTP {response.status_code}: {response.text}")
                )
                break

            data = response.json()
            invoices = data.get("data", [])

            if not invoices:
                self.stdout.write(self.style.WARNING("No se encontraron más facturas."))
                break

            total_processed += len(invoices)

            # 1) RFCs únicos de la página
            rfcs = {
                (inv.get("customer") or {}).get("tax_id")
                for inv in invoices
                if (inv.get("customer") or {}).get("tax_id")
            }

            # 2) Clientes en memoria: 1 sola query
            clients_map = {
                client.rfc: client
                for client in Client.objects.filter(rfc__in=rfcs)
            }

            # 3) Facturas ya existentes en memoria: 1 sola query
            facturapi_ids = [inv.get("id") for inv in invoices if inv.get("id")]
            existing_ids = set(
                FacturapiInvoice.objects.filter(facturapi_id__in=facturapi_ids)
                .values_list("facturapi_id", flat=True)
            )

            to_create = []

            for inv in invoices:
                try:
                    facturapi_id = inv.get("id")
                    if not facturapi_id or facturapi_id in existing_ids:
                        continue

                    stamp_info = inv.get("stamp") or {}
                    cancel_data = inv.get("cancellation") or {}
                    customer_data = inv.get("customer") or {}

                    customer_rfc = customer_data.get("tax_id")
                    client = clients_map.get(customer_rfc)

                    stamp_date_str = (
                        stamp_info.get("date")
                        or inv.get("date")
                        or inv.get("created_at")
                    )

                    obj = FacturapiInvoice(
                        facturapi_id=facturapi_id,
                        customer=client,
                        type=inv.get("type"),
                        use=inv.get("use"),
                        amount_due=inv.get("amount_due", 0),
                        payment_method=inv.get("payment_form"),
                        payment_form=inv.get("payment_method"),
                        currency=inv.get("currency", "MXN"),
                        pdf_custom_section=inv.get("pdf_custom_section"),
                        relation_type=inv.get("relation_type"),
                        related_uuids=inv.get("related_uuids"),
                        idempotency_key=inv.get("idempotency_key"),
                        status=inv.get("status", "valid"),
                        is_ready_to_stamp=inv.get("is_ready_to_stamp", True),
                        uuid=inv.get("uuid"),
                        series=inv.get("series"),
                        folio_number=inv.get("folio_number"),
                        total=inv.get("total", 0),
                        stamp_date=safe_parse_datetime(stamp_date_str),
                        sat_cert_number=stamp_info.get("sat_cert_number"),
                        verification_url=inv.get("verification_url"),
                        sat_signature=stamp_info.get("sat_signature"),
                        signature=stamp_info.get("signature"),
                        cancellation_status=cancel_data.get("status"),
                        related_documents=inv.get("related_documents"),
                        target_invoice_ids=inv.get("target_invoice_ids"),
                        received_payment_ids=inv.get("received_payment_ids"),
                        complements=inv.get("complements"),
                        facturapi_response=inv,
                        is_live=inv.get("livemode", False),
                        canceled_at=safe_parse_datetime(cancel_data.get("last_checked")),
                    )

                    to_create.append(obj)
                except Exception as e:
                    print(e)

            # 4) Inserción en bloque
            try:
                if to_create:
                    with transaction.atomic():
                        FacturapiInvoice.objects.bulk_create(to_create, batch_size=500)
                    total_created += len(to_create)
            except Exception as e:
                print(e)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Página {page}: procesadas={len(invoices)}, nuevas={len(to_create)}, total_creadas={total_created}"
                )
            )

            page += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación finalizada: {total_created}/{total_processed} facturas creadas."
            )
        )