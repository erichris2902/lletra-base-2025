from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.generic import ListView, TemplateView
from django.db import transaction, models
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
        categories = Category.objects.order_by("priority").all()

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
    ordering = "asc"
    virtual_search = {
        # "name": Concat(
        #    Coalesce("first_name", Value("")),
        #    Value(" "),
        #    Coalesce("last_name", Value("")),
        #    output_field=CharField()
        # )
    }

    def _safe_search_fields(self, fields):
        safe = []
        for f in fields:
            # si ya trae __, asumimos que ya apunta a un campo concreto
            if "__" in f:
                safe.append(f)
                continue
            try:
                field = self.model._meta.get_field(f)
            except FieldDoesNotExist:
                continue
            # si es FK, intenta buscar por <fk>__name por default
            if field.is_relation and field.many_to_one:
                related_model = field.related_model
                text_field = self._get_text_field_for_fk(related_model)

                if text_field:
                    safe.append(f"{f}__{text_field}")
            else:
                safe.append(f)
        return safe

    def _get_text_field_for_fk(self, model):
        # prioridad de nombres "humanos"
        preferred = ["name", "first_name", "last_name", "business_name", "title", "username", "email", "folio"]

        fields = {
            f.name: f
            for f in model._meta.get_fields()
            if isinstance(f, (models.CharField, models.TextField))
        }

        # 1️⃣ usar uno preferido si existe
        for p in preferred:
            if p in fields:
                return p

        # 2️⃣ usar cualquier CharField/TextField
        return next(iter(fields), None)


    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.model.objects.all()
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
            'ordering': self.ordering,
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
        print(data)
        context = {
            'form': form_instance,
            'form_action': action,
            'form_type': self.form_type,
            'id': instance.id if instance else None,
            'data': data,
            'add_form_layout': getattr(form_instance, 'layout', []),
            'add_form_fields': {name: form_instance[name] for name in form_instance.fields},
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
        # DataTables manda esto
        draw = int(request.POST.get("draw", 1))
        start = int(request.POST.get("start", 0))
        length = int(request.POST.get("length", 50))
        search = (request.POST.get("search", "") or "").strip()

        # 1) queryset base
        qs = self.get_queryset()
        records_total = qs.count()

        # 2) filtro por búsqueda
        if search:
            search_fields = getattr(self, "search_fields", self.search_fields)
            search_fields = self._safe_search_fields(search_fields)

            q_obj = Q()
            for field in search_fields:
                q_obj |= Q(**{f"{field}__icontains": search})
            qs = qs.filter(q_obj)

        records_filtered = qs.count()

        # 3) orden (opcional, pero recomendado)
        order_col = request.POST.get("order_col")
        order_dir = request.POST.get("order_dir", "asc")
        if order_col is not None and order_col != "":
            try:
                col_idx = int(order_col)
                col_key = self.datatable_keys[col_idx]  # ej: "name"

                # si es columna virtual, se anota
                if col_key in self.virtual_search:
                    qs = qs.annotate(**{col_key: self.virtual_search[col_key]})
                    order_field = col_key
                else:
                    order_field = self.datatable_keys[col_idx]

                if order_dir == "desc":
                    order_field = f"-{order_field}"

                qs = qs.order_by(order_field)
            except (ValueError, IndexError):
                pass

        # 4) paginación
        qs_page = qs[start:start + length]

        # 5) data
        data = [obj.to_display_dict(keys=self.datatable_keys) for obj in qs_page]

        return {
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data
        }

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
