from django.urls import path, include
from . import views
from ..system.catalog_view import CatalogView

app_name = 'system_panel'

urlpatterns = [
    # Dashboard URL for SYSTEM users
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    path('sections/', views.SectionListView.as_view(), name='sections'),
    path('assistants/', views.AssistantListView.as_view(), name='assistants'),
    path('catalog', CatalogView.as_view(), name='catalog'),

    path('facturapi/', include("apps.facturapi.urls")),
]
