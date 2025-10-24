from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from ...models import TelegramUser
from core.system.models.users import SystemUser

User = get_user_model()

class TelegramUserService:
    """
    Encapsula toda la lógica para obtener, crear y vincular usuarios de Telegram.
    """

    @staticmethod
    def get_or_create(data):
        print("GET_OR_CREATE")
        if not data or 'id' not in data:
            return None

        telegram_id = data['id']
        username = data.get('first_name', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        language = data.get('language_code', '')
        is_bot = data.get('is_bot', False)

        # Buscar o crear usuario de Telegram
        telegram_user, created = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'language_code': language,
                'is_bot': is_bot,
            }
        )

        if not created:
            # Actualizar datos si cambiaron
            updated_fields = []
            for field, value in {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'language_code': language,
            }.items():
                if getattr(telegram_user, field) != value:
                    setattr(telegram_user, field, value)
                    updated_fields.append(field)
            if updated_fields:
                telegram_user.save(update_fields=updated_fields)

        # Vincular con SystemUser
        if first_name:
            system_user = SystemUser.get_by_telegram_username(first_name)
            if system_user:
                system_user.user = telegram_user
                system_user.save()
            else:
                print(f"[TelegramUserService] No existe SystemUser para {first_name}")

        # Crear Django User si es necesario (solo si no es bot)
        if not is_bot:
            email = f"{username or telegram_id}@telegram.user"
            User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username or f"telegram_{telegram_id}",
                    'password': get_random_string(length=12),
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                }
            )

        return telegram_user
