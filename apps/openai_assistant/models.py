from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
import json


class Assistant(models.Model):
    """
    Model to store OpenAI Assistant configurations.
    """
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
        """
        Returns a dictionary representation of the model instance for display in datatables.
        - Simple fields: their value.
        - FK/M2M: their __str__ (or list of __str__).
        If keys is passed, only returns those fields.
        """
        from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField
        from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel

        result = {}
        # Use keys, or all fields (excluding reverse relations)
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
        # Always add the id if it's in keys
        result["id"] = str(self.id)

        return result

    class Meta:
        verbose_name = _("Assistant")
        verbose_name_plural = _("Assistants")
        ordering = ["-created_at"]


class Tool(models.Model):
    """
    Model to store tool configurations for assistants.
    """
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


class Chat(models.Model):
    """
    Model to store chat sessions between users and assistants.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="chats"
    )
    assistant = models.ForeignKey(
        Assistant, on_delete=models.CASCADE, 
        related_name="chats"
    )
    title = models.CharField(_("Title"), max_length=255, blank=True)
    openai_thread_id = models.CharField(_("OpenAI Thread ID"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    is_active = models.BooleanField(_("Is active"), default=True)

    def __str__(self):
        return f"{self.title or 'Chat'} - {self.user.username} with {self.assistant.name}"

    class Meta:
        verbose_name = _("Chat")
        verbose_name_plural = _("Chats")
        ordering = ["-updated_at"]


class Message(models.Model):
    """
    Model to store messages in a chat.
    """
    ROLE_CHOICES = (
        ('user', _('User')),
        ('assistant', _('Assistant')),
        ('system', _('System')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(
        Chat, on_delete=models.CASCADE, 
        related_name="messages"
    )
    role = models.CharField(_("Role"), max_length=20, choices=ROLE_CHOICES)
    content = models.TextField(_("Content"))
    openai_message_id = models.CharField(_("OpenAI Message ID"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ["created_at"]


class ToolExecution(models.Model):
    """
    Model to store tool execution details.
    """
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, 
        related_name="tool_executions"
    )
    tool = models.ForeignKey(
        Tool, on_delete=models.SET_NULL, 
        null=True, related_name="executions"
    )
    tool_name = models.CharField(_("Tool Name"), max_length=255)
    input_data = models.JSONField(_("Input Data"), default=dict)
    output_data = models.JSONField(_("Output Data"), default=dict, blank=True)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='pending')
    openai_tool_call_id = models.CharField(_("OpenAI Tool Call ID"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.tool_name} - {self.get_status_display()}"

    class Meta:
        verbose_name = _("Tool Execution")
        verbose_name_plural = _("Tool Executions")
        ordering = ["-created_at"]
