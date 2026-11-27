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
            {"name": "email", "size": 3},
            {"name": "phone", "size": 3},
            {"name": "tax_regime", "size": 3},
            {"name": "credit_days", "size": 3},
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
            "credit_days",
            "notes",
        ]

