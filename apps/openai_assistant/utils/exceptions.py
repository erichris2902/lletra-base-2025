class OpenAIError(Exception):
    """Error genérico para cualquier operación con OpenAI."""


class ActiveRunError(OpenAIError):
    """Intento de agregar mensaje o ejecutar acción mientras un run está activo."""


class ToolExecutionError(OpenAIError):
    """Error al ejecutar una herramienta registrada en el asistente."""


class TimeoutError(OpenAIError):
    """El run de OpenAI excedió el tiempo máximo de espera."""


class InvalidResponseError(OpenAIError):
    """La respuesta de OpenAI no tiene el formato esperado."""
