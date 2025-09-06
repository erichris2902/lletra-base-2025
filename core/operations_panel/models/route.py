from django.db import models

from core.operations_panel.models.delivery_location import DeliveryLocation

from core.operations_panel.models.client import Client
from core.system.models import BaseModel

class Route(BaseModel):
    """
    Modelo para rutas con un punto de inicio y una lista de paradas intermedias.
    """
    name = models.CharField(max_length=100, verbose_name="Nombre")

    initial_location = models.ForeignKey(
        DeliveryLocation,
        on_delete=models.PROTECT,
        related_name="routes_as_initial",
        verbose_name="Ubicación inicial"
    )

    destination_location = models.ForeignKey(
        DeliveryLocation,
        on_delete=models.PROTECT,
        related_name="routes_as_destination",
        blank=True,
        null=True,
        verbose_name="Destino final"
    )

    route_stops = models.ManyToManyField(
        DeliveryLocation,
        related_name="routes_as_stop",
        blank=True,
        verbose_name="Paradas intermedias"
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        verbose_name="Cliente"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas"
    )

    direct_distance = models.IntegerField(
        default=0,
        blank=True,
        null=True,
        verbose_name="Distancia directa (Origen-Destino) (km)"
    )

    optimized_distance = models.IntegerField(
        default=0,
        blank=True,
        null=True,
        verbose_name="Distancia total (km)"
    )

    published = models.BooleanField(
        default=False,
        verbose_name="Publicada"
    )

    optimized_route = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Ruta optimizada"
    )

    def save(self, *args, **kwargs):
        from core.operations_panel.services import calculate_optimized_route
        super().save(*args, **kwargs)

        if self.initial_location and self.destination_location and self.direct_distance == 0:
            stops = list(self.route_stops.all())
            route_data, optimized_distance, direct_distance = calculate_optimized_route(
                origin=self.initial_location,
                stops=stops,
                destination=self.destination_location
            )
            self.optimized_route = route_data
            self.optimized_distance = optimized_distance / 1000
            self.direct_distance = direct_distance / 1000

            super().save(update_fields=["optimized_route", "optimized_distance", "direct_distance"])

    def __str__(self):
        return f"{self.name} - {self.client.name}"

    def look_for_route(name):
        """
        Get or create a DeliveryLocation by name using fuzzy matching.

        Args:
            name (str): Location name

        Returns:
            Route: The found or created Route instance
        """
        if not name:
            return None

        # Try exact match first
        try:
            return Route.objects.get(name__iexact=name)
        except Route.DoesNotExist:
            pass

        # Try fuzzy matching
        best_coincidence = extract_best_coincidence_from_field_in_model(Route, 'name', name, 90)

        if best_coincidence:
            return best_coincidence

    class Meta:
        verbose_name = "Ruta"
        verbose_name_plural = "Rutas"
        ordering = ['-created_at']

