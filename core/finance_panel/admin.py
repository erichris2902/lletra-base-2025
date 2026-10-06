from django.contrib import admin

from core.finance_panel.models import ExternalFinanceCategory, ExternalFinanceEntry


@admin.register(ExternalFinanceCategory)
class ExternalFinanceCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "active")
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(ExternalFinanceEntry)
class ExternalFinanceEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "entry_type", "concept", "category", "operation", "amount", "paid")
    list_filter = ("entry_type", "paid", "category", "date")
    search_fields = ("concept", "comments", "operation__folio")
