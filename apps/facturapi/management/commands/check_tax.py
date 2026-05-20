import logging
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from apps.facturapi.models import FacturapiInvoice
from apps.facturapi.services import get_taxes

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Descarga facturas de FacturAPI por rango de fechas y actualiza "
        "las facturas locales existentes mediante facturapi_id."
    )

    def handle(self, *args, **options):

        print(get_taxes("699cba43998ca18b4cc89103"))