import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.expressions import result

from core.operations_panel.models import DeliveryLocation
from core.operations_panel.models.address import Address


class Command(BaseCommand):
    help = (
        "Lee un archivo JSON de tiendas con URL de Google Maps y obtiene "
        "direccion segmentada, latitud y longitud."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            required=True,
            help="Ruta del archivo JSON de entrada",
        )

        parser.add_argument(
            "--timeout",
            type=int,
            default=15,
            help="Timeout de requests en segundos",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.2,
            help="Pausa entre requests para no saturar la API",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"]).expanduser().resolve()
        output_path = options.get("output")
        timeout = options["timeout"]
        sleep_seconds = options["sleep"]

        if not input_path.exists():
            raise CommandError(f"No existe el archivo de entrada: {input_path}")

        api_key = 'AIzaSyAoON3wq-chyN1RwnRPEjZOeftu83ftSP0'

        try:
            with input_path.open("r", encoding="utf-8") as f:
                tiendas = json.load(f)
        except json.JSONDecodeError as exc:
            raise CommandError(f"El archivo no es JSON válido: {exc}") from exc

        if not isinstance(tiendas, list):
            raise CommandError("El JSON de entrada debe ser una lista de objetos")

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; DjangoManagementCommand/1.0)"
                )
            }
        )

        resultados = []
        total = len(tiendas)

        for index, tienda in enumerate(tiendas, start=1):
            codigo = tienda.get("codigo")
            nombre = tienda.get("tienda")
            url = tienda.get("url")

            self.stdout.write(
                f"[{index}/{total}] Procesando {codigo or 'SIN_CODIGO'} - {nombre or 'SIN_NOMBRE'}"
            )

            enriquecido = dict(tienda)

            if not url:
                enriquecido.update(
                    {
                        "lat": None,
                        "lng": None,
                        "direccion_formateada": None,
                        "calle": None,
                        "numero": None,
                        "colonia": None,
                        "ciudad": None,
                        "municipio": None,
                        "estado": None,
                        "pais": None,
                        "cp": None,
                        "error": "No tiene URL",
                    }
                )
                resultados.append(enriquecido)
                continue

            try:
                expanded_url = self.expand_url(session, url, timeout)
                lat, lng = self.extract_lat_lng_from_url(expanded_url)

                if lat is None or lng is None:
                    lat, lng = self.geocode_from_url_string(
                        session=session,
                        api_key=api_key,
                        url=expanded_url,
                        timeout=timeout,
                    )

                if lat is None or lng is None:
                    enriquecido.update(
                        {
                            "expanded_url": expanded_url,
                            "lat": None,
                            "lng": None,
                            "direccion_formateada": None,
                            "calle": None,
                            "numero": None,
                            "colonia": None,
                            "ciudad": None,
                            "municipio": None,
                            "estado": None,
                            "pais": None,
                            "cp": None,
                            "error": "No se pudieron obtener coordenadas",
                        }
                    )
                    resultados.append(enriquecido)
                    time.sleep(sleep_seconds)
                    continue

                address_data = self.reverse_geocode(
                    session=session,
                    api_key=api_key,
                    lat=lat,
                    lng=lng,
                    timeout=timeout,
                )

                enriquecido.update(
                    {
                        "expanded_url": expanded_url,
                        "lat": lat,
                        "lng": lng,
                        "direccion_formateada": address_data.get("direccion_formateada"),
                        "calle": address_data.get("calle"),
                        "numero": address_data.get("numero"),
                        "colonia": address_data.get("colonia"),
                        "ciudad": address_data.get("ciudad"),
                        "municipio": address_data.get("municipio"),
                        "estado": address_data.get("estado"),
                        "pais": address_data.get("pais"),
                        "cp": address_data.get("cp"),
                        "error": None,
                    }
                )

            except Exception as exc:
                enriquecido.update(
                    {
                        "lat": None,
                        "lng": None,
                        "direccion_formateada": None,
                        "calle": None,
                        "numero": None,
                        "colonia": None,
                        "ciudad": None,
                        "municipio": None,
                        "estado": None,
                        "pais": None,
                        "cp": None,
                        "error": str(exc),
                    }
                )
            print(enriquecido)
            resultados.append(enriquecido)
            time.sleep(sleep_seconds)

        for result in resultados:
            try:
                with transaction.atomic():
                    name = result['codigo'] + " " + result['tienda']
                    if DeliveryLocation.objects.filter(name=name).exists():
                        print("Ya existe" + name)
                        delivery = DeliveryLocation.objects.get(name=name)
                        print(delivery)
                        if delivery.address.state == "Querétaro":
                            print("Es Queretaro")
                            address = delivery.address
                            address.state = "Queretaro de Arteaga"
                            address.save()
                            print("Se cambio el estado a Queretaro de Arteaga")
                        continue
                    deliveryLocation = DeliveryLocation()
                    deliveryLocation.name = name
                    deliveryLocation.business_name = "ADMINISTRACION DE EMPRESAS AL MENUDEO"
                    deliveryLocation.rfc = "AEM151124N36"
                    deliveryLocation.notes = "importada por script"
                    address = Address()
                    address.street = result['calle']
                    address.exterior_number = result['numero']
                    address.colony = result['colonia']
                    address.city = result['ciudad']
                    address.state = result['estado']
                    address.zip_code = result['cp']
                    address.latitude = result['lat']
                    address.longitude = result['lng']
                    address.save()
                    deliveryLocation.save()
                    deliveryLocation.address = address
                    deliveryLocation.save()
                    print("Se creo" + name)
            except Exception as e:
                print("No se pudo crear" + name)

        self.stdout.write(self.style.SUCCESS(f"Archivo generado: {output_path}"))

    def expand_url(self, session, short_url, timeout):
        response = session.get(short_url, allow_redirects=True, timeout=timeout)
        response.raise_for_status()
        return response.url

    def extract_lat_lng_from_url(self, url):
        patterns = [
            r"@(-?\d+\.\d+),(-?\d+\.\d+)",
            r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
            r"ll=(-?\d+\.\d+),(-?\d+\.\d+)",
            r"q=(-?\d+\.\d+),(-?\d+\.\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return float(match.group(1)), float(match.group(2))

        return None, None

    def geocode_from_url_string(self, session, api_key, url, timeout):
        decoded_url = unquote(url)

        text_candidates = []

        place_match = re.search(r"/place/([^/]+)", decoded_url)
        if place_match:
            place_text = place_match.group(1).replace("+", " ")
            text_candidates.append(place_text)

        if "google.com/maps" in decoded_url or "maps.app.goo.gl" in decoded_url:
            text_candidates.append(decoded_url)

        for candidate in text_candidates:
            geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": candidate,
                "key": api_key,
            }
            response = session.get(geo_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                return location["lat"], location["lng"]

        return None, None

    def reverse_geocode(self, session, api_key, lat, lng, timeout):
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{lat},{lng}",
            "key": api_key,
            "language": "es",
        }

        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "direccion_formateada": None,
                "calle": None,
                "numero": None,
                "colonia": None,
                "ciudad": None,
                "municipio": None,
                "estado": None,
                "pais": None,
                "cp": None,
            }

        result = data["results"][0]
        components = result.get("address_components", [])

        parsed = {
            "direccion_formateada": result.get("formatted_address"),
            "calle": None,
            "numero": None,
            "colonia": None,
            "ciudad": None,
            "municipio": None,
            "estado": None,
            "pais": None,
            "cp": None,
        }

        for comp in components:
            long_name = comp.get("long_name")
            types = comp.get("types", [])

            if "route" in types:
                parsed["calle"] = long_name
            elif "street_number" in types:
                parsed["numero"] = long_name
            elif "neighborhood" in types:
                parsed["colonia"] = long_name
            elif "sublocality" in types or "sublocality_level_1" in types:
                if not parsed["colonia"]:
                    parsed["colonia"] = long_name
            elif "locality" in types:
                parsed["ciudad"] = long_name
            elif "administrative_area_level_2" in types:
                parsed["municipio"] = long_name
            elif "administrative_area_level_1" in types:
                parsed["estado"] = long_name
            elif "country" in types:
                parsed["pais"] = long_name
            elif "postal_code" in types:
                parsed["cp"] = long_name

        return parsed