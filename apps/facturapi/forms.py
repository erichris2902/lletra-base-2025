import uuid
from decimal import Decimal

from django.core.validators import RegexValidator
from django.forms import formset_factory, CharField

from apps.facturapi.choices import PAYMENT_METHOD_CHOICES, CancelIssue
from apps.facturapi.models import FacturapiTax, FacturapiInvoice, FacturapiProduct, FacturapiInvoiceItem, \
    FacturapiInvoicePayment
from core.system.forms import BaseModelForm
from django import forms
UUID_PATTERN = r'^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$'
uuid_validator = RegexValidator(
    regex=UUID_PATTERN,
    message='El folio fiscal debe ser un UUID válido (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX).',
    code='invalid_uuid'
)

class FacturapiInvoicePaymentForm(BaseModelForm):
    class Meta:
        model = FacturapiInvoicePayment
        fields = [
            "uuid",
            "amount",
            "installment",
            "last_balance",
            "payment_day",
            "taxes",
        ]

    def clean_related_uuids(self):
        """
        Valida que los UUIDs ingresados sean correctos.
        El usuario los introduce separados por coma en un campo de texto.
        """
        raw_value = self.cleaned_data.get("related_uuids", "")

        if not raw_value:
            return []

        uuid_list = [u.strip() for u in raw_value.split(",") if u.strip()]

        valid_uuids = []
        for u in uuid_list:
            try:
                valid_uuids.append(str(uuid.UUID(u)))
            except ValueError:
                raise forms.ValidationError(
                    f"El valor '{u}' no es un UUID válido."
                )

        return valid_uuids


class SelectItemForm(BaseModelForm):
    class Meta:
        model = FacturapiInvoiceItem
        fields = [
            "product",
        ]

        widgets = {
            # 'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            # 'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }


class FacturapiInvocieForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "customer", "size": 8},
            {"name": "use", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "type", "size": 3},
            {"name": "payment_form", "size": 3},
            {"name": "payment_method", "size": 3},
            {"name": "currency", "size": 3},
        ]},
        {"type": "row", "fields": [
            {"name": "relation_type", "size": 4},
            {"name": "related_uuids", "size": 8},
        ]},
        {"type": "row", "fields": [
            {"name": "pdf_custom_section", "size": 12},
        ]},
    ]

    class Meta:
        model = FacturapiInvoice
        fields = [
            "customer",
            "use",
            "type",
            "payment_form",
            "payment_method",
            "currency",
            "relation_type",
            "related_uuids",
            "pdf_custom_section",
        ]

    def clean_related_uuids(self):
        """
        Valida que los UUIDs ingresados sean correctos.
        El usuario los introduce separados por coma en un campo de texto.
        """
        raw_value = self.cleaned_data.get("related_uuids", "")

        if not raw_value:
            return []

        uuid_list = [u.strip() for u in raw_value.split(",") if u.strip()]

        valid_uuids = []
        for u in uuid_list:
            try:
                valid_uuids.append(str(uuid.UUID(u)))
            except ValueError:
                raise forms.ValidationError(
                    f"El valor '{u}' no es un UUID válido."
                )

        return valid_uuids


class FacturapiProductForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "name", "size": 8},
            {"name": "sku", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "product_key", "size": 3},
            {"name": "unit_key", "size": 3},
            {"name": "price", "size": 3},
            {"name": "taxes", "size": 3},
        ]},
        {"type": "row", "fields": [
            {"name": "description", "size": 12},
        ]},
    ]

    class Meta:
        model = FacturapiProduct
        fields = [
            "name",
            "sku",
            "description",
            "product_key",
            "unit_key",
            "price",
            "taxes",
        ]


class FacturapiTaxForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "name", "size": 12},
        ]},
        {"type": "row", "fields": [
            {"name": "type", "size": 4},
            {"name": "rate", "size": 4},
            {"name": "factor", "size": 4},
        ]},
        {"type": "row", "fields": [
            {"name": "withholding", "size": 12},
        ]},
    ]

    class Meta:
        model = FacturapiTax
        fields = [
            "name",
            "type",
            "rate",
            "factor",
            "withholding",
        ]


class FacturapiInvoiceForm(BaseModelForm):
    class Meta:
        model = FacturapiInvoice
        fields = [
            "customer",
            "payment_form",
            "use",
            "type",
            "currency",
        ]


class FacturapiInvoiceItemForm(BaseModelForm):
    class Meta:
        model = FacturapiInvoiceItem
        fields = [
            "product",
            "quantity",
            "discount",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = FacturapiProduct.objects.all()
        self.fields['product'].widget.attrs.update({'class': 'product-select'})
        self.fields['quantity'].widget.attrs.update({'min': '1', 'step': '1'})
        self.fields['discount'].widget.attrs.update({'min': '0', 'step': '0.01'})


class InvoiceItemForm(BaseModelForm):
    product = forms.ModelChoiceField(
        queryset=FacturapiProduct.objects.all(),
        label="Producto/Servicio",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, initial=Decimal("1.00"),
                                  widget=forms.NumberInput(attrs={"class": "form-control"}), label="Cantidad")
    unit_price = forms.DecimalField(max_digits=10, decimal_places=2,
                                    widget=forms.NumberInput(attrs={"class": "form-control"}), label="Precio unitario")
    discount = forms.DecimalField(max_digits=10, decimal_places=2, required=False, initial=Decimal("0.00"),
                                  widget=forms.NumberInput(attrs={"class": "form-control"}), label="Descuento")
    description = forms.CharField(required=False, max_length=255,
                                  widget=forms.TextInput(attrs={"class": "form-control",
                                                                "placeholder": "Dejar vacío para usar la descripción del producto"}),
                                  label="Descripción (opcional)")


class FacturapiCancelInvoiceForm(forms.Form):
    issue = forms.ChoiceField(
        label='Motivo de cancelación',
        choices=CancelIssue.choices,
        initial=CancelIssue.M02,
        widget=forms.Select(attrs={
            'class': 'form-select select2',      # NiceAdmin + Select2
            'data-placeholder': 'Selecciona motivo',
        }),
        error_messages={
            'required': 'Selecciona el motivo de cancelación.'
        }
    )

    substitute = forms.CharField(
        max_length=36,
        label='Sustitución (solo requerido si el motivo es 01 o 04)',
        required=False,
        validators=[uuid_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'placeholder': 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',
            'inputmode': 'latin',
            'style': 'text-transform: uppercase;',
        })
    )

    # Opcional: estilos/attrs comunes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si no quieres Select2, cambia 'form-select select2' por 'form-select'
        # Ya pusimos clases específicas por campo; no hace falta iterar visible_fields.

    # Normaliza UUID a MAYÚSCULAS y valida formato solo si viene algo
    def clean_substitute(self):
        s = (self.cleaned_data.get('substitute') or '').strip()
        if not s:
            return ''
        # RegexValidator ya valida; solo normalizamos
        return s.upper()

    # Validación cruzada: si issue es 01 o 04, substitute es obligatorio
    def clean(self):
        cleaned = super().clean()
        issue = str(cleaned.get('issue') or '').strip()
        substitute = cleaned.get('substitute') or ''

        if issue in ('01', '04') and not substitute:
            self.add_error('substitute', 'Este campo es obligatorio cuando el motivo es 01 o 04.')

        return cleaned

    # Helper para armar el payload que espera FacturAPI
    def to_facturapi_payload(self) -> dict:
        """
        Devuelve un dict listo para enviar a FacturAPI:
        {
          "motive": "01|02|03|04",
          "substitution": "UUID"  # sólo si aplica
        }
        """
        payload = {"motive": self.cleaned_data['issue']}
        if self.cleaned_data.get('substitute'):
            payload["substitution"] = self.cleaned_data['substitute']
        return payload

InvoiceItemFormSet = formset_factory(InvoiceItemForm, extra=1, can_delete=True)
