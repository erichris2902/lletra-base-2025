from django.contrib import admin

from apps.facturapi.models import FacturapiInvoice, FacturapiTax, FacturapiProduct, FacturapiInvoiceItem, \
    FacturapiInvoicePayment

# Register your models here.
admin.site.register(FacturapiInvoice)
admin.site.register(FacturapiTax)
admin.site.register(FacturapiProduct)
admin.site.register(FacturapiInvoiceItem)
admin.site.register(FacturapiInvoicePayment)