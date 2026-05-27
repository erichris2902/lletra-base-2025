from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout

from core.operations_panel.models import Supplier
from core.system.enums import SystemEnum
from core.system.functions import dispatch_user
from core.system.models import SystemUser
from core.system.views import AdminTemplateView


class AdminLoginView(LoginView):
    template_name = 'base/elements/pages/login.html'
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        # 1) Tomar credenciales directo del POST (sin AuthenticationForm)
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        print("=== MANUAL LOGIN DEBUG ===")
        print("POST username:", username)
        print("POST password:", password)

        # 2) Intento normal (usuario ya existe en Django)
        user = authenticate(request, username=username, password=password)
        print("authenticate normal:", user)

        # 3) Si falla, intenta tu lógica Supplier -> crear SystemUser -> autenticar
        if user is None:
            if Supplier.objects.filter(code=username, rfc=password).exists():
                user_obj = SystemUser()
                user_obj.system = SystemEnum.SUPPLIER
                user_obj.username = username
                user_obj.set_password(password)
                user_obj.save()

                user = authenticate(request, username=username, password=password)
                print("authenticate after create:", user)

        # 4) Si al final hay user, loguea y redirige / responde JSON
        if user is not None:
            login(request, user)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': False, 'url': self.get_success_url()})

            return redirect(self.get_success_url())

        # 5) Si no, devuelve error (JSON o recarga con invalid)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Credenciales inválidas'}, status=400)

        # “Forzar form_invalid” (sin usar el form real)
        # Puedes mandar un mensaje simple o usar messages framework si quieres.
        return self.render_to_response(self.get_context_data(error="Credenciales inválidas"))

    def get_success_url(self):
        """
        Return the URL to redirect to after successful login.
        """
        return reverse_lazy('admin_panel:dispatch')

class UserDispatchView(LoginRequiredMixin, TemplateView):
    """
    View that redirects users based on their system type.
    """
    template_name = 'admin_panel/dispatch.html'  # Fallback template

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # Check if user has a system type
        if user.is_authenticated:
            if hasattr(user, 'system') and user.system:
                # Redirect based on system type
                dispatch_required, redirect_url = dispatch_user(user.system)
                if dispatch_required:
                    return HttpResponseRedirect(redirect_url)
        return HttpResponseRedirect(reverse('system:LogoutView'))
        # If no specific redirect, use the parent dispatch

class DashboardView(LoginRequiredMixin, AdminTemplateView):
    """
    Dashboard view for SYSTEM users.
    """
    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard'
        return context

class AdminLogoutView(LogoutView):
    success_url = settings.LOGOUT_REDIRECT_URL

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return HttpResponseRedirect(self.success_url)


from decimal import Decimal, ROUND_HALF_UP

from django.shortcuts import get_object_or_404

from core.operations_panel.models import Supplier
from core.supplier_panel.forms import PaymentRequestInvoiceForm, PaymentRequestCommentsForm, \
    PaymentRequestComplementForm, PaymentRequestCompleteForm
from core.supplier_panel.models import PaymentRequest
from core.system.views import AdminTemplateView, AdminListView
import xml.etree.ElementTree as ET

class SupplierPaymentsListView(AdminListView):
    model = PaymentRequest
    form = PaymentRequestCompleteForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Control Vehicular", "Monto", "Status"]
    datatable_keys = ["vehicle_control", "amount_before_taxes", "status"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Pagos'
    category = 'Pago a proveedores'



    def get_queryset(self):
        qs = self.model.objects.all()
        return qs



