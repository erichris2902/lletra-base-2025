import json
from datetime import datetime
from apps.openai_assistant.models import Chat, Message, Tool
from apps.openai_assistant.models.chat import ToolExecution
from apps.openai_assistant.services.base_service import BaseOpenAIService
from apps.openai_assistant.utils.serialization import make_json_safe, clean_json_blocks
from apps.openai_assistant.utils.exceptions import (
    OpenAIError, ActiveRunError, ToolExecutionError, TimeoutError
)
from apps.telegram_bots.models import TelegramUser


class ChatService(BaseOpenAIService):

    def send_message(self, chat: Chat, content: str, user: TelegramUser = None):
        print("SEND_MESSAGE_OPENAI")
        print(content)
        # Guardar localmente el mensaje
        user_message = Message.objects.create(chat=chat, role="user", content=content)

        # Crear thread si no existe
        if not chat.openai_thread_id:
            thread = self.client.create_thread()
            chat.openai_thread_id = thread.id
            chat.save(update_fields=["openai_thread_id"])
            self.log(f"Nuevo thread creado: {thread.id}")

        # Agregar mensaje a thread
        try:
            message = self.client.add_message(chat.openai_thread_id, "user", content)
            user_message.openai_message_id = message.id
            user_message.save(update_fields=["openai_message_id"])
        except Exception as e:
            if "run" in str(e).lower() and "active" in str(e).lower():
                self.log(f"[ChatService] Run activo detectado en {chat.openai_thread_id}, cancelando y reintentando...")
                self.client.cancel_active_runs(chat.openai_thread_id, wait_until_cleared=True)
                # Esperamos un momento para que OpenAI confirme la cancelación
                import time
                time.sleep(1.5)
                # Reintentar una sola vez
                message = self.client.add_message(chat.openai_thread_id, "user", content)
                user_message.openai_message_id = message.id
                user_message.save(update_fields=["openai_message_id"])
            else:
                raise OpenAIError(f"Error agregando mensaje: {e}")

        # Ejecutar el asistente
        run = self.client.create_run(chat.openai_thread_id, chat.assistant.openai_id)
        self.log(f"Run iniciado: {run.id}")

        # Esperar resultado
        run = self.client.wait_for_run_completion(chat.openai_thread_id, run.id)

        # Procesar tools si es necesario
        if run.status == "requires_action":
            run, new_messages = self._handle_tool_calls(chat, run, user)
            print(1)
            print(new_messages)
            return new_messages

        # Sincronizar mensajes
        new_messages = self.sync_messages(chat)

        print(2)
        print(new_messages)
        return new_messages

    def _handle_tool_calls(self, chat: Chat, run, user: TelegramUser = None):
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []

        for call in tool_calls:
            tool_name = call.function.name
            args = call.function.arguments
            self.log(f"Ejecutando tool '{tool_name}' con args: {args}")

            sys_msg = Message.objects.create(
                chat=chat, role="system", content=f"Llamando a tool {tool_name} con {args}"
            )
            exec_rec = ToolExecution.objects.create(
                message=sys_msg, tool_name=tool_name,
                input_data=args, status="in_progress", openai_tool_call_id=call.id
            )

            output = self._execute_tool(tool_name, args, user)
            output_safe = make_json_safe(output)
            exec_rec.output_data = output_safe
            exec_rec.status = "completed"
            exec_rec.save()

            tool_outputs.append({
                "tool_call_id": call.id,
                "output": json.dumps(output_safe)
            })

        updated_run = self.client.submit_tool_outputs(
            chat.openai_thread_id, run.id, tool_outputs
        )
        completed = self.client.wait_for_run_completion(
            chat.openai_thread_id, updated_run.id
        )

        # Procesar recursivamente si hay más tools
        if completed.status == "requires_action":
            return self._handle_tool_calls(chat, completed, user)

        new_messages = self.sync_messages(chat)
        return completed, new_messages

    def _execute_tool(self, tool_name: str, args: str, user: TelegramUser = None):
        from apps.telegram_bots.operations import register_operations
        from apps.telegram_bots.event import register_event
        from apps.telegram_bots.quote import register_quote

        if tool_name == "register_operations":
            return register_operations(args)
        elif tool_name == "create_calendar_event":
            return register_event(args, user)
        elif tool_name == "get_current_date":
            today_str = datetime.now().strftime("%Y-%m-%d")
            return {"result": f"La fecha de hoy es {today_str}"}
        elif tool_name == "solicitar_cotizacion":
            return register_quote(args, user)
        else:
            return {"result": f"Ejecutado {tool_name} con {args}"}

    def sync_messages(self, chat: Chat):
        if not chat.openai_thread_id:
            return []

        openai_messages = self.client.list_messages(chat.openai_thread_id)
        existing = set(
            Message.objects.filter(chat=chat)
            .exclude(openai_message_id="")
            .values_list("openai_message_id", flat=True)
        )

        new_messages = []
        for msg in openai_messages.data:
            if msg.id not in existing:
                content = ""
                if msg.content:
                    for part in msg.content:
                        if part.type == "text":
                            content += part.text.value
                content = clean_json_blocks(content)
                message = Message.objects.create(
                    chat=chat, role=msg.role,
                    content=content, openai_message_id=msg.id
                )
                new_messages.append(message)

        self.log(f"Sincronizados {len(new_messages)} nuevos mensajes.")
        return new_messages
