from ..business_rules.folios_lletra import FoliosLletraRule
from ..business_rules.embarques_lletra import EmbarquesLletraRule
from ..models import TelegramChat
from ..services.domain.telegram_user_service import TelegramUserService


class ReactionHandler:
    """
    Maneja reacciones de mensajes (👍, 👎, 🤔, etc.) y aplica las reglas de negocio.
    """
    def __init__(self, bot):
        self.bot = bot

    def handle(self, reaction_data):
        user = TelegramUserService.get_or_create(reaction_data.get('user'))
        chat_id = reaction_data.get('chat', {}).get('id')

        if not user or not chat_id:
            print("[ReactionHandler] Reacción inválida o sin chat_id.")
            return {"status": "invalid_reaction"}

        try:
            chat = TelegramChat.objects.get(telegram_id=chat_id)
        except TelegramChat.DoesNotExist:
            print(f"[ReactionHandler] Chat no encontrado: {chat_id}")
            return {"status": "chat_not_found"}

        if not chat.telegram_group:
            return {"status": "no_group"}

        group_name = chat.telegram_group.name
        print(f"[ReactionHandler] Reacción en grupo: {group_name}")

        match group_name:
            case "Folios Lletra":
                return FoliosLletraRule.handle_reaction(self.bot, chat, user, reaction_data)
            case "Embarques Lletra":
                return EmbarquesLletraRule.handle_reaction(self.bot, chat, user, reaction_data)
            case _:
                return {"status": "reaction_ignored"}
