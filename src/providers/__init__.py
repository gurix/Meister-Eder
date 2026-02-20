"""LLM provider registry."""

from .base import LLMProvider, LLMMessage, LLMResponse
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "AnthropicProvider",
    "OpenAIProvider",
    "create_provider",
]


def create_provider(provider: str, api_key: str, model: str = "") -> LLMProvider:
    """Instantiate the correct LLMProvider by name.

    Args:
        provider: "anthropic" or "openai"
        api_key: API key for the chosen provider.
        model: Optional model name override.

    Returns:
        Configured LLMProvider instance.
    """
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    if provider == "openai":
        return OpenAIProvider(api_key=api_key, model=model)
    raise ValueError(
        f"Unknown AI provider: '{provider}'. Supported values: 'anthropic', 'openai'."
    )
