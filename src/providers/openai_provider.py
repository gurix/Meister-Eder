"""OpenAI (GPT) LLM provider."""

from .base import LLMProvider, LLMMessage, LLMResponse


class OpenAIProvider(LLMProvider):
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: str, model: str = "") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai' package to use the OpenAI provider: "
                "pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def complete(self, system: str, messages: list) -> LLMResponse:
        api_messages = [{"role": "system", "content": system}]
        api_messages.extend(
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=api_messages,
            max_tokens=2048,
        )
        return LLMResponse(content=response.choices[0].message.content)

    @property
    def model_name(self) -> str:
        return self._model
