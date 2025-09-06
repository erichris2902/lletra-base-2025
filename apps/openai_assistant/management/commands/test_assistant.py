import sys
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.openai_assistant.models import Assistant, Chat, Message
from apps.openai_assistant.services import OpenAIService

User = get_user_model()

class Command(BaseCommand):
    help = 'Test an OpenAI Assistant by starting a conversation'

    def add_arguments(self, parser):
        parser.add_argument('--assistant', required=True, help='ID or name of the assistant to test')
        parser.add_argument('--user', help='Username of the user for the conversation')
        parser.add_argument('--interactive', action='store_true', help='Start an interactive conversation')
        parser.add_argument('--message', help='Single message to send (non-interactive mode)')
        parser.add_argument('--chat', help='ID of an existing chat to continue')

    def handle(self, *args, **options):
        try:
            # Get the OpenAI service
            openai_service = OpenAIService()
            
            # Get user
            user = None
            if options['user']:
                try:
                    user = User.objects.get(username=options['user'])
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"User {options['user']} not found. Using the first available user."))
                    user = User.objects.first()
            else:
                user = User.objects.first()
            
            if not user:
                raise CommandError("No user found. Please create a user first.")
            
            # Get assistant
            assistant = None
            assistant_id = options['assistant']
            
            # Try to get by ID first
            try:
                assistant = Assistant.objects.get(pk=assistant_id)
            except (Assistant.DoesNotExist, ValueError):
                # Try to get by name
                try:
                    assistant = Assistant.objects.get(name=assistant_id, is_active=True)
                except Assistant.DoesNotExist:
                    raise CommandError(f"Assistant with ID or name '{assistant_id}' not found.")
            
            # Get or create chat
            chat = None
            if options['chat']:
                try:
                    chat = Chat.objects.get(pk=options['chat'], user=user, assistant=assistant, is_active=True)
                    self.stdout.write(self.style.SUCCESS(f"Continuing chat: {chat.title}"))
                except (Chat.DoesNotExist, ValueError):
                    self.stdout.write(self.style.WARNING(f"Chat with ID '{options['chat']}' not found. Creating a new chat."))
                    chat = None
            
            if not chat:
                chat = Chat.objects.create(
                    user=user,
                    assistant=assistant,
                    title=f"Test chat with {assistant.name}"
                )
                # Create thread in OpenAI
                chat.openai_thread_id = openai_service.create_thread()
                chat.save()
                self.stdout.write(self.style.SUCCESS(f"Created new chat: {chat.title}"))
            
            # Interactive mode
            if options['interactive']:
                self.stdout.write(self.style.SUCCESS(f"Starting interactive conversation with {assistant.name}"))
                self.stdout.write(self.style.SUCCESS("Type 'exit' or 'quit' to end the conversation"))
                self.stdout.write("")
                
                # Show existing messages
                messages = Message.objects.filter(chat=chat).order_by('created_at')
                if messages.exists():
                    self.stdout.write(self.style.SUCCESS("Previous messages:"))
                    for msg in messages:
                        role_style = self.style.WARNING if msg.role == 'user' else self.style.SUCCESS
                        self.stdout.write(role_style(f"{msg.role.upper()}: {msg.content}"))
                    self.stdout.write("")
                
                # Start conversation loop
                while True:
                    # Get user input
                    try:
                        user_input = input("YOU: ")
                    except EOFError:
                        break
                    
                    # Check for exit command
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    
                    # Send message and get response
                    try:
                        new_messages = openai_service.send_message_and_get_response(chat, user_input)
                        
                        # Print assistant response
                        for msg in new_messages:
                            if msg.role == 'assistant':
                                self.stdout.write(self.style.SUCCESS(f"ASSISTANT: {msg.content}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
                
                self.stdout.write(self.style.SUCCESS("Conversation ended"))
                self.stdout.write(self.style.SUCCESS(f"Chat ID: {chat.id}"))
            
            # Single message mode
            elif options['message']:
                self.stdout.write(self.style.SUCCESS(f"Sending message to {assistant.name}"))
                
                try:
                    # Send message and get response
                    new_messages = openai_service.send_message_and_get_response(chat, options['message'])
                    
                    # Print all messages
                    self.stdout.write(self.style.WARNING(f"USER: {options['message']}"))
                    for msg in new_messages:
                        if msg.role == 'assistant':
                            self.stdout.write(self.style.SUCCESS(f"ASSISTANT: {msg.content}"))
                    
                    self.stdout.write(self.style.SUCCESS(f"Chat ID: {chat.id}"))
                except Exception as e:
                    raise CommandError(f"Error sending message: {str(e)}")
            
            else:
                self.stdout.write(self.style.WARNING("No action specified. Use --interactive or --message."))
                self.stdout.write(self.style.SUCCESS(f"Chat ID: {chat.id}"))
            
        except Exception as e:
            raise CommandError(f"Error testing assistant: {str(e)}")