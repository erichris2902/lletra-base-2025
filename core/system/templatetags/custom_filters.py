from django import template
from django.forms import ModelMultipleChoiceField, FileField, TimeField
from django.forms.fields import DateField, SelectMultiple
from django.utils.text import slugify

register = template.Library()

@register.filter
def is_time_field(field):
    return isinstance(field.field, TimeField)

@register.filter
def is_date_field(field):
    return isinstance(field.field, DateField)

@register.filter
def is_multiselect(field):
    return (isinstance(field.field, ModelMultipleChoiceField))

@register.filter
def is_file_field(field):
    return isinstance(field.field, FileField)

@register.filter
def slugify_filter(value):
    return slugify(value)

@register.filter
def dict_get(d, key):
    try:
        return d[key]
    except (KeyError, TypeError):
        return None