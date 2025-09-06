# System App

This Django app provides a solid foundation of abstract models, forms, views, and templates that can be extended by other apps in the project. It serves as a base layer for building consistent and maintainable applications.

## Features

- Abstract models with common fields and functionality
- Base form classes with validation and utility methods
- Base view classes for common CRUD operations
- Base templates that can be extended for consistent UI

## Models

### BaseModel

An abstract model that provides common fields for all models:

```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
```

### ActiveModel

An abstract model that extends BaseModel with an active status field:

```python
class ActiveModel(BaseModel):
    is_active = models.BooleanField(_("Is active"), default=True)
    
    class Meta:
        abstract = True
```

### TimestampedModel

An abstract model that extends BaseModel with additional timestamp fields:

```python
class TimestampedModel(BaseModel):
    published_at = models.DateTimeField(_("Published at"), null=True, blank=True)
    
    def publish(self):
        self.published_at = timezone.now()
        self.save(update_fields=['published_at'])
    
    class Meta:
        abstract = True
```

### OrderedModel

An abstract model that extends BaseModel with ordering capabilities:

```python
class OrderedModel(BaseModel):
    order = models.PositiveIntegerField(_("Order"), default=0)
    
    class Meta:
        abstract = True
        ordering = ['order', '-created_at']
```

### SoftDeleteModel

An abstract model that extends BaseModel with soft delete functionality:

```python
class SoftDeleteModel(BaseModel):
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)
    
    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)
    
    class Meta:
        abstract = True
```

### SlugModel

An abstract model that extends BaseModel with a slug field:

```python
class SlugModel(BaseModel):
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    
    class Meta:
        abstract = True
```

## Forms

### BaseForm

A base form class with common functionality for all forms:

```python
class BaseForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
    
    @classmethod
    def get_field_names(cls):
        return list(cls.base_fields.keys())
```

### BaseModelForm

A base model form class with common functionality for all model forms:

```python
class BaseModelForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
    
    @classmethod
    def get_field_names(cls):
        return list(cls.base_fields.keys())
```

### Form Mixins

- **CrispyFormMixin**: Adds crispy forms functionality to forms
- **AjaxFormMixin**: Adds AJAX functionality to forms
- **DateRangeFormMixin**: Adds date range fields to forms

## Views

### Base Views

- **BaseView**: Base view class with common functionality
- **BaseTemplateView**: Base template view class
- **BaseListView**: Base list view class with pagination
- **BaseDetailView**: Base detail view class
- **BaseCreateView**: Base create view class with success messages
- **BaseUpdateView**: Base update view class with success messages
- **BaseDeleteView**: Base delete view class with success messages
- **BaseFormView**: Base form view class with success messages

### View Mixins

- **AjaxViewMixin**: Adds AJAX functionality to views
- **SecureViewMixin**: Adds security to views
- **FilteredListViewMixin**: Adds filtering to list views

## Templates

### Base Templates

- **base.html**: Main layout template with common elements
- **form.html**: Template for rendering forms
- **list.html**: Template for rendering lists of objects
- **detail.html**: Template for displaying object details

## Admin

### Base Admin Classes

- **BaseAdmin**: Base admin class with common functionality
- **BaseTabularInline**: Base tabular inline class
- **BaseStackedInline**: Base stacked inline class
- **TimestampedAdmin**: Admin class for TimestampedModel
- **SoftDeleteAdmin**: Admin class for SoftDeleteModel
- **ActiveAdmin**: Admin class for ActiveModel

## Usage

### Extending Models

```python
from core.system.models import BaseModel, ActiveModel


class MyModel(ActiveModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
```

### Extending Forms

```python
from core.system.forms import BaseModelForm, CrispyFormMixin


class MyModelForm(CrispyFormMixin, BaseModelForm):
    class Meta:
        model = MyModel
        fields = ['name', 'description', 'is_active']
```

### Extending Views

```python
from core.system.views import BaseListView, BaseDetailView


class MyModelListView(BaseListView):
    model = MyModel
    template_name = 'myapp/mymodel_list.html'


class MyModelDetailView(BaseDetailView):
    model = MyModel
    template_name = 'myapp/mymodel_detail.html'
```

### Extending Templates

```html
{% extends "system/base.html" %}

{% block content %}
<h1>My Custom Content</h1>
<p>This extends the base template from the system app.</p>
{% endblock %}
```

### Extending Admin

```python
from core.system import ActiveAdmin


@admin.register(MyModel)
class MyModelAdmin(ActiveAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
```