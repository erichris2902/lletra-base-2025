from django.urls import path
from . import views

app_name = 'supplier_panel'

urlpatterns = [
    # Dashboard URL for SYSTEM users
    path('dashboard/', views.SupplierListView.as_view(), name='dashboard'),
    path('operations/', views.OperationSupplierListView.as_view(), name='operations'),
]
