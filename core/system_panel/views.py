import dateutil
from dateutil.utils import today
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest

from core.operations_panel.views.report.attendance import report_attendance
from core.operations_panel.views.report.invoice import report_xml_invoices
from core.operations_panel.views.report.worksheet_folio_operation import report_xml_worksheet_folios_by_date
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

        if report_type == "folios":
            return report_xml_worksheet_folios_by_date(request)
        elif report_type == "facturacion":
            return report_xml_invoices(request)
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
        report_type = request.POST.get("report_type")
        start_date = parse_date(request.POST.get("fecha_inicial"))
        end_date = parse_date(request.POST.get("fecha_final"))

        if not report_type or not start_date or not end_date:
            return HttpResponseBadRequest("Faltan parámetros: tipo, fecha de inicio o fecha de fin")

        if report_type == "folios":
            return report_xml_worksheet_folios_by_date(request)
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