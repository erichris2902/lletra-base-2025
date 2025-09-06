from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.system.enums import SystemEnum  # Asegúrate de tener esto en tu proyecto
from core.system.models import SystemUser
from core.system.models.base import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Nombre de la categoría")
    icon = models.CharField(
        default="fas fa-folder-open",
        max_length=150,
        verbose_name="Clase de ícono (Font Awesome)"
    )
    priority = models.IntegerField(default=0, verbose_name="Prioridad")
    url = models.CharField(
        max_length=150,
        verbose_name="URL a la que redirige",
        default="",
        blank=True,
        null=True
    )
    system = models.CharField(
        max_length=150,
        choices=SystemEnum.choices,
        default=SystemEnum.NONE,
        verbose_name="Sistema",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True, verbose_name="¿Está activa?")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Categoría del navbar'
        verbose_name_plural = 'Categorías del navbar'
        db_table = 'navbar_category'
        ordering = ['priority']


class Section(BaseModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="Categoría a la que pertenece",
        related_name="sections"
    )
    name = models.CharField(max_length=150, verbose_name="Nombre de la sección")
    icon = models.CharField(
        default="far fa-circle nav-icon",
        max_length=150,
        verbose_name="Clase de ícono (Font Awesome)"
    )
    priority = models.IntegerField(default=0, verbose_name="Prioridad")
    url = models.CharField(
        max_length=150,
        verbose_name="URL a la que redirige",
        default="",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True, verbose_name="¿Está activa?")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Sección del navbar'
        verbose_name_plural = 'Secciones del navbar'
        db_table = 'navbar_section'
        ordering = ['priority']


class UserPermission(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Usuario",
        related_name="permissions"
    )
    sections = models.ManyToManyField(
        Section,
        verbose_name="¿A qué secciones tiene acceso el usuario?"
    )
    categories = models.ManyToManyField(
        Category,
        verbose_name="¿A qué categorías tiene acceso el usuario?"
    )

    def __str__(self):
        sections_names = ", ".join([s.name for s in self.sections.all()])
        categories_names = ", ".join([c.name for c in self.categories.all()])
        return f"{self.user}: Secciones [{sections_names}] - Categorías [{categories_names}]"

    class Meta:
        verbose_name = 'Permiso de usuario'
        verbose_name_plural = 'Permisos de usuarios'
        db_table = 'user_permission'
        ordering = ['id']
