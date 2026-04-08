import dateutil
from dateutil.utils import today
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest, HttpResponse
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment
from openpyxl.styles.borders import BORDER_THIN

from core.operations_panel.choices import AsturianoPacking
from core.operations_panel.models import Operation, TransportedProduct, Client
from core.operations_panel.models.distribution_packing import DistributionPacking
from core.operations_panel.views.report.attendance import report_attendance
from core.operations_panel.views.report.invoice import report_xml_invoices
from core.operations_panel.views.report.worksheet_folio_operation import report_xml_worksheet_folios_by_date, \
    report_xml_worksheet_folios_by_folio
from core.system.models import Category, Section
from core.system.views import AdminTemplateView, AdminListView
from core.system_panel.forms import CategoryForm, SectionForm, AssistantForm, ActionEngineForm, ReportEngineForm, \
    ReportEngineByFolioForm
from apps.openai_assistant.models import Assistant


class DashboardView(LoginRequiredMixin, AdminTemplateView):
    """
    Dashboard view for SYSTEM users.
    """
    template_name = 'system_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard de Sistema'
        return context

class CategoryListView(AdminListView):
    model = Category
    form = CategoryForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Prioridad", "URL", "Sistema"]
    datatable_keys = ["name", "priority", "url", "system"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Categorias de las barras de navegacion'
    category = 'Sidebar'

class SectionListView(AdminListView):
    model = Section
    form = SectionForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Prioridad", "URL", "Categoria", "Activo"]
    datatable_keys = ["name", "priority", "url", "category", "is_active"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Secciones de las barras de navegacion'
    category = 'Sidebar'

class AssistantListView(AdminListView):
    model = Assistant
    form = AssistantForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Command", "Modelo", "Activo"]
    datatable_keys = ["name", "telegram_command", "model", "is_active"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Asistentes de IA'
    category = 'OpenAI'


class ActionEngineView(AdminTemplateView):
    template_name = 'system_panel/actions_form.html'

    form_action = "ExecuteActionEngine"
    form_type = "vertical"
    title = "Motor de acciones"
    section = "Motor de acciones"
    category = "Facturacion MX"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ActionEngineForm()
        context.update({
            'form_action': self.form_action,
            'form': form,
            'form_type': self.form_type,
            'add_form_layout': getattr(form, 'layout', []),
            'add_form_fields': {name: form[name] for name in form.fields},
            'title': self.title,
            'category': self.category,
            'section': self.section,
        })
        return context

class ReportEngineView(AdminTemplateView):
    template_name = 'system_panel/reports_form.html'

    form_action = "ExecuteReportEngine"
    form_type = "vertical"
    title = "Motor de reportes"
    section = "Motor de reportes"
    category = "Reporteria"

    def post(self, request, *args, **kwargs):
        from django.utils.dateparse import parse_date
        report_type = request.POST.get("report_type")
        start_date = parse_date(request.POST.get("fecha_inicial"))
        end_date = parse_date(request.POST.get("fecha_final"))

        if not report_type or not start_date or not end_date:
            return HttpResponseBadRequest("Faltan parámetros: tipo, fecha de inicio o fecha de fin")
        print(request.POST)
        if report_type == "folios":
            return report_xml_worksheet_folios_by_date(request)
        elif report_type == "facturacion":
            return report_xml_invoices(request)
        elif report_type == "packing_asturiano":
            return report_asturiano(request)
        elif report_type == "asistencia":
            return report_attendance(request)

        return HttpResponseBadRequest("Tipo de reporte no reconocido.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_form = ReportEngineForm()
        report_form.fields["fecha_inicial"].initial = today()
        report_form.fields["fecha_final"].initial = today() + dateutil.relativedelta.relativedelta(days=1)
        form = report_form
        context.update({
            'form_action': self.form_action,
            'form': form,
            'form_type': self.form_type,
            'add_form_layout': getattr(form, 'layout', []),
            'add_form_fields': {name: form[name] for name in form.fields},
            'title': self.title,
            'category': self.category,
            'section': self.section,
        })
        return context

class ReportEngineByFolioView(ReportEngineView):
    template_name = 'system_panel/reports_form.html'

    form_action = "ExecuteReportEngine"
    form_type = "vertical"
    title = "Motor de reportes por folio"
    section = "Motor de reportes por folio"
    category = "Reporteria"

    def post(self, request, *args, **kwargs):
        from django.utils.dateparse import parse_date
        print(request.POST)
        report_type = request.POST.get("report_type")
        folio_serie = parse_date(request.POST.get("folio_serie"))
        folio_number = parse_date(request.POST.get("folio_number"))

        if report_type == "folios":
            return report_xml_worksheet_folios_by_folio(request)
        elif report_type == "facturacion":
            return report_xml_invoices(request)
        elif report_type == "asistencia":
            return report_attendance(request)

        return HttpResponseBadRequest("Tipo de reporte no reconocido.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_form = ReportEngineByFolioForm()
        form = report_form
        context.update({
            'form_action': self.form_action,
            'form': form,
            'form_type': self.form_type,
            'add_form_layout': getattr(form, 'layout', []),
            'add_form_fields': {name: form[name] for name in form.fields},
            'title': self.title,
            'category': self.category,
            'section': self.section,
        })
        return context


def report_asturiano(request):
    fecha_inicio = request.POST.get("fecha_inicial")
    fecha_fin = request.POST.get("fecha_final")
    operations = Operation.objects.filter(
        operation_date__range=[fecha_inicio, fecha_fin],

    ).order_by("operation_date")
    wb = Workbook()
    ws = None
    date_title = ""
    base_col = 0
    clients = [
        Client.objects.get(name__icontains="Asturiano"),
        Client.objects.get(name__icontains="Asturito"),
    ]
    for operation in Operation.objects.filter(client__in=clients).filter(operation_date__range=[fecha_inicio, fecha_fin]).order_by("operation_date").all():

        if date_title != str(operation.operation_date):
            date_title = str(operation.operation_date)
            ws = wb.create_sheet(operation.folio)
            ws.title = date_title
            base_col = 0
        else:
            base_col += 8

        ws['A' + str(base_col + 1)] = operation.folio
        ws['A' + str(base_col + 2)] = 'CLIENTE'
        ws['A' + str(base_col + 3)] = 'OPERADOR'
        ws['A' + str(base_col + 4)] = 'PLACAS'
        ws['A' + str(base_col + 5)] = 'RUTA'
        ws['C' + str(base_col + 4)] = 'ECONOMICO'
        ws['C' + str(base_col + 5)] = 'ENTREGAS'
        ws['E' + str(base_col + 4)] = 'PROVEEDOR'

        ws['A' + str(base_col + 6)] = 'CANTIDAD'
        ws['B' + str(base_col + 6)] = 'DESCRIPCION'
        ws['C' + str(base_col + 6)] = 'PESO'
        ws['D' + str(base_col + 6)] = 'CLAVE'
        ws['E' + str(base_col + 6)] = 'TIENDA'
        ws['F' + str(base_col + 6)] = 'CLASIF'

        ws['B' + str(base_col + 2)] = str(operation.client)
        ws['B' + str(base_col + 3)] = str(operation.driver)
        if operation.vehicle:
            ws['B' + str(base_col + 4)] = str(operation.vehicle.license_plate)
            ws['B' + str(base_col + 5)] = str("")
            ws['D' + str(base_col + 4)] = str(operation.vehicle)
        ws['D' + str(base_col + 5)] = ""
        ws['E' + str(base_col + 5)] = str(operation.driver)

        ws.merge_cells(start_row=base_col + 1, start_column=1, end_row=base_col + 1, end_column=6)
        ws.merge_cells(start_row=base_col + 2, start_column=2, end_row=base_col + 2, end_column=6)
        ws.merge_cells(start_row=base_col + 3, start_column=2, end_row=base_col + 3, end_column=6)
        ws.merge_cells(start_row=base_col + 4, start_column=5, end_row=base_col + 4, end_column=6)
        ws.merge_cells(start_row=base_col + 5, start_column=5, end_row=base_col + 5, end_column=6)

        titleFill = PatternFill(start_color='EBA67D',
                                end_color='EBA67D',
                                fill_type='solid',
                                )
        thin_border = Border(
            left=Side(border_style=BORDER_THIN, color='00000000'),
            right=Side(border_style=BORDER_THIN, color='00000000'),
            top=Side(border_style=BORDER_THIN, color='00000000'),
            bottom=Side(border_style=BORDER_THIN, color='00000000')
        )

        ws['A' + str(base_col + 1)].fill = titleFill
        ws['A' + str(base_col + 2)].fill = titleFill
        ws['A' + str(base_col + 3)].fill = titleFill
        ws['A' + str(base_col + 4)].fill = titleFill
        ws['A' + str(base_col + 5)].fill = titleFill
        ws['C' + str(base_col + 4)].fill = titleFill
        ws['C' + str(base_col + 5)].fill = titleFill
        ws['E' + str(base_col + 4)].fill = titleFill

        ws['A' + str(base_col + 6)].fill = titleFill
        ws['B' + str(base_col + 6)].fill = titleFill
        ws['C' + str(base_col + 6)].fill = titleFill
        ws['D' + str(base_col + 6)].fill = titleFill
        ws['E' + str(base_col + 6)].fill = titleFill
        ws['F' + str(base_col + 6)].fill = titleFill

        controlador = base_col + 7

        # for transportedProduct in operation.transported_products.all():
        #     # Cantidad
        #     ws.cell(row=controlador, column=1).value = str(transportedProduct.amount)
        #     # Descripcion
        #     ws.cell(row=controlador, column=2).value = str(transportedProduct.description)
        #     # Peso
        #     ws.cell(row=controlador, column=3).value = str(transportedProduct.weight)
        #     # Clave
        #     ws.cell(row=controlador, column=4).value = str(transportedProduct.transported_product_key)
        #     # Destino
        #     if operation.route:
        #         ws.cell(row=controlador, column=5).value = str(operation.route.destination_location)
        #     # Clasif


        for packing in DistributionPacking.objects.filter(operation=operation).all():
            ws.cell(row=controlador, column=1).value = str(packing.amount)
            ws.cell(row=controlador, column=2).value = str(packing.distribution)
            ws.cell(row=controlador, column=3).value = str(packing.weight)
            if packing.distribution == AsturianoPacking.CVZ:
                ws.cell(row=controlador, column=4).value = str(50202201)
            else:
                ws.cell(row=controlador, column=4).value = str(24121804)
            ws.cell(row=controlador, column=5).value = str(packing.delivery_shop.name)
            controlador += 1
            base_col += 1

        dims = {}
        i = 1
        for row in ws.rows:
            j = 1
            for cell in row:
                ws.cell(row=i, column=j).border = thin_border
                ws.cell(row=i, column=j).alignment = Alignment(horizontal='center')
                if cell.value:
                    dims[cell.column_letter] = max((dims.get(cell.column_letter, 0), len(str(cell.value)) + 10))
                j += 1
            i += 1
        for col, value in dims.items():
            ws.column_dimensions[col].width = 20

    # Establecer el nombre de mi archivo
    nombre_archivo = "Packing" + str(operation.folio) + ".xlsx"
    # Definir el tipo de respuesta que se va a dar
    response = HttpResponse(content_type="application/ms-excel")
    contenido = "attachment; filename = {0}".format(nombre_archivo)
    response["Content-Disposition"] = contenido
    wb.save(response)
    return response