from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.generic import ListView, TemplateView

from core.system.functions import dispatch_user
from core.system.models import Category, Section

def log_action(user, instance, action):
    """
    Registra una acción del usuario sobre una instancia.
    Puedes modificar esto para guardar en base de datos si deseas.
    """
    model_name = instance.__class__.__name__
    print(f"[{now().strftime('%Y-%m-%d %H:%M:%S')}] {user} {action.upper()} {model_name} #{instance.pk}")

class AdminView:
    def context_data_nav(self, context, user, session=None):
        """
        Agrega categorías y secciones al contexto para navegación.
        """
        system = user.system

        # Obtiene categorías ordenadas por prioridad
        categories = Category.objects.filter(system=system).order_by("priority").all()

        # Carga secciones relacionadas (evita consultas N+1)
        for category in categories:
            category.sections_for_template = list(Section.objects.filter(category=category).order_by("priority"))


        context['navcategories'] = categories
        context['user'] = user
        return context


class AdminListView(AdminView, ListView):
    model = None
    form = None

    # UI Config
    datatable_headers = []
    datatable_keys = []
    datatable_actions = True
    action_headers = True
    title = None
    template_name = 'base/elements/views/datatable_list.html'
    form_path = 'base/elements/forms/form.html'
    form_action = "NoAction"
    form_type = "vertical"
    dropdown_path = 'base/elements/static/dropdown.js'
    dropdown_action_path = 'base/elements/table/actions.js'
    static_path = 'base/elements/table/base.html'
    section = ''
    category = ''
    catalogs = []
    callback_js = None
    search_fields = ['name', 'description', 'rfc']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.model.objects.all()
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = self.context_data_nav(context, self.request.user, self.request.session)

        context.update({
            'dropdown_path': self.dropdown_path,
            'dropdown_action_path': self.dropdown_action_path,
            'static_path': self.static_path,
            'datatable_keys': self.datatable_keys,
            'title': self.title,
            'datatable_headers': self.datatable_headers,
            'datatable_actions': self.datatable_actions,
            'category': self.category,
            'section': self.section,
            'add_form': self.form() if self.form else None,
            'catalogs': self.catalogs,
            'form_type': self.form_type,
            'action_headers': self.action_headers,
            'callback_js': self.callback_js,
            'add_form_layout': getattr(self.form() if self.form else None, 'layout', []),
        })
        return context

    def render_form(self, request, instance, form=None):
        form_instance = self.form(instance=instance) if instance else self.form()
        context = {
            'form': form_instance,
            'form_action': self.form_action,
            'form_type': self.form_type,
            'id': instance.id if instance else None,
            'add_form_layout': getattr(form_instance, 'layout', []),
            'add_form_fields': {name: form_instance[name] for name in form_instance.fields},
        }
        html = render(request, self.form_path, context)
        return html.content.decode("utf-8")

    def render_others_form(self, request, instance, form, action, data=None):
        form_instance = form
        context = {
            'form': form_instance,
            'form_action': action,
            'form_type': self.form_type,
            'id': instance.id if instance else None,
            'data': data
        }
        html = render(request, self.form_path, context)
        return html.content.decode("utf-8")

    def render_formset(self, request, queryset, form=None):
        formset = [form(instance=dp, prefix=str(dp.id)) for dp in queryset]
        context = {
            'formset': formset,
            'form_action': self.form_action,
            'form_type': self.form_type,
            'id': queryset.first().operation_id if queryset else None,
        }
        html = render(request, "base/elements/forms/render_table_form.html", context)
        return html.content.decode("utf-8")

    def save_form(self, request, instance=None):
        form = self.form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            return form.save(), None
        return None, form.errors

    def handle_searchdata(self, request, data):
        queryset = self.get_queryset()
        data = [obj.to_display_dict(keys=self.datatable_keys) for obj in queryset]
        return data

    def handle_add(self, request, data):
        instance, errors = self.save_form(request)
        if instance:
            log_action(request.user, instance, "create")
            data['success'] = True
            data['id'] = str(instance.id)
        else:
            data['error'] = str(errors)
        return data

    def handle_get(self, request, data):
        obj_id = request.POST.get('id')
        if obj_id == '-1':
            instance = self.model()
            self.form_action = "Add"
        else:
            instance = get_object_or_404(self.model, pk=obj_id)
            self.form_action = "Update"
        data['id'] = str(instance.id)
        data['form'] = self.render_form(request, instance)
        return data

    def handle_update(self, request, data):
        instance = get_object_or_404(self.model, pk=request.POST.get('id'))
        instance, errors = self.save_form(request, instance=instance)
        if instance:
            log_action(request.user, instance, "update")
            data['success'] = True
            data['id'] = str(instance.id)
        else:
            data['error'] = errors
        return data

    def handle_delete(self, request, data):
        instance = get_object_or_404(self.model, pk=request.POST.get('id'))
        log_action(request.user, instance, "delete")
        instance.delete()
        data['success'] = True
        return data

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


class AdminTemplateView(AdminView, TemplateView):
    """
    Vista base para plantillas protegidas con navegación del sistema y dispatch inteligente.
    Herédala para crear páginas personalizadas de administración.
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            self.user = request.user
            dispatch, url = dispatch_user(request.user.system)
            if dispatch:
                return HttpResponseRedirect(url)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Construye el contexto común para todas las vistas administrativas.
        Incluye navegación, sistema y usuario actual.
        """
        context = super().get_context_data(**kwargs)
        context = self.context_data_nav(context, self.request.user, self.request.session)
        return context


class PopupView(AdminView, TemplateView):
    """
    Vista base para plantillas protegidas con navegación del sistema y dispatch inteligente.
    Herédala para crear páginas personalizadas de administración.
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            self.user = request.user
            dispatch, url = dispatch_user(request.user.system)
            if dispatch:
                return HttpResponseRedirect(url)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Construye el contexto común para todas las vistas administrativas.
        Incluye navegación, sistema y usuario actual.
        """
        context = super().get_context_data(**kwargs)
        return context
