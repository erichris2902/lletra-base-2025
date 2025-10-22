import os

from celery import shared_task
from django.conf import settings
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
from .services import process_update

User = get_user_model()

def _mask_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        # Ocultar password si viene en el netloc
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "********")
        else:
            netloc = parsed.netloc
        return parsed._replace(netloc=netloc).geturl()
    except Exception:
        return "<invalid URL>"

def _probe_redis_connectivity(broker_url: str, log_prefix: str = "") -> dict:
    """Prueba de conexión rápida al broker Redis: redis-py + kombu.
       Retorna un dict con detalles; NO lanza excepción (para no tumbar el webhook)."""
    info = {
        "broker_url_masked": _mask_url(broker_url or ""),
        "env.REDISCLOUD_URL_set": bool(os.getenv("REDISCLOUD_URL")),
        "settings.CELERY_BROKER_URL_set": bool(getattr(settings, "CELERY_BROKER_URL", None)),
        "redis_ping_ok": False,
        "kombu_ok": False,
        "errors": []
    }

    # 1) redis-py ping (rápido)
    try:
        import redis
        r = redis.from_url(broker_url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        info["redis_ping_ok"] = True
        print(f"{log_prefix}Redis PING OK → {info['broker_url_masked']}")
    except Exception as e:
        info["errors"].append(f"redis_ping_error={e}")
        print(f"{log_prefix}Redis PING ERROR: {e}")

    # 2) kombu ensure_connection (opcional, muy explícito)
    try:
        from kombu import Connection
        with Connection(broker_url, connect_timeout=3) as conn:
            conn.ensure_connection(max_retries=1)
        info["kombu_ok"] = True
        print(f"{log_prefix}Kombu connect OK → {info['broker_url_masked']}")
    except Exception as e:
        info["errors"].append(f"kombu_connect_error={e}")
        print(f"{log_prefix}Kombu connect ERROR: {e}")

    return info

@csrf_exempt
@require_POST
def telegram_webhook(request, bot_username):
    try:
        # 1) Bot
        bot = TelegramBot.objects.get(username=bot_username, is_active=True)

        # 2) Parse update
        update_data = json.loads(request.body)
        print(f"[WEBHOOK] Received update for bot {bot_username}: {update_data}")

        # 3) Probe (rápido: timeouts cortos). Útil en local; en prod puedes condicionar por DEBUG.
        broker_url = getattr(settings, "CELERY_BROKER_URL", os.getenv("REDISCLOUD_URL"))
        probe = _probe_redis_connectivity(broker_url, log_prefix="[WEBHOOK] ")
        print(f"[WEBHOOK] Probe summary: {probe}")

        # 4) Si el broker no está alcanzable, evitamos .delay() para no lanzar WinError 10061 en local
        if not (probe["redis_ping_ok"] or probe["kombu_ok"]):
            # Respondemos 200 a Telegram para que no reintente, pero dejamos constancia en logs.
            return JsonResponse({
                "status": "accepted",
                "message": "Broker not reachable; skipped enqueue",
                "probe": probe if settings.DEBUG else {"hint": "enable DEBUG to see probe"}
            }, status=200)

        # 5) Enqueue asíncrono
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
    return process_update(bot, update_data)

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
            print(f"Invalid webapp data for bot {bot_username}")
            return HttpResponseForbidden("Invalid data")
        
        # Process the webapp data
        # Implementation depends on specific webapp requirements
        
        return JsonResponse({"success": True})
    except TelegramBot.DoesNotExist:
        print(f"Bot with username {bot_username} not found or inactive")
        return HttpResponseForbidden("Bot not found or inactive")
    except Exception as e:
        print(f"Error processing webapp callback for bot {bot_username}: {str(e)}")
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