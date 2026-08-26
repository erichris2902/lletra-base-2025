import json
from typing import Dict, Tuple

from apps.openai_assistant.services import ResponsesConfig, ToolSpec

# UUID del Assistant en BD para enrutar desde Telegram sin afectar a otros asistentes
ASTURIANO_ASSISTANT_ID = "8ac318b1-e362-4f01-825a-e6bf4eebe68e"

ASTURIANO_INSTRUCTIONS = (
    """
    Interpreta mensajes de texto plano relacionados con solicitudes de transporte y estructura los datos en formato JSON para cada viaje mencionado.

    Cada mensaje puede contener una o varias operaciones de transporte. Descompón y estructura cada viaje individual con la siguiente plantilla y agrúpalos en una sola llamada a la función `register_operations`.

    Campos por operación:
    - `type`: Debe ser "ASTURIANO" (nota: para la función, se espera "Asturiano" exactamente).
    - `cliente`: Siempre será "Asturiano".
    - `origen`: Por defecto "CEDIS Asturiano".
    - `destino`: Ruta o punto final del viaje, extraída del mensaje (por ejemplo: "ruta 11F").
    - `placas`: String vacío si no se menciona.
    - `unidad`: Unidad del transporte como "3.5 tn", "Torton", etc., extraída del mensaje.
    - `proveedor`: Nombre del proveedor, extraído del mensaje.
    - `operador`: String vacío si no se menciona.
    - `fecha`: String vacío si no se menciona. Si se menciona, convertir a YYYY-MM-DD interpretando dd/mm/aaaa por defecto.
    - `log_inv`: true si el mensaje incluye "log inv", "logistica inversa", "logística inversa" o similar; en caso contrario false.
    - `cargo_time`: Hora de carga en formato 24h (entero). Ej.: "horario: 22hrs" => 22. Si no se menciona, usar -1.

    Reglas de logística inversa:
    - Si es logística inversa, intercambia origen/destino:
      - origen = ruta o punto extraído del mensaje
      - destino = "CEDIS Asturiano"
    - Si NO es logística inversa:
      - origen = "CEDIS Asturiano"
      - destino = ruta o punto extraído del mensaje

    Restricciones importantes:
    - Nunca uses más de un function calling por mensaje.
    - Siempre agrupa todas las operaciones detectadas en una sola llamada a `register_operations`.
    - Todos los campos deben estar presentes; usa "" para los opcionales cuando falte el dato.
    - `cargo_time` debe ser entero y `log_inv` booleano.

    Ejemplos

    Entrada:
    Confirmar ruta 11F / 3.5 tn vifer

    Salida (estructura a pasar dentro de register_operations):
    [
      {
        "type": "ASTURIANO",
        "cliente": "Asturiano",
        "origen": "CEDIS Asturiano",
        "destino": "ruta 11F",
        "placas": "",
        "unidad": "3.5 tn",
        "proveedor": "vifer",
        "operador": "",
        "fecha": "",
        "log_inv": false,
        "cargo_time": -1
      }
    ]

    Entrada:
    Confirmar ruta 4F / 3.5 tn Nazario horario: 22hrs\nConfirmar ruta 2R / Torton Ruth

    Salida (estructura a pasar dentro de register_operations):
    [
      {
        "type": "ASTURIANO",
        "cliente": "Asturiano",
        "origen": "CEDIS Asturiano",
        "destino": "ruta 4F",
        "placas": "",
        "unidad": "3.5 tn",
        "proveedor": "Nazario",
        "operador": "",
        "fecha": "",
        "log_inv": false,
        "cargo_time": 22
      },
      {
        "type": "ASTURIANO",
        "cliente": "Asturiano",
        "origen": "CEDIS Asturiano",
        "destino": "ruta 2R",
        "placas": "",
        "unidad": "Torton",
        "proveedor": "Ruth",
        "operador": "",
        "fecha": "",
        "log_inv": false,
        "cargo_time": -1
      }
    ]

    Entrada con logística inversa:
    Confirmar ruta 7A / 3.5 tn vifer log inv horario: 18hrs

    Salida (estructura a pasar dentro de register_operations):
    [
      {
        "type": "ASTURIANO",
        "cliente": "Asturiano",
        "origen": "ruta 7A",
        "destino": "CEDIS Asturiano",
        "placas": "",
        "unidad": "3.5 tn",
        "proveedor": "vifer",
        "operador": "",
        "fecha": "",
        "log_inv": true,
        "cargo_time": 18
      }
    ]

    Notas
    - Interpreta por defecto fechas dd/mm/aaaa como DD/MM/AAAA y conviértelas a YYYY-MM-DD.
    - Si hay múltiples viajes, devuélvelos como lista de objetos, siempre en una sola llamada a la función.
    - Recuerda: la función `register_operations` espera el tipo exacto "Asturiano" (con mayúscula inicial). Si internamente generas "ASTURIANO" para el razonamiento, normaliza el valor final a "Asturiano" al construir el JSON.
    """
)

ASTURIANO_TOOL_SPEC = ToolSpec(
    name="register_operations",
    description=(
        "Extrae todas las operaciones contenidas y devuelve un listado con sus datos estructurados."
    ),
    parameters={
        "type": "object",
        "properties": {
            "operations": {
                "type": "array",
                "description": "Listado de operaciones extraídas desde el mensaje original.",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Tipo de viaje: 'Asturiano'",
                            "enum": ["Asturiano"],
                        },
                        "cliente": {"type": "string", "description": "Siempre 'Asturiano'"},
                        "origen": {"type": "string", "description": "Punto de origen (por defecto CEDIS Asturiano)."},
                        "destino": {"type": "string", "description": "Ruta o punto final del viaje."},
                        "placas": {"type": "string", "description": "Placas del vehículo."},
                        "unidad": {"type": "string", "description": "Tipo/capacidad de la unidad."},
                        "proveedor": {"type": "string", "description": "Proveedor del servicio."},
                        "operador": {"type": "string", "description": "Nombre del operador."},
                        "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD."},
                        "log_inv": {"type": "boolean", "description": "Es logística inversa"},
                        "cargo_time": {"type": "integer", "description": "Hora de carga (entero 0–23, -1 si no aplica)"},
                    },
                    "required": [
                        "type",
                        "cliente",
                        "origen",
                        "destino",
                        "placas",
                        "unidad",
                        "proveedor",
                        "operador",
                        "fecha",
                    ],
                },
            }
        },
        "required": ["operations"],
    },
)


def _register_operations_wrapper(args: Dict) -> Dict:
    """Wrapper para compatibilidad con la función existente que espera un string JSON.

    La implementación actual en apps.telegram_bots.operations.register_operations(tool_input)
    espera un string JSON con la forma {"operations": [...]} y devuelve un dict con "results".
    """
    from apps.telegram_bots.operations import register_operations as _impl

    # Forzar normalización de tipo a "Asturiano" si el prompt generó "ASTURIANO"
    data = args or {}
    ops = data.get("operations")
    if isinstance(ops, list):
        for op in ops:
            if isinstance(op, dict):
                ty = op.get("type")
                if ty == "ASTURIANO":
                    op["type"] = "Asturiano"
                # Defaults por especificación de negocio
                op.setdefault("cliente", "Asturiano")
                # origen/destino ya vienen aplicando reglas de log_inv desde el modelo, pero
                # si falta origen, aplicar por defecto
                op.setdefault("origen", "CEDIS Asturiano")
                op.setdefault("placas", "")
                op.setdefault("operador", "")
                # fecha puede ser vacía
                op.setdefault("fecha", "")
                # cargo_time entero obligatorio: si falta, -1
                if op.get("cargo_time") is None:
                    op["cargo_time"] = -1
                # log_inv boolean obligatorio: si falta, false
                if op.get("log_inv") is None:
                    op["log_inv"] = False

    payload_str = json.dumps(data, ensure_ascii=False)
    return _impl(payload_str)


def get_asturiano_config_and_handlers() -> Tuple[ResponsesConfig, Dict[str, callable]]:
    """Devuelve configuración y handlers para el Assistant Lyna-Asturiano."""
    config = ResponsesConfig(
        key="lyna_asturiano",
        model="gpt-4o-mini",
        instructions=ASTURIANO_INSTRUCTIONS,
        tools=[ASTURIANO_TOOL_SPEC],
        # Forzar que el primer turno ejecute register_operations
        tool_choice={
            "type": "function",
            "name": "register_operations",
        },
    )

    handlers = {
        "register_operations": _register_operations_wrapper,
    }
    return config, handlers
