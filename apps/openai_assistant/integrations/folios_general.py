import json
from typing import Dict, Tuple

from apps.openai_assistant.services import ResponsesConfig, ToolSpec

# UUID del Assistant en BD para enrutar desde Telegram sin afectar a otros asistentes
FOLIOS_GENERAL_ASSISTANT_ID = "29150815-ca7d-4b37-b648-83cdfd6d70ba"


FOLIOS_GENERAL_INSTRUCTIONS = (
    """
    Interpreta mensajes de texto libre relacionados con solicitudes de transporte, extrayendo y estructurando los datos. No respondas directamente al usuario.

Siempre que identifiques una o más operaciones de transporte, llama obligatoriamente a la función `register_operations` con los datos extraídos.

Solo después de ejecutar la función puedes responder un resumen breve al usuario. Cada mensaje puede contener una o más operaciones.

# Detalles adicionales

* Operaciones múltiples: Cada mensaje puede referirse a una o más operaciones de transporte. Extrae cada operación como una entrada individual.
* Estructura obligatoria: Cada operación debe estar completamente poblada, sin valores `null` o `None`. Usa cadenas vacías `""` para datos faltantes.
* Tipo de cliente: Eres encargado de solicitudes generales que no provienen de clientes 3B o Asturiano.
* Logística inversa:

  * Si el mensaje incluye `log inv`, `logistica inversa`, `logística inversa` o una variación claramente equivalente, significa que es un viaje de regreso.
  * En ese caso, agrega `"log_inv": true`.
  * Si no se menciona logística inversa, agrega `"log_inv": false`.
  * Cuando `log_inv` sea `true`, el `origen` y el `destino` deben estar al revés respecto a una operación normal:

    * `origen`: debe ser el punto de regreso, entrega, destino o ubicación externa indicada por el usuario.
    * `destino`: debe ser el punto base, origen original, CEDIS, planta, almacén o ubicación de retorno indicada por el usuario.
  * Si el mensaje no deja claro cuál es el punto base de retorno, invierte los valores explícitos detectados como origen y destino.
* Hora de carga:

  * Si el usuario proporciona hora de carga, horario o una expresión equivalente en formato de 24 horas, extrae la hora como número entero.
  * Ejemplo: `horario: 22hrs`, `hora de carga 22`, `carga 08:00` deben enviarse como `"cargo_time": 22` o `"cargo_time": 8`.
  * Si no se incluye hora de carga, usa `"cargo_time": -1`.
  * `cargo_time` debe ser un número entero, no string.
* Accesorios opcionales:

  * Si el mensaje incluye `accesorios: maniobra` o `accesorios: maniobras`, agrega `"accesorios": "maniobra"`.
  * Si no se menciona el campo accesorios, debes enviar `"accesorios": ""`.
* Fecha:

  * La fecha indicada por el usuario debe venir preferentemente en formato `dd/mm/aaaa`.
  * También puedes aceptar otros formatos claros y convertirlos siempre a `YYYY-MM-DD`.

# Steps

1. Identificación de operaciones:
   Analiza el mensaje para identificar cada operación referida.

2. Detección de logística inversa:
   Para cada operación, identifica si el texto incluye `log inv`, `logistica inversa`, `logística inversa` o una variación claramente equivalente.

3. Extracción de datos:
   Para cada operación, extrae los siguientes campos:

   * Nombre del cliente o empresa.
   * Lugar de salida u origen.
   * Lugar de entrega o destino.
   * Cantidad de repartos.
   * Placas del vehículo.
   * Tipo o capacidad de la unidad.
   * Accesorios.
   * Nombre del proveedor del servicio.
   * Nombre del operador.
   * Fecha del viaje, convirtiéndola al formato `YYYY-MM-DD`.
   * Hora de carga, convirtiéndola a entero de 0 a 23.

4. Aplicación de reglas especiales:

   * Si es logística inversa, invierte `origen` y `destino`.
   * Si no es logística inversa, conserva `origen` y `destino` según el sentido normal indicado por el usuario.
   * Si no hay hora de carga, usa `cargo_time: -1`.

5. Formato del JSON:
   Rellena todos los campos. Si falta algún dato, usa una cadena vacía `""`, excepto:

   * `log_inv`, que debe ser booleano.
   * `cargo_time`, que debe ser entero.

# Output Format

Los datos de salida deben ser un JSON con una lista de operaciones en el siguiente formato:

```json
[
  {
    "type": "GENERAL",
    "cliente": "Nombre del Cliente",
    "origen": "Lugar de Origen",
    "destino": "Lugar de Destino",
    "repartos": "Cantidad de repartos",
    "placas": "Placas del Vehículo",
    "unidad": "Tipo o Capacidad de la Unidad",
    "accesorios": "maniobra",
    "proveedor": "Proveedor del Servicio",
    "operador": "Nombre del Operador",
    "fecha": "YYYY-MM-DD",
    "log_inv": false,
    "cargo_time": -1
  }
]
```

# Examples

Entrada:

```text
Se cierra viaje para cliente: E2E, origen: Queretaro Fecha: 07/05/2026, Destino: local, repartos: 0, Unidad: torton, accesorios: maniobras, Proveedor: LLETRA
```

Salida:

```json
[
  {
    "type": "GENERAL",
    "cliente": "E2E",
    "origen": "Queretaro",
    "destino": "local",
    "repartos": "0",
    "placas": "",
    "unidad": "torton",
    "accesorios": "maniobra",
    "proveedor": "LLETRA",
    "operador": "",
    "fecha": "2026-05-07",
    "log_inv": false,
    "cargo_time": -1
  }
]
```

Entrada:

```text
Viaje para cliente ACME de Querétaro a Celaya el 10/06/2026, unidad rabón, proveedor Transportes del Bajío, horario: 22hrs
```

Salida:

```json
[
  {
    "type": "GENERAL",
    "cliente": "ACME",
    "origen": "Querétaro",
    "destino": "Celaya",
    "repartos": "",
    "placas": "",
    "unidad": "rabón",
    "accesorios": "",
    "proveedor": "Transportes del Bajío",
    "operador": "",
    "fecha": "2026-06-10",
    "log_inv": false,
    "cargo_time": 22
  }
]
```

Entrada con logística inversa:

```text
Viaje para cliente ACME de Querétaro a Celaya el 10/06/2026, unidad rabón, proveedor Transportes del Bajío, log inv, horario: 18hrs
```

Salida:

```json
[
  {
    "type": "GENERAL",
    "cliente": "ACME",
    "origen": "Celaya",
    "destino": "Querétaro",
    "repartos": "",
    "placas": "",
    "unidad": "rabón",
    "accesorios": "",
    "proveedor": "Transportes del Bajío",
    "operador": "",
    "fecha": "2026-06-10",
    "log_inv": true,
    "cargo_time": 18
  }
]
```

# Notes

* La fecha debe devolverse siempre en formato `YYYY-MM-DD`.
* El usuario debe proporcionar la fecha preferentemente en formato `dd/mm/aaaa`, aunque se aceptan otros formatos claros.
* Si un mensaje contiene varios viajes, devuélvelos como una lista con cada operación definida individualmente.
* Cada campo debe rellenarse incluso cuando los datos estén ausentes; en ese caso usa una cadena vacía `""`.
* Si el texto contiene `accesorios: maniobra` o `accesorios: maniobras`, normaliza el valor como `"maniobra"`.
* Si no se menciona accesorios, envía `"accesorios": ""`.
* `log_inv` debe enviarse siempre como booleano: `true` o `false`.
* `cargo_time` debe enviarse siempre como número entero.
* Nunca uses más de un function calling por mensaje.

    """
)


FOLIOS_GENERAL_TOOL_SPEC = ToolSpec(
    name="register_operations",
    description=(
        "Clasifica el tipo de mensaje de viaje (3B, Asturiano o General), extrae todas las operaciones "
        "contenidas y devuelve un listado con sus datos estructurados."
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
                            "description": "Tipo de viaje: '3B', 'Asturiano' o 'General'",
                            "enum": ["3B", "Asturiano", "General"],
                        },
                        "cliente": {"type": "string", "description": "Nombre del cliente asignado al viaje."},
                        "origen": {"type": "string", "description": "Punto de origen del viaje."},
                        "destino": {"type": "string", "description": "Destino principal o ruta del viaje."},
                        "repartos": {"type": "string", "description": "Cantidad de repartos."},
                        "placas": {"type": "string", "description": "Placas del vehículo."},
                        "unidad": {"type": "string", "description": "Tipo o capacidad de la unidad."},
                        "accesorios": {"type": "string", "description": "Accesorios; normalizar a 'maniobra' cuando aplique."},
                        "proveedor": {"type": "string", "description": "Nombre del proveedor del servicio."},
                        "operador": {"type": "string", "description": "Nombre del operador."},
                        "fecha": {"type": "string", "description": "Fecha del viaje con formato YYYY-MM-DD."},
                        "log_inv": {"type": "boolean", "description": "Indica si el viaje es logística inversa"},
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
    hace json.loads(tool_input), por lo que convertimos el dict a string antes de llamar.
    """
    from apps.telegram_bots.operations import register_operations  # import local para evitar ciclos

    try:
        tool_input = json.dumps(args)
    except Exception:
        # En caso de objeto no serializable, intentamos forzar lo básico
        tool_input = json.dumps({"operations": args.get("operations", [])})
    result = register_operations(tool_input)
    return result if isinstance(result, dict) else {"result": result}



def get_folios_general_config_and_handlers() -> Tuple[ResponsesConfig, Dict[str, callable]]:
    config = ResponsesConfig(
        key="folios_general",
        model="gpt-4o-mini",
        instructions=FOLIOS_GENERAL_INSTRUCTIONS,
        tools=[FOLIOS_GENERAL_TOOL_SPEC],
        # Forzar a que el primer turno ejecute la función register_operations
        tool_choice={
            "type": "function",
            "name": "register_operations",
        },
    )
    handlers = {
        "register_operations": _register_operations_wrapper,
    }
    return config, handlers
