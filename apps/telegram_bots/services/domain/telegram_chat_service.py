from django.db import transaction
from ...models import TelegramChat, TelegramGroup


class TelegramChatService:
    """
    Encapsula la creación y mantenimiento de TelegramChat y su relación con grupos.
    """

    @staticmethod
    @transaction.atomic
    def get_or_create(data):
        if not data or 'id' not in data:
            return None

        telegram_id = data['id']
        chat_type = data.get('type', 'private')
        title = data.get('title', '')
        username = data.get('username', '')

        chat, created = TelegramChat.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'type': chat_type,
                'title': title,
                'username': username,
            }
        )

        # Actualizar si cambió algo
        updated_fields = []
        if chat.title != title:
            chat.title = title
            updated_fields.append('title')
        if chat.username != username:
            chat.username = username
            updated_fields.append('username')
        if chat.type != chat_type:
            chat.type = chat_type
            updated_fields.append('type')

        # Asociar a grupo si es grupo/supergrupo
        if chat_type in ['group', 'supergroup']:
            if not chat.telegram_group:
                group, _ = TelegramGroup.objects.get_or_create(
                    telegram_id=telegram_id,
                    defaults={
                        'name': title or f"Group {telegram_id}",
                        'description': f"Auto-created from chat {telegram_id}",
                    },
                )
                chat.telegram_group = group
                updated_fields.append('telegram_group')

        if updated_fields:
            chat.save(update_fields=updated_fields)

        return chat
