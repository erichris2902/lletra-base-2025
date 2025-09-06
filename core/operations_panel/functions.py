from django.utils.timezone import localtime

from core.operations_panel.choices import CARTAPORTE_NS, MEXICAN_STATES_KEY
from xml.etree import ElementTree as ET


def _s(v, default=""):
    return default if v is None else str(v)


def _fecha(dt):
    return localtime(dt).strftime("%Y-%m-%dT%H:%M:%S")


def _estado_clave(direction, CLAVE_ESTADO):
    # direction.state => clave SAT (p.ej. "QUE", "NLE", etc.)
    try:
        return CLAVE_ESTADO[_s(getattr(direction, "state", None))]
    except Exception:
        return _s(getattr(direction, "state", None), "NLE")


def _add_domicilio(parent, location):
    """location.direction con: street, exterior_number, colony, cp, state"""
    direction = getattr(location, "direction", None)
    ET.register_namespace("cartaporte31", CARTAPORTE_NS)
    ET.SubElement(
        parent, f"{{{CARTAPORTE_NS}}}Domicilio",
        {
            "Calle": _s(getattr(direction, "street", None), "Sin calle"),
            "NumeroExterior": _s(getattr(direction, "exterior_number", None), "Sin numero"),
            "Colonia": _s(getattr(direction, "colony", None), "Sin colonia"),
            "Estado": _estado_clave(direction, MEXICAN_STATES_KEY),
            "Pais": "MEX",
            "CodigoPostal": _s(getattr(direction, "zip_code", None), "00000"),
        }
    )
