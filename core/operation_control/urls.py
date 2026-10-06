from django.urls import path

from core.operation_control import views

app_name = "operation_control"

urlpatterns = [
    # HTML pages
    path("", views.master_list, name="list"),
    path("master-edit/finance/", views.master_edit_finance, name="master_edit_finance"),

    # API endpoints
    path("api/list/", views.api_list, name="api_list"),
    path("api/update-field/", views.api_update_field, name="api_update_field"),
    path("api/update/finance/", views.api_update_finance, name="api_update_finance"),

    # Export
    path("export/", views.export, name="export"),
]
