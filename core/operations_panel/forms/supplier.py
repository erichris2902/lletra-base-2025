from core.operations_panel.models.supplier import Supplier
from core.system.forms import BaseModelForm


class SupplierForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "status", "size": 4},
            {"name": "code", "size": 8},
        ]},
        {"type": "row", "fields": [
            {"name": "business_name", "size": 7},
            {"name": "rfc", "size": 5},
        ]},
        {"type": "row", "fields": [
            {"name": "email", "size": 4},
            {"name": "phone", "size": 4},
            {"name": "tax_regime", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "bank", "size": 4},
            {"name": "clabe", "size": 8},
        ]},
    ]
    class Meta:
        model = Supplier
        fields = [
            "code",
            "business_name",
            "tax_regime",
            "rfc",
            "email",
            "phone",
            "bank",
            "clabe",
            "status",
        ]

