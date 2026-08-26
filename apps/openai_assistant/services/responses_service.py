import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.utils.timezone import now

from apps.openai_assistant.integrations.responses_client import OpenAIResponsesClient
from apps.openai_assistant.utils.serialization import make_json_safe
from apps.openai_assistant.utils.exceptions import (
    OpenAIError,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    """Declarative tool spec for Responses API."""
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_openai_tool(self) -> Dict[str, Any]:
        # Flattened schema expected by OpenAI Responses API
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters or {"type": "object", "properties": {}},
        }


@dataclass
class ResponsesConfig:
    """Configuration for each logical assistant/integration using Responses API."""
    key: str  # logical name for logging (e.g., "assistant_sales")
    model: str
    instructions: Optional[str] = None
    tools: List[ToolSpec] = field(default_factory=list)
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    # Optional hint to force a specific tool on first turn when needed
    tool_choice: Optional[Dict[str, Any]] = None


class ResponsesService:
    """
    Reusable service to interact with OpenAI Responses API with optional Conversations
    and with support for function calling and a safe dispatcher.

    This service is designed to run side-by-side with the legacy Assistants API
    while we migrate assistants one-by-one.
    """

    def __init__(self, client: Optional[OpenAIResponsesClient] = None):
        self.client = client or OpenAIResponsesClient()

    # -------- Public API
    def run_stateless(
        self,
        config: ResponsesConfig,
        user_input: Any,
        *,
        tool_handlers: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_tool_loops: int = 5,
    ) -> Dict[str, Any]:
        """Execute a single-turn interaction without creating a persistent conversation."""
        return self._run_internal(
            config=config,
            user_input=user_input,
            tool_handlers=tool_handlers or {},
            metadata=metadata,
            conversation_id=None,
            max_tool_loops=max_tool_loops,
        )

    def run_with_conversation(
        self,
        config: ResponsesConfig,
        user_input: Any,
        *,
        conversation_id: Optional[str] = None,
        create_conversation_when_missing: bool = True,
        tool_handlers: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_tool_loops: int = 5,
    ) -> Dict[str, Any]:
        """Execute an interaction attached to a persistent conversation.

        Returns a dict that includes the conversation_id for the caller to persist.
        """
        if conversation_id is None and create_conversation_when_missing:
            conv = self.client.create_conversation()
            conversation_id = getattr(conv, "id", None)
            logger.info(
                "[ResponsesService] (%s) Created conversation id=%s",
                config.key, conversation_id
            )

        result = self._run_internal(
            config=config,
            user_input=user_input,
            tool_handlers=tool_handlers or {},
            metadata=metadata,
            conversation_id=conversation_id,
            max_tool_loops=max_tool_loops,
        )
        result["conversation_id"] = conversation_id
        return result

    # -------- Core flow
    def _run_internal(
        self,
        *,
        config: ResponsesConfig,
        user_input: Any,
        tool_handlers: Dict[str, Callable[[Dict[str, Any]], Any]],
        metadata: Optional[Dict[str, Any]],
        conversation_id: Optional[str],
        max_tool_loops: int,
    ) -> Dict[str, Any]:
        started_at = now()
        tools_payload = [t.to_openai_tool() for t in (config.tools or [])]

        # First call
        response = self.client.create_response(
            model=config.model,
            instructions=config.instructions,
            input=user_input,
            tools=tools_payload if tools_payload else None,
            conversation_id=conversation_id,
            metadata=metadata,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            tool_choice=config.tool_choice,
        )
        response_id = getattr(response, "id", None)
        logger.info(
            "[ResponsesService] (%s) start response_id=%s conv=%s",
            config.key, response_id, conversation_id
        )

        loop_count = 0
        all_tool_calls: List[Dict[str, Any]] = []
        final_text_fragments: List[str] = []

        while True:
            # Debug: log output item types for diagnostics
            try:
                output_items = getattr(response, "output", None) or []
                item_types = [getattr(it, "type", None) for it in output_items]
                logger.debug("[ResponsesService] (%s) output item types: %s", config.key, item_types)
            except Exception:
                pass

            # Extract tool calls from response
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                # no more tool calls; extract final text and finish
                final_text_fragments.extend(self._extract_text_fragments(response))
                break

            loop_count += 1
            if loop_count > max_tool_loops:
                logger.warning(
                    "[ResponsesService] (%s) Max tool loops exceeded (>%d) for response_id=%s",
                    config.key, max_tool_loops, response_id
                )
                final_text_fragments.append(
                    "Lo siento, he alcanzado el límite de herramientas encadenadas."
                )
                break

            tool_outputs_payload, executed = self._execute_tools_safely(
                tool_calls=tool_calls,
                handlers=tool_handlers,
                config=config,
            )
            all_tool_calls.extend(executed)

            # Submit tool outputs and get an updated response
            try:
                response = self.client.submit_tool_outputs(
                    response_id=response_id,
                    tool_outputs=tool_outputs_payload,
                    conversation_id=conversation_id,
                )
            except Exception as e:
                logger.error(
                    "[ResponsesService] (%s) submit_tool_outputs failed for response_id=%s conv=%s error=%s; building fallback and stopping tool loop",
                    config.key, response_id, conversation_id, str(e),
                )
                # Build a minimal fallback message using executed tool results
                try:
                    ops_count = None
                    err_count = 0
                    for meta in all_tool_calls + executed:
                        r = meta.get("result") if isinstance(meta, dict) else None
                        if isinstance(r, dict) and isinstance(r.get("results"), list):
                            items = r["results"]
                            ops_count = sum(1 for it in items if isinstance(it, dict) and it.get("status") == "success")
                            err_count = sum(1 for it in items if isinstance(it, dict) and it.get("status") == "error")
                            break
                    if ops_count is not None:
                        if err_count:
                            final_text_fragments.append(f"Se registraron {ops_count} operaciones con {err_count} errores.")
                        else:
                            final_text_fragments.append(f"Se registraron {ops_count} operaciones exitosamente.")
                    else:
                        final_text_fragments.append("Tu mensaje ha sido procesado y las operaciones fueron registradas.")
                except Exception:
                    logger.exception("[ResponsesService] (%s) Error building fallback after submit_tool_outputs failure", config.key)
                    final_text_fragments.append("Tu mensaje ha sido procesado.")
                break

        finished_at = now()
        final_text = "\n".join([t for t in final_text_fragments if t]) or ""
        result = {
            "ok": True,
            "assistant_key": config.key,
            "response_id": response_id,
            "conversation_id": conversation_id,
            "text": final_text.strip(),
            "tool_calls": all_tool_calls,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
        }

        # Fallback summary if tools executed but no assistant text was returned
        if not result["text"] and all_tool_calls:
            try:
                ops_count = None
                err_count = 0
                for meta in all_tool_calls:
                    r = meta.get("result") if isinstance(meta, dict) else None
                    if isinstance(r, dict) and isinstance(r.get("results"), list):
                        items = r["results"]
                        ops_count = sum(1 for it in items if isinstance(it, dict) and it.get("status") == "success")
                        err_count = sum(1 for it in items if isinstance(it, dict) and it.get("status") == "error")
                        break
                if ops_count is not None:
                    if err_count:
                        fallback_text = f"Se registraron {ops_count} operaciones con {err_count} errores."
                    else:
                        fallback_text = f"Se registraron {ops_count} operaciones exitosamente."
                else:
                    fallback_text = "Tu mensaje ha sido procesado y las operaciones fueron registradas."
                result["text"] = fallback_text
                logger.info("[ResponsesService] (%s) Fallback summary applied for response_id=%s", config.key, response_id)
            except Exception:
                logger.exception("[ResponsesService] (%s) Error building fallback summary", config.key)

        if not result["text"] and not all_tool_calls:
            logger.warning(
                "[ResponsesService] (%s) Empty final text for response_id=%s",
                config.key, response_id
            )
        return result

    # -------- Helpers
    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from a Responses API response object.

        Defensive across SDK variations. We inspect `response.output` items and
        accept types commonly used for function calls.
        """
        calls: List[Dict[str, Any]] = []
        output = getattr(response, "output", None)
        if not output:
            return calls

        for item in output:
            item_type = getattr(item, "type", None)
            if item_type not in ("tool_call", "tool_use", "function_call", "function.invocation"):
                continue

            # Extract fields from multiple possible shapes
            tool_name = (
                getattr(item, "name", None)
                or getattr(item, "tool_name", None)
                or getattr(getattr(item, "function", None), "name", None)
                or getattr(getattr(item, "tool", None), "name", None)
            )
            call_id = (
                getattr(item, "id", None)
                or getattr(item, "tool_call_id", None)
                or getattr(getattr(item, "function", None), "id", None)
            )

            arguments = (
                getattr(item, "arguments", None)
                or getattr(item, "input", None)
                or getattr(getattr(item, "function", None), "arguments", None)
            )

            calls.append({
                "id": call_id,
                "name": tool_name,
                "arguments": arguments,
            })
        return calls

    def _extract_text_fragments(self, response: Any) -> List[str]:
        """Extract assistant text from a Responses API response.
        The message output items typically include type 'message' with content parts.
        Be liberal in what we accept to accommodate SDK shape differences.
        """
        texts: List[str] = []
        output = getattr(response, "output", None)
        if not output:
            return texts
        for item in output:
            if getattr(item, "type", None) == "message":
                content = getattr(item, "content", None) or []
                for part in content:
                    p_type = getattr(part, "type", None)
                    if p_type in ("output_text", "text"):
                        value = (
                            getattr(part, "text", None)
                            or getattr(part, "value", None)
                        )
                        if isinstance(value, str) and value:
                            texts.append(value)
        # Fallbacks for some SDK shapes
        text_attr = getattr(response, "output_text", None)
        if isinstance(text_attr, str) and text_attr:
            texts.append(text_attr)
        return texts

    def _execute_tools_safely(
        self,
        *,
        tool_calls: List[Dict[str, Any]],
        handlers: Dict[str, Callable[[Dict[str, Any]], Any]],
        config: ResponsesConfig,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Execute tool calls with validation and error handling.

        Returns (tool_outputs_payload, executed_calls_metadata)
        where tool_outputs_payload is suitable for submit_tool_outputs, and
        executed_calls_metadata is a list with details for logging/reporting.
        """
        outputs: List[Dict[str, str]] = []
        executed_meta: List[Dict[str, Any]] = []

        for call in tool_calls:
            tool_name = call.get("name") or ""
            call_id = call.get("id") or ""
            raw_args = call.get("arguments")

            logger.info(
                "[ResponsesService] (%s) Tool request: name=%s id=%s", config.key, tool_name, call_id
            )

            handler = handlers.get(tool_name)
            if not handler:
                error_msg = f"Función no permitida o desconocida: {tool_name}"
                logger.warning("[ResponsesService] (%s) %s", config.key, error_msg)
                outputs.append({"tool_call_id": call_id, "output": json.dumps({"error": error_msg})})
                executed_meta.append({
                    "id": call_id,
                    "name": tool_name,
                    "ok": False,
                    "error": error_msg,
                    "arguments": raw_args,
                })
                continue

            # Parse args safely
            try:
                if raw_args is None or raw_args == "":
                    args_obj: Dict[str, Any] = {}
                elif isinstance(raw_args, str):
                    args_obj = json.loads(raw_args)
                elif isinstance(raw_args, dict):
                    args_obj = raw_args
                else:
                    raise ValueError("Argumentos inválidos: tipo no soportado")
            except Exception as e:
                err = f"Error parseando argumentos de {tool_name}: {e}"
                logger.exception("[ResponsesService] (%s) %s", config.key, err)
                outputs.append({"tool_call_id": call_id, "output": json.dumps({"error": err})})
                executed_meta.append({
                    "id": call_id,
                    "name": tool_name,
                    "ok": False,
                    "error": err,
                    "arguments": raw_args,
                })
                continue

            # Execute handler with isolation
            try:
                result = handler(args_obj)
                result_safe = make_json_safe(result)
                outputs.append({"tool_call_id": call_id, "output": json.dumps(result_safe)})
                executed_meta.append({
                    "id": call_id,
                    "name": tool_name,
                    "ok": True,
                    "arguments": args_obj,
                    "result": result_safe,
                })
                logger.info(
                    "[ResponsesService] (%s) Tool executed: %s (id=%s)", config.key, tool_name, call_id
                )
            except ToolExecutionError as te:
                msg = f"Error de herramienta {tool_name}: {te}"
                logger.exception("[ResponsesService] (%s) %s", config.key, msg)
                outputs.append({"tool_call_id": call_id, "output": json.dumps({"error": str(te)})})
                executed_meta.append({
                    "id": call_id,
                    "name": tool_name,
                    "ok": False,
                    "error": str(te),
                    "arguments": args_obj,
                })
            except Exception as e:
                msg = f"Excepción en herramienta {tool_name}: {e}"
                logger.exception("[ResponsesService] (%s) %s", config.key, msg)
                outputs.append({"tool_call_id": call_id, "output": json.dumps({"error": str(e)})})
                executed_meta.append({
                    "id": call_id,
                    "name": tool_name,
                    "ok": False,
                    "error": str(e),
                    "arguments": args_obj,
                })

        return outputs, executed_meta
