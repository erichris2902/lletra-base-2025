from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class TelegramBotsConfig(AppConfig):
    name = 'apps.telegram_bots'
    verbose_name = _('Telegram Bots')
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        # Import signal handlers
        # import apps.telegram_bots.signals
        pass