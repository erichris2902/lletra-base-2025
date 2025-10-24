# apps/openai_assistant/models/assistant.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class Assistant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255)
    telegram_command = models.CharField(_("Command"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    instructions = models.TextField(_("Instructions"))
    model = models.CharField(_("Model"), max_length=100, default="gpt-4o")
    openai_id = models.CharField(_("OpenAI Assistant ID"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_assistants"
    )
    is_active = models.BooleanField(_("Is active"), default=True)

    def __str__(self):
        return self.name

    def to_display_dict(self, keys=None):
        from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField
        from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel

        result = {}
        all_fields = [f for f in self._meta.get_fields() if not isinstance(f, (ManyToOneRel, ManyToManyRel))]
        for field in all_fields:
            name = field.name
            if keys and name not in keys:
                continue
            value = getattr(self, name, None)
            if isinstance(field, (ForeignKey, OneToOneField)):
                result[name] = str(value) if value else ""
            elif isinstance(field, ManyToManyField):
                result[name] = [str(obj) for obj in value.all()]
            else:
                result[name] = value
        result["id"] = str(self.id)
        return result

    class Meta:
        verbose_name = _("Assistant")
        verbose_name_plural = _("Assistants")
        ordering = ["-created_at"]


class Tool(models.Model):
    TYPE_CHOICES = (
        ('function', _('Function')),
        ('retrieval', _('Retrieval')),
        ('code_interpreter', _('Code Interpreter')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assistant = models.ForeignKey(
        Assistant, on_delete=models.CASCADE,
        related_name="tools"
    )
    name = models.CharField(_("Name"), max_length=255)
    type = models.CharField(_("Type"), max_length=50, choices=TYPE_CHOICES)
    description = models.TextField(_("Description"), blank=True)
    parameters = models.JSONField(_("Parameters"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        verbose_name = _("Tool")
        verbose_name_plural = _("Tools")
        ordering = ["assistant", "name"]
