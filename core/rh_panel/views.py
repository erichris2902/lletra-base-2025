from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from core.system.views import AdminTemplateView


class DashboardView(LoginRequiredMixin, AdminTemplateView):
    """
    Dashboard view for RH users.
    """
    template_name = 'rh_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard de Recursos Humanos'
        return context