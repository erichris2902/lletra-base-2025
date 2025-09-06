from django.shortcuts import get_object_or_404, render

from core.operations_panel.forms.address import AddressForm
from core.operations_panel.forms.supplier import SupplierForm
from core.operations_panel.models.supplier import Supplier
from core.system.views import AdminListView


class SupplierListView(AdminListView):
    model = Supplier
    form = SupplierForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Código", "Razón Social", "RFC", "Email", "Teléfono", "Banco", "CLABE", "Dirección"]
    datatable_keys = ["code", "business_name", "rfc", "email", "phone", "bank", "clabe", "address"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Proveedores'
    category = 'Catálogos'

    def handle_add(self, request, data):
        form = self.form(request.POST, request.FILES)
        form_address = AddressForm(request.POST, request.FILES)
        if form.is_valid() and form_address.is_valid():
            instance = form.save()
            address = form_address.save()
            instance.address = address
            instance.save()
            data['success'] = True
            data['id'] = str(instance.id)
        else:
            data['error'] = form.errors
        return data

    def handle_update(self, request, data):
        instance = get_object_or_404(self.model, pk=request.POST.get('id'))
        form = self.form(request.POST, request.FILES, instance=instance)
        form_address = AddressForm(request.POST, request.FILES, instance=instance.address)
        if form.is_valid() and form_address.is_valid():
            instance = form.save()
            instance.address = form_address.save()
            data['success'] = True
            data['id'] = str(instance.id)
        else:
            data['error'] = form.errors
        return data

    def render_form(self, request, instance, form=None):
        """
        Renderiza el formulario y lo incluye en un dict como HTML.
        """
        form_step_1 = self.form(instance=instance)
        form_step_2 = AddressForm(instance=getattr(instance, 'address', None))
        forms = [
            form_step_1,
            form_step_2,
        ]

        titles = ["General", "Direcion"]

        form = self.form(instance=instance)
        context = {
            'form': form,
            'form_action': self.form_action,
            'form_type': 'vertical',
            'id': instance.id,
            'add_form_layout': getattr(form, 'layout', []),
            'add_form_fields': {name: form[name] for name in form.fields},  # 👈 importante
            'pages': [],  # 👈 importante
        }
        for i in range(len(forms)):
            context['pages'].append({'form': forms[i], 'title': titles[i], 'layout': getattr(forms[i], 'layout', []),
                                     'fields': {name: forms[i][name] for name in forms[i].fields}})
        html = render(request, self.form_path, context)
        return html.content.decode("utf-8")

