"""Anthropic (Claude) LLM provider."""

from .base import LLMProvider, LLMMessage, LLMResponse


class AnthropicProvider(LLMProvider):
    DEFAULT_MODEL = "claude-opus-4-6"

    def __init__(self, api_key: str, model: str = "") -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "Install the 'anthropic' package to use the Anthropic provider: "
                "pip install anthropic"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def complete(self, system: str, messages: list) -> LLMResponse:
        api_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system,
            messages=api_messages,
        )
        return LLMResponse(content=response.content[0].text)

    @property
    def model_name(self) -> str:
        return self._model
