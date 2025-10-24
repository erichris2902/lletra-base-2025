from apps.telegram_bots.business_rules.cotizaciones_lletra import CotizacionesLletraRule
from apps.telegram_bots.business_rules.embarques_lletra import EmbarquesLletraRule
from apps.telegram_bots.business_rules.folios_lletra import FoliosLletraRule
from apps.telegram_bots.handlers.command_handler import CommandHandler
from apps.telegram_bots.services.telegram_api import TelegramAPI

from apps.telegram_bots.services.domain.telegram_user_service import TelegramUserService

from apps.telegram_bots.services.domain.telegram_chat_service import TelegramChatService

from apps.telegram_bots.services.domain.telegram_message_service import TelegramMessageService


class MessageHandler:
    def __init__(self, bot):
        self.bot = bot
        self.api = TelegramAPI(bot.token)

    def handle(self, message_data):
        # 1️⃣ Usuario y chat
        print(f"MESSAGE_HANDLER")
        user = TelegramUserService.get_or_create(message_data.get('from'))
        chat = TelegramChatService.get_or_create(message_data.get('chat'))

        if not chat or not user:
            print(f"[MessageHandler] Usuario o chat no válidos para mensaje: {message_data}")
            return {"status": "invalid_message"}

        # 2️⃣ Crear mensaje en DB
        message = TelegramMessageService.create(self.bot, chat, user, message_data)

        # 3️⃣ Comandos (empiezan con '/')
        text = (message_data.get('text') or "").strip()
        if text.startswith("/"):
            print(f"[MessageHandler] Comando detectado: {text}")
            return CommandHandler(self.bot, chat, message).execute(text)

        # 4️⃣ Reglas de negocio por grupo
        if chat.telegram_group:
            group_name = chat.telegram_group.name
            print(f"[MessageHandler] Mensaje en grupo: {group_name}")

            if group_name == "Folios Lletra":
                return FoliosLletraRule.execute(self.bot, chat, message)
            elif group_name == "Embarques Lletra":
                return EmbarquesLletraRule.execute(self.bot, chat, message)
            elif group_name == "Comercial Lletra":
                return CotizacionesLletraRule.execute(self.bot, chat, message_data)

        # 5️⃣ Interacción con asistente (grupos o privados)
        from apps.telegram_bots.services.openai_integration import TelegramOpenAIIntegration
        ai_integration = TelegramOpenAIIntegration()

        if chat.type in ['group', 'supergroup']:
            if f"@{self.bot.username}" in text:
                print(f"[MessageHandler] Bot mencionado en grupo, procesando con asistente.")
                response_text = ai_integration.process_message(message, user)
                self.api.send_message(chat.telegram_id, response_text, reply_to=message.telegram_id)
                return {"status": "assistant_response_sent"}
            return {"status": "not_mentioned_in_group"}

        # 6️⃣ Chat privado: procesar con asistente directamente
        self.api.send_message(chat.telegram_id, "Procesando...")
        response_text = ai_integration.process_message(message, user)
        self.api.send_message(chat.telegram_id, response_text, reply_to=message.telegram_id)

        return {"status": "assistant_response_sent"}
