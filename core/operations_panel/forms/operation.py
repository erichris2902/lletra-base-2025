from django import forms

from core.operations_panel.models.operation import Operation
from core.system.forms import BaseModelForm


class OperationForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "folio", "size": 3},
            {"name": "client", "size": 5},
            {"name": "supplier", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "driver", "size": 4},
            {"name": "vehicle", "size": 4},
            {"name": "vehicle_box", "size": 4},
        ]},
        {"type": "callout", "title": "Ruta", "sections": [
            {"type": "row", "fields": [
                {"name": "route", "size": 12},
            ]},
        ]},
        {"type": "callout", "title": "Horarios de carga/descarga", "sections": [
            {"type": "row", "fields": [
                {"name": "cargo_appointment", "size": 4},
                {"name": "download_appointment", "size": 4},
                {"name": "scheduled_departure_time", "size": 4},
            ]},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Operation
        fields = [
            "folio",
            "client",
            "supplier",
            "driver",
            "vehicle",
            "vehicle_box",
            "route",
            "cargo_appointment",
            "download_appointment",
            "scheduled_departure_time",
            "need_cartaporte",
            "notes",
        ]

        widgets = {
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class OperationFolioWebsiteForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "client", "size": 3},
            {"name": "operation_date", "size": 3},
            {"name": "vehicle_type", "size": 3},
            {"name": "supplier", "size": 3},
        ]},
        {"type": "callout", "title": "Información del folio", "sections": [
            {"type": "row", "fields": [
                {"name": "status", "size": 3},
                {"name": "folio", "size": 3},
                {"name": "total", "size": 3},
                {"name": "handling_amount", "size": 3},
            ]},
            {"type": "row", "fields": [

                {"name": "need_cartaporte", "size": 6},
                {"name": "is_rent", "size": 6},
            ]},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Operation
        fields = [
            ## Row
            "vehicle_type",
            "supplier",

            # Callout
            ## Row
            "folio",
            "total",
            "status",
            ## Row
            "handling_amount",
            "need_cartaporte",
            "is_rent",
            # EndCallout
            ## Row
            "operation_date",
            "client",
            ## Row
            "notes",
        ]

        widgets = {
            'operation_date': forms.DateInput(attrs={'type': 'date'}),
            'cargo_appointment': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'download_appointment': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'scheduled_departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is a new operation, don't show the status field
        if not kwargs.get('instance'):
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].initial = 'PENDING'

class OperationShipmentForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "folio", "size": 3},
            {"name": "client", "size": 5},
            {"name": "supplier", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "driver", "size": 4},
            {"name": "vehicle", "size": 4},
            {"name": "vehicle_box", "size": 4},
        ]},
        {"type": "callout", "title": "Horarios de carga/descarga", "sections": [
            {"type": "row", "fields": [
                {"name": "cargo_appointment", "size": 4},
                {"name": "download_appointment", "size": 4},
                {"name": "scheduled_departure_time", "size": 4},
            ]},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Operation
        fields = [
            ## Row
            "folio",
            "client",
            "supplier",

            "driver",
            "vehicle",
            "vehicle_box",

            "cargo_appointment",
            "download_appointment",
            "scheduled_departure_time",

            "notes",
        ]


class OperationApprovalForm(BaseModelForm):
    """
    Form for approving an operation and assigning a pre-folio.
    """

    class Meta:
        model = Operation
        fields = [
            "status",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.status == 'APPROVED' and not instance.pre_folio:
            instance.approve()
        if commit:
            instance.save()
        return instance


class OperationFolioForm(BaseModelForm):
    """
    Form for assigning a folio to an operation.
    """

    class Meta:
        model = Operation
        fields = [
            "folio",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and instance.pre_folio and not instance.folio:
            self.fields['folio'].initial = instance.pre_folio
            self.fields['folio'].help_text = f"Pre-folio: {instance.pre_folio}"
