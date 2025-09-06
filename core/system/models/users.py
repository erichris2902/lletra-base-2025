from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from core.system.enums import SystemEnum
from apps.telegram_bots.models import TelegramUser
from core.system.models.base import BaseModel


class SystemUser(BaseModel, AbstractUser):
    """
    Custom user model that extends Django's AbstractUser with system-specific fields.
    """
    system = models.CharField(
        max_length=150, 
        choices=SystemEnum.choices, 
        default=SystemEnum.NONE, 
        verbose_name=_("Sistema"), 
        blank=True, 
        null=True
    )
    calendar_url = models.CharField(
        max_length=300,
        verbose_name=_("Calendario publico"),
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        'telegram_bots.TelegramUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='system_user'
    )
    telegram_username = models.CharField(
        max_length=255, 
        verbose_name=_("Telegram Username"), 
        blank=True, 
        null=True
    )

    doc_nombre = models.CharField(
        max_length=255,
        verbose_name=_("Nombre de documentos"),
        blank=True,
        null=True
    )

    doc_cargo = models.CharField(
        max_length=255,
        verbose_name=_("Cargo de documentos"),
        blank=True,
        null=True
    )

    doc_tel = models.CharField(
        max_length=255,
        verbose_name=_("Telefono de documentos"),
        blank=True,
        null=True
    )

    doc_mail = models.CharField(
        max_length=255,
        verbose_name=_("Email de documentos"),
        blank=True,
        null=True
    )


    @classmethod
    def get_by_telegram_username(cls, username):
        """
        Get a user by their Telegram username.
        """
        return cls.objects.filter(telegram_username=username).first()

    @classmethod
    def get_by_telegram_user(cls, telegram_user):
        """
        Get a user by their associated TelegramUser.
        """
        return cls.objects.filter(user=telegram_user).first()

    class Meta:
        verbose_name = _('Usuario de sistema')
        verbose_name_plural = _('Usuarios de sistema')
        db_table = 'system_user'
        ordering = ['id']
