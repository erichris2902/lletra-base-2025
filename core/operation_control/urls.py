from django.urls import path

from core.operation_control import views

app_name = "operation_control"

urlpatterns = [
    # HTML pages
    path("", views.master_list, name="list"),

    # API endpoints
    path("api/list/", views.api_list, name="api_list"),
    path("api/update-field/", views.api_update_field, name="api_update_field"),
]
