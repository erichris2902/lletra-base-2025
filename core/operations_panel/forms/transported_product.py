from django import forms

from core.operations_panel.models.transported_product import TransportedProduct
from core.system.forms import BaseModelForm

class TransportedProductForm(BaseModelForm):
    """
    Form for transported products.
    """
    layout = [
        {"type": "row", "fields": [
            {"name": "transported_product_key", "size": 3},
            {"name": "description", "size": 6},
            {"name": "unit_key", "size": 3},
        ]},
        {"type": "row", "fields": [
            {"name": "currency", "size": 4},
            {"name": "weight", "size": 4},
            {"name": "amount", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "is_danger", "size": 12},
        ]},
    ]

    class Meta:
        model = TransportedProduct
        fields = [
            "transported_product_key",
            "unit_key",
            "description",
            "currency",
            "weight",
            "amount",
            "is_danger",
        ]


class TransportedProductsFormByCSV(forms.Form):
    csv_products = forms.FileField(label='CSV de productos')

    layout = [
        {"type": "callout", "title": "Archivo CSV", "sections": [
            {"type": "row", "fields": [
                {"name": "csv_products", "size": 12},
            ]},
        ]},
    ]
