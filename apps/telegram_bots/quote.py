import json
import logging
from datetime import datetime
from apps.telegram_bots.models import TelegramGroup, TelegramUser, TelegramBot, TelegramChat, TelegramMessage
from apps.telegram_bots.services import send_telegram_message
from core.sales_panel.models.commercial import Quotation
from core.system.functions import normalize_string
from core.system.models import SystemUser

logger = logging.getLogger(__name__)


def register_quote(tool_input, telegram_user: TelegramUser=None):
    """
    Process the register_operations tool call from OpenAI Assistant.

    Args:
        tool_input (str): JSON string with operations data

    Returns:
        dict: Result of the operation
    """
    try:
        # Parse the input JSON
        input_data = json.loads(tool_input)

        # Cargar credenciales almacenadas para el usuario
        _user = SystemUser.objects.get(telegram_username=telegram_user.first_name) if telegram_user else None

        origen = normalize_string(input_data["origen"])
        destino = normalize_string(input_data["destino"])
        tipo_carga = normalize_string(input_data["tipo_carga"])
        unidad_requerida = normalize_string(input_data["unidad_requerida"])
        requerimientos = normalize_string(input_data["requerimientos"])
        peso = input_data["peso"]

        quote, created = Quotation.objects.get_or_create(
            origin=origen,
            destiny=destino,
            tipo_carga=tipo_carga,
            unit=unidad_requerida,
            requerimientos=requerimientos,
            peso=peso,
            user=_user,
        )
        result_lines = ["SE SOLICITO LA SIGUIENTE COTIZACION\n"]
        result_lines.append(
            f"• Origen: `{str(origen)}`\n"
            f"• Destino: `{str(destino)}`\n"
            f"• Tipo de carga: `{str(tipo_carga)}`\n"
            f"• Unidad: `{str(unidad_requerida)}`\n"
            f"• Requerimientos: `{str(requerimientos)}`\n"
            f"• Peso: `{str(peso)}`\n"
        )

        if "fecha" in input_data.keys():
            date = datetime.strptime(input_data["fecha"], "%Y-%m-%d").date()
            quote.date = date
            quote.save()
            result_lines.append(
                f"• Fecha: `{str(date)}`\n"
            )

        bot_token = TelegramBot.objects.get(username='prueba_lletra_bot').token
        group_chat_id = TelegramGroup.objects.get(name='Comercial Lletra').telegram_id

        if not bot_token or not group_chat_id:
            logger.warning("Telegram notification settings not configured")
            return False

        # Get or create the bot
        bot, created = TelegramBot.objects.get_or_create(
            token=bot_token,
            defaults={'name': 'Operations Notification Bot'}
        )

        # Format the message
        message_text = "\n".join(result_lines)

        # Send the message
        response = send_telegram_message(bot, group_chat_id, message_text)

        # If the message was sent successfully, link it to the operation
        if response and 'result' in response and 'message_id' in response['result']:
            message_id = response['result']['message_id']

            # Get the chat
            chat = TelegramChat.objects.get(telegram_id=group_chat_id)

            # Get or create the message
            telegram_message, created = TelegramMessage.objects.get_or_create(
                telegram_id=message_id,
                chat=chat,
                bot=bot,
                defaults={
                    'text': message_text,
                    'quote': quote
                }
            )

            # If the message already existed but wasn't linked to the operation, link it
            if not created and not telegram_message.operation:
                telegram_message.quote = quote
                telegram_message.save()

            logger.info(f"Linked message {message_id} to quote {quote.id}")

        return {"results": "Cotizacion registrada con exito"}

    except Exception as e:
        logger.exception(f"Error in register_operations: {str(e)}")
        print(e)
        return {"error": str(e)}

