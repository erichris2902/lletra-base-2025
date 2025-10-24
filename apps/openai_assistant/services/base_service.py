from apps.openai_assistant.integrations.openai_client import OpenAIClient


class BaseOpenAIService:

    def __init__(self):
        self.client = OpenAIClient()

    def log(self, message):
        print(f"[{self.__class__.__name__}] {message}")
