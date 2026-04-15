import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Generator, Iterable, List, Optional, Tuple

import unicodedata
from django.contrib.postgres.search import TrigramSimilarity
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection, models
from django.db.models import Case, When, Value, FloatField, Q
from django.db.models.functions import Greatest
from django.utils.dateparse import parse_date, parse_datetime

from apps.facturapi.choices import VehicleConfig
from core.operations_panel.choices import MEXICAN_STATES, ShipmentType
from core.operations_panel.models import Client, Supplier, Vehicle, Driver, DeliveryLocation, Route, TransportedProduct, \
    Operation
from core.operations_panel.models.address import Address

class Command(BaseCommand):
    help = "Importa DeliveryLocations desde CSV, reutilizando registros existentes de ASTURIANO por código"

    def handle(self, *args, **options):
        codes = [
            "G1418",
            "G1419",
            "G1420",
            "G1422",
            "G1423",
            "G1424",
            "G1426",
            "G1421",
            "G1425",
            "G1437",
            "G1438",
            "G1439",
            "G1440",
            "G1441",
            "G1443",
            "G1478"
        ]
        for code in codes:
            print("--------------------")
            operation = Operation.objects.get(folio=code)
            print(operation.route.initial_location)
            cedis = DeliveryLocation.objects.get(name="CEDIS ASTURIANO QRO")
            operation.route.initial_location = cedis
            operation.route.save()
            print(operation.route.initial_location)
