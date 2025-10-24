from celery import shared_task
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
import json
import hashlib
import hmac

from .models import (
    TelegramBot
)
from .services.dispatcher import TelegramUpdateDispatcher

User = get_user_model()

@csrf_exempt
@require_POST
def telegram_webhook(request, bot_username):
    try:
        # 1) Bot
        bot = TelegramBot.objects.get(username=bot_username, is_active=True)

        # 2) Parse update
        update_data = json.loads(request.body)
        print(f"[WEBHOOK] Received update for bot {bot_username}: {update_data}")

        # 3) Enqueue asíncrono
        process_update_task.delay(bot.id, update_data)
        return JsonResponse({"status": "accepted", "message": "Processing async"}, status=200)
    except TelegramBot.DoesNotExist:
        print(f"Bot with username {bot_username} not found or inactive")
        return JsonResponse({"status": "accepted", "message": f"Bot with username {bot_username} not found or inactive"}, status=200)
    except Exception as e:
        print(f"Error processing webhook for bot {bot_username}: {str(e)}")
        return JsonResponse({"status": "accepted", "message": f"Error processing webhook for bot {bot_username}: {str(e)}"}, status=200)

@shared_task
def process_update_task(bot_id, update_data):
    from .models import TelegramBot  # Import local para evitar circular import
    bot = TelegramBot.objects.get(id=bot_id)
    print(f"[WebhookTask] Processing update for bot {bot_id}: {update_data}")
    dispatcher = TelegramUpdateDispatcher(bot)
    result = dispatcher.dispatch(update_data)
    print(f"[WebhookTask] Resultado: {result}")
    return result

@csrf_exempt
@require_POST
def telegram_webapp_callback(request, bot_username):
    try:
        bot = TelegramBot.objects.get(username=bot_username, is_active=True)
        data = json.loads(request.body)
        
        if not verify_telegram_webapp_data(data.get('initData', ''), bot.token):
            print(f"Invalid webapp data for bot {bot_username}")
            return HttpResponseForbidden("Invalid data")
        
        return JsonResponse({"success": True})
    except TelegramBot.DoesNotExist:
        print(f"Bot with username {bot_username} not found or inactive")
        return HttpResponseForbidden("Bot not found or inactive")
    except Exception as e:
        print(f"Error processing webapp callback for bot {bot_username}: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def verify_telegram_webapp_data(init_data, bot_token):
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