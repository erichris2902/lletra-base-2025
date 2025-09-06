from core.sales_panel.models.commercial import Lead, LeadCategory, LeadIndustry, LeadContact, LeadEvent, \
    LeadExpense, Quotation
from core.system.forms import BaseForm, BaseModelForm


class LeadForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "state", "size": 3},
            {"name": "business_name", "size": 9},
            {"name": "geographic_zone", "size": 6},
            {"name": "category", "size": 3},
            {"name": "industry", "size": 3},
            {"name": "requirements", "size": 12},
        ]},
    ]
    class Meta:
        model = Lead
        fields = [
            "business_name",
            "category",
            "industry",
            "state",
            "geographic_zone",
            "requirements",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }

class LeadCategoryForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "category", "size": 12},
        ]},
    ]
    class Meta:
        model = LeadCategory
        fields = [
            "category",
        ]

class LeadIndustryForm(BaseModelForm):
    class Meta:
        model = LeadIndustry
        fields = [
            "industry",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }

class LeadContactForm(BaseModelForm):
    class Meta:
        model = LeadContact
        fields = [
            "name",
            "position",
            "email",
            "phone",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }

class LeadEventForm(BaseModelForm):
    class Meta:
        model = LeadEvent
        fields = [
            "lead",
            "title",
            "description",
            "event_type",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }

class LeadExpenseForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "lead", "size": 4},
            {"name": "expense_date", "size": 4},
            {"name": "expense_type", "size": 4},
            {"name": "title", "size": 9},
            {"name": "amount", "size": 3},
            {"name": "receipt", "size": 12},
            {"name": "description", "size": 12},

        ]},
    ]
    class Meta:
        model = LeadExpense
        fields = [
            "lead",
            "title",
            "description",
            "amount",
            "expense_date",
            "expense_type",
            "receipt",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }

class QuotationForm(BaseModelForm):
    layout = [
        {"type": "row", "fields": [
            {"name": "client", "size": 4},
            {"name": "unit", "size": 3},
            {"name": "tipo_carga", "size": 3},
            {"name": "peso", "size": 2},
            {"name": "origin", "size": 6},
            {"name": "destiny", "size": 6},
            {"name": "requerimientos", "size": 12},
        ]},
    ]
    class Meta:
        model = Quotation
        fields = [
            "client",
            "origin",
            "destiny",
            "tipo_carga",
            "unit",
            "requerimientos",
            "peso",
        ]

        widgets = {
            #'name': forms.TextInput(attrs={'placeholder': 'Ingresa tu nombre'}),
            #'icon': forms.TextInput(attrs={'placeholder': 'Icono de la libreria Font Awesome'}),
        }