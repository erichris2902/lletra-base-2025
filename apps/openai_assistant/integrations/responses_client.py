import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIResponsesClient:
    """
    Thin wrapper around the OpenAI SDK (Responses + Conversations), so we can
    evolve internals without touching higher-level services during the migration.

    Notes
    - We intentionally DO NOT remove or change the legacy Assistants wrapper.
      This new client will coexist until all assistants are migrated.
    - Uses SDK interfaces available in openai~=1.97.0.
    """

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=api_key)

    # ======================
    # Conversations
    # ======================
    def create_conversation(self, title: Optional[str] = None) -> Any:
        """Create a new conversation for stateful sessions.

        Returns the SDK conversation object with at least `.id`.
        """
        payload: Dict[str, Any] = {}
        if title:
            payload["title"] = title
        conv = self.client.conversations.create(**payload)
        logger.debug("[OpenAIResponsesClient] Created conversation %s", getattr(conv, "id", None))
        return conv

    # ======================
    # Responses
    # ======================

    def _normalize_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize tool schema to the flattened Responses API format.

        Accepts either:
        - {"type": "function", "name": "...", "description": "...", "parameters": {...}}
        - {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
        and returns the flattened version.
        """
        normalized: List[Dict[str, Any]] = []
        for t in tools:
            if not isinstance(t, dict):
                normalized.append(t)
                continue
            if t.get("type") == "function" and "name" in t:
                normalized.append(t)
                continue
            fn = t.get("function")
            if t.get("type") == "function" and isinstance(fn, dict):
                normalized.append({
                    "type": "function",
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
                })
            else:
                normalized.append(t)
        return normalized

    def _normalize_tool_choice(self, tool_choice: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize tool_choice to include top-level name when provided in legacy nested shape.
        Accepts either:
        - {"type": "function", "name": "..."}
        - {"type": "function", "function": {"name": "..."}}
        Returns flattened dict.
        """
        if not isinstance(tool_choice, dict):
            return tool_choice
        ttype = tool_choice.get("type")
        if ttype == "function" and tool_choice.get("name"):
            return tool_choice
        fn = tool_choice.get("function")
        if ttype == "function" and isinstance(fn, dict) and fn.get("name"):
            return {"type": "function", "name": fn.get("name")}
        return tool_choice

    def create_response(
        self,
        *,
        model: str,
        instructions: Optional[str] = None,
        input: Optional[Any] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Create a response. If `conversation_id` is provided, it will be attached
        to keep state across turns.
        """
        payload: Dict[str, Any] = {"model": model}
        if instructions is not None:
            payload["instructions"] = instructions
        if input is not None:
            payload["input"] = input
        if tools:
            tools = self._normalize_tools(tools)
            try:
                names = [t.get("name") for t in tools if isinstance(t, dict)]
                logger.debug("[OpenAIResponsesClient] tools names=%s", names)
            except Exception:
                pass
            payload["tools"] = tools
        if conversation_id:
            payload["conversation"] = conversation_id
        if metadata:
            payload["metadata"] = metadata
        if temperature is not None:
            payload["temperature"] = temperature
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        logger.info(
            "[OpenAIResponsesClient] create_response start model=%s conv=%s", model, conversation_id
        )
        resp = self.client.responses.create(**payload)
        logger.info(
            "[OpenAIResponsesClient] create_response done response_id=%s status=%s",
            getattr(resp, "id", None), getattr(resp, "status", None)
        )
        return resp

    def get_response(self, response_id: str) -> Any:
        resp = self.client.responses.retrieve(response_id=response_id)
        return resp

    def submit_tool_outputs(self, response_id: str, tool_outputs: List[Dict[str, str]], conversation_id: Optional[str] = None) -> Any:
        """Submit outputs for previously requested tool calls.

        tool_outputs: list of {"tool_call_id": str, "output": str}
        """
        payload: Dict[str, Any] = {"response_id": response_id, "tool_outputs": tool_outputs}
        # Some SDK versions accept conversation in this call; include when provided.
        if conversation_id:
            payload["conversation"] = conversation_id
        logger.info(
            "[OpenAIResponsesClient] submit_tool_outputs response_id=%s conv=%s calls=%d",
            response_id, conversation_id, len(tool_outputs)
        )
        # Compatibility shim: not all SDK builds expose submit_tool_outputs yet.
        try:
            submit_fn = getattr(self.client.responses, "submit_tool_outputs", None)
            if callable(submit_fn):
                updated = submit_fn(**payload)
            else:
                # Fallback: raise a clear error so upper layer can handle gracefully
                raise AttributeError("Responses.submit_tool_outputs is not available in this SDK version")
        except Exception as e:
            logger.warning("[OpenAIResponsesClient] submit_tool_outputs unavailable or failed: %s", e)
            raise
        logger.info(
            "[OpenAIResponsesClient] submit_tool_outputs done response_id=%s status=%s",
            getattr(updated, "id", None), getattr(updated, "status", None)
        )
        return updated
