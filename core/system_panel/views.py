from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from core.system.models import Category, Section
from core.system.views import AdminTemplateView, AdminListView
from core.system_panel.forms import CategoryForm, SectionForm, AssistantForm
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
