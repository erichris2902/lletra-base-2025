# apps/openai_assistant/utils/serialization.py
import uuid
import re
from datetime import datetime


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


def clean_json_blocks(text: str) -> str:
    if not text:
        return text

    # Eliminar bloques de código tipo ```json ... ```
    text = re.sub(r"```json[\s\S]*?```", "", text, flags=re.MULTILINE)

    # Eliminar llamadas tipo register_operations({...})
    text = re.sub(r"register_operations\s*\([^)]*\)", "", text)

    # Eliminar posibles triples backticks o etiquetas sobrantes
    text = text.replace("```", "").strip()

    return text
