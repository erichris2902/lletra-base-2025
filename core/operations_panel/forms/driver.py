from django import forms

from core.operations_panel.models.driver import Driver
from core.system.forms import BaseModelForm


class DriverForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "name", "size": 4},
            {"name": "last_name", "size": 4},
            {"name": "mother_last_name", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "rfc", "size": 12},
        ]},
        {"type": "row", "fields": [
            {"name": "license_number", "size": 4},
            {"name": "license_type", "size": 4},
            {"name": "license_expiration", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Driver
        fields = [
            "name",
            "last_name",
            "mother_last_name",
            "rfc",
            "license_number",
            "license_type",
            "license_expiration",
            "notes",
        ]

        widgets = {
            'license_expiration': forms.DateInput(attrs={'type': 'date'}),
        }
