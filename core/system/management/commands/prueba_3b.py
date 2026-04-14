import csv
import re
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from core.operations_panel.choices import MEXICAN_STATES, MEXICAN_STATES_KEY
from core.operations_panel.models import DeliveryLocation
from core.operations_panel.models.address import Address


DEFAULT_BUSINESS_NAME_3B = "TIENDAS TRES B"
DEFAULT_RFC_3B = "TTB040915CY9"

VALID_BUSINESS_NAMES_3B = [
    "TIENDAS TRES B",
    "TIENDAS TRES B SA DE CV",
    "TIENDAS DE TRES B SA DE CV",
    "TIENDAS DE TRES B",
    "TRES B",
]


def normalize_text(text):
    if not text:
        return ""
    text = str(text).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip()


def normalize_store_name(name):
    return normalize_text(name).upper()


def build_state_alias_map():
    """
    Crea aliases normalizados a partir de MEXICAN_STATES y MEXICAN_STATES_KEY.
    El valor final siempre será uno de los choices válidos del modelo.
    """
    valid_states = {value for value, _ in MEXICAN_STATES if value}

    alias_map = {}

    # aliases directos desde choices
    for state in valid_states:
        alias_map[normalize_text(state).upper()] = state

    # aliases extra útiles
    manual_aliases = {
        "ESTADO DE MEXICO": "Mexico",
        "EDO MEX": "Mexico",
        "EDO. MEXICO": "Mexico",
        "MEXICO": "Mexico",
        "CDMX": "Ciudad de México",
        "CIUDAD DE MEXICO": "Ciudad de México",
        "CIUDAD DE MEXICO CDMX": "Ciudad de México",
        "QUERETARO": "Queretaro de Arteaga",
        "QUERETARO DE ARTEAGA": "Queretaro de Arteaga",
        "MICHOACAN": "Michoacan de Ocampo",
        "MICHOACAN DE OCAMPO": "Michoacan de Ocampo",
        "NUEVO LEON": "Nuevo Leon",
        "SAN LUIS POTOSI": "San Luis Potosi",
        "YUCATAN": "Yucatan",
        "COAHUILA": "Coahuila  de Zaragoza",
        "COAHUILA DE ZARAGOZA": "Coahuila  de Zaragoza",
        "QUINTANA ROO": "Quintana",
    }

    for key, value in manual_aliases.items():
        if value in valid_states:
            alias_map[normalize_text(key).upper()] = value

    # también aprovecha llaves del diccionario de abreviaturas
    for key in MEXICAN_STATES_KEY.keys():
        normalized_key = normalize_text(key).upper()
        if normalized_key and normalized_key not in alias_map:
            # solo agregamos si existe alguna equivalencia obvia dentro de los choices
            if key in valid_states:
                alias_map[normalized_key] = key

    return alias_map


STATE_ALIAS_MAP = build_state_alias_map()
VALID_STATES = {value for value, _ in MEXICAN_STATES if value}


def normalize_state(raw_state):
    normalized = normalize_text(raw_state).upper()
    if not normalized:
        return "Mexico"

    if normalized in STATE_ALIAS_MAP:
        return STATE_ALIAS_MAP[normalized]

    # fallback tolerante
    for alias, value in STATE_ALIAS_MAP.items():
        if normalized in alias or alias in normalized:
            return value

    return "Mexico"


def is_valid_business_name_3b(name):
    normalized = normalize_text(name).upper()
    return any(
        normalize_text(valid).upper() in normalized
        for valid in VALID_BUSINESS_NAMES_3B
    )


def extract_identifier_variants(identifier):
    """
    Para '50' devuelve:
    - canonical: T050
    - numeric: 50
    - padded: 050
    """
    raw = normalize_text(identifier).upper().replace(" ", "")
    match = re.search(r"(\d+)", raw)
    if not match:
        return raw, raw, raw

    numeric = str(int(match.group(1)))
    padded = numeric.zfill(3)
    canonical = f"T{padded}"
    return canonical, numeric, padded


def name_has_identifier(name, canonical_code, numeric_code, padded_code):
    """
    Debe detectar:
    - T050 NICOLAS ROMERO
    - 050 NICOLAS ROMERO
    - 50 NICOLAS ROMERO
    - T50 NICOLAS ROMERO
    """
    normalized = normalize_store_name(name)

    patterns = [
        rf"(^|\W){re.escape(canonical_code)}($|\W)",
        rf"(^|\W)T{re.escape(numeric_code)}($|\W)",
        rf"(^|\W){re.escape(padded_code)}($|\W)",
        rf"(^|\W){re.escape(numeric_code)}($|\W)",
        rf"^{re.escape(canonical_code)}\b",
        rf"^T{re.escape(numeric_code)}\b",
        rf"^{re.escape(padded_code)}\b",
        rf"^{re.escape(numeric_code)}\b",
    ]

    return any(re.search(pattern, normalized) for pattern in patterns)


def split_3b_name(raw_name, identifier):
    """
    Ejemplos:
    050NicolasRomero   -> NICOLAS ROMERO
    176NicolasRomero2  -> NICOLAS ROMERO 2
    072Tultepec        -> TULTEPEC
    """
    canonical_code, numeric_code, padded_code = extract_identifier_variants(identifier)
    clean_name = normalize_text(raw_name)

    clean_name = re.sub(
        rf"^\s*T?0*{re.escape(numeric_code)}\s*",
        "",
        clean_name,
        flags=re.IGNORECASE,
    )

    # separa CamelCase
    clean_name = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean_name)
    # separa número final
    clean_name = re.sub(r"([A-Za-z])(\d+)$", r"\1 \2", clean_name)

    clean_name = normalize_text(clean_name).upper()

    return canonical_code, clean_name


def build_final_name_3b(identifier, raw_name):
    canonical_code, clean_name = split_3b_name(raw_name, identifier)
    return f"{canonical_code} {clean_name}".strip()


def parse_address_3b(raw_address):
    """
    Ejemplo:
    'Fernando Montes de Oca No. 2 col Nicolas Romero, Estado de México cp 54405'
    """
    original = normalize_text(raw_address)

    state = "Mexico"
    zip_code = "00000"
    colony = ""
    city = ""
    street = original
    exterior_number = ""
    interior_number = ""

    zip_match = re.search(r"\bcp\s*(\d{5})\b", original, flags=re.IGNORECASE)
    if zip_match:
        zip_code = zip_match.group(1)

    state_match = re.search(
        r"\b(Estado de Mexico|Estado de México|Edo\.? Mexico|Edo\.? de Mexico|CDMX|Ciudad de Mexico|Ciudad de México|Queretaro|Queretaro de Arteaga|Hidalgo|Guanajuato|Guerrero|Jalisco|Morelos|Michoacan|Michoacan de Ocampo|Nuevo Leon|Oaxaca|Puebla|San Luis Potosi|Tlaxcala|Veracruz|Yucatan|Zacatecas|Aguascalientes|Baja California|Baja California Sur|Campeche|Chiapas|Chihuahua|Coahuila|Colima|Durango|Nayarit|Quintana Roo|Sinaloa|Sonora|Tabasco|Tamaulipas)\b",
        original,
        flags=re.IGNORECASE,
    )
    if state_match:
        state = normalize_state(state_match.group(1))

    colony_match = re.search(r"\bcol\.?\s*(.+?)(,|$)", original, flags=re.IGNORECASE)
    if colony_match:
        colony = normalize_text(colony_match.group(1)).upper()

    number_match = re.search(
        r"\b(?:NO\.?|N°|NUM\.?|#)\s*([A-Z0-9/-]+)\b",
        original,
        flags=re.IGNORECASE,
    )
    if number_match:
        exterior_number = normalize_text(number_match.group(1)).upper()
    elif re.search(r"\bS\/N\b", original, flags=re.IGNORECASE):
        exterior_number = "S/N"
    elif re.search(r"\bs\/n\b", original, flags=re.IGNORECASE):
        exterior_number = "S/N"

    # limpiar street quitando col / estado / cp
    street = re.sub(r"\bcol\.?\s*.+?(,|$)", "", original, flags=re.IGNORECASE).strip(" ,")
    street = re.sub(r"\bcp\s*\d{5}\b", "", street, flags=re.IGNORECASE).strip(" ,")
    if state_match:
        street = re.sub(re.escape(state_match.group(0)), "", street, flags=re.IGNORECASE).strip(" ,")

    street = normalize_text(street).upper()

    return {
        "street": street,
        "exterior_number": exterior_number,
        "interior_number": interior_number,
        "colony": colony,
        "zip_code": zip_code,
        "city": city,
        "state": state if state in VALID_STATES else "Mexico",
    }


def find_existing_delivery_location_3b(identifier):
    canonical_code, numeric_code, padded_code = extract_identifier_variants(identifier)

    candidates = DeliveryLocation.objects.all().only(
        "id", "name", "business_name", "rfc", "address", "notes"
    )

    for candidate in candidates:
        if not is_valid_business_name_3b(candidate.business_name or ""):
            continue

        if name_has_identifier(candidate.name or "", canonical_code, numeric_code, padded_code):
            return candidate

    return None


class Command(BaseCommand):
    help = "Importa DeliveryLocations de 3B desde CSV reutilizando registros existentes por identificador"

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

            with open(file_path, newline="", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        identifier = (row.get("identifier") or "").strip()
                        raw_name = (row.get("name") or "").strip()
                        raw_address = row.get("address", "")

                        if not identifier:
                            raise ValueError("La fila no tiene identifier")

                        if not raw_name:
                            raise ValueError("La fila no tiene name")

                        final_name = build_final_name_3b(identifier, raw_name)
                        address_data = parse_address_3b(raw_address)

                        address_obj, _ = Address.objects.get_or_create(
                            street=address_data["street"],
                            exterior_number=address_data["exterior_number"],
                            interior_number=address_data["interior_number"],
                            colony=address_data["colony"],
                            city=address_data["city"],
                            state=address_data["state"],
                            zip_code=address_data["zip_code"],
                            defaults={
                                "latitude": None,
                                "longitude": None,
                            },
                        )

                        existing_location = find_existing_delivery_location_3b(identifier)

                        if existing_location:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'[UPDATE] id={existing_location.id} "{existing_location.name}" -> "{final_name}"'
                                )
                            )

                            if not dry_run:
                                existing_location.name = final_name
                                existing_location.business_name = DEFAULT_BUSINESS_NAME_3B
                                existing_location.address = address_obj
                                existing_location.notes = (
                                    f"Actualizado desde CSV ID {row.get('id')} | import 3B"
                                )
                                if not existing_location.rfc:
                                    existing_location.rfc = DEFAULT_RFC_3B
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
                                    business_name=DEFAULT_BUSINESS_NAME_3B,
                                    rfc=DEFAULT_RFC_3B,
                                    address=address_obj,
                                    notes=f"Importado desde CSV ID {row.get('id')} | import 3B",
                                )

                            created_count += 1

                    except Exception as exc:
                        error_count += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f'Error en fila id={row.get("id", "N/A")}: {exc}'
                            )
                        )

            if dry_run:
                transaction.set_rollback(True)

            summary = (
                f"Proceso terminado. "
                f"Creados: {created_count}, "
                f"Actualizados: {updated_count}, "
                f"Errores: {error_count}, "
                f"Dry-run: {'sí' if dry_run else 'no'}"
            )
            self.stdout.write(self.style.SUCCESS(summary))