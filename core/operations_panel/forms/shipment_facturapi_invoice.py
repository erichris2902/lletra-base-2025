from core.operations_panel.models.shipment_facturapi_invoice import ShipmentFacturapiInvoice
from core.system.forms import BaseModelForm


class ShipmentFacturapiInvoiceForm(BaseModelForm):

    layout = [
        {"type": "row", "fields": [
            {"name": "sender_name", "size": 6},
            {"name": "sender_rfc", "size": 6},
        ]},
        {"type": "row", "fields": [
            {"name": "total_distance_km", "size": 6},
            {"name": "departure_at", "size": 3},
            {"name": "scheduled_arrival_at", "size": 3},
        ]},
        {"type": "row", "fields": [
            {"name": "sct_permit_number", "size": 3},
            {"name": "insurer_name", "size": 3},
            {"name": "insurance_policy_number", "size": 3},
            {"name": "sct_permit_type", "size": 3},
        ]},
    ]
    class Meta:
        model = ShipmentFacturapiInvoice
        fields = [
            "total_distance_km",
            "departure_at",
            "scheduled_arrival_at",
            "sender_name",
            "sender_rfc",
            "sct_permit_number",
            "insurer_name",
            "insurance_policy_number",
            "sct_permit_type",
        ]