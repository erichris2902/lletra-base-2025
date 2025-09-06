from core.operations_panel.forms.vehicle import VehicleForm
from core.operations_panel.models.vehicle import Vehicle
from core.system.views import AdminListView


class VehicleListView(AdminListView):
    model = Vehicle
    form = VehicleForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Número Económico", "Modelo", "Marca", "Placa", "Año", "Tipo de Unidad", "Estado"]
    datatable_keys = ["econ_number", "model", "brand", "license_plate", "year", "unit_type", "status"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Vehículos'
    category = 'Catálogos'

