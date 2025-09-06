from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
import json
import logging
import hashlib
import hmac

from .models import (
    TelegramBot
)
from .services import process_update

logger = logging.getLogger(__name__)
User = get_user_model()

@csrf_exempt
@require_POST
def telegram_webhook(request, bot_username):
    """
    Main webhook endpoint for Telegram updates.
    Each bot has its own webhook URL with its username in the path.
    """
    try:
        # Get the bot by username
        bot = TelegramBot.objects.get(username=bot_username, is_active=True)
        
        # Parse the update data
        update_data = json.loads(request.body)
        logger.debug(f"Received update for bot {bot_username}: {update_data}")
        
        # Process the update
        response_data = process_update(bot, update_data)
        print(response_data)
        return JsonResponse(response_data)
    except TelegramBot.DoesNotExist:
        logger.error(f"Bot with username {bot_username} not found or inactive")
        return HttpResponseForbidden("Bot not found or inactive")
    except Exception as e:
        logger.exception(f"Error processing webhook for bot {bot_username}: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_POST
def telegram_webapp_callback(request, bot_username):
    """
    Endpoint for handling callbacks from Telegram WebApps.
    """
    try:
        # Get the bot by username
        bot = TelegramBot.objects.get(username=bot_username, is_active=True)
        
        # Parse the data
        data = json.loads(request.body)
        
        # Verify the data with Telegram's validation
        if not verify_telegram_webapp_data(data.get('initData', ''), bot.token):
            logger.warning(f"Invalid webapp data for bot {bot_username}")
            return HttpResponseForbidden("Invalid data")
        
        # Process the webapp data
        # Implementation depends on specific webapp requirements
        
        return JsonResponse({"success": True})
    except TelegramBot.DoesNotExist:
        logger.error(f"Bot with username {bot_username} not found or inactive")
        return HttpResponseForbidden("Bot not found or inactive")
    except Exception as e:
        logger.exception(f"Error processing webapp callback for bot {bot_username}: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def verify_telegram_webapp_data(init_data, bot_token):
    """
    Verify the data received from Telegram WebApp.
    """
    if not init_data:
        return False
    
    # Parse the init_data
    data_dict = {}
    for item in init_data.split('&'):
        if '=' in item:
            key, value = item.split('=', 1)
            data_dict[key] = value
    
    if 'hash' not in data_dict:
        return False
    
    # Extract the hash
    received_hash = data_dict.pop('hash')
    
    # Sort the data
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(data_dict.items())])
    
    # Create the secret key
    secret_key = hmac.new(
        "WebAppData".encode(), 
        bot_token.encode(), 
        hashlib.sha256
    ).digest()
    
    # Calculate the hash
    calculated_hash = hmac.new(
        secret_key, 
        data_check_string.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    # Compare the hashes
    return calculated_hash == received_hash