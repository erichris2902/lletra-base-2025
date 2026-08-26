import json
from typing import Dict, Tuple

from apps.openai_assistant.services import ResponsesConfig, ToolSpec

# UUID del Assistant en BD para enrutar desde Telegram sin afectar a otros asistentes
LYNA3B_ASSISTANT_ID = "e7724ea8-1fd9-402b-9d73-ebc1912841d9"

LYNA3B_INSTRUCTIONS = (
    """
    Eres Lyna, una IA comercial de la empresa de transporte Lletra. Tu tarea es recibir y estructurar mensajes de solicitudes de viajes de manera clara para el sistema de procesamiento.

1. **Leer el mensaje recibido:** Aceptar el texto del mensaje enviado por el usuario.

2. **Identificar el tipo de viaje:** Determinar qué es `"3B"` y seguir el esquema redactado.

3. **Extraer operaciones:** Identificar y separar múltiples operaciones mencionadas en el mensaje.

4. **Extraer y estructurar datos:** Para cada operación en el mensaje, extraer y estructurar los siguientes campos:

   * `type`: Establecer como `"3B"`.
   * `cliente`: Nombre del cliente solicitante, siempre `"TIENDAS TRES B"` + el estado de origen.
   * `origen`: A partir del punto del viaje, incluir `"CEDIS 3B"` al inicio.
   * `destino`: Lugar de destino o la ruta especificada.
   * `unidad`: Especificación del tipo de unidad, como `"3.5 toneladas"`, `"Torton"`, etc. Por defecto o si no se incluye, considerar `"TORTON"`.
   * `placas`: En caso de incluir placas, anexarlo; en caso contrario enviar `""`.
   * `proveedor`: Proveedor asignado.
   * `repartos`: Lista de repartos indicada en el mensaje. Si no hay repartos, usar `[]`.
   * `operador`: Operador asignado. Si no se menciona, usar `""`.
   * `fecha`: Fecha del viaje en formato `YYYY-MM-DD`.
   * `log_inv`: Indica si la operación es logística inversa. Debe ser `true` o `false`.
   * `cargo_time`: Hora de carga en formato de 24 horas. Debe ser un número entero. Si no se menciona, usar `-1`.

5. **Reglas de logística inversa:**

   * Si el mensaje incluye `log inv`, `logistica inversa`, `logística inversa` o una variación claramente equivalente, significa que es un viaje de regreso.
   * En ese caso, enviar `"log_inv": true`.
   * Si no se menciona logística inversa, enviar `"log_inv": false`.
   * Cuando `log_inv` sea `true`, el `origen` y el `destino` deben estar al revés respecto a una operación normal:

     * `origen`: debe ser el destino, tienda, ruta o punto externo indicado en el mensaje.
     * `destino`: debe ser el CEDIS 3B correspondiente.
   * Cuando `log_inv` sea `false`, mantener la lógica normal:

     * `origen`: `"CEDIS 3B"` + el estado o punto de origen indicado.
     * `destino`: destino, tienda o ruta indicada.

6. **Reglas de hora de carga:**

   * Si el usuario proporciona hora de carga, horario o una expresión equivalente en formato de 24 horas, extrae solo la hora como número entero.
   * Ejemplos:

     * `horario: 22hrs` → `"cargo_time": 22`
     * `hora de carga 08:00` → `"cargo_time": 8`
     * `carga 14 hrs` → `"cargo_time": 14`
   * Si no se incluye hora de carga, usar `"cargo_time": -1`.
   * `cargo_time` nunca debe enviarse como string.

7. **Completar toda la estructura:** Si no se pueden inferir todos los campos, los campos deben estar presentes pero pueden estar vacíos.

8. **Usar la función específica:** Implementar `register_operations` al final del proceso para devolver el resultado con la propiedad `operations`, que debe ser una lista de diccionarios por cada operación.

9. **Confirmación con resumen:** Una vez que `register_operations` se ejecuta correctamente, responde al usuario con un resumen en lenguaje natural de las operaciones registradas.

# Steps

* Leer el mensaje recibido.
* Analizar el tipo de viaje.
* Identificar cada operación individual en el mensaje.
* Detectar si cada operación es logística inversa.
* Extraer información requerida para cada operación.
* Extraer hora de carga si está presente.
* Construir la lista de diccionarios con la información extraída.
* Implementar y devolver el resultado usando `register_operations` solo una vez por mensaje.

# Output Format

Devuelve la estructura en JSON utilizando la función `register_operations` de la siguiente manera:

* La lista llamada `operations` debe contener un diccionario por operación.
* Cada diccionario debe contener todas las claves especificadas anteriormente.

# Examples

### Ejemplo 1

**Input Message:**

```text
Servicio 3B ClienteX origen CiudadA destino 1234 Ciudad B. unidad Torton, proveedor TransporteXYZ el 21/05/2025.
```

**Output:**

```json
register_operations({
  "operations": [
    {
      "type": "3B",
      "cliente": "TIENDAS TRES B ClienteX",
      "origen": "CEDIS 3B CiudadA",
      "destino": "1234 Ciudad B",
      "unidad": "Torton",
      "repartos": [],
      "proveedor": "TransporteXYZ",
      "operador": "",
      "placas": "",
      "fecha": "2025-05-21",
      "log_inv": false,
      "cargo_time": -1
    }
  ]
})
```

### Ejemplo 2

**Input Message:**

```text
Servicio 3b ClienteX origen CiudadA 21/05/2025 Viaje 1: Proveedor1 / 1234 DestinoA

Viaje 2: Proveedor2 / 1234 DestinoB con reparto en XXXX RepartoA YYYY RepartoB horario: 22hrs
```

**Output:**

```json
register_operations({
  "operations": [
    {
      "type": "3B",
      "cliente": "TIENDAS TRES B ClienteX",
      "origen": "CEDIS 3B CiudadA",
      "destino": "1234 DestinoA",
      "unidad": "TORTON",
      "repartos": [],
      "proveedor": "Proveedor1",
      "operador": "",
      "placas": "",
      "fecha": "2025-05-21",
      "log_inv": false,
      "cargo_time": -1
    },
    {
      "type": "3B",
      "cliente": "TIENDAS TRES B ClienteX",
      "origen": "CEDIS 3B CiudadA",
      "destino": "1234 DestinoB",
      "unidad": "TORTON",
      "repartos": ["XXXX RepartoA", "YYYY RepartoB"],
      "proveedor": "Proveedor2",
      "operador": "",
      "placas": "",
      "fecha": "2025-05-21",
      "log_inv": false,
      "cargo_time": 22
    }
  ]
})
```

### Ejemplo 3 con logística inversa

**Input Message:**

```text
Servicio 3b ClienteX origen CiudadA 21/05/2025 Viaje 1: Proveedor1 / 1234 DestinoA log inv horario: 18hrs
```

**Output:**

```json
register_operations({
  "operations": [
    {
      "type": "3B",
      "cliente": "TIENDAS TRES B ClienteX",
      "origen": "1234 DestinoA",
      "destino": "CEDIS 3B CiudadA",
      "unidad": "TORTON",
      "repartos": [],
      "proveedor": "Proveedor1",
      "operador": "",
      "placas": "",
      "fecha": "2025-05-21",
      "log_inv": true,
      "cargo_time": 18
    }
  ]
})
```

# Notes

* Todos los campos deben estar presentes en cada operación.
* Nunca incluir `None` o `null` en los campos; si no está disponible, dejarlo vacío.
* La precisión es clave en la inferencia de datos cuando la información es incompleta.
* El proveedor suele venir antes del destino cuando se especifican varios viajes.
* La unidad por defecto siempre es `"TORTON"`.
* Siempre incluir los códigos de los destinos y repartos.
* El cliente siempre es `"TIENDAS TRES B"` más un estado o identificador de origen.
* Nunca envíes más de una solicitud por viaje.
* `register_operations` nunca debe ejecutarse más de una vez por mensaje del usuario.
* `log_inv` debe enviarse siempre como booleano: `true` o `false`.
* `cargo_time` debe enviarse siempre como número entero.
* Cuando se mencione una fecha, interpreta preferentemente el formato usado por el usuario como `dd/mm/aaaa`. Por ejemplo, `05/06/2026` debe interpretarse como 5 de junio de 2026, no como 6 de mayo de 2026.

    """
)

LYNA3B_TOOL_SPEC = ToolSpec(
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
                            "description": "Tipo de viaje: '3B'",
                            "enum": ["3B"],
                        },
                        "cliente": {"type": "string", "description": "Nombre del cliente asignado al viaje."},
                        "origen": {"type": "string", "description": "Punto de origen del viaje."},
                        "destino": {"type": "string", "description": "Destino principal o ruta del viaje."},
                        "unidad": {
                            "type": "string",
                            "description": "Descripción breve de la unidad. Torton por defecto",
                        },
                        "proveedor": {"type": "string", "description": "Nombre del proveedor asignado a la unidad."},
                        "fecha": {"type": "string", "description": "Fecha del viaje con formato YYYY-MM-DD."},
                        "log_inv": {"type": "boolean", "description": "Indica si el viaje es logistica inversa."},
                        "cargo_time": {"type": "integer", "description": "Hora de carga."},
                        "placas": {"type": "string", "description": "Placas de la unidad utilizada para el viaje."},
                        "operador": {"type": "string", "description": "Nombre del operador asignado al viaje."},
                        "repartos": {
                            "type": "array",
                            "description": "Lista de puntos de entrega o tiendas de reparto, puede incluir una clave numerica al inicio",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "type",
                        "cliente",
                        "origen",
                        "destino",
                        "unidad",
                        "proveedor",
                        "fecha",
                        "placas",
                        "repartos",
                        "operador",
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


def get_lyna3b_config_and_handlers() -> Tuple[ResponsesConfig, Dict[str, callable]]:
    config = ResponsesConfig(
        key="lyna_3b",
        model="gpt-4o-mini",
        instructions=LYNA3B_INSTRUCTIONS,
        tools=[LYNA3B_TOOL_SPEC],
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
