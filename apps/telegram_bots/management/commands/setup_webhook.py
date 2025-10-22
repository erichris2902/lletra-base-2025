import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.telegram_bots.models import TelegramBot


class Command(BaseCommand):
    help = 'Set up webhook for a Telegram bot'

    def add_arguments(self, parser):
        parser.add_argument('bot_username', type=str, help='Username of the bot to set up webhook for')
        parser.add_argument('--base-url', type=str, help='Base URL for the webhook (e.g., https://example.com)')
        parser.add_argument('--remove', action='store_true', help='Remove webhook instead of setting it')

    def handle(self, *args, **options):
        bot_username = options['bot_username']
        base_url = options.get('base_url')
        remove = options.get('remove', False)

        try:
            bot = TelegramBot.objects.get(username=bot_username, is_active=True)
        except TelegramBot.DoesNotExist:
            raise CommandError(f'Bot with username {bot_username} not found or inactive')

        if remove:
            self.remove_webhook(bot)
        else:
            if not base_url:
                # Try to get base URL from settings
                base_url = getattr(settings, 'WEBHOOK_BASE_URL', None)
                if not base_url:
                    raise CommandError('Base URL is required. Provide it with --base-url or set WEBHOOK_BASE_URL in settings')

            self.set_webhook(bot, base_url)

    def set_webhook(self, bot, base_url):
        """
        Set up webhook for a bot.
        """
        # Construct webhook URL
        webhook_url = f"{base_url.rstrip('/')}/telegram/webhook/{bot.username}/"
        
        # Set up webhook with Telegram
        url = f"https://api.telegram.org/bot{bot.token}/setWebhook"
        data = {
            'url': webhook_url,
            'allowed_updates': ['message', 'edited_message', 'callback_query', 'inline_query', 'message_reaction']
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get('ok'):
            # Update bot in database
            bot.webhook_url = webhook_url
            bot.webhook_set = True
            bot.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully set webhook for {bot.name} to {webhook_url}'))
        else:
            error_message = result.get('description', 'Unknown error')
            self.stdout.write(self.style.ERROR(f'Failed to set webhook: {error_message}'))

    def remove_webhook(self, bot):
        """
        Remove webhook for a bot.
        """
        url = f"https://api.telegram.org/bot{bot.token}/deleteWebhook"
        
        response = requests.post(url)
        result = response.json()
        
        if result.get('ok'):
            # Update bot in database
            bot.webhook_url = ''
            bot.webhook_set = False
            bot.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully removed webhook for {bot.name}'))
        else:
            error_message = result.get('description', 'Unknown error')
            self.stdout.write(self.style.ERROR(f'Failed to remove webhook: {error_message}'))