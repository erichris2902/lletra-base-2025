from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from apps.openai_assistant.models import Assistant, Chat as OpenAIChat
from core.operations_panel.models.operation import Operation


class TelegramBot(models.Model):
    """
    Model to store Telegram Bot configurations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255)
    username = models.CharField(_("Bot Username"), max_length=255, unique=True)
    token = models.CharField(_("Bot Token"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    webhook_url = models.URLField(_("Webhook URL"), blank=True)
    webhook_set = models.BooleanField(_("Webhook Set"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    is_active = models.BooleanField(_("Is active"), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Telegram Bot")
        verbose_name_plural = _("Telegram Bots")
        ordering = ["-created_at"]


class TelegramGroup(models.Model):
    """
    Model to store Telegram Group information and their assigned assistants.
    This allows tracking groups where bots interact and assigning specific assistants to each group.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(_("Telegram Group ID"), unique=True)
    name = models.CharField(_("Group Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    assigned_assistant = models.ForeignKey(
        Assistant, on_delete=models.SET_NULL, 
        related_name="assigned_telegram_groups", null=True, blank=True,
        verbose_name=_("Assigned Assistant")
    )
    is_active = models.BooleanField(_("Is active"), default=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    contact_info = models.TextField(_("Contact Information"), blank=True, 
                                   help_text=_("Contact information for the group administrator or relevant contacts"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Telegram Group")
        verbose_name_plural = _("Telegram Groups")
        ordering = ["-updated_at"]


class TelegramUser(models.Model):
    """
    Model to store Telegram User information and link to Django User.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(_("Telegram ID"), unique=True)
    username = models.CharField(_("Username"), max_length=255, blank=True)
    first_name = models.CharField(_("First Name"), max_length=255, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=255, blank=True)
    language_code = models.CharField(_("Language Code"), max_length=10, blank=True)
    is_bot = models.BooleanField(_("Is Bot"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (@{self.username})" if self.username else f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = _("Telegram User")
        verbose_name_plural = _("Telegram Users")
        ordering = ["-created_at"]


class TelegramChat(models.Model):
    """
    Model to store Telegram Chat information.
    """
    CHAT_TYPE_CHOICES = (
        ('private', _('Private')),
        ('group', _('Group')),
        ('supergroup', _('Supergroup')),
        ('channel', _('Channel')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(_("Telegram Chat ID"), unique=True)
    type = models.CharField(_("Chat Type"), max_length=20, choices=CHAT_TYPE_CHOICES)
    title = models.CharField(_("Title"), max_length=255, blank=True)
    username = models.CharField(_("Username"), max_length=255, blank=True)
    participants = models.ManyToManyField(
        TelegramUser, related_name="chats", blank=True
    )
    active_assistant = models.ForeignKey(
        Assistant, on_delete=models.SET_NULL, 
        related_name="telegram_chats", null=True, blank=True
    )
    openai_chat = models.ForeignKey(
        OpenAIChat, on_delete=models.SET_NULL, 
        related_name="telegram_chat", null=True, blank=True
    )
    telegram_group = models.ForeignKey(
        TelegramGroup, on_delete=models.SET_NULL,
        related_name="telegram_chats", null=True, blank=True,
        help_text=_("Associated Telegram Group (for group chats only)")
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        if self.type == 'private':
            return f"Private chat with {self.participants.first() if self.participants.exists() else 'Unknown'}"
        if self.telegram_group:
            return f"{self.get_type_display()} {self.title} (Group: {self.telegram_group.name})"
        return self.title or f"{self.get_type_display()} {self.telegram_id}"

    def set_active_assistant(self, assistant):
        """
        Set the active assistant for this chat and create a new OpenAI Chat if needed.
        If there's already an OpenAI Chat for this assistant and chat, use that instead.

        Args:
            assistant (Assistant): The assistant to set as active
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # Get or create a system user for OpenAI chats
        system_user, _ = User.objects.get_or_create(
            username='telegram_system',
            defaults={'email': 'telegram_system@example.com', 'is_active': True}
        )

        # Set the active assistant
        previous_assistant = self.active_assistant
        self.active_assistant = assistant

        # If the assistant is the same as before, don't change the chat
        if assistant and previous_assistant and assistant.id == previous_assistant.id and self.openai_chat:
            self.save(update_fields=['active_assistant'])
            return self.openai_chat

        # Create a new OpenAI Chat if needed
        if assistant:
            # Try to find an existing chat for this assistant and telegram chat
            existing_chat = OpenAIChat.objects.filter(
                assistant=assistant,
                title=f"Telegram Chat {self.telegram_id}"
            ).first()

            if existing_chat:
                self.openai_chat = existing_chat
            else:
                # Create a new chat if none exists
                new_chat = OpenAIChat.objects.create(
                    user=system_user,
                    assistant=assistant,
                    title=f"Telegram Chat {self.telegram_id}"
                )
                self.openai_chat = new_chat
        else:
            self.openai_chat = None

        self.save()

        return self.openai_chat

    def get_or_set_default_assistant(self):
        """
        Get the active assistant or set a default one if none is active.
        For group chats, use the assigned assistant from the associated TelegramGroup if available.

        Returns:
            Assistant: The active assistant
        """
        # If there's already an active assistant, use it
        if self.active_assistant:
            return self.active_assistant

        # For group chats, check if there's an associated group with an assigned assistant
        if self.type in ['group', 'supergroup'] and self.telegram_group and self.telegram_group.assigned_assistant:
            self.set_active_assistant(self.telegram_group.assigned_assistant)
            return self.telegram_group.assigned_assistant

        # Get the first active assistant as default
        default_assistant = Assistant.objects.filter(is_active=True).first()

        if default_assistant:
            self.set_active_assistant(default_assistant)
            return default_assistant

        return None

    class Meta:
        verbose_name = _("Telegram Chat")
        verbose_name_plural = _("Telegram Chats")
        ordering = ["-updated_at"]


class TelegramMessage(models.Model):
    """
    Model to store Telegram Messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(_("Telegram Message ID"))
    chat = models.ForeignKey(
        TelegramChat, on_delete=models.CASCADE, 
        related_name="messages"
    )
    sender = models.ForeignKey(
        TelegramUser, on_delete=models.SET_NULL, 
        related_name="sent_messages", null=True, blank=True
    )
    bot = models.ForeignKey(
        TelegramBot, on_delete=models.CASCADE, 
        related_name="messages"
    )
    text = models.TextField(_("Text"), blank=True)
    reply_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, 
        related_name="replies", null=True, blank=True
    )
    operation = models.ForeignKey(
        Operation, on_delete=models.SET_NULL,
        related_name="telegram_messages", null=True, blank=True
    )
    quote = models.ForeignKey(
        "sales_panel.Quotation", on_delete=models.SET_NULL,
        related_name="telegram_quote", null=True, blank=True
    )
    media_type = models.CharField(_("Media Type"), max_length=50, blank=True)
    media_file_id = models.CharField(_("Media File ID"), max_length=255, blank=True)
    media_url = models.URLField(_("Media URL"), blank=True)
    image = models.ImageField(upload_to="telegram_images/", null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    def __str__(self):
        return f"Message {self.telegram_id} in {self.chat}"

    class Meta:
        verbose_name = _("Telegram Message")
        verbose_name_plural = _("Telegram Messages")
        ordering = ["created_at"]
        unique_together = ('telegram_id', 'chat')


class TelegramReaction(models.Model):
    """
    Model to store reactions to Telegram messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        TelegramMessage, on_delete=models.CASCADE, 
        related_name="reactions"
    )
    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, 
        related_name="reactions"
    )
    emoji = models.CharField(_("Emoji"), max_length=50)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    def __str__(self):
        return f"{self.emoji} by {self.user} on {self.message}"

    class Meta:
        verbose_name = _("Telegram Reaction")
        verbose_name_plural = _("Telegram Reactions")
        ordering = ["-created_at"]
        unique_together = ('message', 'user', 'emoji')


class TelegramWebApp(models.Model):
    """
    Model to store Telegram WebApp configurations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(
        TelegramBot, on_delete=models.CASCADE, 
        related_name="webapps"
    )
    name = models.CharField(_("Name"), max_length=255)
    url = models.URLField(_("URL"))
    button_text = models.CharField(_("Button Text"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    is_active = models.BooleanField(_("Is active"), default=True)

    def __str__(self):
        return f"{self.name} for {self.bot.name}"

    class Meta:
        verbose_name = _("Telegram WebApp")
        verbose_name_plural = _("Telegram WebApps")
        ordering = ["-created_at"]
