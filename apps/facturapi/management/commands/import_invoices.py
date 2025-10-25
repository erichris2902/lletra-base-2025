import requests
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.conf import settings

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.models import Client

FACTURAPI_BASE_URL = "https://www.facturapi.io/v2"
API_KEY = settings.FACTURAPI_API_KEY  # Define esto en tu settings.py


class Command(BaseCommand):
    help = "DESCARGA TODAS LAS FACTURAS DE FACTURAPI Y LAS GUARDA EN FacturapiInvoice CON PAGINACIÓN."

    def handle(self, *args, **options):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        page = 1
        limit = 100  # Máximo permitido por FacturAPI
        total_processed = 0
        total_created = 0

        while True:
            self.stdout.write(self.style.NOTICE(f"📦 DESCARGANDO PÁGINA {page}..."))
            response = requests.get(
                f"{FACTURAPI_BASE_URL}/invoices",
                headers=headers,
                params={"page": page, "limit": limit},
                timeout=60,
            )

            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ ERROR HTTP {response.status_code}: {response.text}"))
                break

            data = response.json()
            invoices = data.get("data", [])
            if not invoices:
                self.stdout.write(self.style.WARNING("⚠ NO SE ENCONTRARON MÁS FACTURAS."))
                break

            for inv in invoices:
                total_processed += 1
                try:
                    facturapi_id = inv.get("id")
                    amount_due = inv.get("amount_due", 0)
                    status = inv.get("status", "valid")
                    is_live = inv.get("livemode", False)
                    uuid_folio = inv.get("uuid")
                    series = inv.get("series")
                    folio_number = inv.get("folio_number")
                    total_amount = inv.get("total", 0)

                    # Fecha de timbrado (tomamos primero la del SAT si existe)
                    stamp_dt = None
                    stamp_info = inv.get("stamp") or {}
                    stamp_date_str = stamp_info.get("date") or inv.get("date") or inv.get("created_at")

                    if stamp_date_str:
                        try:
                            # Normalizamos formato
                            stamp_date_str = stamp_date_str.replace("Z", "+00:00")
                            # Intentamos parsear distintos formatos válidos
                            for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                                try:
                                    parsed_date = datetime.strptime(stamp_date_str, fmt)
                                    stamp_dt = make_aware(parsed_date) if parsed_date.tzinfo is None else parsed_date
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f"⚠ No se pudo convertir fecha de timbrado: {stamp_date_str} ({e})"))

                    verification_url = inv.get("verification_url")
                    stamp_info = inv.get("stamp", {}) or {}

                    sat_cert_number = stamp_info.get("sat_cert_number")
                    sat_signature = stamp_info.get("sat_signature")
                    signature = stamp_info.get("signature")

                    # Cliente (por id de FacturAPI)
                    customer_data = inv.get("customer") or {}
                    customer_rfc = customer_data.get("tax_id")
                    client = None

                    # Puedes cambiar este filtro si tus clientes tienen guardado facturapi_id
                    if customer_rfc:
                        client = Client.objects.filter(rfc=customer_rfc).first()
                        if not client:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠ CLIENTE FACTURAPI ID {customer_rfc} NO ENCONTRADO PARA FACTURA {facturapi_id}"
                                )
                            )

                    cancel_data = inv.get("cancellation") or {}
                    cancellation_status = cancel_data.get("status")
                    canceled_at = cancel_data.get("last_checked")
                    if canceled_at:
                        try:
                            canceled_at = make_aware(datetime.fromisoformat(canceled_at.replace("Z", "+00:00")))
                        except Exception:
                            canceled_at = None

                    obj, created = FacturapiInvoice.objects.get_or_create(
                        facturapi_id=facturapi_id,
                        defaults={
                            "customer": client,
                            "type": inv.get("type"),
                            "use": inv.get("use"),
                            "amount_due": amount_due,
                            "payment_method": inv.get("payment_form"),
                            "payment_form": inv.get("payment_method"),
                            "currency": inv.get("currency", "MXN"),
                            "pdf_custom_section": inv.get("pdf_custom_section"),
                            "relation_type": inv.get("relation_type"),
                            "related_uuids": inv.get("related_uuids"),
                            "idempotency_key": inv.get("idempotency_key"),
                            "status": status,
                            "is_ready_to_stamp": inv.get("is_ready_to_stamp", True),
                            "uuid": uuid_folio,
                            "series": series,
                            "folio_number": folio_number,
                            "total": total_amount,
                            "stamp_date": stamp_dt,
                            "sat_cert_number": sat_cert_number,
                            "verification_url": verification_url,
                            "sat_signature": sat_signature,
                            "signature": signature,
                            "cancellation_status": cancellation_status,
                            "related_documents": inv.get("related_documents"),
                            "target_invoice_ids": inv.get("target_invoice_ids"),
                            "received_payment_ids": inv.get("received_payment_ids"),
                            "complements": inv.get("complements"),
                            "facturapi_response": inv,
                            "is_live": is_live,
                            "canceled_at": canceled_at,
                        },
                    )
                    print(f"FacturapiInvoice {facturapi_id} created: {created} | Total created: {total_created} | Total processed: {total_processed}")
                    if created:
                        total_created += 1

                    if total_processed % 100 == 0:
                        self.stdout.write(
                            self.style.NOTICE(f"➡ {total_processed} facturas procesadas, {total_created} creadas...")
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ ERROR EN FACTURA {inv.get('id')} ({type(e).__name__}): {e}")
                    )

            page += 1  # Avanzar a la siguiente página

        self.stdout.write(
            self.style.SUCCESS(f"✅ IMPORTACIÓN FINALIZADA: {total_created}/{total_processed} FACTURAS CREADAS.")
        )
