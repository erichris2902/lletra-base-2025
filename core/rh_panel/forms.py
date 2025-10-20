from django import forms

from core.rh_panel.models import Employee, Embedding
from core.system.forms import BaseModelForm


class EmployeeForm(BaseModelForm):
    """
    Form for cargo (load). A cargo can have multiple transported products.
    """

    class Meta:
        model = Employee
        fields = [
            "name",
        ]

