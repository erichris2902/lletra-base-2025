import requests
import folium
from django.conf import settings
from polyline import decode as decode_polyline

GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY


def draw_route_on_map(route_data, output_html='route_map.html'):
    """
    Dibuja la ruta en un mapa interactivo usando la polyline de overview.
    """
    overview_polyline = route_data['overview_polyline']['points']
    coords = decode_polyline(overview_polyline)

    # Centrar mapa en el primer punto
    map_center = coords[0]
    fmap = folium.Map(location=map_center, zoom_start=13)

    # Añadir línea de ruta
    folium.PolyLine(coords, color="blue", weight=5, opacity=0.7).add_to(fmap)

    # Marcadores inicio y fin
    folium.Marker(coords[0], tooltip="Inicio", icon=folium.Icon(color="green")).add_to(fmap)
    folium.Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(fmap)

    # Guardar a HTML
    fmap.save(output_html)
    print(f"✅ Mapa generado: {output_html}")


def build_address_string(address):
    parts = [address.street, address.exterior_number, address.colony, address.city, address.state, "México"]
    return ", ".join(filter(None, parts))


def calculate_optimized_route(origin, stops, destination):
    if not GOOGLE_MAPS_API_KEY:
        raise Exception("Google Maps API key is not set")

    base_url = "https://maps.googleapis.com/maps/api/directions/json"

    for stop in stops + [origin, destination]:
        if not stop.address.latitude or not stop.address.longitude:
            stop.address.get_coords_from_address()

    if not origin.address.latitude or not origin.address.longitude:
        origin.address.get_coords_from_address()

    if not destination.address.latitude or not destination.address.longitude:
        destination.address.get_coords_from_address()

    # Distancia optimizada (con paradas)
    params_optimized = {
        "origin": f"{origin.address.latitude},{origin.address.longitude}",
        "destination": f"{destination.address.latitude},{destination.address.longitude}",
        "waypoints": "optimize:true|" + "|".join([
            f"{s.address.latitude},{s.address.longitude}" for s in stops
        ]) if stops else None,
        "mode": "driving",
        "key": GOOGLE_MAPS_API_KEY
    }

    print("🔍 Waypoints:")
    for s in stops:
        print("-", build_address_string(s.address))

    print(params_optimized)
    response = requests.get(base_url, params=params_optimized)
    data = response.json()

    if data.get("status") != "OK":
        print(data)
        raise Exception(f"Error from Google Maps API: {data.get('status')}")

    route_data = data["routes"][0]
    legs = route_data["legs"]
    optimized_distance = sum(leg["distance"]["value"] for leg in legs)  # en metros

    # Actualizar coordenadas
    locations = [origin] + [stops[i] for i in route_data.get("waypoint_order", range(len(stops)))] + [destination]
    for location, leg in zip(locations, legs):
        lat = leg["start_location"]["lat"]
        lng = leg["start_location"]["lng"]
        if location.address.latitude != lat or location.address.longitude != lng:
            location.address.latitude = lat
            location.address.longitude = lng
            location.address.save()

    # Actualizar ubicación final
    last_leg = legs[-1]
    if destination.address.latitude != last_leg["end_location"]["lat"] or destination.address.longitude != \
            last_leg["end_location"]["lng"]:
        destination.address.latitude = last_leg["end_location"]["lat"]
        destination.address.longitude = last_leg["end_location"]["lng"]
        destination.address.save()

    # ➕ Calcular distancia directa sin paradas
    params_direct = {
        "origin": build_address_string(origin.address),
        "destination": build_address_string(destination.address),
        "mode": "driving",
        "key": GOOGLE_MAPS_API_KEY
    }

    response_direct = requests.get(base_url, params=params_direct)
    data_direct = response_direct.json()

    if data_direct.get("status") != "OK":
        print(data_direct)
        raise Exception(f"Error getting direct distance: {data_direct.get('status')}")

    direct_legs = data_direct["routes"][0]["legs"]
    direct_distance = sum(leg["distance"]["value"] for leg in direct_legs)

    return route_data, optimized_distance, direct_distance
