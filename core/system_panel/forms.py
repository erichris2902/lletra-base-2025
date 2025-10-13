from django import forms

from core.system.forms import BaseModelForm, BaseForm
from core.system.models import Section, Category
from apps.openai_assistant.models import Assistant


class AssistantForm(BaseModelForm):
    class Meta:
        model = Assistant
        fields = [
            "name",
            "telegram_command",
            "instructions",
            "model",
            "openai_id",
            "is_active",
        ]


class CategoryForm(BaseModelForm):
    class Meta:
        model = Category
        fields = [
            "name",
            "icon",
            "priority",
            "url",
            "system",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }


class SectionForm(BaseModelForm):
    class Meta:
        model = Section
        fields = [
            "category",
            "name",
            "icon",
            "priority",
            "url",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }


class ActionEngineForm(BaseForm):
    ACTION_CHOICES = [
        ("CM", "CM - Cancelación masiva de facturas"),
        ("CMR", "CMR - Cancelación masiva de facturas con relacion"),
        ("CP", "CP - Complementos de pago"),
    ]

    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "action", "size": 6},
                {"name": "file", "size": 6},
            ],
        },
    ]

    action = forms.ChoiceField(
        label="Acción a ejecutar",
        choices=ACTION_CHOICES,
    )
    file = forms.FileField(
        label="Archivo de acciones (Excel)",
        help_text="Sube un archivo XLSX o XLS con los datos requeridos para la acción seleccionada.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        action_widget = self.fields["action"].widget
        action_classes = action_widget.attrs.get("class", "")
        action_widget.attrs["class"] = (
            action_classes.replace("form-control", "").strip() + " form-select"
        ).strip()
        self.fields["file"].widget.attrs.setdefault("accept", ".xlsx,.xls")