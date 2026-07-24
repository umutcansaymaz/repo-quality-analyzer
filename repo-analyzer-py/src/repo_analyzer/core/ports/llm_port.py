"""LLM port (abstract interface for AI providers)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class LLMPort(ABC):
    """Abstract interface for an LLM provider.

    Implementations include the z-ai-web-dev-sdk adapter, OpenAI, Anthropic
    and a local Ollama adapter. The orchestrator depends only on this port.
    """

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a completion for ``prompt``.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            max_tokens: Optional max output tokens.
            temperature: Optional sampling temperature.
            **kwargs: Provider-specific options.

        Returns:
            The generated text.
        """

    @abstractmethod
    def complete_stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream a completion token-by-token."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate the token count of ``text`` for this provider."""

    @abstractmethod
    def max_context(self) -> int:
        """Return the maximum context window size in tokens."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """The provider identifier (e.g. ``"zai"``)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier."""


__all__ = ["LLMPort"]
