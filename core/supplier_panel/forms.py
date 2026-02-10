from core.operations_panel.models.address import Address
from core.supplier_panel.models import PaymentRequest
from core.system.forms import BaseModelForm

class PaymentRequestInvoiceForm(BaseModelForm):

    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "invoice_pdf", "size": 6},
                {"name": "invoice_xml", "size": 6},
            ]
        },
        {
            "type": "row",
            "fields": [
                {"name": "vehicle_control", "size": 6},
                {"name": "amount_before_taxes", "size": 6},
            ]
        },
    ]

    class Meta:
        model = PaymentRequest
        fields = [
            "invoice_pdf",
            "invoice_xml",
            "vehicle_control",
            "amount_before_taxes",
        ]

class PaymentRequestCommentsForm(BaseModelForm):

    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "comments", "size": 12},
            ]
        },
    ]

    class Meta:
        model = PaymentRequest
        fields = [
            "comments",
        ]

class PaymentRequestComplementForm(BaseModelForm):

    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "payment_complement_pdf", "size": 6},
                {"name": "payment_complement_xml", "size": 6},
            ]
        },
    ]

    class Meta:
        model = PaymentRequest
        fields = [
            "payment_complement_pdf",
            "payment_complement_xml",
        ]


class PaymentRequestCompleteForm(BaseModelForm):

    layout = [
        {
            "type": "row",
            "fields": [
                {"name": "status", "size": 4},
                {"name": "vehicle_control", "size": 4},
                {"name": "amount_before_taxes", "size": 4},
            ]
        },
        {
            "type": "row",
            "fields": [
                {"name": "invoice_pdf", "size": 6},
                {"name": "invoice_xml", "size": 6},
            ]
        },
        {
            "type": "row",
            "fields": [
                {"name": "payment_complement_pdf", "size": 6},
                {"name": "payment_complement_xml", "size": 6},
            ]
        },
        {
            "type": "row",
            "fields": [
                {"name": "comments", "size": 12},
            ]
        },
    ]

    class Meta:
        model = PaymentRequest
        fields = [
            "invoice_pdf",
            "invoice_xml",
            "status",
            "vehicle_control",
            "amount_before_taxes",
            "payment_complement_pdf",
            "payment_complement_xml",
            "comments",
        ]