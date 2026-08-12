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
        ("CMI", "CMI - Control maestro INGRESOS"),
        ("CME", "CME - Control maestro EGRESOS"),
        ("CMP", "CMP - Control maestro PLANTILLAS"),
        ("PPP", "PPP - Plantilla de productos precargados"),
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


class ReportEngineForm(BaseForm):

    REPORT_CHOICES = [
        ("folios", "Folios"),
        ("facturacion", "Facturacion"),
        ("packing_asturiano", "Packing de Asturiano"),
        ("asistencia", "Reporte de asistencia"),
        ("operations_master", "Control maestro de operaciones"),
    ]
    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "report_type", "size": 6},
                {"name": "fecha_inicial", "size": 3},
                {"name": "fecha_final", "size": 3},
            ],
        },
    ]

    report_type = forms.ChoiceField(
        label="Tipo de reporte",
        choices=REPORT_CHOICES,
    )

    fecha_inicial = forms.DateField(
        label="Fecha inicial",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    fecha_final = forms.DateField(
        label="Fecha final",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


class ReportEngineByFolioForm(BaseForm):

    REPORT_CHOICES = [
        #("packing_asturiano", "Packing de Asturiano"),
        ("folios", "Folios"),
    ]
    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "report_type", "size": 6},
                {"name": "folio_serie", "size": 2},
                {"name": "folio_number", "size": 4},
            ],
        },
    ]

    report_type = forms.ChoiceField(
        label="Tipo de reporte",
        choices=REPORT_CHOICES,
    )

    folio_serie = forms.CharField(
        label="Serie",
    )

    folio_number = forms.CharField(
        label="Folio",
    )


class ExpedienteZipForm(BaseForm):
    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "zip_file", "size": 8},
            ],
        },
    ]

    zip_file = forms.FileField(
        label="Archivo ZIP de expedientes",
        help_text="Sube un archivo .zip que contenga carpetas con PDFs por expediente.",
    )

    def __init__(self, *args, max_mb: int = 200, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_mb = max_mb
        self.fields["zip_file"].widget.attrs.setdefault("accept", ".zip")

    def clean_zip_file(self):
        f = self.cleaned_data.get("zip_file")
        if not f:
            return f
        name = getattr(f, 'name', '') or ''
        if not name.lower().endswith('.zip'):
            raise forms.ValidationError("Debe subir un archivo con extensión .zip")
        size = getattr(f, 'size', None)
        if size is not None and size > self.max_mb * 1024 * 1024:
            raise forms.ValidationError(f"El archivo excede el límite de {self.max_mb} MB")
        return f


class PdfReduceZipForm(BaseForm):
    QUALITY_CHOICES = [
        (50, "Baja — Menor tamaño, mayor pérdida de calidad."),
        (65, "Media — Buen balance entre tamaño y calidad."),
        (80, "Alta — Buena calidad, reducción moderada."),
        (90, "Muy alta — Menor pérdida visual, archivo más pesado."),
    ]

    SCALE_CHOICES = [
        (0.6, "Pequeña — menor resolución, archivos más pequeños."),
        (0.8, "Media — buen equilibrio de detalle y peso."),
        (1.0, "Normal — mantiene resolución original."),
        (1.2, "Alta — más detalle, archivos más grandes."),
    ]

    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "zip_file", "size": 6},
                {"name": "quality", "size": 3},
                {"name": "scale", "size": 3},
            ],
        },
        {
            "type": "row",
            "fields": [
                {"name": "keep_first_page", "size": 6},
            ],
        },
    ]

    zip_file = forms.FileField(
        label="Archivo ZIP con PDFs",
        help_text="Sube un archivo .zip que contenga PDFs a reducir. Se mantendrán los mismos nombres.",
    )
    quality = forms.ChoiceField(
        label="Calidad",
        choices=QUALITY_CHOICES,
        initial=65,
    )
    scale = forms.ChoiceField(
        label="Escala",
        choices=SCALE_CHOICES,
        initial=0.8,
    )
    keep_first_page = forms.BooleanField(
        label="Mantener primera página sin compresión",
        required=False,
        initial=True,
    )

    def __init__(self, *args, max_mb: int = 200, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_mb = max_mb
        self.fields["zip_file"].widget.attrs.setdefault("accept", ".zip")
        # Render select nicely using project style (form-select)
        for name in ("quality", "scale"):
            w = self.fields[name].widget
            css = w.attrs.get("class", "")
            w.attrs["class"] = (css.replace("form-control", "").strip() + " form-select").strip()

    def clean_zip_file(self):
        f = self.cleaned_data.get("zip_file")
        if not f:
            return f
        name = getattr(f, 'name', '') or ''
        if not name.lower().endswith('.zip'):
            raise forms.ValidationError("Debe subir un archivo con extensión .zip")
        size = getattr(f, 'size', None)
        if size is not None and size > self.max_mb * 1024 * 1024:
            raise forms.ValidationError(f"El archivo excede el límite de {self.max_mb} MB")
        return f

    def clean_quality(self):
        val = int(self.cleaned_data.get("quality"))
        if val not in {50, 65, 80, 90}:
            raise forms.ValidationError("Valor de calidad no permitido.")
        return val

    def clean_scale(self):
        try:
            val = float(self.cleaned_data.get("scale"))
        except Exception:
            raise forms.ValidationError("Valor de escala inválido.")
        if val not in {0.6, 0.8, 1.0, 1.2}:
            raise forms.ValidationError("Valor de escala no permitido.")
        return val