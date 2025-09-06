from core.operations_panel.models.address import Address
from core.system.forms import BaseModelForm

class AddressForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "street", "size": 6},
            {"name": "exterior_number","size": 3},
            {"name": "interior_number", "size": 3},
        ]},
        {"type": "row", "fields": [
            {"name": "colony", "size": 4},
            {"name": "city", "size": 3},
            {"name": "state", "size": 3},
            {"name": "zip_code", "size": 2},
        ]},
    ]
    class Meta:
        model = Address
        fields = [
            "street",
            "exterior_number",
            "interior_number",
            "colony",
            "city",
            "state",
            "zip_code",
        ]
