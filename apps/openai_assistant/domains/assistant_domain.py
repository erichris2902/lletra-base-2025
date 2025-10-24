# apps/openai_assistant/domains/assistant_domain.py

class AssistantDomain:

    def __init__(self, name, description, instructions, model, tools=None, openai_id=None):
        self.name = name
        self.description = description
        self.instructions = instructions
        self.model = model
        self.tools = tools or []
        self.openai_id = openai_id

    def validate(self):
        if not self.name:
            raise ValueError("El assistant debe tener un nombre.")
        if not self.instructions:
            raise ValueError("El assistant debe tener instrucciones.")
        if not self.model:
            raise ValueError("Debe especificarse un modelo para el assistant.")
        return True

    def build_openai_payload(self):
        self.validate()
        tools_payload = []

        for tool in self.tools:
            if tool["type"] == "function":
                tools_payload.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })
            else:
                tools_payload.append({"type": tool["type"]})

        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "model": self.model,
            "tools": tools_payload
        }

    def add_tool(self, tool_dict):
        self.tools.append(tool_dict)

    def summary(self):
        return {
            "name": self.name,
            "tools_count": len(self.tools),
            "model": self.model,
            "openai_id": self.openai_id
        }
