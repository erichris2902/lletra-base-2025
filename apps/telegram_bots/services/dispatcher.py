from apps.telegram_bots.handlers.callback_handler import CallbackHandler
from apps.telegram_bots.handlers.inline_query_handler import InlineQueryHandler
from apps.telegram_bots.handlers.message_handler import MessageHandler
from apps.telegram_bots.handlers.reaction_handler import ReactionHandler


class TelegramUpdateDispatcher:
    def __init__(self, bot):
        self.bot = bot

    def dispatch(self, update_data):
        try:
            print("DISPATCHER")
            if 'message' in update_data:
                return MessageHandler(self.bot).handle(update_data['message'])
            elif 'callback_query' in update_data:
                return CallbackHandler(self.bot).handle(update_data['callback_query'])
            elif 'message_reaction' in update_data:
                return ReactionHandler(self.bot).handle(update_data['message_reaction'])
            elif 'inline_query' in update_data:
                return InlineQueryHandler(self.bot).handle(update_data['inline_query'])
            else:
                print(f"[Dispatcher] Tipo de update no manejado: {update_data.keys()}")
                return {"status": "unhandled_update"}
        except Exception as e:
            print(f"[Dispatcher] Error procesando update: {e}")
            return {"status": "error", "error": str(e)}