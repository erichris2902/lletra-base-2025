from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.operations_panel.models import DeliveryLocation, Route, Operation


class Command(BaseCommand):
    help = "Crea o actualiza rutas por Region-Zona y muestra resultados en consola"


    def handle(self, *args, **options):
        operation = Operation.objects.get(folio="G2700")
        print(operation.shipment_invoice)