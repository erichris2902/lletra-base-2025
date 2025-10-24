from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Assistant, Tool, Chat, Message

class ToolInline(admin.TabularInline):
    model = Tool
    extra = 1
    fields = ('name', 'type', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Assistant)
class AssistantAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'created_by', 'created_at', 'is_active')
    list_filter = ('model', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'instructions')
    readonly_fields = ('openai_id', 'created_at', 'updated_at')
    inlines = [ToolInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'instructions', 'model', 'is_active')
        }),
        (_('OpenAI Information'), {
            'fields': ('openai_id',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('role', 'content', 'created_at')
    readonly_fields = ('role', 'content', 'created_at', 'openai_message_id')
    can_delete = False
    max_num = 0
    ordering = ('created_at',)

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'assistant', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'user__username', 'assistant__name')
    readonly_fields = ('openai_thread_id', 'created_at', 'updated_at')
    inlines = [MessageInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'user', 'assistant', 'is_active')
        }),
        (_('OpenAI Information'), {
            'fields': ('openai_thread_id',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'assistant', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('name', 'description', 'assistant__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('assistant', 'name', 'type', 'description')
        }),
        (_('Parameters'), {
            'fields': ('parameters',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )