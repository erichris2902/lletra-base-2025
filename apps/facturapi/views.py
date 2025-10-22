import json
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse

from django.utils.safestring import mark_safe

from core.operations_panel.models import Client
from core.system.views import AdminListView, AdminTemplateView, PopupView
from . import services
from .forms import FacturapiTaxForm, FacturapiInvocieForm, SelectItemForm, FacturapiProductForm, \
    FacturapiInvoicePaymentForm, FacturapiCancelInvoiceForm
from .models import FacturapiInvoice, FacturapiTax, FacturapiInvoicePayment
from .models import FacturapiProduct, FacturapiInvoiceItem

PRODUCT_KEY_RE = re.compile(r'^products\[(\d+)\]\[(\w+)\]$')
PAYMENT_KEY_RE = re.compile(r'^payments\[(\d+)\]\[(\w+)\]$')


def _to_decimal(val, q='0.00'):
    """Convierte a Decimal de forma segura."""
    try:
        return Decimal(str(val)).quantize(Decimal(q), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0.00').quantize(Decimal(q), rounding=ROUND_HALF_UP)

def extract_payments_from_post(post):
    grouped = defaultdict(dict)

    # Usamos .lists() para conservar arrays (p.ej. tax_ids con múltiples valores)
    for key, values in post.lists():
        m = PAYMENT_KEY_RE.match(key)
        if not m:
            continue
        idx, field = m.groups()
        idx = int(idx)

        if field == 'tax_ids':
            # Mantén orden y elimina duplicados/vacíos
            seen, arr = set(), []
            for v in values:
                if v and v not in seen:
                    seen.add(v)
                    arr.append(v)
            grouped[idx][field] = arr
        else:
            grouped[idx][field] = values[-1] if values else None

    # Normaliza y ordena por índice
    payments = []
    for idx in sorted(grouped.keys()):
        d = grouped[idx]

        uuid_val = (d.get('uuid') or '').strip()
        if not uuid_val:
            raise Exception(f"No hay Folio fiscal en alguno de los pagos (índice {idx}).")

        # Numéricos seguros
        amount = _to_decimal(d.get('amount', '0.00'), '0.00')
        last_balance = _to_decimal(d.get('previous_balance', '0.00'), '0.00')
        try:
            installment = int(d.get('number') or 1)
        except (TypeError, ValueError):
            installment = 1

        payments.append({
            'uuid': uuid_val.upper(),
            'amount': amount,
            'installment': installment,
            'last_balance': last_balance,
            'tax_ids': d.get('tax_ids', []),
        })

    return payments

def extract_products_from_post(post):
    """
    post: request.POST (QueryDict)
    Devuelve una lista ordenada por índice: [{'id':..., 'product':..., 'description':..., 'price':..., 'quantity':..., 'discount':..., 'tax':..., 'total':...}, ...]
    """
    grouped = defaultdict(dict)

    # Agrupa por índice: products[<idx>][<field>]
    for key, value in post.items():
        m = PRODUCT_KEY_RE.match(key)
        if not m:
            continue
        idx, field = m.groups()
        grouped[int(idx)][field] = value

    # Normaliza y ordena por índice
    items = []
    for idx in sorted(grouped.keys()):
        d = grouped[idx]
        # Saltar si no hay id de producto
        if not d.get('id'):
            continue

        # Normaliza numéricos
        d['price'] = _to_decimal(d.get('price', '0.00'), '0.00')
        d['quantity'] = _to_decimal(d.get('quantity', '0'), '0.00')
        d['discount'] = _to_decimal(d.get('discount', '0.00'), '0.00')
        d['tax'] = _to_decimal(d.get('tax', '0.0000'), '0.0000')

        # Recalcula total en servidor (no confíes en el que viene del cliente)
        base = d['price'] * d['quantity'] - d['discount']
        if base < 0:
            base = Decimal('0.00')
        total = (base + (base * d['tax'])).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        d['total'] = total

        items.append(d)

    return items


# Invoice Download Views
@login_required
def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(FacturapiInvoice, id=invoice_id)
    try:
        pdf_content = services.download_invoice_pdf(invoice.facturapi_id)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{invoice.series}-{invoice.folio_number}.pdf"'
        return response
    except Exception as e:
        print(f"Error downloading invoice PDF: {str(e)}")
        return render(request, 'facturapi/error.html', {
            'error_message': f"Error downloading invoice PDF: {str(e)}"
        })

@login_required
def download_invoice_acuse(request, invoice_id):
    invoice = get_object_or_404(FacturapiInvoice, id=invoice_id)
    try:
        pdf_content = services.download_invoice_cancellation_pdf(invoice.facturapi_id)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{invoice.series}-{invoice.folio_number} - ACUSE CANCELACION.pdf"'
        return response
    except Exception as e:
        print(f"Error downloading invoice PDF: {str(e)}")
        return render(request, 'facturapi/error.html', {
            'error_message': f"Error downloading invoice PDF: {str(e)}"
        })


@login_required
def download_invoice_xml(request, invoice_id):
    invoice = get_object_or_404(FacturapiInvoice, id=invoice_id)
    try:
        xml_content = services.download_invoice_xml(invoice.facturapi_id)
        response = HttpResponse(xml_content, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="{invoice.series}-{invoice.folio_number}.xml"'
        return response
    except Exception as e:
        print(f"Error downloading invoice XML: {str(e)}")
        return render(request, 'facturapi/error.html', {
            'error_message': f"Error downloading invoice XML: {str(e)}"
        })


@login_required
def download_invoice_zip(request, invoice_id):
    invoice = get_object_or_404(FacturapiInvoice, id=invoice_id)
    try:
        zip_content = services.download_invoice_zip(invoice.facturapi_id)
        response = HttpResponse(zip_content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{invoice.series}-{invoice.folio_number}.zip"'
        return response
    except Exception as e:
        print(f"Error downloading invoice ZIP: {str(e)}")
        return render(request, 'facturapi/error.html', {
            'error_message': f"Error downloading invoice ZIP: {str(e)}"
        })


class InvoiceFormView(AdminTemplateView):
    template_name = 'facturapi/invoice_form.html'

    form_action = "GenerateInvoice"
    form_type = "vertical"
    title = "Facturacion MX"
    section = "Facturacion MX"
    category = "Facturacion MX"

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = {}
        print(request.POST)
        try:
            action = request.POST.get('action', '').lower()
            handler = getattr(self, f'handle_{action}', None)
            if callable(handler):
                result = handler(request, data)
                if result is not None:
                    data = result
            else:
                data['error'] = f'Acción "{action}" no reconocida'
        except Exception as e:
            print(e)
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    @transaction.atomic
    def handle_generateinvoice(self, request, data):
        form = FacturapiInvocieForm(request.POST, request.FILES)
        if not form.is_valid():
            print(form.errors)
            raise Exception("Los datos ingresados no son validos")
        invoice = FacturapiInvoice()
        invoice.customer = Client.objects.get(pk=request.POST['customer'])
        invoice.payment_form = request.POST['payment_form']
        invoice.payment_method = request.POST['payment_method']
        invoice.type = request.POST['type']
        invoice.use = request.POST['use']
        invoice.currency = request.POST['currency']
        invoice.pdf_custom_section = request.POST['pdf_custom_section']
        invoice.relation_type = request.POST['relation_type']
        raw_value = request.POST.get("related_uuids", "")
        related_uuids = [u.strip() for u in raw_value.split(",") if u.strip()]
        invoice.related_uuids = related_uuids or None
        invoice.save()

        products = extract_products_from_post(request.POST)
        for p in products:
            try:
                product_obj = FacturapiProduct.objects.get(pk=p['id'])
            except FacturapiProduct.DoesNotExist:
                # Puedes decidir: saltar, o lanzar una excepción
                continue

            invoice_item = FacturapiInvoiceItem(
                invoice=invoice,
                product=product_obj,
                description=p.get('description', ''),
                quantity=p['quantity'],  # Decimal
                discount=p['discount'],  # Decimal
                unit_price=p['price'],  # Decimal
            )
            subtotal = (p['price'] * p['quantity']).quantize(Decimal('0.00'))
            invoice_item.subtotal = subtotal
            invoice_item.save()
        payments = extract_payments_from_post(request.POST)
        for p in payments:
            payment_item = FacturapiInvoicePayment(
                invoice=invoice,
                uuid=p.get('uuid', ''),
                amount=p['amount'],  # Decimal
                installment=p['installment'],  # Int
                last_balance=p['last_balance'],  # Decimal
                payment_day=request.POST["payment_day"],  # Date
            )
            payment_item.save()
            if p['tax_ids']:
                payment_item.taxes.set(FacturapiTax.objects.filter(pk__in=p['tax_ids']))
            payment_item.save()
        invoice.idempotency_key = invoice.pk
        invoice.status = "pending"
        invoice.is_ready_to_stamp = True
        invoice.save()

        invoice.bill()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pages'] = []

        context["form_action"] = self.form_action
        context["form_invoice"] = FacturapiInvocieForm()
        context["form_product"] = SelectItemForm()
        context["payment_form"] = FacturapiInvoicePaymentForm()
        context["tax_form"] = FacturapiProductForm()
        context['add_form_layout'] = getattr(FacturapiInvocieForm, 'layout', []),

        taxes = list(FacturapiTax.objects.values('id', 'name', 'type', 'rate', 'factor', 'withholding'))
        context['taxes_json'] = mark_safe(json.dumps(taxes, cls=DjangoJSONEncoder))

        context.update({
            'title': self.title,
            'category': self.category,
            'section': self.section,
            'form_type': self.form_type,
            'add_form_layout': getattr(context["form_invoice"], 'layout', []),
            'add_form_fields': {name: context["form_invoice"][name] for name in context["form_invoice"].fields},
        })

        return context


class TaxListView(AdminListView):
    model = FacturapiTax
    form = FacturapiTaxForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre"]
    datatable_keys = ["name"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Impuestos'
    category = 'Facturacion MX'


class ProductListView(AdminListView):
    model = FacturapiProduct
    form = FacturapiProductForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre"]
    datatable_keys = ["name"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Productos'
    category = 'Facturacion MX'
    catalogs = [
        {
            'id': 'id_product_key',
            'service': 'ProductAndServiceCatalog',
            'placeholder': '',
        },
        {
            'id': 'id_unit_key',
            'service': 'UnitSat',
            'placeholder': '',
        },
    ]


class InvoiceListView(AdminListView):
    model = FacturapiInvoice
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Fecha", "Folio", "Status", "Cancelacion", "Folio fiscal", "Receptor", "Total", "Tipo"]
    datatable_keys = ["created_at", "folio_number", "status", "cancellation_status", "uuid", "customer", "total", "type"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    section = 'Facturas Vigentes'
    category = 'Facturacion MX'
    action_headers = False

    static_path = 'facturapi/invoice/base.html'

    def get_queryset(self):
        qs = self.model.objects.exclude(status="canceled")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs

    def handle_getcancelinvoice(self, request, data):
        obj_id = request.POST.get('id')
        instance = get_object_or_404(self.model, pk=obj_id)
        self.form_action = "Update"
        data['id'] = str(instance.id)
        data['form'] = self.render_cancel_form(request, instance, FacturapiCancelInvoiceForm, "cancelinvoice")
        return data

    def handle_cancelinvoice(self, request, data):
        obj_id = request.POST.get('id')
        instance = get_object_or_404(self.model, pk=obj_id)
        instance.cancel(request.POST["issue"], request.POST["substitute"])


    def render_cancel_form(self, request, instance, form, action):
        form_instance = form
        context = {
            'form': form_instance,
            'form_action': action,
            'form_type': self.form_type,
            'id': instance.id if instance else None,
        }
        html = render(request, self.form_path, context)
        return html.content.decode("utf-8")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'custom_action_headers': 'facturapi/invoice_reports.html',
        })

        return context


class CanceledInvoiceListView(InvoiceListView):
    section = 'Facturas Canceladas'

    def get_queryset(self):
        qs = self.model.objects.filter(status="canceled")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs


class IncomeInvoiceListView(InvoiceListView):
    section = 'Facturas de Ingreso'

    def get_queryset(self):
        qs = self.model.objects.filter(type="I")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs


class PaymentInvoiceListView(InvoiceListView):
    section = 'Complementos de pago'

    def get_queryset(self):
        qs = self.model.objects.filter(type="P")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs


class OutcomeInvoiceListView(InvoiceListView):
    section = 'Facturas de Egreso'

    def get_queryset(self):
        qs = self.model.objects.filter(type="E")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs


class TranslateInvoiceListView(InvoiceListView):
    section = 'Facturas de Egreso'

    def get_queryset(self):
        qs = self.model.objects.filter(type="E")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs


class Report(PopupView):
    section = 'Facturas de Egreso'