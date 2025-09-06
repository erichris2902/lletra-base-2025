from core.operations_panel.models.client import Client
from core.system.forms import BaseModelForm


class ClientForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "name", "size": 12},
        ]},
        {"type": "row", "fields": [
            {"name": "business_name", "size": 8},
            {"name": "rfc", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "email", "size": 4},
            {"name": "phone", "size": 4},
            {"name": "tax_regime", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]
    class Meta:
        model = Client
        fields = [
            "name",
            "business_name",
            "rfc",
            "email",
            "phone",
            "tax_regime",
            "notes",
        ]

