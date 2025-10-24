from apps.openai_assistant.models import Assistant
from apps.openai_assistant.services.base_service import BaseOpenAIService
from apps.openai_assistant.utils.exceptions import OpenAIError


class AssistantService(BaseOpenAIService):

    def create_assistant(self, assistant: Assistant):
        self.log(f"Creando assistant '{assistant.name}'...")

        tools = []
        for tool in assistant.tools.all():
            if tool.type == "function":
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

        payload = {
            "name": assistant.name,
            "description": assistant.description,
            "instructions": assistant.instructions,
            "model": assistant.model,
            "tools": tools,
        }

        try:
            openai_assistant = self.client.create_assistant(payload)
            assistant.openai_id = openai_assistant.id
            assistant.save(update_fields=["openai_id"])
            self.log(f"Assistant '{assistant.name}' creado con ID {assistant.openai_id}")
            return openai_assistant
        except Exception as e:
            raise OpenAIError(f"Error creando assistant: {e}")

    def update_assistant(self, assistant: Assistant):
        self.log(f"Actualizando assistant '{assistant.name}'...")
        if not assistant.openai_id:
            return self.create_assistant(assistant)

        tools = []
        for tool in assistant.tools.all():
            if tool.type == "function":
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

        payload = {
            "name": assistant.name,
            "description": assistant.description,
            "instructions": assistant.instructions,
            "model": assistant.model,
            "tools": tools,
        }

        try:
            openai_assistant = self.client.update_assistant(assistant.openai_id, payload)
            self.log(f"Assistant '{assistant.name}' actualizado correctamente.")
            return openai_assistant
        except Exception as e:
            raise OpenAIError(f"Error actualizando assistant: {e}")

    def delete_assistant(self, assistant: Assistant):
        self.log(f"Eliminando assistant '{assistant.name}'...")
        try:
            if not assistant.openai_id:
                return True
            self.client.delete_assistant(assistant.openai_id)
            self.log(f"Assistant '{assistant.name}' eliminado en OpenAI.")
            return True
        except Exception as e:
            raise OpenAIError(f"Error eliminando assistant: {e}")
