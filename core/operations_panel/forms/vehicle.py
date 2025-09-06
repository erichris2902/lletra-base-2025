from core.operations_panel.models.vehicle import Vehicle
from core.system.forms import BaseModelForm


class VehicleForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "econ_number", "size": 6},
        ]},
        {"type": "callout", "title": "Informacion de cartaporte", "sections": [
            {"type": "row", "fields": [
                {"name": "sct_permit", "size": 4},
                {"name": "insurance_company", "size": 4},
                {"name": "insurance_code", "size": 4},
            ]},
            {"type": "row", "fields": [
                {"name": "unit_type", "size": 4},
                {"name": "vehicle_config", "size": 4},
                {"name": "license_plate", "size": 4},
            ]},
        ]},
        {"type": "row", "fields": [
            {"name": "serial_number", "size": 4},
            {"name": "circulation_card_number", "size": 4},
            {"name": "supplier", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "model", "size": 3},
            {"name": "brand", "size": 3},
            {"name": "year", "size": 3},
            {"name": "status", "size": 3},
        ]},

        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Vehicle
        fields = [
            "econ_number",
            "serial_number",
            "circulation_card_number",

            "supplier",
            "model",
            "brand",
            "year",

            "sct_permit",
            "unit_type",
            "vehicle_config",
            "license_plate",
            "insurance_company",
            "insurance_code",

            "status",
            "notes",

        ]

