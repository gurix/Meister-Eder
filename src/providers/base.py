"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str     # "user" or "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str


class LLMProvider(ABC):
    """Uniform interface for any LLM backend."""

    @abstractmethod
    def complete(self, system: str, messages: list) -> LLMResponse:
        """Generate a completion.

        Args:
            system: System prompt text.
            messages: List of LLMMessage objects (user/assistant turns).

        Returns:
            LLMResponse with the model's text output.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier."""
