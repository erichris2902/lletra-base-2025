from core.system.forms import BaseModelForm
from core.admin_panel.models.purchase_order import PurchaseOrder


class PurchaseOrderSupplierInvoiceForm(BaseModelForm):
    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "supplier_invoice_pdf", "size": 6},
                {"name": "supplier_invoice_xml", "size": 6},
            ]
        },
    ]

    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier_invoice_pdf",
            "supplier_invoice_xml",
        ]