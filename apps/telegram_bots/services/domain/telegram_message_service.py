from django.db import transaction
from ...models import TelegramMessage

class TelegramMessageService:
    """
    Gestiona la creación y persistencia de mensajes de Telegram (texto o medios).
    """

    @staticmethod
    @transaction.atomic
    def create(bot, chat, user, message_data):
        if not message_data:
            return None

        reply_to = None
        if 'reply_to_message' in message_data:
            try:
                reply_to = TelegramMessage.objects.get(
                    telegram_id=message_data['reply_to_message']['message_id'],
                    chat=chat,
                )
            except TelegramMessage.DoesNotExist:
                print(f"[TelegramMessageService] Reply message not found.")

        media_type, media_file_id = TelegramMessageService._extract_media(message_data)

        message, _ = TelegramMessage.objects.get_or_create(
            telegram_id=message_data['message_id'],
            chat=chat,
            defaults={
                "sender": user,
                "bot": bot,
                "text": message_data.get('text', ''),
                "reply_to": reply_to,
                "media_type": media_type,
                "media_file_id": media_file_id,
            },
        )
        return message

    @staticmethod
    def _extract_media(message_data):
        """
        Extrae tipo y file_id si el mensaje contiene medios.
        """
        media_types = ['photo', 'video', 'audio', 'voice', 'document', 'sticker']
        for mtype in media_types:
            if mtype in message_data:
                if mtype == 'photo':
                    return 'photo', message_data['photo'][-1]['file_id']
                return mtype, message_data[mtype]['file_id']
        return '', ''
