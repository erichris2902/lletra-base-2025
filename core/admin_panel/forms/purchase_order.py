from django import forms

from core.admin_panel.models.purchase_order import PurchaseOrder
from core.operations_panel.models.cargo import Cargo
from core.system.forms import BaseModelForm, BaseForm


class PurchaseOrderForm(BaseModelForm):
    """
    Form for cargo (load). A cargo can have multiple transported products.
    """

    class Meta:
        model = PurchaseOrder
        fields = [
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If operation is provided in initial data, set it as the only choice
        operation = kwargs.get('initial', {}).get('operation')
        if operation:
            self.fields['operation'].initial = operation
            self.fields['operation'].widget = forms.HiddenInput()
