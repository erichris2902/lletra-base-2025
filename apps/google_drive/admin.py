from django.contrib import admin
from .models import GoogleDriveCredential, GoogleDriveFolder, GoogleDriveFile

@admin.register(GoogleDriveCredential)
class GoogleDriveCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_expiry', 'created_at', 'updated_at')
    list_filter = ('token_expiry',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Tokens', {
            'fields': ('access_token', 'refresh_token', 'token_expiry')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(GoogleDriveFolder)
class GoogleDriveFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'drive_id', 'parent_folder', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'drive_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'parent_folder')
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'drive_id')
        }),
        ('Hierarchy', {
            'fields': ('parent_folder',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(GoogleDriveFile)
class GoogleDriveFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'drive_id', 'mime_type', 'size', 'folder', 'created_at')
    list_filter = ('mime_type', 'created_at')
    search_fields = ('name', 'drive_id', 'user__username', 'mime_type')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'folder')
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'drive_id')
        }),
        ('File Details', {
            'fields': ('mime_type', 'size', 'md5_checksum')
        }),
        ('Location', {
            'fields': ('folder',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )