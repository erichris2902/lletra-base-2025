from django import forms

from core.operations_panel.models.transported_product import TransportedProduct
from core.system.forms import BaseModelForm

class TransportedProductForm(BaseModelForm):
    """
    Form for transported products.
    """

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
        widgets = {
            'transported_product_key': forms.Select(attrs={
                'class': 'select2',
            }),
            'unit_key': forms.Select(attrs={
                'class': 'select2',
            }),
        }


class TransportedProductsFormByCSV(forms.Form):
    csv_products = forms.FileField(label='CSV de productos')

    layout = [
        {"type": "callout", "title": "Archivo CSV", "sections": [
            {"type": "row", "fields": [
                {"name": "csv_products", "size": 12},
            ]},
        ]},
    ]
