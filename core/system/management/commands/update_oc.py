from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.admin_panel.models.purchase_order import PurchaseOrder
from core.operations_panel.models import DeliveryLocation, Route, Operation


class Command(BaseCommand):
    help = "Crea o actualiza rutas por Region-Zona y muestra resultados en consola"


    def handle(self, *args, **options):

        order = PurchaseOrder.objects.get(folio='OC-2026-0139')
        print(order.total)
        order.calculate_totals()
        print(order.total)