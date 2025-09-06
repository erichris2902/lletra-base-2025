from django.urls import path

from core.operations_panel.views.cargo import CargoListView
from core.operations_panel.views.client import ClientListView
from core.operations_panel.views.dashboards import DashboardView
from core.operations_panel.views.delivery_location import DeliveryLocationListView
from core.operations_panel.views.downloads import DownloadShipmentPDF
from core.operations_panel.views.driver import DriverListView
from core.operations_panel.views.invoice_facturapi_shipment import InvoiceShipmentIFormView
from core.operations_panel.views.operation import FolioOperationListView, OperationListView, ShipmentOperationListView
from core.operations_panel.views.route import RouteListView, RouteMapView
from core.operations_panel.views.supplier import SupplierListView
from core.operations_panel.views.transported_product import TransportedProductListView
from core.operations_panel.views.vehicle import VehicleListView

app_name = 'operations_panel'

urlpatterns = [
    # Dashboard URL for OPERACIONES users
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # Catalog URLs
    path('delivery-locations/', DeliveryLocationListView.as_view(), name='delivery_locations'),
    path('clients/', ClientListView.as_view(), name='clients'),
    path('suppliers/', SupplierListView.as_view(), name='suppliers'),
    path('drivers/', DriverListView.as_view(), name='drivers'),
    path('vehicles/', VehicleListView.as_view(), name='vehicles'),

    # Operation URLs
    path('folios/', FolioOperationListView.as_view(), name='operation_folios'),
    path('', OperationListView.as_view(), name='operations'),
#    path('/invoice/<uuid:operation_id>/', InvoiceShipmentIFormView.as_view(), name='cartaporte_i'),

    # Transported Products and Cargo URLs
    path('transported-products/', TransportedProductListView.as_view(), name='transported_products'),
    path('cargos/', CargoListView.as_view(), name='cargos'),
    
    # Route URLs
    path('routes/', RouteListView.as_view(), name='routes'),
    path('routes/<uuid:route_id>/map/', RouteMapView.as_view(), name='route_map'),

    # Route URLs
    path('shipments/', ShipmentOperationListView.as_view(), name='shipments'),

    path('generate_invoice/i/<uuid:operation_id>/', InvoiceShipmentIFormView.as_view(), name='invoice_shipment_i'),

    path('download/shipment-invoice/<uuid:operation_id>/no-signed', DownloadShipmentPDF, name='shipment_cartaporte'),
]
