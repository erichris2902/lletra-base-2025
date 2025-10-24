from apps.telegram_bots.services.openai_integration import TelegramOpenAIIntegration
from apps.telegram_bots.services.telegram_api import TelegramAPI


class CommandHandler:
    def __init__(self, bot, chat, message):
        self.bot = bot
        self.chat = chat
        self.message = message
        self.api = TelegramAPI(bot.token)

    def execute(self, command_text):
        parts = command_text.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ''

        match command:
            case '/start':
                return self._handle_start(args)
            case '/help':
                return self._handle_help(args)
            case '/assistants':
                return self._handle_assistants(args)
            case _ if command.startswith('/') and len(command) > 1:
                return self._handle_switch(command[1:])
            case _:
                return {"status": "unknown_command"}

    def _handle_start(self, args):
        chat = self.chat
        if not chat.active_assistant:
            chat.get_or_set_default_assistant()

        assistant_info = ""
        if chat.active_assistant:
            assistant_info = f"\n\nCurrently talking to: {chat.active_assistant.name}"

        message = (
            f"Welcome to {self.bot.name}!\n"
            f"This bot lets you chat with AI assistants.{assistant_info}\n\n"
            f"Use /help to see commands."
        )
        self.api.send_message(chat.telegram_id, message)
        return {"status": "start_command"}

    def _handle_help(self, args):
        help_text = (
            f"Available commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/assistants - List assistants\n"
            "/<id> - Switch assistant (e.g., /3B)"
        )
        self.api.send_message(self.chat.telegram_id, help_text)
        return {"status": "help_command"}

    def _handle_assistants(self, args):
        integration = TelegramOpenAIIntegration()
        assistants = integration.get_available_assistants()

        if not assistants:
            self.api.send_message(self.chat.telegram_id, "No assistants available.")
            return {"status": "no_assistants"}

        text = "Available assistants:\n\n"
        for a in assistants:
            text += f"/{a.id} - {a.name}\n"
            if a.description:
                text += f"  {a.description}\n\n"
        self.api.send_message(self.chat.telegram_id, text)
        return {"status": "assistants_listed"}

    def _handle_switch(self, assistant_id):
        integration = TelegramOpenAIIntegration()
        success, response = integration.switch_assistant(self.chat, assistant_id)
        self.api.send_message(self.chat.telegram_id, response)
        return {"status": "assistant_switched" if success else "assistant_switch_failed"}
