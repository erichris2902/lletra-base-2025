from django import forms
from django.core.exceptions import ValidationError

from core.finance_panel.models import ExternalFinanceEntry, ExternalFinanceCategory
from core.system.forms import BaseModelForm


def _validate_pdf(f):
    if f and not str(f.name).lower().endswith('.pdf'):
        raise ValidationError('Adjunta un archivo PDF válido (.pdf).')


def _validate_xml(f):
    if f and not str(f.name).lower().endswith('.xml'):
        raise ValidationError('Adjunta un archivo XML válido (.xml).')


class ExternalFinanceEntryForm(BaseModelForm):

    layout = [
        {"type": "row", "fields": [
            {"name": "entry_type", "size": 4},
            {"name": "concept", "size": 8},
        ]},
        {"type": "row", "fields": [
            {"name": "amount", "size": 4},
            {"name": "category", "size": 4},
            {"name": "operation", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "date", "size": 6},
            {"name": "paid_date", "size": 6},
        ]},
        {"type": "row", "fields": [
            {"name": "invoice_pdf", "size": 6},
            {"name": "invoice_xml", "size": 6},
        ]},
        {"type": "row", "fields": [
            {"name": "comments", "size": 12},
        ]},
        {"type": "row", "fields": [
            {"name": "paid", "size": 4},
        ]},
    ]
    class Meta:
        model = ExternalFinanceEntry
        fields = [
            "concept",
            "entry_type",
            "amount",
            "date",
            "paid",
            "paid_date",
            "invoice_pdf",
            "invoice_xml",
            "category",
            "operation",
            "comments",
        ]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "placeholder": "Importe final con impuestos (MXN)"
                }
            ),
            "concept": forms.TextInput(
                attrs={
                    "placeholder": "Ej. Compra de cinchos"
                }
            ),
            "comments": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Comentarios"
                }
            ),
        }

    def clean_invoice_pdf(self):
        f = self.cleaned_data.get("invoice_pdf")

        if f:
            _validate_pdf(f)

        return f

    def clean_invoice_xml(self):
        f = self.cleaned_data.get("invoice_xml")

        if f:
            _validate_xml(f)

        return f

    def clean(self):
        cleaned = super().clean()

        paid = cleaned.get("paid")
        paid_date = cleaned.get("paid_date")
        amount = cleaned.get("amount")

        if paid and not paid_date:
            self.add_error(
                "paid_date",
                "Si está marcado como pagado, ingresa la fecha de pago."
            )

        if amount is None or amount <= 0:
            self.add_error(
                "amount",
                "El monto debe ser mayor a 0."
            )

        return cleaned


class ExternalFinanceCategoryForm(forms.ModelForm):
    class Meta:
        model = ExternalFinanceCategory
        fields = ['name', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nombre de la categoría (p. ej., Cinchos)'}),
        }
