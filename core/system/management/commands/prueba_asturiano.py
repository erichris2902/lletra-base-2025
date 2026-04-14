import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Generator, Iterable, List, Optional, Tuple

import unicodedata
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.utils.dateparse import parse_date, parse_datetime

from apps.facturapi.choices import VehicleConfig
from core.operations_panel.choices import MEXICAN_STATES
from core.operations_panel.models import Client, Supplier, Vehicle, Driver, DeliveryLocation, Route, TransportedProduct, \
    Operation
from core.operations_panel.models.address import Address

BATCH_SIZE_DEFAULT = 1000

STATE_MAP = {
    "QUERETARO": "Queretaro de Arteaga",
    "QUERETARO DE ARTEAGA": "Queretaro de Arteaga",
    "ESTADO DE MEXICO": "Estado de Mexico",
    "MEXICO": "Estado de Mexico",
    "CDMX": "Ciudad de Mexico",
    "CIUDAD DE MEXICO": "Ciudad de Mexico",
    "GUERRERO": "Guerrero",
    "GUANAJUATO": "Guanajuato",
    "HIDALGO": "Hidalgo",
}

VALID_BUSINESS_NAMES = [
    "ASTURIANO",
    "ASTURITO",
    "CEDIS ASTURITO",
    "OPINEG",
    "ADMINISTRACION DE EMPRESAS AL MENUDEO",
]

def is_valid_business_name(name):
    normalized = normalize_text(name).upper()

    return any(
        normalize_text(valid).upper() in normalized
        for valid in VALID_BUSINESS_NAMES
    )

def normalize_text(text):
    if not text:
        return ""
    text = str(text).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip()


def normalize_state(state):
    state = normalize_text(state).upper()
    return STATE_MAP.get(state, state.title() if state else "Queretaro de Arteaga")


def normalize_store_name(name):
    """
    Normaliza para comparar nombres ignorando acentos, mayúsculas y espacios extra.
    """
    return normalize_text(name).upper()


def extract_identifier_variants(identifier):
    """
    Para T463 devuelve:
    - canonical: T463
    - numeric: 463
    """
    raw = normalize_text(identifier).upper().replace(" ", "")
    match = re.search(r"(\d+)", raw)
    if not match:
        return raw, raw

    numeric = match.group(1)
    canonical = f"T{numeric}"
    return canonical, numeric


def name_has_identifier(name, canonical_code, numeric_code):
    """
    Detecta si el name contiene T463 o 463 como token.
    """
    normalized = normalize_store_name(name)

    patterns = [
        rf"(^|\W){re.escape(canonical_code)}($|\W)",
        rf"(^|\W){re.escape(numeric_code)}($|\W)",
    ]

    return any(re.search(pattern, normalized) for pattern in patterns)


def build_final_name(identifier, name):
    """
    Siempre guarda el nombre con formato:
    T463 TEC METEPEC
    Evita duplicar el código si ya venía.
    """
    canonical_code, numeric_code = extract_identifier_variants(identifier)
    clean_name = normalize_text(name).upper()

    # Remover código al inicio si ya existe como T463 o 463
    clean_name = re.sub(rf"^\s*(T?{re.escape(numeric_code)})\b[\s\-]*", "", clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r"\s+", " ", clean_name).strip()

    return f"{canonical_code} {clean_name}".strip()


def parse_address(raw_address):
    """
    Intenta mapear el formato:
    street, exterior_number, interior_number, colony, zip_code, city, state

    Si no viene completo, rellena con vacíos.
    """
    parts = [p.strip() for p in (raw_address or "").split(",")]

    while len(parts) < 7:
        parts.append("")

    street = parts[0] or ""
    exterior_number = parts[1] or ""
    interior_number = parts[2] or ""
    colony = parts[3] or ""
    zip_code = parts[4] or ""
    city = parts[5] or ""
    state = normalize_state(parts[6])

    return {
        "street": street,
        "exterior_number": exterior_number,
        "interior_number": interior_number,
        "colony": colony,
        "zip_code": zip_code,
        "city": city,
        "state": state or "Queretaro de Arteaga",
    }


def find_existing_delivery_location(identifier):
    canonical_code, numeric_code = extract_identifier_variants(identifier)

    # Traemos todos y filtramos en Python (más flexible)
    candidates = DeliveryLocation.objects.all().only(
        "id", "name", "business_name", "rfc", "address", "notes"
    )

    for candidate in candidates:
        if not is_valid_business_name(candidate.business_name or ""):
            continue

        if name_has_identifier(candidate.name or "", canonical_code, numeric_code):
            return candidate

    return None


class Command(BaseCommand):
    help = "Importa DeliveryLocations desde CSV, reutilizando registros existentes de ASTURIANO por código"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Ruta del archivo CSV")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la importación sin guardar cambios",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            file_path = options["file_path"]
            dry_run = options["dry_run"]

            created_count = 0
            updated_count = 0
            error_count = 0

            with open(file_path, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        identifier = (row.get("identifier") or "").strip()
                        raw_name = (row.get("name") or "").strip()
                        razon_social = "ADMINISTRACION DE EMPRESAS AL MENUDEO"
                        raw_address = row.get("address", "")

                        if not identifier:
                            raise ValueError("La fila no tiene identifier")

                        if not raw_name:
                            raise ValueError("La fila no tiene name")

                        final_name = build_final_name(identifier, raw_name)
                        address_data = parse_address(raw_address)

                        address_obj, _ = Address.objects.get_or_create(
                            street=address_data["street"],
                            exterior_number=address_data["exterior_number"],
                            interior_number=address_data["interior_number"],
                            colony=address_data["colony"],
                            city=address_data["city"],
                            state=address_data["state"],
                            zip_code=address_data["zip_code"] or "00000",
                            defaults={
                                "latitude": None,
                                "longitude": None,
                            },
                        )

                        existing_location = find_existing_delivery_location(
                            identifier=identifier,
                        )

                        if existing_location:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"[UPDATE] Encontrado existente: id={existing_location.id} "
                                    f'name="{existing_location.name}" -> "{final_name}"'
                                )
                            )

                            if not dry_run:
                                existing_location.name = final_name
                                existing_location.business_name = razon_social
                                existing_location.address = address_obj
                                existing_location.notes = (
                                    f"Actualizado desde CSV ID {row.get('id')} | maps: {row.get('maps', '')}"
                                )
                                # Si rfc es requerido y no quieres sobrescribir uno existente:
                                if not existing_location.rfc:
                                    existing_location.rfc = "AEM151124N36"
                                existing_location.save()

                            updated_count += 1
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'[CREATE] Nuevo DeliveryLocation: "{final_name}"'
                                )
                            )

                            if not dry_run:
                                DeliveryLocation.objects.create(
                                    name=final_name,
                                    business_name="ADMINISTRACION DE EMPRESAS AL MENUDEO",
                                    rfc="AEM151124N36",
                                    address=address_obj,
                                    notes=f"Importado desde CSV ID {row.get('id')} | maps: {row.get('maps', '')}",
                                )

                            created_count += 1

                    except Exception as exc:
                        error_count += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f'Error en fila id={row.get("id", "N/A")}: {exc}'
                            )
                        )

            summary = (
                f"Proceso terminado. "
                f"Creados: {created_count}, "
                f"Actualizados: {updated_count}, "
                f"Errores: {error_count}, "
                f"Dry-run: {'sí' if dry_run else 'no'}"
            )
            self.stdout.write(self.style.SUCCESS(summary))
