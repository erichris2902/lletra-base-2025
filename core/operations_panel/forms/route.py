from django import forms

from core.operations_panel.models.route import Route
from core.system.forms import BaseModelForm


class RouteForm(BaseModelForm):
    """
    Form for routes with an initial delivery location and stops.
    """
    layout = [
        {"type": "row", "fields": [
            {"name": "name", "size": 6},
            {"name": "client", "size": 6},
        ]},

        {"type": "callout", "title": "Locaciones", "sections": [
            {"type": "row", "fields": [
                {"name": "initial_location", "size": 6},
                {"name": "destination_location", "size": 6},
            ]},
            {"type": "row", "fields": [

                {"name": "route_stops", "size": 12},
            ]},
        ]},
        {"type": "row", "fields": [
            {"name": "direct_distance", "size": 6},
            {"name": "optimized_distance", "size": 6},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Route
        fields = [
            "name",
            "initial_location",
            "route_stops",
            "client",
            "notes",
            "destination_location",
            "direct_distance",
            "optimized_distance"
        ]

        widgets = {
            'route_stops': forms.SelectMultiple(attrs={'class': 'select2'}),
        }

class RouteShipmentForm(BaseModelForm):
    """
    Form for routes with an initial delivery location and stops.
    """
    layout = [
        {"type": "row", "fields": [
            {"name": "direct_distance", "size": 6},
            {"name": "optimized_distance", "size": 6},
        ]},
        {"type": "row", "fields": [
            {"name": "notes", "size": 12},
        ]},
    ]

    class Meta:
        model = Route
        fields = [
            "direct_distance",
            "optimized_distance",
            "notes"
        ]