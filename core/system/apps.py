from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class SystemConfig(AppConfig):
    name = 'core.system'
    verbose_name = _('System')
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        # Import signal handlers
        # import apps.system.signals
        pass