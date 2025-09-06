from django.urls import path

from . import views
from .views import *

app_name = 'facturapi'

urlpatterns = [
    # Invoice downloads
    path('invoices/<uuid:invoice_id>/download/pdf/', views.download_invoice_pdf, name='download_invoice_pdf'),
    path('invoices/<uuid:invoice_id>/download/xml/', views.download_invoice_xml, name='download_invoice_xml'),
    path('invoices/<uuid:invoice_id>/download/zip/', views.download_invoice_zip, name='download_invoice_zip'),
    path('invoices/<uuid:invoice_id>/download/acuse/', views.download_invoice_acuse, name='download_invoice_acuse'),

    path("taxes/", TaxListView.as_view(), name="facturapi_taxes"),                          # CHECK
    path("invoice/", InvoiceFormView.as_view(), name="facturapi_taxes"),                    # CHECK
    path("invoice/cancels/", CanceledInvoiceListView.as_view(), name="facturapi_taxes"),    # CHECK
    path("invoice/general/", InvoiceListView.as_view(), name="facturapi_taxes"),            # CHECK
    path("invoice/incomes/", IncomeInvoiceListView.as_view(), name="facturapi_taxes"),      # CHECK
    path("invoice/outcomes/", OutcomeInvoiceListView.as_view(), name="facturapi_taxes"),    # CHECK
    path("invoice/payments/", PaymentInvoiceListView.as_view(), name="facturapi_taxes"),    # CHECK
    path("invoice/translate/", TranslateInvoiceListView.as_view(), name="facturapi_taxes"),    # CHECK
    path("products/", ProductListView.as_view(), name="facturapi_products"),                # CHECK

    # API endpoints
    # path('api/customers/create/', views.create_customer_view, name='api_create_customer'),
    # path('api/products/create/', views.create_product_view, name='api_create_product'),
    # path('api/taxes/create/', views.create_tax_view, name='api_create_tax'),
    # path('api/invoices/create/', views.create_invoice_view, name='api_create_invoice'),
    # path('api/invoices/cancel/', views.cancel_invoice_view, name='api_cancel_invoice'),
]
