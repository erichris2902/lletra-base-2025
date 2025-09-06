from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class OpenAIAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.openai_assistant'
    verbose_name = _('OpenAI Assistant')
    
    def ready(self):
        # Import signals or perform other initialization here
        pass