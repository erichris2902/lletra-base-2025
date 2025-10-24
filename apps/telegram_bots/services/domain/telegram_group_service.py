from django.db import transaction
from ...models import TelegramGroup
from apps.openai_assistant.models import Assistant

class TelegramGroupService:
    """
    Gestiona grupos de Telegram y su relación con asistentes.
    """

    @staticmethod
    @transaction.atomic
    def get_or_create(telegram_id, name, description=""):
        group, _ = TelegramGroup.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={"name": name, "description": description},
        )
        return group

    @staticmethod
    def assign_assistant(group, assistant_id):
        try:
            assistant = Assistant.objects.get(id=assistant_id)
            group.assigned_assistant = assistant
            group.save(update_fields=["assigned_assistant"])
            print(f"[TelegramGroupService] Asistente {assistant.name} asignado a {group.name}")
            return True
        except Assistant.DoesNotExist:
            print(f"[TelegramGroupService] Asistente {assistant_id} no encontrado")
            return False
