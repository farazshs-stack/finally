"""Unit tests for app.llm.client — mock litellm, never hit the network."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.llm.client import _FALLBACK_MESSAGE, call_llm
from app.llm.schema import ChatResponse


def _make_llm_response(content: str) -> MagicMock:
    """Build a fake litellm completion response object."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


_VALID_JSON = json.dumps(
    {
        "message": "Buying AAPL for you.",
        "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        "watchlist_changes": [],
    }
)

_SIMPLE_JSON = json.dumps({"message": "All good."})


class TestCallLlmSuccess:
    def test_returns_parsed_chat_response(self):
        with patch("app.llm.client.completion", return_value=_make_llm_response(_VALID_JSON)):
            result = call_llm([{"role": "user", "content": "buy 5 AAPL"}])
        assert isinstance(result, ChatResponse)
        assert result.message == "Buying AAPL for you."
        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"

    def test_empty_trades_and_changes(self):
        with patch("app.llm.client.completion", return_value=_make_llm_response(_SIMPLE_JSON)):
            result = call_llm([{"role": "user", "content": "hello"}])
        assert result.message == "All good."
        assert result.trades == []
        assert result.watchlist_changes == []

    def test_strips_code_fence(self):
        fenced = f"```json\n{_SIMPLE_JSON}\n```"
        with patch("app.llm.client.completion", return_value=_make_llm_response(fenced)):
            result = call_llm([{"role": "user", "content": "hi"}])
        assert result.message == "All good."


class TestCallLlmRetry:
    def test_retries_on_first_parse_failure(self):
        """Second call succeeds after first returns bad JSON."""
        bad_response = _make_llm_response("not json at all!!")
        good_response = _make_llm_response(_SIMPLE_JSON)

        with patch("app.llm.client.completion", side_effect=[bad_response, good_response]):
            result = call_llm([{"role": "user", "content": "hello"}])
        assert result.message == "All good."

    def test_fallback_when_both_attempts_fail(self):
        bad_response = _make_llm_response("not json")

        with patch("app.llm.client.completion", side_effect=[bad_response, bad_response]):
            result = call_llm([{"role": "user", "content": "hello"}])
        assert result.message == _FALLBACK_MESSAGE
        assert result.trades == []
        assert result.watchlist_changes == []

    def test_fallback_on_network_error(self):
        with patch("app.llm.client.completion", side_effect=RuntimeError("network down")):
            result = call_llm([{"role": "user", "content": "hello"}])
        assert result.message == _FALLBACK_MESSAGE


class TestCallLlmRetryReprompt:
    def test_reprompt_appended_on_retry(self):
        """Verify the retry call appends a JSON-repair user message."""
        captured: list[list] = []

        def fake_completion(model, messages, **kwargs):
            captured.append(list(messages))
            if len(captured) == 1:
                return _make_llm_response("bad json")
            return _make_llm_response(_SIMPLE_JSON)

        with patch("app.llm.client.completion", side_effect=fake_completion):
            call_llm([{"role": "user", "content": "test"}])

        assert len(captured) == 2
        # Retry messages should be longer (reprompt appended)
        assert len(captured[1]) > len(captured[0])
        # Last message in retry should be the reprompt
        last_msg = captured[1][-1]
        assert last_msg["role"] == "user"
        assert "valid JSON" in last_msg["content"]
