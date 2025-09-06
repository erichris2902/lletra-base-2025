from django import forms
from django.forms import TextInput
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_current_timezone, is_naive, make_aware, localtime
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date, datetime
from django.forms import *


class BaseForm(forms.Form):
    """
    Base form class with common functionality for all forms.
    """

    def clean(self):
        """
        Base clean method that ensures datetime fields are timezone-aware.
        """
        cleaned_data = super().clean()
        tz = get_current_timezone()

        for name, field in self.fields.items():
            if isinstance(field, DateTimeField):
                value = cleaned_data.get(name)
                if value and is_naive(value):
                    cleaned_data[name] = make_aware(value, timezone=tz)
        return cleaned_data

    @classmethod
    def get_field_names(cls):
        """
        Get a list of all field names in the form.
        """
        return list(cls.base_fields.keys())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for form in self.visible_fields():
            field = form.field
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['autocomplete'] = 'off'
            field.widget.attrs['placeholder'] = form.field.label
            field.widget.attrs['size'] = '12'

            # Campo de fecha o datetime
            if isinstance(field, DateTimeField):
                field.widget = TextInput(attrs=field.widget.attrs)
                field.widget.attrs['class'] += ' flatpickr flatpickr-datetime'
            elif isinstance(field, DateField):
                field.widget = TextInput(attrs=field.widget.attrs)
                field.widget.attrs['class'] += ' flatpickr flatpickr-date'

        # Formatear fechas iniciales para Flatpickr
        for name, value in self.initial.items():
            if isinstance(value, datetime):
                self.initial[name] = localtime(value).strftime("%d/%m/%Y %H:%M")
            elif isinstance(value, date):
                self.initial[name] = value.strftime("%d/%m/%Y")


class BaseModelForm(ModelForm):
    """
    Base model form class with common functionality for all model forms.
    """

    class Meta:
        fields = []
        exclude = ['id', 'created_at', 'updated_at']
        widgets = {
        }

    def clean(self):
        """
        Base clean method that can be extended by subclasses.
        """
        cleaned_data = super().clean()
        return cleaned_data

    @classmethod
    def get_field_names(cls):
        """
        Get a list of all field names in the form.
        """
        return list(cls.base_fields.keys())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for form in self.visible_fields():
            field = form.field
            classes = field.widget.attrs.get('class', '')
            if 'form-control' not in classes:
                classes += ' form-control'
            # Si el campo es de tipo DateField o DateTimeField
            if isinstance(field, DateTimeField):
                field.widget = TextInput(attrs=field.widget.attrs)
                if 'flatpickr' not in classes:
                    classes += ' flatpickr'
                if 'flatpickr-datetime' not in classes:
                    classes += ' flatpickr-datetime'
                # 🟨 Aquí se ajusta al formato que espera Flatpickr (d/m/Y H:i)
                initial_value = self.initial.get(form.name)
                if initial_value:
                    if isinstance(initial_value, datetime):
                        field.initial = initial_value.strftime('%d/%m/%Y %H:%M')
                    else:
                        try:
                            parsed = initial_value
                            if parsed:
                                field.initial = parsed.strftime('%d/%m/%Y %H:%M')
                        except Exception:
                            pass
            elif isinstance(field, DateField):
                field.widget = TextInput(attrs=field.widget.attrs)
                if 'flatpickr' not in classes:
                    classes += ' flatpickr'
                if 'flatpickr-date' not in classes:
                    classes += ' flatpickr-date'
            field.widget.attrs['class'] = classes.strip()
            field.widget.attrs['autocomplete'] = 'off'
            field.widget.attrs['placeholder'] = form.field.label
            field.widget.attrs['size'] = '12'

            # Formatear fechas iniciales para Flatpickr
            for name, value in self.initial.items():
                if isinstance(value, datetime):
                    self.initial[name] = localtime(value).strftime("%d/%m/%Y %H:%M")
                elif isinstance(value, date):
                    self.initial[name] = value.strftime("%d/%m/%Y")


class CrispyFormMixin:
    """
    Mixin to add crispy forms functionality to forms.
    """
    form_id = None
    form_class = 'form'
    form_method = 'post'
    form_action = ''
    layout = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_crispy_form()

    def setup_crispy_form(self):
        """
        Set up the crispy form helper and layout.
        """
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Layout

        self.helper = FormHelper()
        self.helper.form_id = self.form_id
        self.helper.form_class = self.form_class
        self.helper.form_method = self.form_method
        self.helper.form_action = self.form_action

        if self.layout:
            self.helper.layout = self.layout
        else:
            self.helper.layout = Layout(*self.fields.keys())


class AjaxFormMixin:
    """
    Mixin to add AJAX functionality to forms.
    """

    def form_invalid(self, form):
        """
        Return JSON response for invalid form in AJAX requests.
        """
        from django.http import JsonResponse

        if self.request.is_ajax():
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            })
        return super().form_invalid(form)

    def form_valid(self, form):
        """
        Return JSON response for valid form in AJAX requests.
        """
        from django.http import JsonResponse

        if self.request.is_ajax():
            return JsonResponse({
                'success': True,
            })
        return super().form_valid(form)


class DateRangeFormMixin:
    """
    Mixin to add date range fields to forms.
    """
    start_date = DateField(
        label=_("Start Date"),
        required=False,
        widget=DateInput(attrs={'type': 'date'})
    )
    end_date = DateField(
        label=_("End Date"),
        required=False,
        widget=DateInput(attrs={'type': 'date'})
    )

    def clean(self):
        """
        Validate that end_date is after start_date.
        """
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise ValidationError(_("End date must be after start date."))

        return cleaned_data
