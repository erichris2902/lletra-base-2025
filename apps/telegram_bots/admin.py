from django.contrib import admin
from .models import (
    TelegramBot, TelegramUser, TelegramChat, TelegramGroup,
    TelegramMessage, TelegramReaction, TelegramWebApp
)

@admin.register(TelegramBot)
class TelegramBotAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'is_active', 'webhook_set', 'created_at')
    list_filter = ('is_active', 'webhook_set')
    search_fields = ('name', 'username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'username', 'token', 'description')
        }),
        ('Webhook', {
            'fields': ('webhook_url', 'webhook_set')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'last_name', 'created_at')
    list_filter = ('is_bot',)
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at')
    #raw_id_fields = ('user',)

@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'assigned_assistant', 'is_active', 'created_at')
    list_filter = ('is_active', 'assigned_assistant')
    search_fields = ('name', 'telegram_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'telegram_id', 'description', 'contact_info')
        }),
        ('Assistant', {
            'fields': ('assigned_assistant',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    raw_id_fields = ('assigned_assistant',)

@admin.register(TelegramChat)
class TelegramChatAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'type', 'title', 'username', 'telegram_group', 'active_assistant', 'created_at')
    list_filter = ('type', 'telegram_group', 'active_assistant')
    search_fields = ('telegram_id', 'title', 'username')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('participants',)
    raw_id_fields = ('active_assistant', 'openai_chat', 'telegram_group')

@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'chat', 'sender', 'bot', 'created_at')
    list_filter = ('bot', 'media_type')
    search_fields = ('telegram_id', 'text')
    readonly_fields = ('created_at',)
    raw_id_fields = ('chat', 'sender', 'bot', 'reply_to')

@admin.register(TelegramReaction)
class TelegramReactionAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'user', 'message', 'created_at')
    list_filter = ('emoji',)
    search_fields = ('emoji',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('message', 'user')

@admin.register(TelegramWebApp)
class TelegramWebAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'bot', 'url', 'is_active', 'created_at')
    list_filter = ('is_active', 'bot')
    search_fields = ('name', 'url', 'button_text')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('bot',)
