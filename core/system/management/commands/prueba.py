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

VALID_BUSINESS_NAMES_3B = [
    "TIENDAS TRES B",
    "TIENDAS TRES B SA DE CV",
    "TIENDAS DE TRES B SA DE CV",
    "TIENDAS DE TRES B",
    "TRES B",
]

def filter_queryset_by_business_3b(qs):
    """
    Filtra queryset dejando solo registros cuyo business_name
    sea suficientemente similar a alguna variante de 3B.
    """
    similarity_expressions = []

    for valid in VALID_BUSINESS_NAMES_3B:
        similarity_expressions.append(
            TrigramSimilarity("business_name", valid)
        )

    qs = qs.annotate(
        business_3b_score=Greatest(*similarity_expressions)
    ).filter(
        business_3b_score__gte=0.45  # <-- ajustable
    )

    return qs

def _normalize_text(value: str) -> str:
    if not value:
        return ""

    value = value.strip().upper()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def _extract_initial_code(value: str) -> str | None:
    normalized = _normalize_text(value)
    match = re.match(r"^(T\d+)\b", normalized)
    return match.group(1) if match else None


def _find_special_match_postgres(name: str, min_score: float = 0.55, ShipmentType=ShipmentType.GENERAL):
    """
    Para 3B / Asturiano:
    - prioriza código inicial T###
    - combina similitud trigram del name
    - agrega bonus si inicia o contiene el código
    """
    normalized_name = _normalize_text(name)
    initial_code = _extract_initial_code(name)

    qs = DeliveryLocation.objects.all()

    # similitud base
    qs = qs.annotate(
        name_similarity=TrigramSimilarity("name", normalized_name),
        business_similarity=TrigramSimilarity("business_name", normalized_name),
    ).annotate(
        base_similarity=Greatest("name_similarity", "business_similarity")
    )

    if initial_code:
        qs = qs.annotate(
            code_bonus=Case(
                When(name__istartswith=initial_code, then=Value(0.35)),
                When(name__icontains=initial_code, then=Value(0.20)),
                default=Value(0.0),
                output_field=FloatField(),
            )
        ).annotate(
            final_score=models.F("base_similarity") + models.F("code_bonus")
        )

        # si hay código, primero reducimos candidatos al universo relevante
        filtered = qs.filter(
            Q(name__icontains=initial_code) |
            Q(business_name__icontains=initial_code)
        ).order_by("-final_score", "-base_similarity")

        best = filtered.first()
        if best and best.final_score >= min_score:
            return best

    # fallback sin código o sin match suficiente
    best = qs.annotate(
        final_score=models.F("base_similarity")
    ).order_by("-final_score").first()

    if best and best.final_score >= 0.70:
        return best

    return None

def _find_general_match_postgres(name: str, min_score: float = 0.72):
    """
    Para GENERAL:
    - solo toma el nombre más similar
    - sin sobrepeso por código
    """
    normalized_name = _normalize_text(name)

    qs = DeliveryLocation.objects.annotate(
        name_similarity=TrigramSimilarity("name", normalized_name),
        business_similarity=TrigramSimilarity("business_name", normalized_name),
    ).annotate(
        final_score=Greatest("name_similarity", "business_similarity")
    ).order_by("-final_score")

    best = qs.first()
    if best and best.final_score >= min_score:
        return best

    return None

def _create_default_location(name: str):
    address = Address.objects.create(
        street="Default Street",
        exterior_number="S/N",
        colony="Default Colony",
        city="Default City",
        state="Ciudad de México",
        zip_code="00000"
    )

    return DeliveryLocation.objects.create(
        name=name,
        business_name=name,
        rfc="XAXX010101000",
        address=address
    )

def get_or_create_by_str(name: str = None, shipment_type=None):
    if not name:
        return None

    cleaned_name = name.strip()

    # 1) Exact match
    exact_match = DeliveryLocation.objects.filter(name__iexact=cleaned_name).first()
    if exact_match:
        return exact_match

    # 2) Matching por tipo
    if shipment_type == ShipmentType.THREE_B:
        best_match = _find_special_match_postgres(
            cleaned_name,
            min_score=0.55,
            ShipmentType=shipment_type
        )
    else:
        best_match = _find_general_match_postgres(
            cleaned_name,
            min_score=0.72
        )

    if best_match:
        return best_match

    # 3) Crear nuevo
    return _create_default_location(cleaned_name)

class Command(BaseCommand):
    help = "Importa DeliveryLocations desde CSV, reutilizando registros existentes de ASTURIANO por código"

    def handle(self, *args, **options):
        with transaction.atomic():
            shop = get_or_create_by_str("T947 ", ShipmentType.ASTURIANO)
            print(shop)
            raise Exception("Error")
