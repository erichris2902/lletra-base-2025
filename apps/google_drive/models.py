from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
import os
from django.conf import settings


class GoogleDriveCredential(models.Model):
    """
    Model to store Google Drive OAuth2 credentials for users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="google_drive_credential"
    )
    access_token = models.TextField(_("Access Token"))
    refresh_token = models.TextField(_("Refresh Token"))
    token_expiry = models.DateTimeField(_("Token Expiry"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"Google Drive Credential for {self.user.username}"

    class Meta:
        verbose_name = _("Google Drive Credential")
        verbose_name_plural = _("Google Drive Credentials")
        ordering = ["-updated_at"]


class GoogleDriveServiceAccount(models.Model):
    """
    Model to store Google Drive service account credentials.
    This allows for API-based authentication without being tied to specific users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255, unique=True)
    credentials_json = models.TextField(_("Service Account Credentials JSON"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"Google Drive Service Account: {self.name}"

    class Meta:
        verbose_name = _("Google Drive Service Account")
        verbose_name_plural = _("Google Drive Service Accounts")
        ordering = ["-updated_at"]


class GoogleDriveFolder(models.Model):
    """
    Model to track Google Drive folders.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="google_drive_folders"
    )
    name = models.CharField(_("Folder Name"), max_length=255)
    drive_id = models.CharField(_("Google Drive ID"), max_length=255)
    parent_folder = models.ForeignKey(
        'self', on_delete=models.SET_NULL, 
        null=True, blank=True, related_name="subfolders"
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.drive_id})"

    class Meta:
        verbose_name = _("Google Drive Folder")
        verbose_name_plural = _("Google Drive Folders")
        ordering = ["name"]
        unique_together = ('user', 'drive_id')


class GoogleDriveFile(models.Model):
    """
    Model to track Google Drive files.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="google_drive_files"
    )
    name = models.CharField(_("File Name"), max_length=255)
    drive_id = models.CharField(_("Google Drive ID"), max_length=255)
    mime_type = models.CharField(_("MIME Type"), max_length=100)
    size = models.BigIntegerField(_("Size in bytes"), default=0)
    md5_checksum = models.CharField(_("MD5 Checksum"), max_length=32, blank=True)
    folder = models.ForeignKey(
        GoogleDriveFolder, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name="files"
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.drive_id})"

    @property
    def extension(self):
        """Get the file extension."""
        return os.path.splitext(self.name)[1].lower() if '.' in self.name else ''

    class Meta:
        verbose_name = _("Google Drive File")
        verbose_name_plural = _("Google Drive Files")
        ordering = ["name"]
        unique_together = ('user', 'drive_id')
