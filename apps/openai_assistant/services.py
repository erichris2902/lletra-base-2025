import os
import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from django.conf import settings
from openai import OpenAI, AsyncOpenAI
from openai.types.beta.threads import Run

from .models import Assistant, Chat, Message, Tool, ToolExecution
import uuid

from ..telegram_bots.models import TelegramUser
from ..telegram_bots.quote import register_quote

logger = logging.getLogger(__name__)


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    # Agrega aquí otros tipos que te interese serializar (ej: datetime)
    else:
        return obj


class OpenAIService:
    """
    Service class for interacting with the OpenAI API.
    """

    def __init__(self):
        """Initialize the OpenAI client with API key from settings."""
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is not set in settings")

        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)

    def create_assistant(self, assistant: Assistant) -> str:
        """
        Create an assistant in OpenAI and update the local model with the OpenAI ID.

        Args:
            assistant: The Assistant model instance

        Returns:
            str: The OpenAI Assistant ID
        """
        try:
            # Prepare tools configuration
            tools = []
            for tool in assistant.tools.all():
                if tool.type == 'function':
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters
                        }
                    })
                else:
                    tools.append({"type": tool.type})

            # Create assistant in OpenAI
            openai_assistant = self.client.beta.assistants.create(
                name=assistant.name,
                description=assistant.description,
                instructions=assistant.instructions,
                model=assistant.model,
                tools=tools
            )

            # Update local model with OpenAI ID
            assistant.openai_id = openai_assistant.id
            assistant.save(update_fields=['openai_id'])

            return openai_assistant.id

        except Exception as e:
            print(e)
            raise

    def update_assistant(self, assistant: Assistant) -> str:
        """
        Update an assistant in OpenAI.

        Args:
            assistant: The Assistant model instance

        Returns:
            str: The OpenAI Assistant ID
        """
        try:
            if not assistant.openai_id:
                return self.create_assistant(assistant)

            # Prepare tools configuration
            tools = []
            for tool in assistant.tools.all():
                if tool.type == 'function':
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters
                        }
                    })
                else:
                    tools.append({"type": tool.type})

            # Update assistant in OpenAI
            openai_assistant = self.client.beta.assistants.update(
                assistant_id=assistant.openai_id,
                name=assistant.name,
                description=assistant.description,
                instructions=assistant.instructions,
                model=assistant.model,
                tools=tools
            )

            return openai_assistant.id

        except Exception as e:
            print(e)
            raise

    def delete_assistant(self, assistant: Assistant) -> bool:
        """
        Delete an assistant from OpenAI.

        Args:
            assistant: The Assistant model instance

        Returns:
            bool: True if successful
        """
        try:
            if not assistant.openai_id:
                return True

            self.client.beta.assistants.delete(assistant_id=assistant.openai_id)
            return True

        except Exception as e:
            print(e)
            raise

    def create_thread(self) -> str:
        """
        Create a new thread in OpenAI.

        Returns:
            str: The OpenAI Thread ID
        """
        try:
            thread = self.client.beta.threads.create()
            return thread.id

        except Exception as e:
            print(e)
            raise

    def add_message_to_thread(self, chat: Chat, content: str, role: str = 'user') -> Tuple[str, str]:
        """
        Add a message to a thread in OpenAI.

        Args:
            chat: The Chat model instance
            content: The message content
            role: The message role (default: 'user')

        Returns:
            Tuple[str, str]: The OpenAI Thread ID and Message ID
        """
        try:
            # Create thread if it doesn't exist
            if not chat.openai_thread_id:
                chat.openai_thread_id = self.create_thread()
                chat.save(update_fields=['openai_thread_id'])

            # Add message to thread
            message = self.client.beta.threads.messages.create(
                thread_id=chat.openai_thread_id,
                role=role,
                content=content
            )

            return chat.openai_thread_id, message.id

        except Exception as e:
            print(e)
            raise

    def run_assistant(self, chat: Chat) -> Run:
        """
        Run the assistant on the thread.

        Args:
            chat: The Chat model instance

        Returns:
            Run: The OpenAI Run object
        """
        try:
            if not chat.openai_thread_id:
                raise ValueError("Thread ID is not set")

            if not chat.assistant.openai_id:
                raise ValueError("Assistant ID is not set")

            run = self.client.beta.threads.runs.create(
                thread_id=chat.openai_thread_id,
                assistant_id=chat.assistant.openai_id
            )

            return run

        except Exception as e:
            print(e)
            raise

    def wait_for_run_completion(self, thread_id: str, run_id: str, timeout: int = 300) -> Run:
        """
        Wait for a run to complete.

        Args:
            thread_id: The OpenAI Thread ID
            run_id: The OpenAI Run ID
            timeout: Maximum time to wait in seconds

        Returns:
            Run: The completed Run object
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            print(run.status)

            if run.status in ['completed', 'failed', 'cancelled', 'expired']:
                return run

            # If the run requires action (tool calls)
            if run.status == 'requires_action':
                return run

            # Wait before checking again
            time.sleep(1)

        # If we reach here, the run timed out
        self.client.beta.threads.runs.cancel(
            thread_id=thread_id,
            run_id=run_id
        )
        raise TimeoutError(f"Run {run_id} timed out after {timeout} seconds")

    def submit_tool_outputs(self, thread_id: str, run_id: str, tool_outputs: List[Dict[str, Any]]) -> Run:
        """
        Submit tool outputs for a run.

        Args:
            thread_id: The OpenAI Thread ID
            run_id: The OpenAI Run ID
            tool_outputs: List of tool outputs

        Returns:
            Run: The updated Run object
        """
        try:
            run = self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=tool_outputs
            )

            return run

        except Exception as e:
            print(e)
            raise

    def get_messages(self, thread_id: str, limit: int = 20) -> List[Dict]:
        """
        Get messages from a thread.

        Args:
            thread_id: The OpenAI Thread ID
            limit: Maximum number of messages to retrieve

        Returns:
            List[Dict]: List of messages
        """
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit
            )

            return messages.data

        except Exception as e:
            print(e)
            raise

    def process_run_with_tools(self, chat: Chat, run: Run, user: TelegramUser=None) -> Tuple[Run, List[Message]]:
        """
        Process a run that requires tool actions.

        Args:
            chat: The Chat model instance
            run: The OpenAI Run object

        Returns:
            Tuple[Run, List[Message]]: The completed Run object and new messages
        """
        if run.status != 'requires_action' or not run.required_action:
            return run, []

        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []

        for tool_call in tool_calls:
            # Create a ToolExecution record
            tool_name = tool_call.function.name
            input_data = tool_call.function.arguments

            # Find the corresponding tool in the database
            tool = None
            try:
                tool = Tool.objects.get(assistant=chat.assistant, name=tool_name)
            except Tool.DoesNotExist:
                print(f"Tool {tool_name} not found in database")

            # Create a system message for the tool call
            system_message = Message.objects.create(
                chat=chat,
                role='system',
                content=f"Tool call: {tool_name} with arguments: {input_data}"
            )

            # Create a ToolExecution record
            tool_execution = ToolExecution.objects.create(
                message=system_message,
                tool=tool,
                tool_name=tool_name,
                input_data=input_data,
                status='in_progress',
                openai_tool_call_id=tool_call.id
            )
            #print(chat)
            #print(run)
            #print(user)
            #print(tool_name)
            # Execute the appropriate tool based on the tool name
            output = None
            if tool_name == 'register_operations':
                # Import and use the register_operations function
                from apps.telegram_bots.operations import register_operations
                output = register_operations(input_data)
            elif tool_name == 'create_calendar_event':
                # Import and use the register_operations function
                from apps.telegram_bots.event import register_event
                output = register_event(input_data, user)
            elif tool_name == 'get_current_date':
                # Import and use the register_operations function
                today_str = datetime.now().strftime("%Y-%m-%d")
                output = "La fecha de hoy es: " + today_str
            elif tool_name == 'solicitar_cotizacion':
                # Import and use the register_operations function
                output = register_quote(input_data, user)
            else:
                # Default placeholder for other tools
                output = {"result": f"Executed {tool_name} with {input_data}"}

            output_safe = make_json_safe(output)
            tool_execution.output_data = output_safe
            tool_execution.status = 'completed'
            tool_execution.save()

            tool_outputs.append({
                "tool_call_id": str(tool_call.id),
                "output": json.dumps(output_safe)
            })
            print(output_safe)
        print("-----------")
        print(tool_outputs)
        # Submit tool outputs back to OpenAI
        updated_run = self.submit_tool_outputs(
            thread_id=chat.openai_thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

        # Wait for the run to complete
        completed_run = self.wait_for_run_completion(
            thread_id=chat.openai_thread_id,
            run_id=updated_run.id
        )

        # If the run still requires action, process it recursively
        if completed_run.status == 'requires_action':
            return self.process_run_with_tools(chat, completed_run, user)

        # Get new messages
        new_messages = self.sync_messages(chat)

        return completed_run, new_messages

    def sync_messages(self, chat: Chat) -> List[Message]:
        """
        Sync messages from OpenAI to the local database.

        Args:
            chat: The Chat model instance

        Returns:
            List[Message]: List of new messages created
        """
        if not chat.openai_thread_id:
            return []

        # Get messages from OpenAI
        openai_messages = self.get_messages(chat.openai_thread_id)

        # Get existing message IDs
        existing_message_ids = set(
            Message.objects.filter(chat=chat)
            .exclude(openai_message_id='')
            .values_list('openai_message_id', flat=True)
        )

        new_messages = []

        # Create new messages
        for openai_message in openai_messages:
            if openai_message.id not in existing_message_ids:
                # Extract content
                content = ""
                if openai_message.content:
                    for content_part in openai_message.content:
                        if content_part.type == 'text':
                            content += content_part.text.value

                # Create message
                message = Message.objects.create(
                    chat=chat,
                    role=openai_message.role,
                    content=content,
                    openai_message_id=openai_message.id
                )

                new_messages.append(message)

        return new_messages

    def send_message_and_get_response(self, chat: Chat, content: str, user: TelegramUser=None) -> List[Message]:
        # Add user message to local database
        user_message = Message.objects.create(
            chat=chat,
            role='user',
            content=content
        )

        # Add message to OpenAI thread
        thread_id, message_id = self.add_message_to_thread(chat, content)

        # Update the message with OpenAI ID
        user_message.openai_message_id = message_id
        user_message.save(update_fields=['openai_message_id'])

        # Run the assistant
        run = self.run_assistant(chat)

        # Wait for the run to complete
        completed_run = self.wait_for_run_completion(
            thread_id=chat.openai_thread_id,
            run_id=run.id
        )

        # If the run requires action (tool calls), process it
        if completed_run.status == 'requires_action':
            completed_run, new_messages = self.process_run_with_tools(chat, completed_run, user)
            return new_messages

        # Sync messages from OpenAI
        new_messages = self.sync_messages(chat)

        return new_messages
