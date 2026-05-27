from django.urls import path
from core.admin_panel.views import login_views as views
from ..rh_panel.views import CaptureLocationView
from core.admin_panel.views.purchase_order import (
    PurchaseOrderListView,
    purchase_order_create,
    purchase_order_detail,
    purchase_order_update_status,
    purchase_order_generate_pdf,
    get_operations_by_filter, purchase_order_generate_docx
)

app_name = 'admin_panel'

urlpatterns = [
    # Login URL
    path('', views.AdminLoginView.as_view(), name='login'),
    path('capture/', CaptureLocationView.as_view(), name='capture'),

    # Logout URL
    path('logout/', views.AdminLogoutView.as_view(), name='logout'),

    # Dispatch URL - redirects users based on their system type
    path('dispatch/', views.UserDispatchView.as_view(), name='dispatch'),

    # Dashboard URL for SYSTEM users
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('supplier/payments/', views.SupplierPaymentsListView.as_view(), name='supplier_payments'),

    path('purchase-orders/', PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/create/', purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<uuid:order_id>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<uuid:order_id>/update-status/', purchase_order_update_status,
         name='purchase_order_update_status'),
    path('purchase-orders/<uuid:order_id>/pdf/', purchase_order_generate_docx, name='purchase_order_pdf'),
    path("purchase-orders/<uuid:order_id>/docx/", purchase_order_generate_docx, name="purchase_order_docx"),

    # API endpoints
    path('api/operations/', get_operations_by_filter, name='api_operations_filter'),
]
