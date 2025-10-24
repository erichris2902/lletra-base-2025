import requests
from django.core.files.base import ContentFile

from apps.telegram_bots.models import TelegramMessage, TelegramUser, TelegramChat
from apps.telegram_bots.services.telegram_api import TelegramAPI
from core.sales_panel.models.commercial import StatusDeCotizacion
from core.system.functions import get_file_path


class CotizacionesLletraRule:
    """
    Regla de negocio para el grupo 'Comercial Lletra'.
    Maneja fotos de cotizaciones y su envío al cliente.
    """

    @staticmethod
    def execute(bot, chat, message_data):
        """
        Maneja mensajes con fotos enviadas en respuesta a cotizaciones del bot.
        """
        reply_to_message = message_data.get('reply_to_message')
        if not reply_to_message or not chat.telegram_group or chat.telegram_group.name != "Comercial Lletra":
            return {"status": "no_action"}

        # Solo procesar fotos
        if 'photo' not in message_data:
            return {"status": "no_photo"}

        from_user = reply_to_message.get('from', {})
        from_username = from_user.get('username')
        if not from_username or from_username != bot.name:
            return {"status": "not_a_bot_reply"}

        api = TelegramAPI(bot.token)

        try:
            # 1️⃣ Guardar imagen
            photo_sizes = message_data['photo']
            best_photo = photo_sizes[-1]  # mejor calidad
            file_id = best_photo['file_id']

            file_path = get_file_path(bot.token, file_id)
            file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

            image_data = requests.get(file_url).content

            message = TelegramMessage.objects.get(
                telegram_id=message_data['message_id'], chat=chat
            )
            message.media_type = 'photo'
            message.media_file_id = file_id
            message.media_url = file_url
            message.image.save(f"{message.telegram_id}.jpg", ContentFile(image_data), save=True)

            # 2️⃣ Recuperar cotización original
            reply_message = TelegramMessage.objects.get(
                telegram_id=reply_to_message['message_id'], chat=chat
            )
            quote = reply_message.quote
            if not quote:
                print(f"[CotizacionesLletra] No se encontró cotización asociada a {reply_message}")
                return {"status": "no_quote"}

            # 3️⃣ Actualizar la cotización
            quote.image.save(f"{message.telegram_id}.jpg", ContentFile(image_data), save=True)
            quote.status_de_cotizacion = StatusDeCotizacion.EMITIDA
            quote.save()

            print(f"[CotizacionesLletra] Cotización {quote.id} marcada como EMITIDA")

            # 4️⃣ Enviar al cliente
            system_user = quote.user
            telegram_user = TelegramUser.objects.filter(first_name=system_user.telegram_username).first()
            if not telegram_user:
                print(f"[CotizacionesLletra] No se encontró usuario Telegram para {system_user}")
                return {"status": "no_telegram_user"}

            tele_chat = TelegramChat.objects.filter(type="private", participants=telegram_user).first()
            if not tele_chat:
                print(f"[CotizacionesLletra] No se encontró chat privado con {telegram_user}")
                return {"status": "no_chat"}

            api.send_message(
                tele_chat.telegram_id,
                "",
                image=quote.image.file
            )

            print(f"[CotizacionesLletra] Cotización {quote.id} enviada a {telegram_user.username}")
            return {"status": "quote_sent"}

        except Exception as e:
            print(f"[CotizacionesLletra] Error procesando foto de cotización: {e}")
            return {"status": "error", "error": str(e)}
