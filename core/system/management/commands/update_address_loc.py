import re

from django.core.management.base import BaseCommand

from core.operations_panel.choices import MEXICAN_STATES
from core.operations_panel.models import DeliveryLocation


STATE_MAP = {
    "AGS": "Aguascalientes",
    "AGU": "Aguascalientes",
    "QRO": "Queretaro de Arteaga",
    "QUE": "Queretaro de Arteaga",
    "GTO": "Guanajuato",
    "GUA": "Guanajuato",
    "SLP": "San Luis Potosi",
    "JAL": "Jalisco",
    "HGO": "Hidalgo",
    "HID": "Hidalgo",
    "MEX": "Mexico",
    "MEXICO": "Mexico",
    "EDOMEX": "Mexico",
    "NAY": "Nayarit",
    "ZAC": "Zacatecas",
    "MICH": "Michoacan de Ocampo",
    "MIC": "Michoacan de Ocampo",
    "MICHOACAN": "Michoacan de Ocampo",
    "GRO": "Guerrero",
    "GUERRERO": "Guerrero",
    "MOR": "Morelos",
    "MORELOS": "Morelos",
}

STATE_REGEX = (
    r"S\.?L\.?P\.?|MICHOACAN|GUERRERO|MORELOS|MEXICO|EDOMEX|"
    r"CDMX|AGS|AGU|QRO|QUE|GTO|GUA|SLP|JAL|HGO|HID|MEX|NAY|ZAC|MICH|MIC|GRO|MOR"
)

def extract_zip_and_state(raw):
    text = (raw or "").upper()

    zip_match = re.search(r"\b\d{5}\b", text)
    state_match = re.search(rf"\b({STATE_REGEX})\.?\b", text)

    state = None
    if state_match:
        key = state_match.group(1).replace(".", "").upper()
        state = STATE_MAP.get(key)

    return {
        "zip_code": zip_match.group(0) if zip_match else None,
        "state": state,
    }


class Command(BaseCommand):
    help = "Actualiza zip_code y state en direcciones con zip_code 00000"


    def handle(self, *args, **options):
        valid_states = dict(MEXICAN_STATES)

        locations = DeliveryLocation.objects.filter(
            address__zip_code="00000",
            name__regex=r"^T\d{3,4}",
            business_name__icontains="TRES B",
        ).select_related("address")

        self.stdout.write(f"Registros encontrados: {locations.count()}")

        updated = 0
        skipped = 0

        for loc in locations:
            address = loc.address

            if not address:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"\n{loc.name} - Sin address"))
                continue

            parsed = extract_zip_and_state(address.street)

            if (
                    not parsed["state"]
                    and address.state in valid_states
                    and address.state not in ["", "Mexico"]
            ):
                parsed["state"] = address.state

            self.stdout.write(f"\n{loc.name}")
            self.stdout.write(f"ID: {loc.id}")
            self.stdout.write(f"RAW: {address.street}")
            self.stdout.write(f"ZIP actual: {address.zip_code}")
            self.stdout.write(f"Estado actual: {address.state}")
            self.stdout.write(f"Detectado: {parsed}")

            if not parsed["zip_code"]:
                skipped += 1
                self.stdout.write(self.style.WARNING("Omitido: no se detectó código postal"))
                continue

            if not parsed["state"]:
                skipped += 1
                self.stdout.write(self.style.WARNING("Omitido: no se detectó estado"))
                continue

            if parsed["state"] not in valid_states:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Omitido: estado inválido para choices: {parsed['state']}"
                    )
                )
                continue

            if True:
                address.zip_code = parsed["zip_code"]
                address.state = parsed["state"]
                address.save(update_fields=["zip_code", "state"])

                self.stdout.write(self.style.SUCCESS("Actualizado"))
            else:
                self.stdout.write(self.style.SUCCESS("OK para actualizar"))

            updated += 1

        self.stdout.write("\nResumen")
        self.stdout.write(f"Actualizables: {updated}")
        self.stdout.write(f"Omitidos: {skipped}")
