from django.contrib.auth.mixins import LoginRequiredMixin

from core.system.views import AdminTemplateView


class DashboardView(LoginRequiredMixin, AdminTemplateView):
    """
    Dashboard view for OPERACIONES users.
    """
    template_name = 'operations_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard de Operaciones'
        return context


