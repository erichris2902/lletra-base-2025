import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.facturapi.models import FacturapiInvoice
from core.operations_panel.models import Client, Operation


class Command(BaseCommand):
    help = "Descarga facturas de FacturAPI y las guarda de forma optimizada."

    def handle(self, *args, **options):

        operation = Operation.objects.get(folio='G1250')
        print(operation.raw_payload.get('type', ''))