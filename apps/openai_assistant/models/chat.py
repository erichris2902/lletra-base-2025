# apps/openai_assistant/models/chat.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
from .assistant import Assistant, Tool


class Chat(models.Model):
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
