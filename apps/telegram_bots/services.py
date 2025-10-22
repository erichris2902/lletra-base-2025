import logging
import requests
import json

from django.core.files.base import ContentFile
from django.db import transaction
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string

from core.sales_panel.models.commercial import StatusDeCotizacion
from core.system.functions import get_file_path
from .models import (
    TelegramBot, TelegramUser, TelegramChat, 
    TelegramMessage, TelegramReaction, TelegramWebApp
)

logger = logging.getLogger(__name__)
User = get_user_model()

def process_update(bot, update_data):
    try:
        # Determine the type of update
        if 'message' in update_data:
            return process_message(bot, update_data['message'])
        elif 'edited_message' in update_data:
            return process_edited_message(bot, update_data['edited_message'])
        elif 'callback_query' in update_data:
            return process_callback_query(bot, update_data['callback_query'])
        elif 'inline_query' in update_data:
            return process_inline_query(bot, update_data['inline_query'])
        elif 'message_reaction' in update_data:
            return process_message_reaction(bot, update_data['message_reaction'])
        else:
            print(f"Unhandled update type: {update_data}")
            return {"status": "unhandled_update_type"}
    except Exception as e:
        print(f"Error processing update: {str(e)}")
        return {"status": "error", "message": str(e)}

def process_message(bot, message_data):
    with transaction.atomic():
        # Get or create the user
        user = get_or_create_telegram_user(message_data.get('from', {}))

        # Get or create the chat
        chat = get_or_create_telegram_chat(message_data.get('chat', {}))

        # If user is None, it means no matching SystemUser was found
        if user is None:
            if chat:
                # Send permission denied message
                send_telegram_message(
                    bot, 
                    chat.telegram_id,
                    "No tienes permiso para interactuar con este bot"
                )
            return {"status": "permission_denied"}

        # If we get here, user is not None

        # Add user to chat participants if not already there
        if chat and chat.type == 'private':
            chat.participants.add(user)

        # Create the message
        message = create_telegram_message(bot, message_data, chat, user)

        # Process commands if present
        if 'text' in message_data and message_data['text'].startswith('/'):
            return process_command(bot, message, message_data['text'])

        # Verificar si el mensaje es una respuesta a uno del bot
        reply_to_message = message_data.get('reply_to_message')

        if reply_to_message and chat.telegram_group and chat.telegram_group.name == "Comercial Lletra" and 'photo' in message_data:
            from_user = reply_to_message.get('from', {})
            from_user_username = from_user.get('username')
            if from_user_username and str(from_user_username) == str(bot.name):  # Asegúrate de tener el ID del bot guardado
                photo_sizes = message_data['photo']
                best_photo = photo_sizes[-1]  # Mejor calidad
                file_id = best_photo['file_id']

                # Guarda tipo y file_id en el modelo
                message.media_type = 'photo'
                message.media_file_id = file_id

                # Obtén file_path desde Telegram
                file_path = get_file_path(bot.token, file_id)
                file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

                # Opcional: descargar y subir a tu propio almacenamiento o solo guardar la URL
                message.media_url = file_url
                message.save()

                image_data = requests.get(file_url).content
                message.image.save(f"{message.telegram_id}.jpg", ContentFile(image_data), save=True)

                print(reply_to_message)
                telegram_message = TelegramMessage.objects.get(telegram_id=reply_to_message['message_id'], chat=chat)
                quote = telegram_message.quote
                print(telegram_message)
                print(telegram_message.quote)

                system_user = quote.user
                print(system_user)
                telegram_user = TelegramUser.objects.get(first_name=system_user.telegram_username)
                print(telegram_user)

                quote.image.save(f"{message.telegram_id}.jpg", ContentFile(image_data), save=True)
                quote.status_de_cotizacion = StatusDeCotizacion.EMITIDA
                quote.save()
                print("quote save")
                # Send the response back to the user
                print(message)
                print(telegram_message)
                print(chat)
                tele_chat = TelegramChat.objects.get(type="private", participants=telegram_user)
                print(tele_chat)
                send_telegram_message(
                    bot,
                    tele_chat.telegram_id,
                    "",
                    image=quote.image.file
                )
                print("response ok")


                return {"status": "cotizacion enviada"}

        # Check for "Asignar folios" message in Folios Lletra group
        if ('text' in message_data and 
            message_data['text'].strip().lower() == "asignar folios" and
            chat.telegram_group and 
            chat.telegram_group.name == "Folios Lletra"):
            

            # Find all operations with pre-folios but no folios
            from core.operations_panel.models import Operation
            from core.operations_panel.choices import OperationStatus

            operations_to_update = Operation.objects.filter(
                pre_folio__isnull=False,
                folio__isnull=True,
                status=OperationStatus.APPROVED
            )
            
            count = 0
            for operation in operations_to_update:
                # Assign the folio
                operation.assign_folio()
                count += 1
            
            # Reply with the result
            if count > 0:
                reply_text = f"✅ {count} pre-folios han sido convertidos a folios."
            else:
                reply_text = "ℹ️ No hay pre-folios pendientes para convertir."
                
            send_telegram_message(
                bot, 
                chat.telegram_id, 
                reply_text,
                reply_to_message_id=message_data.get('message_id')
            )
            
            print(f"Converted {count} pre-folios to folios")
            return {"status": "folios_assigned", "count": count}

        if ('text' in message_data and
                message_data['text'].strip().lower() == "confirmar packing" and
                chat.telegram_group and
                chat.telegram_group.name == "Embarques Lletra"):

            from core.operations_panel.models.operation import Operation
            from core.operations_panel.choices import OperationStatus
            operations_to_update = Operation.objects.filter(
                is_packing_ready=False,
                invoice__isnull=True,
                status=OperationStatus.APPROVED
            )

            count = 0
            for operation in operations_to_update:
                if operation.is_ready_for_invoicing():
                    # Assign the folio
                    operation.is_packing_ready = True
                    operation.save()
                    count += 1

            # Reply with the result
            if count > 0:
                reply_text = f"✅ Se han cerrado {count} packings."
            else:
                reply_text = "ℹ️ No hay packings para cerrar."

            send_telegram_message(
                bot,
                chat.telegram_id,
                reply_text,
                reply_to_message_id=message_data.get('message_id')
            )

            print(f"Converted {count} operations to is_packing_ready")
            return {"status": "is_packing_ready_assigned", "count": count}

        # Process regular messages through OpenAI Assistant
        if 'text' in message_data:
            # For group chats, only process messages that mention the bot
            if chat.type in ['group', 'supergroup']:
                # Check if the bot is mentioned in the message
                if f"@{bot.username}" in message_data['text']:
                    return process_message_with_assistant(bot, message, user)
                # If not mentioned, don't process the message
                return {"status": "not_mentioned_in_group"}
            # For private chats, process all messages
            else:
                return process_message_with_assistant(bot, message, user)
    return {"status": "not_found"}

def process_edited_message(bot, message_data):
    """
    Process an edited message update.

    Args:
        bot (TelegramBot): The bot that received the edited message
        message_data (dict): The edited message data from Telegram

    Returns:
        dict: Response data
    """
    with transaction.atomic():
        # Get the chat
        try:
            chat = TelegramChat.objects.get(telegram_id=message_data['chat']['id'])
        except TelegramChat.DoesNotExist:
            print(f"Chat not found for edited message: {message_data}")
            return {"status": "chat_not_found"}

        # Get the message
        try:
            message = TelegramMessage.objects.get(
                telegram_id=message_data['message_id'],
                chat=chat
            )

            # Update the message text
            if 'text' in message_data:
                message.text = message_data['text']
                message.save()

            return {"status": "message_updated", "message_id": str(message.id)}
        except TelegramMessage.DoesNotExist:
            print(f"Message not found for editing: {message_data}")
            return {"status": "message_not_found"}

def process_callback_query(bot, callback_data):
    """
    Process a callback query update.

    Args:
        bot (TelegramBot): The bot that received the callback query
        callback_data (dict): The callback query data from Telegram

    Returns:
        dict: Response data
    """
    # Implementation depends on specific callback requirements
    return {"status": "callback_processed"}

def process_inline_query(bot, inline_query_data):
    """
    Process an inline query update.

    Args:
        bot (TelegramBot): The bot that received the inline query
        inline_query_data (dict): The inline query data from Telegram

    Returns:
        dict: Response data
    """
    # Implementation depends on specific inline query requirements
    print("inline_query_data")
    return {"status": "inline_query_processed"}

def process_message_reaction(bot, reaction_data):
    """
    Process a message reaction update.

    Args:
        bot (TelegramBot): The bot that received the reaction
        reaction_data (dict): The reaction data from Telegram

    Returns:
        dict: Response data
    """
    with transaction.atomic():
        # Get the user
        user = get_or_create_telegram_user(reaction_data.get('user', {}))

        # Get the chat
        try:
            chat = TelegramChat.objects.get(telegram_id=reaction_data['chat']['id'])
        except TelegramChat.DoesNotExist:
            print(f"Chat not found for reaction: {reaction_data}")
            return {"status": "chat_not_found"}
        print(1)
        print(chat.telegram_group)
        if chat.telegram_group:
            if chat.telegram_group.name == "Folios Lletra":
                # Get the message
                try:
                    print(2)
                    message = TelegramMessage.objects.get(
                        telegram_id=reaction_data['message_id'],
                        chat=chat
                    )

                    # Process the reaction
                    print(3)
                    for emoji in reaction_data.get('new_reaction', []):
                        emoji_value = emoji.get('emoji', '')
                        print(4)
                        # Create the reaction record
                        reaction, created = TelegramReaction.objects.get_or_create(
                            message=message,
                            user=user,
                            emoji=emoji_value
                        )

                        # Check if the message is linked to an operation
                        if message.operation:
                            print(5)
                            # Handle thumbs up reaction (👍)
                            if emoji_value == '👍':
                                # Pre-assign a folio to the operation
                                pre_folio = message.operation.approve()

                                if pre_folio:
                                    # Reply with the pre-folio information
                                    reply_text = f"✅ Pre-folio asignado: {pre_folio}"
                                    send_telegram_message(
                                        bot,
                                        chat.telegram_id,
                                        reply_text,
                                        reply_to_message_id=message.telegram_id
                                    )
                                    print(f"Pre-folio {pre_folio} assigned to operation {message.operation.id}")

                            # Handle thumbs down reaction (👎)
                            elif emoji_value == '👎':
                                # Cancel the operation
                                message.operation.status = 'CANCELED'

                                # Delete any assigned folio/pre-folio
                                message.operation.folio = None
                                message.operation.pre_folio = None
                                message.operation.save()

                                # Reply with cancellation confirmation
                                reply_text = f"❌ Operación cancelada"
                                send_telegram_message(
                                    bot,
                                    chat.telegram_id,
                                    reply_text,
                                    reply_to_message_id=message.telegram_id
                                )
                                print(f"Operation {message.operation.id} canceled")

                    # Remove old reactions if specified
                    for emoji in reaction_data.get('old_reaction', []):
                        TelegramReaction.objects.filter(
                            message=message,
                            user=user,
                            emoji=emoji.get('emoji', '')
                        ).delete()

                    return {"status": "reaction_processed"}
                except TelegramMessage.DoesNotExist:
                    print(f"Message not found for reaction: {reaction_data}")
                    return {"status": "message_not_found"}
            elif chat.telegram_group.name == "Embarques Lletra":
                try:
                    message = TelegramMessage.objects.get(
                        telegram_id=reaction_data['message_id'],
                        chat=chat
                    )

                    # Process the reaction
                    for emoji in reaction_data.get('new_reaction', []):
                        emoji_value = emoji.get('emoji', '')

                        # Create the reaction record
                        reaction, created = TelegramReaction.objects.get_or_create(
                            message=message,
                            user=user,
                            emoji=emoji_value
                        )

                        # Check if the message is linked to an operation
                        if message.operation:
                            # Handle thumbs up reaction (🤔)
                            if emoji_value == '🤔':
                                from apps.telegram_bots.operations import send_operation_missing_items
                                from core.operations_panel.models import Operation

                                # Get the latest operation with missing items
                                # For now, we'll just get the latest operation
                                # In a real implementation, you might want to get the operation based on context
                                latest_operation = Operation.objects.order_by('-created_at').first()

                                if latest_operation:
                                    # Send missing items for the operation
                                    send_operation_missing_items(
                                        latest_operation.id,
                                        chat.telegram_id,
                                        message.telegram_id,
                                    )

                                    print(f"Sent missing items for operation {latest_operation.id}")
                                    return {"status": "missing_items_sent", "operation_id": latest_operation.id}
                                else:
                                    # No operations found
                                    reply_text = "ℹ️ No hay operaciones disponibles para mostrar faltantes."

                                    send_telegram_message(
                                        bot,
                                        chat.telegram_id,
                                        reply_text,
                                        reply_to_message_id=message.telegram_id,
                                    )

                                    print("No operations found for missing items")
                                    return {"status": "no_operations_found"}

                    # Default response for non-text messages
                    return {"status": "message_processed", "message_id": str(message.id)}
                except TelegramMessage.DoesNotExist:
                    print(f"Message not found for reaction: {reaction_data}")
                    return {"status": "message_not_found"}
        return {"status": "emoji_group_not_found"}

def process_command(bot, message, command_text):
    """
    Process a command message.

    Args:
        bot (TelegramBot): The bot that received the command
        message (TelegramMessage): The message object
        command_text (str): The command text

    Returns:
        dict: Response data
    """
    # Split the command and arguments
    parts = command_text.split(' ', 1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ''

    # Process different commands
    if command == '/start':
        return handle_start_command(bot, message, args)
    elif command == '/help':
        return handle_help_command(bot, message, args)
    elif command == '/assistants':
        return handle_assistants_command(bot, message, args)
    # Check if it's an assistant switching command (e.g., /3B)
    elif command.startswith('/') and len(command) > 1:
        # Extract the assistant identifier (remove the leading /)
        assistant_id = command[1:]
        return handle_switch_assistant_command(bot, message, assistant_id)
    # Add more command handlers as needed
    else:
        return {"status": "unknown_command"}

def handle_start_command(bot, message, args):
    """
    Handle the /start command.

    Args:
        bot (TelegramBot): The bot that received the command
        message (TelegramMessage): The message object
        args (str): Command arguments

    Returns:
        dict: Response data
    """
    from .openai_integration import TelegramOpenAIIntegration

    # Set default assistant if not already set
    chat = message.chat
    if not chat.active_assistant:
        chat.get_or_set_default_assistant()

    # Get assistant info
    assistant_info = ""
    if chat.active_assistant:
        assistant_info = f"\n\nYou are currently talking to the assistant: {chat.active_assistant.name}"

    # Send welcome message
    welcome_message = (
        f"Welcome to {bot.name}!\n\n"
        f"This bot allows you to chat with different AI assistants.{assistant_info}\n\n"
        f"Type /help to see available commands or /assistants to see all available assistants."
    )

    send_telegram_message(
        bot, 
        message.chat.telegram_id,
        welcome_message
    )

    return {"status": "start_command_processed"}

def handle_help_command(bot, message, args):
    """
    Handle the /help command.

    Args:
        bot (TelegramBot): The bot that received the command
        message (TelegramMessage): The message object
        args (str): Command arguments

    Returns:
        dict: Response data
    """
    # Send help message
    help_text = (
        f"Available commands for {bot.name}:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/assistants - List available assistants\n"
        "/<id> - Switch to a specific assistant (e.g., /3B)\n"
        # Add more commands as needed
    )

    send_telegram_message(
        bot, 
        message.chat.telegram_id,
        help_text
    )

    return {"status": "help_command_processed"}

def handle_assistants_command(bot, message, args):
    """
    Handle the /assistants command.

    Args:
        bot (TelegramBot): The bot that received the command
        message (TelegramMessage): The message object
        args (str): Command arguments

    Returns:
        dict: Response data
    """
    from .openai_integration import TelegramOpenAIIntegration

    # Get available assistants
    integration = TelegramOpenAIIntegration()
    assistants = integration.get_available_assistants()

    if not assistants:
        send_telegram_message(
            bot, 
            message.chat.telegram_id,
            "No assistants available. Please contact the administrator."
        )
        return {"status": "no_assistants"}

    # Format the list of assistants
    assistants_text = "Available assistants:\n\n"
    for assistant in assistants:
        assistants_text += f"/{assistant.id} - {assistant.name}\n"
        if assistant.description:
            assistants_text += f"  {assistant.description}\n"
        assistants_text += "\n"

    assistants_text += "\nUse /<id> to switch to a specific assistant."

    send_telegram_message(
        bot, 
        message.chat.telegram_id,
        assistants_text
    )

    return {"status": "assistants_listed"}

def handle_switch_assistant_command(bot, message, assistant_id):
    """
    Handle the command to switch to a specific assistant.

    Args:
        bot (TelegramBot): The bot that received the command
        message (TelegramMessage): The message object
        assistant_id (str): The assistant identifier

    Returns:
        dict: Response data
    """
    from .openai_integration import TelegramOpenAIIntegration

    # Switch to the specified assistant
    integration = TelegramOpenAIIntegration()
    success, response_message = integration.switch_assistant(message.chat, assistant_id)

    send_telegram_message(
        bot, 
        message.chat.telegram_id,
        response_message
    )

    return {"status": "assistant_switched" if success else "assistant_switch_failed"}

def process_message_with_assistant(bot, message, user):
    """
    Process a message through the OpenAI Assistant.

    Args:
        bot (TelegramBot): The bot that received the message
        message (TelegramMessage): The message object

    Returns:
        dict: Response data
    """
    from .openai_integration import TelegramOpenAIIntegration

    try:
        # Process the message through the OpenAI Assistant
        integration = TelegramOpenAIIntegration()
        response_text = integration.process_message(message, user)

        # Send the response back to the user
        send_telegram_message(
            bot, 
            message.chat.telegram_id,
            response_text,
            reply_to_message_id=message.telegram_id
        )

        return {"status": "assistant_response_sent"}
    except Exception as e:
        print(f"Error processing message with assistant: {str(e)}")

        # Send error message to the user
        send_telegram_message(
            bot, 
            message.chat.telegram_id,
            "Sorry, I encountered an error while processing your message. Please try again later."
        )

        return {"status": "assistant_error", "message": str(e)}

def get_or_create_telegram_user(user_data):
    """
    Get or create a TelegramUser from Telegram user data.
    Also creates a Django User if one doesn't exist.
    Associates TelegramUser with SystemUser based on telegram username.
    If no matching SystemUser is found, returns None.

    Args:
        user_data (dict): User data from Telegram

    Returns:
        TelegramUser: The user object if authorized, None otherwise
    """
    from core.system.models.users import SystemUser
    if not user_data or 'id' not in user_data:
        return None

    telegram_id = user_data['id']
    telegram_username = user_data.get('first_name', '')
    print(telegram_username)

    try:
        # Try to get existing user
        telegram_user = TelegramUser.objects.get(telegram_id=telegram_id)

        # Update user data if needed
        update_fields = []
        if 'username' in user_data and telegram_user.username != user_data['username']:
            telegram_user.username = user_data['username']
            update_fields.append('username')

        if 'first_name' in user_data and telegram_user.first_name != user_data['first_name']:
            telegram_user.first_name = user_data['first_name']
            update_fields.append('first_name')

        if 'last_name' in user_data and telegram_user.last_name != user_data['last_name']:
            telegram_user.last_name = user_data['last_name']
            update_fields.append('last_name')

        if 'language_code' in user_data and telegram_user.language_code != user_data['language_code']:
            telegram_user.language_code = user_data['language_code']
            update_fields.append('language_code')

        if update_fields:
            telegram_user.save(update_fields=update_fields)

        # Check if there's a SystemUser with matching telegram username
        if telegram_username:
            system_user = SystemUser.get_by_telegram_username(telegram_username)
            if system_user:
                # Associate TelegramUser with SystemUser
                system_user.user = telegram_user
                system_user.save()
                return telegram_user
            else:
                # No matching SystemUser found
                return None
        else:
            # No telegram username provided
            return None

    except TelegramUser.DoesNotExist:
        # Check if there's a SystemUser with matching telegram username
        if telegram_username:
            system_user = SystemUser.get_by_telegram_username(telegram_username)
            if not system_user:
                # No matching SystemUser found
                return None
        else:
            # No telegram username provided
            return None

        # Create new Django user if needed
        django_user = None
        if not user_data.get('is_bot', False):
            username = user_data.get('username', f"telegram_{telegram_id}")
            email = f"{username}@telegram.user"

            # Check if user with this email already exists
            try:
                django_user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create new user
                django_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=get_random_string(length=12),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', '')
                )

        # Create new TelegramUser
        telegram_user = TelegramUser.objects.create(
            telegram_id=telegram_id,
            username=user_data.get('username', ''),
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            language_code=user_data.get('language_code', ''),
            is_bot=user_data.get('is_bot', False)
        )

        # Associate TelegramUser with SystemUser
        if system_user:
            system_user.user = telegram_user
            system_user.save()

        return telegram_user

def get_or_create_telegram_chat(chat_data):
    """
    Get or create a TelegramChat from Telegram chat data.
    If the chat is a group chat, associate it with a TelegramGroup if one exists.

    Args:
        chat_data (dict): Chat data from Telegram

    Returns:
        TelegramChat: The chat object
    """
    if not chat_data or 'id' not in chat_data:
        return None

    telegram_id = chat_data['id']
    chat_type = chat_data.get('type', 'private')

    try:
        # Try to get existing chat
        chat = TelegramChat.objects.get(telegram_id=telegram_id)

        # Update chat data if needed
        update_fields = []
        if 'title' in chat_data and chat.title != chat_data['title']:
            chat.title = chat_data['title']
            update_fields.append('title')

        if 'username' in chat_data and chat.username != chat_data['username']:
            chat.username = chat_data['username']
            update_fields.append('username')

        if 'type' in chat_data and chat.type != chat_data['type']:
            chat.type = chat_data['type']
            update_fields.append('type')

        # Check if we need to associate with a TelegramGroup or create one
        if chat_type in ['group', 'supergroup'] and not chat.telegram_group:
            from .models import TelegramGroup
            try:
                group = TelegramGroup.objects.get(telegram_id=telegram_id)
                chat.telegram_group = group
                update_fields.append('telegram_group')
            except TelegramGroup.DoesNotExist:
                # No matching group found, create a new one
                group = TelegramGroup.objects.create(
                    telegram_id=telegram_id,
                    name=chat_data.get('title', f"Group {telegram_id}"),
                    description=f"Automatically created from chat {telegram_id}"
                )
                chat.telegram_group = group
                update_fields.append('telegram_group')

        if update_fields:
            chat.save(update_fields=update_fields)

        return chat

    except TelegramChat.DoesNotExist:
        # Create new chat
        chat = TelegramChat.objects.create(
            telegram_id=telegram_id,
            type=chat_type,
            title=chat_data.get('title', ''),
            username=chat_data.get('username', '')
        )

        # If it's a group chat, try to associate with a TelegramGroup or create one
        if chat_type in ['group', 'supergroup']:
            from .models import TelegramGroup
            try:
                group = TelegramGroup.objects.get(telegram_id=telegram_id)
                chat.telegram_group = group
                chat.save(update_fields=['telegram_group'])
            except TelegramGroup.DoesNotExist:
                # No matching group found, create a new one
                group = TelegramGroup.objects.create(
                    telegram_id=telegram_id,
                    name=chat_data.get('title', f"Group {telegram_id}"),
                    description=f"Automatically created from chat {telegram_id}"
                )
                chat.telegram_group = group
                chat.save(update_fields=['telegram_group'])

        return chat

def create_telegram_message(bot, message_data, chat, user):
    """
    Create a TelegramMessage from Telegram message data.

    Args:
        bot (TelegramBot): The bot that received the message
        message_data (dict): Message data from Telegram
        chat (TelegramChat): The chat object
        user (TelegramUser): The user object

    Returns:
        TelegramMessage: The message object
    """
    # Check for reply
    reply_to = None
    if 'reply_to_message' in message_data:
        reply_message_id = message_data['reply_to_message']['message_id']
        try:
            reply_to = TelegramMessage.objects.get(
                telegram_id=reply_message_id,
                chat=chat
            )
        except TelegramMessage.DoesNotExist:
            print(f"Reply message not found: {reply_message_id}")

    # Determine media type and file ID
    media_type = ''
    media_file_id = ''

    if 'photo' in message_data:
        media_type = 'photo'
        # Get the largest photo (last in the array)
        media_file_id = message_data['photo'][-1]['file_id']
    elif 'video' in message_data:
        media_type = 'video'
        media_file_id = message_data['video']['file_id']
    elif 'audio' in message_data:
        media_type = 'audio'
        media_file_id = message_data['audio']['file_id']
    elif 'voice' in message_data:
        media_type = 'voice'
        media_file_id = message_data['voice']['file_id']
    elif 'document' in message_data:
        media_type = 'document'
        media_file_id = message_data['document']['file_id']
    elif 'sticker' in message_data:
        media_type = 'sticker'
        media_file_id = message_data['sticker']['file_id']

    # Create the message
    print(message_data.get('text', ''))
    message, created = TelegramMessage.objects.get_or_create(
        telegram_id=message_data['message_id'],
        chat=chat,
        sender=user,
        bot=bot,
        text=message_data.get('text', ''),
        reply_to=reply_to,
        media_type=media_type,
        media_file_id=media_file_id
    )

    return message

def send_telegram_message(bot, chat_id, text, reply_to_message_id=None, image=None, **kwargs):
    """
    Send a message to a Telegram chat and store it in the database.

    Args:
        bot (TelegramBot): The bot to send the message from
        chat_id (int): The Telegram chat ID
        text (str): The message text
        reply_to_message_id (int, optional): Message ID to reply to
        **kwargs: Additional parameters for the Telegram API

    Returns:
        dict: The response from Telegram
    """
    if image:
        url = f"https://api.telegram.org/bot{bot.token}/sendPhoto"
        files = {}
        data = {
            'chat_id': chat_id,
            'parse_mode': 'HTML'
        }

        # Si `image` es una URL
        if isinstance(image, str) and image.startswith('http'):
            data['photo'] = image
        else:
            # Si es un archivo Django (InMemoryUploadedFile, File, etc.)
            files['photo'] = image
    else:
        url = f"https://api.telegram.org/bot{bot.token}/sendMessage"

        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

    if reply_to_message_id:
        data['reply_to_message_id'] = reply_to_message_id

    # Add any additional parameters
    data.update(kwargs)
    if image:
        response = requests.post(url, data=data, files=files if image and not isinstance(image, str) else None)
    else:
        response = requests.post(url, json=data)
    response_data = response.json()

    # Store the outgoing message in the database if the API call was successful
    if response_data.get('ok', False):
        try:
            media_type = 'photo' if image else ''
            media_file_id = ''
            media_url = ''

            if image:
                photo_data = response_data['result'].get('photo', [])
                if photo_data:
                    media_file_id = photo_data[-1]['file_id']
                media_url = image if isinstance(image, str) else ''  # Guardamos la URL si aplica

            # Get the chat object
            chat = TelegramChat.objects.get(telegram_id=chat_id)
            
            # Get the reply_to message object if it exists
            reply_to = None
            if reply_to_message_id:
                try:
                    reply_to = TelegramMessage.objects.get(
                        telegram_id=reply_to_message_id,
                        chat=chat
                    )
                except TelegramMessage.DoesNotExist:
                    print(f"Reply message not found: {reply_to_message_id}")
            
            # Create the message object for the outgoing message
            # Note: sender is None because it's from the bot, not a user
            message = TelegramMessage.objects.create(
                telegram_id=response_data['result']['message_id'],
                chat=chat,
                sender=None,  # No sender for bot messages
                bot=bot,
                text=text,
                reply_to=reply_to,
                media_type=media_type,
                media_file_id=media_file_id,
                media_url=media_url
            )
            
            print(f"Stored outgoing message: {message.id}")
        except Exception as e:
            print(f"Error storing outgoing message: {str(e)}")
    
    return response_data
