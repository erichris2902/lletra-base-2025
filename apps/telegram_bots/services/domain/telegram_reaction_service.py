from django.db import transaction
from ...models import TelegramReaction


class TelegramReactionService:
    """
    Gestiona la creación, actualización y eliminación de reacciones.
    """

    @staticmethod
    @transaction.atomic
    def add_reaction(message, user, emoji):
        reaction, created = TelegramReaction.objects.get_or_create(
            message=message,
            user=user,
            emoji=emoji
        )
        if created:
            print(f"[TelegramReactionService] {emoji} añadido por {user}")
        return reaction

    @staticmethod
    @transaction.atomic
    def remove_reaction(message, user, emoji):
        TelegramReaction.objects.filter(
            message=message,
            user=user,
            emoji=emoji
        ).delete()
        print(f"[TelegramReactionService] {emoji} eliminado por {user}")
