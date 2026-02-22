"""Tests for the litellm wrapper in src/llm.py."""

import pytest

from src import llm
from src.models.conversation import ChatMessage


def _make_async_mock(mocker, content: str):
    """Return an awaitable mock that resolves to a response with the given content."""
    mock_response = mocker.MagicMock()
    mock_response.choices[0].message.content = content

    async def _coro(*args, **kwargs):
        return mock_response

    return mocker.patch("litellm.acompletion", side_effect=_coro), mock_response


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


class TestLlmStreamComplete:
    def _make_chunk(self, content):
        chunk = type("Chunk", (), {})()
        choice = type("Choice", (), {})()
        delta = type("Delta", (), {"content": content})()
        choice.delta = delta
        chunk.choices = [choice]
        return chunk

    def test_yields_chunks(self, mocker):
        chunks = [self._make_chunk("Hal"), self._make_chunk("lo!")]
        mocker.patch("litellm.completion", return_value=iter(chunks))

        result = list(llm.stream_complete("anthropic/claude-opus-4-6", "system", []))

        assert result == ["Hal", "lo!"]

    def test_skips_empty_deltas(self, mocker):
        chunks = [self._make_chunk("Hello"), self._make_chunk(None), self._make_chunk("!")]
        mocker.patch("litellm.completion", return_value=iter(chunks))

        result = list(llm.stream_complete("anthropic/claude-opus-4-6", "system", []))

        assert result == ["Hello", "!"]

    def test_passes_stream_true(self, mocker):
        mock_completion = mocker.patch("litellm.completion", return_value=iter([]))

        list(llm.stream_complete("anthropic/claude-opus-4-6", "system", []))

        assert mock_completion.call_args.kwargs["stream"] is True

    def test_passes_model(self, mocker):
        mock_completion = mocker.patch("litellm.completion", return_value=iter([]))

        list(llm.stream_complete("openai/gpt-4o", "system", []))

        assert mock_completion.call_args.kwargs["model"] == "openai/gpt-4o"

    def test_system_prompt_prepended(self, mocker):
        mock_completion = mocker.patch("litellm.completion", return_value=iter([]))

        list(llm.stream_complete("anthropic/claude-opus-4-6", "You are helpful.", []))

        messages = mock_completion.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful."}

    def test_chat_messages_appended(self, mocker):
        mock_completion = mocker.patch("litellm.completion", return_value=iter([]))

        chat = [ChatMessage(role="user", content="Hallo")]
        list(llm.stream_complete("anthropic/claude-opus-4-6", "system", chat))

        messages = mock_completion.call_args.kwargs["messages"]
        assert messages[1] == {"role": "user", "content": "Hallo"}


class TestLlmAComplete:
    @pytest.mark.asyncio
    async def test_returns_model_reply(self, mocker):
        mock_acompletion, _ = _make_async_mock(mocker, "Hallo! Wie heisst dein Kind?")

        result = await llm.acomplete("anthropic/claude-opus-4-6", "system prompt", [])

        assert result == "Hallo! Wie heisst dein Kind?"

    @pytest.mark.asyncio
    async def test_passes_model_to_litellm(self, mocker):
        mock_acompletion, _ = _make_async_mock(mocker, "ok")

        await llm.acomplete("openai/gpt-4o", "system", [])

        call_kwargs = mock_acompletion.call_args.kwargs
        assert call_kwargs["model"] == "openai/gpt-4o"

    @pytest.mark.asyncio
    async def test_system_prompt_prepended_as_system_message(self, mocker):
        mock_acompletion, _ = _make_async_mock(mocker, "ok")

        await llm.acomplete("anthropic/claude-opus-4-6", "You are helpful.", [])

        messages = mock_acompletion.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful."}

    @pytest.mark.asyncio
    async def test_chat_messages_appended_after_system(self, mocker):
        mock_acompletion, _ = _make_async_mock(mocker, "ok")

        chat = [
            ChatMessage(role="user", content="Hallo"),
            ChatMessage(role="assistant", content="Guten Tag"),
        ]
        await llm.acomplete("anthropic/claude-opus-4-6", "system", chat)

        messages = mock_acompletion.call_args.kwargs["messages"]
        assert messages[1] == {"role": "user", "content": "Hallo"}
        assert messages[2] == {"role": "assistant", "content": "Guten Tag"}

    @pytest.mark.asyncio
    async def test_max_tokens_passed(self, mocker):
        mock_acompletion, _ = _make_async_mock(mocker, "ok")

        await llm.acomplete("anthropic/claude-opus-4-6", "system", [])

        assert mock_acompletion.call_args.kwargs["max_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_exception_propagates(self, mocker):
        async def _raise(*args, **kwargs):
            raise RuntimeError("API error")

        mocker.patch("litellm.acompletion", side_effect=_raise)

        with pytest.raises(RuntimeError, match="API error"):
            await llm.acomplete("anthropic/claude-opus-4-6", "system", [])
