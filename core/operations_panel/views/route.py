import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from core.operations_panel.forms.route import RouteForm
from core.operations_panel.models.route import Route
from core.system.views import AdminListView
from polyline import decode

class RouteListView(AdminListView):
    model = Route
    form = RouteForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Ubicación Inicial", "Ubicacion Final", "Repartos", "Notas"]
    datatable_keys = ["name", "initial_location", "destination_location", "route_stops", "notes"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Rutas'
    category = 'Operaciones'
    dropdown_action_path = 'operations_panel/route/table/actions.js'
    static_path = 'operations_panel/route/table/base.html'

    def handle_searchdata(self, request, data):
        queryset = self.get_queryset().exclude(name__contains="OPERATION")
        data = [obj.to_display_dict(keys=self.datatable_keys) for obj in queryset]
        return data

    def get_queryset(self):
        qs = self.model.objects.all().prefetch_related("route_stops", "initial_location", "destination_location")
        search_term = self.request.GET.get('q')
        if search_term:
            search_fields = getattr(self, 'search_fields', ['name'])
            q = Q()
            for field in search_fields:
                q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(q)
        return qs

class RouteAsturianoListView(RouteListView):
    model = Route
    form = RouteForm
    template_name = 'base/elements/views/datatable_list.html'
    datatable_headers = ["Nombre", "Ubicación Inicial", "Ubicacion Final", "Repartos", "Notas"]
    datatable_keys = ["name", "initial_location", "destination_location", "route_stops", "notes"]
    datatable_actions = True
    title = model._meta.verbose_name_plural.title()
    form_path = 'base/elements/forms/form.html'
    section = 'Rutas'
    category = 'Operaciones'
    dropdown_action_path = 'operations_panel/route/table/actions.js'
    static_path = 'operations_panel/route/table/base.html'

    def context_data_nav(self, context, user, session=None):
        context['navcategories'] = []
        context['user'] = user
        return context

    def dispatch(self, request, *args, **kwargs):
        return super(AdminListView, self).dispatch(request, *args, **kwargs)

    def handle_searchdata(self, request, data):
        queryset = self.get_queryset().exclude(name__contains="OPERATION").filter(name__contains="REGION").filter(name__contains="ZONA")
        data = [obj.to_display_dict(keys=self.datatable_keys) for obj in queryset]
        return data


class RouteMapView(LoginRequiredMixin, TemplateView):
    template_name = 'operations_panel/route_map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(self.kwargs)
        route = Route.objects.get(pk=self.kwargs['route_id'])
        print(route)
        data = route.optimized_route
        coords = []
        print(data)
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
