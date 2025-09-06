from core.operations_panel.forms.driver import DriverForm
from core.operations_panel.models.driver import Driver
from core.system.views import AdminListView


class DriverListView(AdminListView):
    model = Driver
    form = DriverForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Apellido Paterno", "Apellido Materno", "RFC", "Licencia", "Tipo", "Vencimiento"]
    datatable_keys = ["name", "last_name", "mother_last_name", "rfc", "license_number", "license_type",
                      "license_expiration"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Conductores'
    category = 'Catálogos'
