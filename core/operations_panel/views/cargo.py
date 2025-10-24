from core.operations_panel.forms.cargo import CargoForm
from core.operations_panel.models.cargo import Cargo
from core.system.views import AdminListView


class CargoListView(AdminListView):
    """
    List view for cargo (load).
    """
    model = Cargo
    form = CargoForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Identificador", "Productos"]
    datatable_keys = ["identifier", "products"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Cargas'
    category = 'Operaciones'
    catalogs = [
        {
            'id': 'id_transported_product',
            'service': 'TransportedProducts',
            'placeholder': '',
        },
    ]
