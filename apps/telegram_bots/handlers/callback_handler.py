from apps.telegram_bots.services.telegram_api import TelegramAPI


class CallbackHandler:
    """
    Maneja callback queries de botones inline.
    """
    def __init__(self, bot):
        self.bot = bot
        self.api = TelegramAPI(bot.token)

    def handle(self, callback_data):
        query_id = callback_data.get('id')
        from_user = callback_data.get('from', {}).get('username', 'unknown')
        data = callback_data.get('data', '')
        chat_id = callback_data.get('message', {}).get('chat', {}).get('id')

        print(f"[CallbackHandler] Callback recibido de @{from_user}: {data}")

        # Aquí puedes enrutar acciones por 'data'
        if data == "approve_action":
            self.api.send_message(chat_id, "✅ Acción aprobada.")
        elif data == "cancel_action":
            self.api.send_message(chat_id, "❌ Acción cancelada.")
        else:
            self.api.send_message(chat_id, f"Comando desconocido: {data}")

        return {"status": "callback_processed", "data": data}
