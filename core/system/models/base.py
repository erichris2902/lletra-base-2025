import json

from django.db import models
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    old_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def to_dict(self, exclude_fields=None):
        if exclude_fields is None:
            exclude_fields = []
            data = model_to_dict(self, exclude=exclude_fields)
        if 'id' not in exclude_fields:
            data['id'] = self.id
        return data

    def to_json(self, exclude_fields=None):
        return json.dumps(self.to_dict(exclude_fields), default=str)



    def to_display_dict(self, keys=None):
        from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField
        from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel

        result = {}
        # Usar keys, o todos los campos (excluyendo relaciones reversas)
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
        # Siempre agrega el id si está en keys
        result["id"] = str(self.id)

        return result


class ActiveModel(BaseModel):
    is_active = models.BooleanField(_("Is active"), default=True)

    class Meta:
        abstract = True


class TimestampedModel(BaseModel):
    published_at = models.DateTimeField(_("Published at"), null=True, blank=True)

    def publish(self):
        """
        Set the published_at timestamp to the current time.
        """
        self.published_at = timezone.now()
        self.save(update_fields=['published_at'])

    class Meta:
        abstract = True


class OrderedModel(BaseModel):
    order = models.PositiveIntegerField(_("Order"), default=0)

    class Meta:
        abstract = True
        ordering = ['order', '-created_at']


class SoftDeleteModel(BaseModel):
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)

    def delete(self, using=None, keep_parents=False):
        """
        Soft delete the model instance by setting deleted_at timestamp.
        """
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """
        Permanently delete the model instance from the database.
        """
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        abstract = True


class SlugModel(BaseModel):
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)

    class Meta:
        abstract = True
