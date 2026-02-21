"""Tests for the litellm wrapper in src/llm.py."""

import pytest

from src import llm
from src.models.conversation import ChatMessage


class TestLlmComplete:
    def test_returns_model_reply(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.choices[0].message.content = "Hallo! Wie heisst dein Kind?"
        mocker.patch("litellm.completion", return_value=mock_response)

        result = llm.complete("anthropic/claude-opus-4-6", "system prompt", [])

        assert result == "Hallo! Wie heisst dein Kind?"

    def test_passes_model_to_litellm(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.choices[0].message.content = "ok"
        mock_completion = mocker.patch("litellm.completion", return_value=mock_response)

        llm.complete("openai/gpt-4o", "system", [])

        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["model"] == "openai/gpt-4o"

    def test_system_prompt_prepended_as_system_message(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.choices[0].message.content = "ok"
        mock_completion = mocker.patch("litellm.completion", return_value=mock_response)

        llm.complete("anthropic/claude-opus-4-6", "You are helpful.", [])

        messages = mock_completion.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful."}

    def test_chat_messages_appended_after_system(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.choices[0].message.content = "ok"
        mock_completion = mocker.patch("litellm.completion", return_value=mock_response)

        chat = [
            ChatMessage(role="user", content="Hallo"),
            ChatMessage(role="assistant", content="Guten Tag"),
        ]
        llm.complete("anthropic/claude-opus-4-6", "system", chat)

        messages = mock_completion.call_args.kwargs["messages"]
        assert messages[1] == {"role": "user", "content": "Hallo"}
        assert messages[2] == {"role": "assistant", "content": "Guten Tag"}

    def test_max_tokens_passed(self, mocker):
        mock_response = mocker.MagicMock()
        mock_response.choices[0].message.content = "ok"
        mock_completion = mocker.patch("litellm.completion", return_value=mock_response)

        llm.complete("anthropic/claude-opus-4-6", "system", [])

        assert mock_completion.call_args.kwargs["max_tokens"] == 2048

    def test_litellm_exception_propagates(self, mocker):
        mocker.patch("litellm.completion", side_effect=RuntimeError("API error"))

        with pytest.raises(RuntimeError, match="API error"):
            llm.complete("anthropic/claude-opus-4-6", "system", [])
