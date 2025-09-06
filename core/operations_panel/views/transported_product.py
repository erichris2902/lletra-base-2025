from core.operations_panel.forms.transported_product import TransportedProductForm
from core.operations_panel.models.transported_product import TransportedProduct
from core.system.views import AdminListView


class TransportedProductListView(AdminListView):
    """
    List view for transported products.
    """
    model = TransportedProduct
    form = TransportedProductForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Bienes Transportados", "Clave SAT", "Descripción", "Moneda", "Material Peligroso"]
    datatable_keys = ["transported_product_key", "unit_key", "description", "currency", "is_danger"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Productos Transportados'
    category = 'Operaciones'
    catalogs = [
        {
            'id': 'id_transported_product_key',
            'service': 'ProductAndServiceCatalog',
            'placeholder': '',
        },
        {
            'id': 'id_unit_key',
            'service': 'UnitSat',
            'placeholder': '',
        },
    ]

    def handle_searchdata(self, request, data):
        """
        Retorna todos los registros como lista de dicts.
        """
        # Obtén los objetos de la tabla (o filtra según tus necesidades)
        queryset = self.get_queryset()
        datatable_keys = self.datatable_keys
        data = [obj.to_display_dict(keys=datatable_keys) for obj in self.get_queryset()]
        print(data)
        return data


