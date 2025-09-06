from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Assistant, Tool, Chat, Message, ToolExecution

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

class ToolExecutionInline(admin.TabularInline):
    model = ToolExecution
    extra = 0
    fields = ('tool_name', 'status', 'created_at')
    readonly_fields = ('tool_name', 'status', 'created_at', 'input_data', 'output_data')
    can_delete = False
    max_num = 0

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('get_chat_title', 'role', 'get_content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'chat__title', 'chat__user__username')
    readonly_fields = ('chat', 'role', 'content', 'openai_message_id', 'created_at')
    inlines = [ToolExecutionInline]
    fieldsets = (
        (None, {
            'fields': ('chat', 'role', 'content')
        }),
        (_('OpenAI Information'), {
            'fields': ('openai_message_id',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_chat_title(self, obj):
        return obj.chat.title
    get_chat_title.short_description = _('Chat')
    get_chat_title.admin_order_field = 'chat__title'
    
    def get_content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = _('Content')

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

@admin.register(ToolExecution)
class ToolExecutionAdmin(admin.ModelAdmin):
    list_display = ('tool_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tool_name', 'message__content')
    readonly_fields = ('message', 'tool', 'tool_name', 'input_data', 'output_data', 'status', 'openai_tool_call_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('message', 'tool', 'tool_name', 'status')
        }),
        (_('Data'), {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        (_('OpenAI Information'), {
            'fields': ('openai_tool_call_id',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )