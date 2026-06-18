"""LLM client using LiteLLM -> OpenRouter -> Cerebras (SS9, cerebras skill).

Public API
----------
    call_llm(messages) -> ChatResponse

Strategy
--------
1. Call the model with structured output (response_format=ChatResponse).
2. Parse the returned JSON string with ChatResponse.model_validate_json().
3. On any parse failure, retry ONCE with a reprompt asking for valid JSON.
4. If the retry also fails, return a safe fallback ChatResponse with an
   error message and empty trades/watchlist_changes (SS13.A.6).
"""

from __future__ import annotations

import json
import logging

from litellm import completion
from pydantic import ValidationError

from .schema import ChatResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cerebras / OpenRouter constants (from SKILL.md)
# ---------------------------------------------------------------------------
MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

# Fallback message shown to the user when LLM response cannot be parsed
_FALLBACK_MESSAGE = (
    "I'm sorry, I encountered an issue processing your request. "
    "Please try again in a moment."
)

_RETRY_REPROMPT = (
    "Your previous response could not be parsed as valid JSON. "
    "Please respond ONLY with a single valid JSON object matching this exact schema "
    "(no markdown, no code fences, no extra text): "
    '{"message": "<string>", "trades": [], "watchlist_changes": []}'
)


def _parse_response(raw: str) -> ChatResponse:
    """Parse raw LLM string into ChatResponse; strip code fences defensively."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence line (e.g. ```json)
        cleaned = cleaned.split("\n", 1)[-1]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()
    return ChatResponse.model_validate_json(cleaned)


def call_llm(messages: list[dict[str, str]]) -> ChatResponse:
    """Call the LLM and return a parsed ChatResponse.

    Uses Cerebras via OpenRouter with structured output.  On parse failure,
    retries once with a JSON-repair reprompt.  Returns a safe fallback on
    second failure (SS13.A.6).

    Args:
        messages: Full message list built by prompt.build_messages().

    Returns:
        Parsed ChatResponse (possibly the fallback on double failure).
    """
    # --- Attempt 1 ---
    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format=ChatResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        raw: str = response.choices[0].message.content or ""
        return _parse_response(raw)
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM response parse failed (attempt 1): %s", exc)
    except Exception as exc:
        logger.error("LLM call failed (attempt 1): %s", exc)
        return ChatResponse(message=_FALLBACK_MESSAGE)

    # --- Attempt 2: JSON-repair reprompt ---
    retry_messages = list(messages) + [{"role": "user", "content": _RETRY_REPROMPT}]
    try:
        response = completion(
            model=MODEL,
            messages=retry_messages,
            response_format=ChatResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        raw = response.choices[0].message.content or ""
        return _parse_response(raw)
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        logger.error("LLM response parse failed (attempt 2 / retry): %s", exc)
    except Exception as exc:
        logger.error("LLM call failed (attempt 2 / retry): %s", exc)

    return ChatResponse(message=_FALLBACK_MESSAGE)
