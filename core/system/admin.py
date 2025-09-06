from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from core.operations_panel.models.distribution_packing import DistributionPacking
from core.sales_panel.models.commercial import LeadCategory, LeadContact, LeadIndustry, LeadExpense, Lead, \
    Quotation
from core.operations_panel.models import Operation, TransportedProduct, Cargo, Route, DeliveryLocation
from core.system.models import SystemUser, Category, Section


class BaseAdmin(admin.ModelAdmin):
    """
    Base admin class with common functionality for all admin classes.
    """
    list_per_page = 25
    date_hierarchy = None

    def get_readonly_fields(self, request, obj=None):
        """
        Get readonly fields based on whether the object is being created or edited.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))

        # Add created_at and updated_at to readonly fields if they exist
        if obj:  # Editing an existing object
            if hasattr(obj, 'created_at') and 'created_at' not in readonly_fields:
                readonly_fields.append('created_at')
            if hasattr(obj, 'updated_at') and 'updated_at' not in readonly_fields:
                readonly_fields.append('updated_at')

        return readonly_fields

class BaseTabularInline(admin.TabularInline):
    """
    Base tabular inline class with common functionality.
    """
    extra = 1

    def get_readonly_fields(self, request, obj=None):
        """
        Get readonly fields based on whether the object is being created or edited.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))

        # Add created_at and updated_at to readonly fields if they exist
        if obj:  # Editing an existing object
            if hasattr(obj, 'created_at') and 'created_at' not in readonly_fields:
                readonly_fields.append('created_at')
            if hasattr(obj, 'updated_at') and 'updated_at' not in readonly_fields:
                readonly_fields.append('updated_at')

        return readonly_fields

class BaseStackedInline(admin.StackedInline):
    """
    Base stacked inline class with common functionality.
    """
    extra = 1

    def get_readonly_fields(self, request, obj=None):
        """
        Get readonly fields based on whether the object is being created or edited.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))

        # Add created_at and updated_at to readonly fields if they exist
        if obj:  # Editing an existing object
            if hasattr(obj, 'created_at') and 'created_at' not in readonly_fields:
                readonly_fields.append('created_at')
            if hasattr(obj, 'updated_at') and 'updated_at' not in readonly_fields:
                readonly_fields.append('updated_at')

        return readonly_fields

class TimestampedAdmin(BaseAdmin):
    """
    Admin class for models that inherit from TimestampedModel.
    """
    list_filter = ['created_at', 'updated_at']

    def get_fieldsets(self, request, obj=None):
        """
        Get fieldsets with a separate 'Timestamps' section.
        """
        fieldsets = super().get_fieldsets(request, obj)

        # Check if fieldsets is a tuple or list
        if isinstance(fieldsets, (tuple, list)):
            # Convert to list if it's a tuple
            fieldsets = list(fieldsets)

            # Add a 'Timestamps' fieldset
            timestamp_fields = []
            if hasattr(self.model, 'created_at'):
                timestamp_fields.append('created_at')
            if hasattr(self.model, 'updated_at'):
                timestamp_fields.append('updated_at')
            if hasattr(self.model, 'published_at'):
                timestamp_fields.append('published_at')

            if timestamp_fields:
                fieldsets.append(
                    (_('Timestamps'), {
                        'fields': timestamp_fields,
                        'classes': ('collapse',),
                    })
                )

        return fieldsets

class SoftDeleteAdmin(BaseAdmin):
    """
    Admin class for models that inherit from SoftDeleteModel.
    """
    list_filter = ['deleted_at']

    def get_queryset(self, request):
        """
        Get queryset that includes soft-deleted items.
        """
        qs = self.model.objects.all()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_fieldsets(self, request, obj=None):
        """
        Get fieldsets with a separate 'Deletion' section.
        """
        fieldsets = super().get_fieldsets(request, obj)

        # Check if fieldsets is a tuple or list
        if isinstance(fieldsets, (tuple, list)):
            # Convert to list if it's a tuple
            fieldsets = list(fieldsets)

            # Add a 'Deletion' fieldset if the object has been deleted
            if obj and hasattr(obj, 'deleted_at') and obj.deleted_at:
                fieldsets.append(
                    (_('Deletion'), {
                        'fields': ['deleted_at'],
                        'classes': ('collapse',),
                    })
                )

        return fieldsets

class ActiveAdmin(BaseAdmin):
    """
    Admin class for models that inherit from ActiveModel.
    """
    list_filter = ['is_active']

    def get_fieldsets(self, request, obj=None):
        """
        Get fieldsets with a separate 'Status' section.
        """
        fieldsets = super().get_fieldsets(request, obj)

        # Check if fieldsets is a tuple or list
        if isinstance(fieldsets, (tuple, list)):
            # Convert to list if it's a tuple
            fieldsets = list(fieldsets)

            # Add a 'Status' fieldset
            if hasattr(self.model, 'is_active'):
                fieldsets.append(
                    (_('Status'), {
                        'fields': ['is_active'],
                    })
                )

        return fieldsets


class SystemUserAdmin(UserAdmin):
    """
    Admin class for the SystemUser model.
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'system', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'system')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('System info'), {'fields': ('system', 'user', 'telegram_username', 'calendar_url', 'doc_nombre', 'doc_cargo', 'doc_tel', 'doc_mail')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('System info'), {'fields': ('system', 'user', 'telegram_username', 'calendar_url', 'doc_nombre', 'doc_cargo', 'doc_tel', 'doc_mail')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    raw_id_fields = ('user',)


# Register models with the admin site
admin.site.register(SystemUser, SystemUserAdmin)
admin.site.register(Category)
admin.site.register(Section)
admin.site.register(Operation)
admin.site.register(TransportedProduct)
admin.site.register(Cargo)
admin.site.register(Route)
admin.site.register(DeliveryLocation)
admin.site.register(DistributionPacking)

admin.site.register(LeadCategory)
admin.site.register(LeadContact)
admin.site.register(LeadIndustry)
admin.site.register(LeadExpense)
admin.site.register(Lead)
admin.site.register(Quotation)
