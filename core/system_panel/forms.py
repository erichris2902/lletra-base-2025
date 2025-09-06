from core.system.forms import BaseModelForm
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
