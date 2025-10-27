from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout

from core.system.enums import SystemEnum
from core.system.functions import dispatch_user
from core.system.views import AdminTemplateView


class AdminLoginView(LoginView):
    template_name = 'base/elements/pages/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        print("=== FORM INVALID DEBUG ===")
        print("Form data:", form.cleaned_data)
        print("Errors:", form.errors)
        print("Request.user:", self.request.user)
        from django.contrib.auth import authenticate
        test_user = authenticate(self.request,
                                 username=self.request.POST.get('username'),
                                 password=self.request.POST.get('password'))
        print("Manual authenticate:", test_user)
        print("==========================")
        return super().form_invalid(form)

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            login(self.request, user)

            # Return JSON response for AJAX requests
            if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': False,
                    'url': self.get_success_url()
                })

            return redirect(self.get_success_url())

        # Return JSON response for AJAX requests
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Credenciales inválidas'
            })

        return self.form_invalid(form)

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
