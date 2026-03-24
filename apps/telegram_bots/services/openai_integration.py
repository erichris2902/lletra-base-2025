from django.conf import settings
from django.db import transaction
from apps.openai_assistant.services import AssistantService, ChatService
from apps.openai_assistant.models import Assistant
from apps.telegram_bots.models import TelegramChat, TelegramMessage, TelegramUser


class TelegramOpenAIIntegration:

    def __init__(self):
        self.openai_service = AssistantService()
        self.chat_service = ChatService()

    def process_message(self, bot, message: TelegramMessage, user: TelegramUser = None):
        print("PROCCESS_MESSAGE")
        chat = message.chat

        assistant = self._resolve_assistant(bot, chat)
        if not assistant:
            return "No assistants available. Please contact the administrator."

        if chat.active_assistant_id != assistant.id or not chat.openai_chat:
            chat.set_active_assistant(assistant)

        openai_chat = chat.openai_chat
        new_messages = self.chat_service.send_message(openai_chat, message.text, user)

        assistant_responses = [m for m in new_messages if m.role == 'assistant']
        if assistant_responses:
            print(assistant_responses)
            return assistant_responses[-1].content

        print("END_PROCCESS_MESSAGE")
        return "I'm processing your message. Please wait a moment."

    def _resolve_assistant(self, bot, chat: TelegramChat):
        # 1. Si el chat ya tiene assistant, respetarlo
        print("-----")
        if chat.active_assistant and chat.active_assistant.is_active:
            print(1)
            return chat.active_assistant

        # 2. Primer intento: assistant por defecto del TelegramBot
        if bot.default_assistant and bot.default_assistant.is_active:
            print(2)
            return bot.default_assistant

        # 3. Fallback global
        print(3)
        return Assistant.objects.filter(is_active=True, is_default=True).first()

    def switch_assistant(self, chat: TelegramChat, assistant_identifier: str):
        try:
            assistant = None
            try:
                assistant = Assistant.objects.get(pk=assistant_identifier)
            except Exception:
                assistant = Assistant.objects.filter(
                    telegram_command__iexact="/" + assistant_identifier,
                    is_active=True
                ).first()

            if not assistant:
                return False, f"Assistant '{assistant_identifier}' not found."

            chat.set_active_assistant(assistant)
            return True, f"Switched to assistant: {assistant.name}"

        except Exception as e:
            print(e)
            return False, f"Error switching assistant: {str(e)}"

    def get_available_assistants(self):
        return Assistant.objects.filter(is_active=True)