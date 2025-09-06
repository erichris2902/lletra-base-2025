import json
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.facturapi.forms import FacturapiInvocieForm
from apps.facturapi.models import FacturapiProduct, FacturapiInvoiceItem
from apps.facturapi.views import InvoiceFormView, extract_products_from_post
from core.operations_panel.forms.shipment_facturapi_invoice import ShipmentFacturapiInvoiceForm
from core.operations_panel.models.client import Client
from core.operations_panel.models.operation import Operation
from core.operations_panel.models.shipment_facturapi_invoice import ShipmentFacturapiInvoice


class InvoiceShipmentIFormView(InvoiceFormView):
    template_name = 'operations_panel/invoice_shipment_form.html'

    @transaction.atomic
    def handle_generateinvoice(self, request, data):
        operation = Operation.objects.get(id=self.kwargs['operation_id'])
        invoice_form = FacturapiInvocieForm(request.POST, request.FILES)
        shipment_form = ShipmentFacturapiInvoiceForm(request.POST, request.FILES)
        if not invoice_form.is_valid():
            raise Exception("Los datos ingresados no son validos:\n" + str(invoice_form.errors))
        if not shipment_form.is_valid():
            raise Exception("Los datos de cartaporte no son validos:\n" + str(invoice_form.errors))
        shipment_invoice = ShipmentFacturapiInvoice()
        shipment_invoice.customer = Client.objects.get(pk=request.POST['customer'])
        shipment_invoice.payment_form = request.POST['payment_form']
        shipment_invoice.payment_method = request.POST['payment_method']
        shipment_invoice.type = request.POST['type']
        shipment_invoice.use = request.POST['use']
        shipment_invoice.currency = request.POST['currency']
        shipment_invoice.pdf_custom_section = request.POST['pdf_custom_section']
        shipment_invoice.relation_type = request.POST['relation_type']
        raw_value = request.POST.get("related_uuids", "")
        related_uuids = [u.strip() for u in raw_value.split(",") if u.strip()]
        shipment_invoice.related_uuids = related_uuids or None

        shipment_invoice.operation = operation
        shipment_invoice.total_distance_km = request.POST['total_distance_km']
        shipment_invoice.departure_at = request.POST['departure_at']
        shipment_invoice.scheduled_arrival_at = request.POST['scheduled_arrival_at']
        shipment_invoice.sender_name = request.POST['sender_name']
        shipment_invoice.sender_rfc = request.POST['sender_rfc']
        shipment_invoice.sct_permit_number = request.POST['sct_permit_number']
        shipment_invoice.insurer_name = request.POST['insurer_name']
        shipment_invoice.insurance_policy_number = request.POST['insurance_policy_number']
        shipment_invoice.sct_permit_type = request.POST['sct_permit_type']

        shipment_invoice.save()

        products = extract_products_from_post(request.POST)
        for p in products:
            try:
                product_obj = FacturapiProduct.objects.get(pk=p['id'])
            except FacturapiProduct.DoesNotExist:
                raise Exception("No se encontro la instancia del producto")

            invoice_item = FacturapiInvoiceItem(
                invoice=shipment_invoice,
                product=product_obj,
                description=p.get('description', ''),
                quantity=p['quantity'],  # Decimal
                discount=p['discount'],  # Decimal
                unit_price=p['price'],  # Decimal
            )
            subtotal = (p['price'] * p['quantity']).quantize(Decimal('0.00'))
            invoice_item.subtotal = subtotal
            invoice_item.save()

        shipment_invoice.idempotency_key = operation.id
        shipment_invoice.status = "pending"
        shipment_invoice.is_ready_to_stamp = True
        shipment_invoice.save()

        shipment_invoice.bill()

    def handle_predictproduct(self, request, context):
        operation = Operation.objects.get(id=self.kwargs['operation_id'])
        if operation.origin.address.zip_code[:2] == "76" and operation.destination.address.zip_code[:2] == "76":
            productInvoice = FacturapiProduct.objects.get(sku="BASE-LOCAL")
        else:
            productInvoice = FacturapiProduct.objects.get(sku="BASE-FORANEA")
        productInvoice.name = operation.folio

        productInvoice.description = operation.folio
        productInvoice.description += " RUTA"
        productInvoice.description += ", ".join([delivery.name for delivery in operation.deliveries.all()])
        productInvoice.description += " " + operation.destination.name
        productInvoice.description += " " + operation.cargo_appointment.strftime('%d/%m/%Y')

        context["price"] = str(productInvoice.price)
        context["product"] = str(productInvoice.name)
        context["description"] = str(productInvoice.description)
        context["id"] = str(productInvoice.id)
        i = 0
        for tax in productInvoice.taxes.all():
            if tax.withholding:
                i -= tax.rate
            else:
                i += tax.rate
        context["tax"] = str(i)
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        operation = get_object_or_404(Operation, pk=self.kwargs['operation_id'])
        context["form_invoice"] = self.set_invoice_form(operation)

        context["shipment_invoice_form"] = self.set_shipment_form(operation)
        products = operation.transported_products.all()
        context['products'] = []
        for product in products:
            context['products'].append(json.loads(product.to_json()))

        context['include_invoice_prediction'] = True
        context['shipment_invoice_form_layout'] = getattr(context["shipment_invoice_form"], 'layout', [])
        context['shipment_invoice_form_fields'] = {
            name: context["shipment_invoice_form"][name] for name in context["shipment_invoice_form"].fields
        }

        context.update({
            'add_form_layout': getattr(context["form_invoice"], 'layout', []),
            'add_form_fields': {name: context["form_invoice"][name] for name in context["form_invoice"].fields},
        })

        return context

    def set_invoice_form(self, operation):
        form = FacturapiInvocieForm()
        client_choices = []
        client_choices.append((operation.client.id, str(operation.client.name)))
        form.fields['customer'].widget.choices = client_choices
        form.fields['customer'].initial = operation.client.id
        return form

    def set_shipment_form(self, operation):
        form = ShipmentFacturapiInvoiceForm()
        form.fields['total_distance_km'].initial = operation.route.optimized_distance
        form.fields['departure_at'].initial = operation.cargo_appointment
        form.fields['scheduled_arrival_at'].initial = operation.download_appointment
        form.fields['sender_name'].initial = operation.client.business_name
        form.fields['sender_rfc'].initial = operation.client.rfc
        form.fields['sct_permit_number'].initial = operation.vehicle.sct_permit if operation.vehicle.sct_permit and operation.vehicle.sct_permit != "NULL" else "0919ACA22052014021001000"
        form.fields['insurer_name'].initial = operation.vehicle.insurance_company
        form.fields['insurance_policy_number'].initial = operation.vehicle.insurance_code
        form.fields['sct_permit_type'].initial = "TPAF01"

        form.fields['total_distance_km'].widget.attrs['readonly'] = True
        form.fields['departure_at'].widget.attrs['readonly'] = True
        form.fields['scheduled_arrival_at'].widget.attrs['readonly'] = True
        form.fields['sender_name'].widget.attrs['readonly'] = True
        form.fields['sender_rfc'].widget.attrs['readonly'] = True
        form.fields['insurer_name'].widget.attrs['readonly'] = True
        form.fields['insurance_policy_number'].widget.attrs['readonly'] = True
        form.fields['sct_permit_type'].widget.attrs['readonly'] = True

        return form

