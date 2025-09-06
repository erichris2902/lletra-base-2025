from django.db import models
from packaging.utils import _

MEXICAN_STATES = [
    ('', 'Seleccion el estado'),
    ('Aguascalientes', 'Aguascalientes'),
    ('Baja California', 'Baja California'),
    ('Baja California Sur', 'Baja California Sur'),
    ('Campeche', 'Campeche'),
    ('Chiapas', 'Chiapas'),
    ('Chihuahua', 'Chihuahua'),
    ('Coahuila  de Zaragoza', 'Coahuila de Zaragoza'),
    ('Colima', 'Colima'),
    ('Ciudad de México', 'Ciudad de México'),
    ('Cdmx', 'Cdmx'),
    ('Durango', 'Durango'),
    ('Guanajuato', 'Guanajuato'),
    ('Guerrero', 'Guerrero'),
    ('Hidalgo', 'Hidalgo'),
    ('Jalisco', 'Jalisco'),
    ('Mexico', 'Mexico'),
    ('Michoacan de Ocampo', 'Michoacan de Ocampo'),
    ('Morelos', 'Morelos'),
    ('Nayarit', 'Nayarit'),
    ('Nuevo Leon', 'Nuevo Leon'),
    ('Oaxaca', 'Oaxaca'),
    ('Puebla', 'Puebla'),
    ('Queretaro de Arteaga', 'Queretaro de Arteaga'),
    ('Quintana', 'Quintana Roo'),
    ('San Luis Potosi', 'San Luis Potosi'),
    ('Sinaloa', 'Sinaloa'),
    ('Sonora', 'Sonora'),
    ('Tabasco', 'Tabasco'),
    ('Tamaulipas', 'Tamaulipas'),
    ('Tlaxcala', 'Tlaxcala'),
    ('Veracruz', 'Veracruz'),
    ('Yucatan', 'Yucatan'),
    ('Zacatecas', 'Zacatecas'),
]

MEXICAN_STATES_KEY = {
    '': '',
    'Aguascalientes': 'AGU',
    'Baja California': 'BCN',
    'Baja California Sur': 'BCS',
    'Campeche': 'CAM',
    'Chiapas': 'CHP',
    'Chihuahua': 'CHH',
    'Coahuila  de Zaragoza': 'COA',
    'Colima': 'COL',
    'Ciudad de México': 'CMX',
    'Cdmx': 'DIF',
    'Durango': 'DUR',
    'Guanajuato': 'GUA',
    'Guerrero': 'GRO',
    'Hidalgo': 'HID',
    'Jalisco': 'JAL',
    'Mexico': 'MEX',
    'Edo. Mexico': 'MEX',
    'Michoacan de Ocampo': 'MIC',
    'Morelos': 'MOR',
    'Nayarit': 'NAY',
    'Nuevo Leon': 'NLE',
    'Oaxaca': 'OAX',
    'Puebla': 'PUE',
    'Queretaro de Arteaga': 'QUE',
    'Queretaro': 'QUE',
    'Quintana': 'ROO',
    'San Luis Potosi': 'SLP',
    'Sinaloa': 'SIN',
    'Sonora': 'SON',
    'Tabasco': 'TAB',
    'Tamaulipas': 'TAM',
    'Tlaxcala': 'TLA',
    'Veracruz': 'VER',
    'Yucatan': 'YUC',
    'Zacatecas': 'ZAC',
}

CARTAPORTE_NS = "http://www.sat.gob.mx/CartaPorte31"


class AsturianoPacking(models.TextChoices):
    CVZ = 'CERVEZA', _('CERVEZA')
    AB = 'ABARROTE', _('ABARROTE')
    CVZ_AB = 'CERVEZA Y ABARROTE', _('CERVEZA Y ABARROTE')


class SupplierStatus(models.TextChoices):
    POR_CONTACTAR = "POR CONTACTAR", "POR CONTACTAR"
    CONTACTADO = "CONTACTADO", "CONTACTADO"
    R_CONTROL = "R CONTROL", "R CONTROL"
    DOCUMENTOS = "DOCUMENTOS", "DOCUMENTOS"
    EN_CAPACITACION = "EN CAPACITACION", "EN CAPACITACIÓN"
    ACTIVO = "ACTIVO", "ACTIVO"


class UnitStatus(models.TextChoices):
    ACTIVE = 'Activa', _('Activa')
    MAINTENANCE = 'En mantenimiento', _('En mantenimiento')
    INACTIVE = 'Baja', _('Baja')
    PENDING = 'Por verificar', _('Por verificar')


class UnitType(models.TextChoices):
    """
    Choices for vehicle types.
    """
    TORTON = 'TORTHON', _('TORTHON')
    TRAILER = 'TRACTO', _('TRACTO')
    BOX = 'CAJA', _('CAJA')
    UNIT_1TN = "UNIDAD 1 TN", _("UNIDAD 1 TN")
    UNIT_25TN = "UNIDAD 2.5 TN", _("UNIDAD 2.5 TN")
    UNIT_35TN = "UNIDAD 3.5 TN", _("UNIDAD 3.5 TN")
    UNIT_5TN = "UNIDAD 5 TN", _("UNIDAD 5 TN")
    RABON = "RABON", _("RABON")
    BOX_40 = "CAJA 40’", _("CAJA 40’")
    BOX_48 = "CAJA 48’", _("CAJA 48’")
    BOX_53 = "CAJA 53’", _("CAJA 53’")
    PLATFORM_40 = "PLATAFORMA 40’", _("PLATAFORMA 40’")
    PLATFORM_48 = "PLATAFORMA 48’", _("PLATAFORMA 48’")
    TANKER = "PIPA", _("PIPA")
    HOPPER = "TOLVA", _("TOLVA")
    CARRIER = "MADRINA", _("MADRINA")
    UTILITY = "VEHICULO UTILITARIO", _("VEHICULO UTILITARIO")


class ShipmentType(models.TextChoices):
    """
    Choices for shipment types.
    """
    THREE_B = '3B', _('3B')
    ASTURIANO = 'ASTURIANO', _('Asturiano')
    GENERAL = 'GENERAL', _('General')
    CHEM = 'CHEM', _('Chem')


class OperationStatus(models.TextChoices):
    """
    Choices for operation statuses.
    """
    PENDING = 'PENDING', 'Pendiente'
    APPROVED = 'APPROVED', 'Aprobado'
    IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
    COMPLETED = 'COMPLETED', 'Completado'
    INVOICED = 'INVOICED', 'Facturado'
    CANCELLED = 'CANCELLED', 'Cancelado'
