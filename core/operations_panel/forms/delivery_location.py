from core.operations_panel.models.delivery_location import DeliveryLocation
from core.system.forms import BaseModelForm


class DeliveryLocationForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "name", "size": 12},
        ]},
        {"type": "row", "fields": [
            {"name": "business_name", "size": 8},
            {"name": "rfc", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]
    class Meta:
        model = DeliveryLocation
        fields = [
            "name",
            "business_name",
            "rfc",
            "notes",
        ]

