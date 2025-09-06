import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from core.operations_panel.forms.route import RouteForm
from core.operations_panel.models.route import Route
from core.system.views import AdminListView
from polyline import decode

class RouteListView(AdminListView):
    """
    List view for routes.
    """
    model = Route
    form = RouteForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Ubicación Inicial", "Cliente", "Notas"]
    datatable_keys = ["name", "initial_location", "client", "notes"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Rutas'
    category = 'Operaciones'
    dropdown_action_path = 'operations_panel/route/table/actions.js'
    static_path = 'operations_panel/route/table/base.html'


class RouteMapView(LoginRequiredMixin, TemplateView):
    """
    Visualiza el mapa de una ruta optimizada desde Google Maps API.
    """
    template_name = 'operations_panel/route_map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route = get_object_or_404(Route, pk=self.kwargs['route_id'])
        data = route.optimized_route
        coords = []
        overview_polyline = data.get("overview_polyline", {}).get("points", "")
        coords = [{"lat": lat, "lng": lng} for lat, lng in decode(overview_polyline)]

        context["route_coords"] = json.dumps(coords)

        # Lista de ubicaciones: inicio, paradas y destino
        waypoints = []
        if not route.initial_location.address.latitude and not route.initial_location.address.longitude:
            route.initial_location.address.get_coords_from_address()

        if not route.destination_location.address.latitude and not route.destination_location.address.longitude:
            route.destination_location.address.get_coords_from_address()

        for stop in route.route_stops.all():
            if not stop.address.latitude and not stop.address.longitude:
                stop.address.get_coords_from_address()

        # 1. Ubicación inicial
        waypoints.append({
            'name': route.initial_location.name,
            'address': str(route.initial_location.address),
            'lat': route.initial_location.address.latitude,
            'lng': route.initial_location.address.longitude,
        })

        # 2. Paradas intermedias
        for stop in route.route_stops.all():
            waypoints.append({
                'name': stop.name,
                'address': str(stop.address),
                'lat': stop.address.latitude,
                'lng': stop.address.longitude,
            })

        # 3. Destino
        if route.destination_location:
            waypoints.append({
                'name': route.destination_location.name,
                'address': str(route.destination_location.address),
                'lat': route.destination_location.address.latitude,
                'lng': route.destination_location.address.longitude,
            })

        context['waypoints'] = waypoints

        return context
