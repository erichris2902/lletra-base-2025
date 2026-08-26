from django.conf import settings
from django.db import transaction
from apps.openai_assistant.services import AssistantService, ChatService, ResponsesService
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

        # Asegurar que el chat tenga el assistant activo registrado
        chat.set_active_assistant2(assistant)

        # Enrutamiento: si es Lyna 3B o Folios General, usar ResponsesService (stateless)
        try:
            from apps.openai_assistant.integrations.lyna_3b import (
                LYNA3B_ASSISTANT_ID,
                get_lyna3b_config_and_handlers,
            )
        except Exception:
            LYNA3B_ASSISTANT_ID = None
            get_lyna3b_config_and_handlers = None

        try:
            from apps.openai_assistant.integrations.folios_general import (
                FOLIOS_GENERAL_ASSISTANT_ID,
                get_folios_general_config_and_handlers,
            )
        except Exception:
            FOLIOS_GENERAL_ASSISTANT_ID = None
            get_folios_general_config_and_handlers = None

        try:
            from apps.openai_assistant.integrations.lyna_asturiano import (
                ASTURIANO_ASSISTANT_ID,
                get_asturiano_config_and_handlers,
            )
        except Exception:
            ASTURIANO_ASSISTANT_ID = None
            get_asturiano_config_and_handlers = None

        if LYNA3B_ASSISTANT_ID and str(assistant.id) == str(LYNA3B_ASSISTANT_ID) and get_lyna3b_config_and_handlers:
            try:
                config, handlers = get_lyna3b_config_and_handlers()
                service = ResponsesService()
                result = service.run_stateless(config, user_input=message.text, tool_handlers=handlers)
                # Responder con el resumen en texto natural tras ejecutar register_operations
                if result and isinstance(result, dict):
                    text = result.get("text") or "Estoy procesando tu mensaje."
                    return text
            except Exception as e:
                # Si algo falla en el nuevo flujo, hacemos fallback al legado
                print(f"[TelegramOpenAIIntegration] Error ResponsesService Lyna3B: {e}")

        if FOLIOS_GENERAL_ASSISTANT_ID and str(assistant.id) == str(FOLIOS_GENERAL_ASSISTANT_ID) and get_folios_general_config_and_handlers:
            try:
                config, handlers = get_folios_general_config_and_handlers()
                service = ResponsesService()
                result = service.run_stateless(config, user_input=message.text, tool_handlers=handlers)
                if result and isinstance(result, dict):
                    text = result.get("text") or "Estoy procesando tu mensaje."
                    return text
            except Exception as e:
                print(f"[TelegramOpenAIIntegration] Error ResponsesService FoliosGeneral: {e}")

        if ASTURIANO_ASSISTANT_ID and str(assistant.id) == str(ASTURIANO_ASSISTANT_ID) and get_asturiano_config_and_handlers:
            try:
                config, handlers = get_asturiano_config_and_handlers()
                service = ResponsesService()
                result = service.run_stateless(config, user_input=message.text, tool_handlers=handlers)
                if result and isinstance(result, dict):
                    text = result.get("text") or "Estoy procesando tu mensaje."
                    return text
            except Exception as e:
                print(f"[TelegramOpenAIIntegration] Error ResponsesService LynaAsturiano: {e}")

        # Flujo legado por defecto (Assistants API)
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