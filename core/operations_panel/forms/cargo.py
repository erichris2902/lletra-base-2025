from django import forms

from core.operations_panel.models.cargo import Cargo
from core.system.forms import BaseModelForm


class CargoForm(BaseModelForm):
    """
    Form for cargo (load). A cargo can have multiple transported products.
    """

    class Meta:
        model = Cargo
        fields = [
            "identifier",
            "products",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If operation is provided in initial data, set it as the only choice
        operation = kwargs.get('initial', {}).get('operation')
        if operation:
            self.fields['operation'].initial = operation
            self.fields['operation'].widget = forms.HiddenInput()
