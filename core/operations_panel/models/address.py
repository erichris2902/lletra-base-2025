import urllib

import requests
from django.conf import settings
from django.db import models
from geopy.distance import geodesic

from core.operations_panel.choices import MEXICAN_STATES
from core.operations_panel.services import build_address_string
from core.system.models import BaseModel
from ikigai2025.settings import GOOGLE_MAPS_API_KEY


class Address(BaseModel):
    """
    Modelo para direcciones.
    """
    street = models.CharField(max_length=255, verbose_name="Calle", blank=True, null=True)
    exterior_number = models.CharField(max_length=35, verbose_name="Número exterior", blank=True, null=True)
    interior_number = models.CharField(max_length=35, blank=True, null=True, verbose_name="Número interior")
    colony = models.CharField(max_length=100, verbose_name="Colonia", blank=True, null=True)
    city = models.CharField(max_length=100, verbose_name="Ciudad", blank=True, null=True)
    state = models.CharField(max_length=50, choices=MEXICAN_STATES, verbose_name="Estado",
                             default="Queretaro de Arteaga")
    zip_code = models.CharField(max_length=10, verbose_name="Código postal")

    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitud")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitud")

    def __str__(self):
        parts = [self.street, f"No. {self.exterior_number}"]
        if self.interior_number:
            parts.append(f"Int. {self.interior_number}")
        parts += [self.colony, self.city, self.state, f"C.P. {self.zip_code}"]
        return ", ".join(filter(None, parts))

    def get_coords_from_address(self):
        # Construye una dirección completa
        full_address = build_address_string(self)
        api_key = settings.GOOGLE_MAPS_API_KEY
        direccion_codificada = urllib.parse.quote(full_address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={direccion_codificada}&key={api_key}"
        response = requests.get(url).json()

        if response['status'] == 'OK':
            location = response['results'][0]['geometry']['location']
            self.latitude = location['lat']
            self.longitude = location['lng']
            self.save()
            return (self.latitude, self.longitude)
        else:
            print(f"Google Maps error: {response.get('error_message')}")
            return None

    def get_coords_from_cp(self):
        # Obtener la API key desde settings o env
        from django.conf import settings
        api_key = GOOGLE_MAPS_API_KEY
        if api_key:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={self.zip_code},Mexico&key={api_key}"
            response = requests.get(url).json()
            if response['status'] == 'OK':
                location = response['results'][0]['geometry']['location']
                coords = (location['lat'], location['lng'])
                if coords != (None, None):
                    self.latitude, self.longitude = coords
                    self.save()

    def get_distance_to_cp(self, other_address):
        if self.zip_code and other_address.zip_code:
            if not self.latitude:
                self.get_coords_from_cp()
            if not other_address.latitude:
                other_address.get_coords_from_cp()
            coords1 = (self.latitude, self.longitude)
            coords2 = (other_address.latitude, other_address.longitude)
            if coords1 and coords2:
                return geodesic(coords1, coords2).km
        return None
