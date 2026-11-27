import logging
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from apps.facturapi.models import FacturapiInvoice
from apps.facturapi.services import get_invoice

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Descarga facturas de FacturAPI por rango de fechas y actualiza "
        "las facturas locales existentes mediante facturapi_id."
    )

    def handle(self, *args, **options):
        uuids = [
            "1406B7F8-EB16-4EDB-B712-CC47895112F7",
            "D9FD9C50-FD73-460C-961F-4701D319C3ED",
            "4BAE3E39-91CC-430A-AEA7-3132F6E63D50",
            "11F9EA9D-781F-4A9A-9B13-4A1C0F5A4F3B",
            "06DCBB94-F552-42A0-B059-924FCE243B99",
            "748F2605-50B1-4093-8EBC-988993B0A5C0",
            "3F50DD76-35ED-4E89-A096-8EBFC7D42887",
            "B8104021-B279-4F58-AA73-9D8801EE56A8",
            "370C07B6-3309-4FD9-AB22-A34321FA65FE",
            "CDDF21C2-CFB5-4FE1-8A06-BC95E81494C2",
            "3339497F-AD57-489C-B08F-581E49685792",
            "1869A83D-DE6B-4AF8-90EA-36C96B88A9FA",
            "33F159F1-0F21-4C0B-8B51-7469DDA5F411",
        ]

        #invoices = FacturapiInvoice.objects.filter(cancellation_status='verifying')
        for uuid in uuids:
            invoice = FacturapiInvoice.objects.get(uuid=uuid)
            print("---------------------")
            print(invoice)
            print(invoice.status)
            print(invoice.cancellation_status)
            s = get_invoice(invoice.facturapi_id)
            invoice.status = s.get('status') or invoice.status  # 'valid' | 'canceled' | 'pending' | 'draft'
            invoice.cancellation_status = s.get('cancellation_status') or invoice.cancellation_status
            invoice.save()
            print(invoice.status)
            print(invoice.cancellation_status)

