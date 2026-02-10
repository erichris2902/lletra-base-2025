from decimal import Decimal, ROUND_HALF_UP

from django.shortcuts import get_object_or_404

from core.operations_panel.models import Supplier
from core.supplier_panel.forms import PaymentRequestInvoiceForm, PaymentRequestCommentsForm, \
    PaymentRequestComplementForm
from core.supplier_panel.models import PaymentRequest
from core.system.views import AdminTemplateView, AdminListView
import xml.etree.ElementTree as ET

class SupplierListView(AdminListView):
    model = PaymentRequest
    form = PaymentRequestInvoiceForm
    template_name = 'base/elements/views/supplier_panel/datatable_list.html'
    datatable_headers = ["Control Vehicular", "Monto", "Status"]
    datatable_keys = ["vehicle_control", "amount_before_taxes", "status"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Facturas'
    category = 'Facturacion'

    def handle_add(self, request, data):
        form = self.form(request.POST, request.FILES)

        if not form.is_valid():
            data["error"] = form.errors
            return data

        xml_file = request.FILES.get("invoice_xml")
        expected_rfc = Supplier.objects.get(code=self.request.user.username).rfc
        expected_amount = form.cleaned_data.get("amount_before_taxes")

        ok, err = validate_cfdi_xml(
            xml_file=xml_file,
            expected_rfc=expected_rfc,
            expected_subtotal=expected_amount,
            rfc_from="emisor",  # o "receptor" según tu regla
        )

        if not ok:
            data["error"] = err
            return data


        instance = form.save()
        instance.status = 'revision'
        instance.user = request.user
        instance.save()
        data["success"] = True
        data["id"] = str(instance.id)
        return data

    def handle_update(self, request, data):
        instance = get_object_or_404(self.model, pk=request.POST.get('id'))
        instance, errors = self.save_form(request, instance=instance)
        if instance:
            data['success'] = True
            data['id'] = str(instance.id)
        else:
            data['error'] = errors
        return data

    def handle_get(self, request, data):
        obj_id = request.POST.get('id')
        if obj_id == '-1':
            instance = self.model()
            self.form_action = "Add"
        else:
            instance = get_object_or_404(self.model, pk=obj_id)
            if instance.status == 'revision':
                self.form = PaymentRequestCommentsForm
            elif instance.status == 'aprobada':
                self.form = PaymentRequestComplementForm
            self.form_action = "Update"
        data['id'] = str(instance.id)
        data['form'] = self.render_form(request, instance)
        return data

    def get_queryset(self):
        qs = self.model.objects.filter(user=self.request.user)
        return qs




def _norm_money(value: Decimal) -> Decimal:
    # Normaliza a 2 decimales para comparar
    return (value or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_cfdi_xml(xml_file, expected_rfc: str, expected_subtotal: Decimal, rfc_from="emisor"):
    """
    Valida:
    - RFC dentro del XML (Emisor o Receptor)
    - SubTotal del CFDI contra el monto capturado

    rfc_from:
      - "emisor": valida cfdi:Emisor@Rfc
      - "receptor": valida cfdi:Receptor@Rfc
    """
    if not xml_file:
        return False, "No se recibió el archivo XML."

    if not expected_rfc:
        return False, "No se pudo determinar el RFC esperado del usuario."

    try:
        # Lee bytes del archivo subido (InMemoryUploadedFile/TemporaryUploadedFile)
        print(1)
        xml_bytes = xml_file.read()
        print(xml_bytes)
        # IMPORTANTE: reset para que Django pueda volver a leer si hace falta
        xml_file.seek(0)
        print(2)
        root = ET.fromstring(xml_bytes)
        print(root)

        # Namespace del CFDI (viene en el tag: {namespace}Comprobante)
        ns_uri = ""
        if root.tag.startswith("{") and "}" in root.tag:
            ns_uri = root.tag.split("}")[0][1:]
        ns = {"cfdi": ns_uri} if ns_uri else {}

        # Root debe ser Comprobante
        # SubTotal está en el atributo SubTotal del Comprobante
        subtotal_str = root.attrib.get("SubTotal") or root.attrib.get("subTotal")  # por si acaso
        if not subtotal_str:
            return False, "El XML no contiene el atributo SubTotal en Comprobante."

        xml_subtotal = _norm_money(Decimal(subtotal_str))
        expected_subtotal = _norm_money(Decimal(expected_subtotal))

        # Buscar RFC
        if rfc_from == "receptor":
            receptor = root.find("cfdi:Receptor", ns) if ns else root.find("Receptor")
            if receptor is None:
                return False, "El XML no contiene el nodo Receptor."
            xml_rfc = (receptor.attrib.get("Rfc") or receptor.attrib.get("RFC") or "").strip().upper()
        else:
            emisor = root.find("cfdi:Emisor", ns) if ns else root.find("Emisor")
            if emisor is None:
                return False, "El XML no contiene el nodo Emisor."
            xml_rfc = (emisor.attrib.get("Rfc") or emisor.attrib.get("RFC") or "").strip().upper()

        expected_rfc = expected_rfc.strip().upper()

        if xml_rfc != expected_rfc:
            return False, f"RFC no coincide. XML: {xml_rfc} vs esperado: {expected_rfc}"

        if xml_subtotal != expected_subtotal:
            return False, f"El SubTotal del XML ({xml_subtotal}) no coincide con el monto capturado ({expected_subtotal})."

        return True, None

    except ET.ParseError:
        return False, "El archivo XML no es válido (no se pudo parsear)."
    except Exception as e:
        return False, f"Error validando XML: {e}"