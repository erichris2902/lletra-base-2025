from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class GoogleDriveConfig(AppConfig):
    name = 'apps.google_drive'
    verbose_name = _('Google Drive')
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        # Import signal handlers
        # import apps.google_drive.signals
        pass