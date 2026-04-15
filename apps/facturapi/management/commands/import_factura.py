import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import make_aware
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
        return make_aware(dt) if dt and dt.tzinfo is None else dt
    except Exception:
        return None


class Command(BaseCommand):
    help = "Descarga una factura de FacturAPI por ID y la guarda."

    def add_arguments(self, parser):
        parser.add_argument("facturapi_id", type=str, help="ID de la factura en FacturAPI")

    def handle(self, *args, **options):
        facturapi_id = options["facturapi_id"]

        # Verificar si ya existe
        if FacturapiInvoice.objects.filter(facturapi_id=facturapi_id).exists():
            self.stdout.write(self.style.WARNING("La factura ya existe en la BD."))
            return

        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        })

        # Request a FacturAPI
        response = session.get(
            f"{FACTURAPI_BASE_URL}/invoices/{facturapi_id}",
            timeout=60,
        )

        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR(f"Error HTTP {response.status_code}: {response.text}")
            )
            return

        inv = response.json()

        try:
            stamp_info = inv.get("stamp") or {}
            cancel_data = inv.get("cancellation") or {}
            customer_data = inv.get("customer") or {}

            # Buscar cliente por RFC
            customer_rfc = customer_data.get("tax_id")
            client = Client.objects.filter(rfc=customer_rfc).first()

            stamp_date_str = (
                stamp_info.get("date")
                or inv.get("date")
                or inv.get("created_at")
            )

            obj = FacturapiInvoice.objects.create(
                facturapi_id=inv.get("id"),
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

            self.stdout.write(self.style.SUCCESS(f"Factura creada: {obj.facturapi_id}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error procesando factura: {str(e)}"))