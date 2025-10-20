from django.db import models
from django.utils.translation import gettext_lazy as _

class SystemEnum(models.TextChoices):
    """
    Enum for system types.
    """
    NONE = 'NONE', _('NONE')
    SYSTEM = 'SYSTEM', _('SYSTEM')
    ADMINISTRACION = 'ADMINISTRACION', _('ADMINISTRACION')
    OPERACIONES = 'OPERACIONES', _('OPERACIONES')
    COMERCIAL = 'COMERCIAL', _('COMERCIAL')
    SALE = 'SALE', _('VENTAS')
    RH = 'RH', _('RH')
    ATTENDANCE = 'ATTENDANCE', _('ATTENDANCE')
    # Add more system types as needed