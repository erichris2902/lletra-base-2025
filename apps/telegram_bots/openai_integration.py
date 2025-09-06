from django.conf import settings
from django.db import transaction
from apps.openai_assistant.services import OpenAIService
from apps.openai_assistant.models import Assistant
from .models import TelegramChat, TelegramMessage, TelegramUser


class TelegramOpenAIIntegration:
    """
    Service class for integrating Telegram with OpenAI Assistants.
    """
    
    def __init__(self):
        """Initialize the OpenAI service."""
        self.openai_service = OpenAIService()
    
    def process_message(self, message: TelegramMessage, user: TelegramUser=None):
        """
        Process a Telegram message through the active OpenAI Assistant.
        
        Args:
            message (TelegramMessage): The Telegram message to process
            
        Returns:
            str: The response from the Assistant
        """
        chat = message.chat
        
        # Get or set the default assistant
        assistant = chat.get_or_set_default_assistant()
        if not assistant:
            return "No assistants available. Please contact the administrator."
        
        # Get the OpenAI chat
        openai_chat = chat.openai_chat
        if not openai_chat:
            # This shouldn't happen normally as get_or_set_default_assistant should create a chat
            openai_chat = chat.set_active_assistant(assistant)
        
        # Send the message to the OpenAI Assistant and get the response
        new_messages = self.openai_service.send_message_and_get_response(
            openai_chat, message.text, user
        )
        
        # Get the assistant's response (last message with role='assistant')
        assistant_responses = [m for m in new_messages if m.role == 'assistant']
        if assistant_responses:
            return assistant_responses[-1].content
        
        return "I'm processing your message. Please wait a moment."
    
    def switch_assistant(self, chat: TelegramChat, assistant_identifier: str):
        """
        Switch the active assistant for a chat.
        
        Args:
            chat (TelegramChat): The Telegram chat
            assistant_identifier (str): The identifier for the assistant
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Try to find the assistant by the identifier
            # First try by ID
            assistant = None
            try:
                assistant = Assistant.objects.get(pk=assistant_identifier)
            except Exception as e:
                # Then try by name (case insensitive)
                assistant = Assistant.objects.filter(
                    telegram_command__iexact="/"+assistant_identifier,
                    is_active=True
                ).first()
            if not assistant:
                return False, f"Assistant '{assistant_identifier}' not found."
            # Set the active assistant (this will create a new OpenAI chat)
            chat.set_active_assistant(assistant)
            return True, f"Switched to assistant: {assistant.name}"
            
        except Exception as e:
            return False, f"Error switching assistant: {str(e)}"
    
    def get_available_assistants(self):
        """
        Get a list of available assistants.
        
        Returns:
            list: List of active assistants
        """
        return Assistant.objects.filter(is_active=True)