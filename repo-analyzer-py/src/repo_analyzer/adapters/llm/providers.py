"""LLM provider abstraction.

Implements the :class:`LLMPort` via a pluggable provider architecture so the
AI comment engine is never coupled to a single vendor. Providers are
registered in a factory and selected by name at runtime.

Supported providers (wired lazily — the SDK is imported only when used):

- ``mock``   — deterministic, offline; used in tests.
- ``openai`` — OpenAI Chat Completions.
- ``anthropic`` — Anthropic Messages API.
- ``gemini`` — Google Gemini.
- ``openrouter`` — OpenRouter (OpenAI-compatible).
- ``ollama`` — local Ollama.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import Any, ClassVar

from repo_analyzer.core.ports.llm_port import LLMPort
from repo_analyzer.infrastructure.errors import AIException
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class BaseLLMProvider(LLMPort):
    """Shared boilerplate for LLM providers."""

    def __init__(self, model: str, **options: Any) -> None:
        self._model = model
        self._options = options

    @property
    def model_name(self) -> str:
        return self._model

    def count_tokens(self, text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return max(1, len(text) // 4)

    def max_context(self) -> int:
        return 128_000

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
        """Generate a completion."""


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, offline provider used in tests.

    Returns a canned engineering-style review so the pipeline can be
    exercised end-to-end without network access.
    """

    def __init__(self, model: str = "mock", **options: Any) -> None:
        super().__init__(model, **options)

    @property
    def provider_name(self) -> str:
        return "mock"

    def max_context(self) -> int:
        return 8_000

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Return a deterministic mock review."""
        _logger.debug("MockLLMProvider.complete called (prompt %d chars)", len(prompt))
        return (
            "## Engineering Review\n\n"
            "The repository exhibits a layered structure with clear separation between "
            "core domain logic and adapters. However, several modules bypass the port "
            "abstractions and depend directly on concrete adapters, which violates the "
            "Dependency Inversion Principle and reduces testability.\n\n"
            "### Strengths\n"
            "- Clear module boundaries.\n"
            "- Test suite present covering core paths.\n\n"
            "### Risks\n"
            "- Circular dependencies detected in the import graph.\n"
            "- High-complexity functions concentrate defect probability.\n\n"
            "### Recommendations\n"
            "1. Introduce interfaces for the most-used collaborators.\n"
            "2. Break circular imports by extracting shared logic.\n"
            "3. Refactor the top-3 complex functions into smaller units.\n"
        )

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Chat Completions provider (SDK imported lazily)."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AIException(
                "openai package is not installed",
                provider="openai",
                model=self._model,
            ) from exc
        api_key = self._options.get("api_key")
        client = OpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens or 4096,
                temperature=temperature if temperature is not None else 0.2,
            )
        except Exception as exc:
            raise AIException(
                f"OpenAI completion failed: {exc}",
                provider="openai",
                model=self._model,
            ) from exc
        return response.choices[0].message.content or ""

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system, **kwargs)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Messages API provider (SDK imported lazily)."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AIException(
                "anthropic package is not installed",
                provider="anthropic",
                model=self._model,
            ) from exc
        api_key = self._options.get("api_key")
        client = anthropic.Anthropic(api_key=api_key)
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens or 4096,
                temperature=temperature if temperature is not None else 0.2,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise AIException(
                f"Anthropic completion failed: {exc}",
                provider="anthropic",
                model=self._model,
            ) from exc
        return response.content[0].text if response.content else ""

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system, **kwargs)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider (SDK imported lazily)."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            import google.generativeai as genai  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AIException(
                "google-generativeai package is not installed",
                provider="gemini",
                model=self._model,
            ) from exc
        api_key = self._options.get("api_key")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self._model)
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens or 4096,
                    "temperature": temperature if temperature is not None else 0.2,
                },
            )
        except Exception as exc:
            raise AIException(
                f"Gemini completion failed: {exc}",
                provider="gemini",
                model=self._model,
            ) from exc
        return response.text or ""

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system, **kwargs)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider (OpenAI-compatible API)."""

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIException(
                "openai package is not installed (used for OpenRouter)",
                provider="openrouter",
                model=self._model,
            ) from exc
        api_key = self._options.get("api_key")
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens or 4096,
                temperature=temperature if temperature is not None else 0.2,
            )
        except Exception as exc:
            raise AIException(
                f"OpenRouter completion failed: {exc}",
                provider="openrouter",
                model=self._model,
            ) from exc
        return response.choices[0].message.content or ""

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system, **kwargs)


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider (HTTP API, no SDK required)."""

    @property
    def provider_name(self) -> str:
        return "ollama"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        import json
        import urllib.request

        host = self._options.get("host", "http://localhost:11434")
        url = f"{host}/api/generate"
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        payload = {
            "model": self._model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else 0.2,
                "num_predict": max_tokens or 4096,
            },
        }
        try:
            req = urllib.request.Request(  # noqa: S310 - trusted local endpoint
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise AIException(
                f"Ollama completion failed: {exc}",
                provider="ollama",
                model=self._model,
            ) from exc
        return str(data.get("response", ""))

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system, **kwargs)


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider (SDK imported lazily).

    Requires ``api_key``, ``azure_endpoint``, and ``api_version`` options.
    """

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise AIException(
                "openai package is not installed (required for Azure OpenAI)",
                provider="azure_openai",
                model=self._model,
            ) from exc
        api_key = self._options.get("api_key")
        azure_endpoint = self._options.get("azure_endpoint")
        api_version = self._options.get("api_version", "2024-02-15-preview")
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
        )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens or 4096,
                temperature=temperature if temperature is not None else 0.3,
            )
        except Exception as exc:
            raise AIException(
                f"Azure OpenAI completion failed: {exc}",
                provider="azure_openai",
                model=self._model,
            ) from exc
        return response.choices[0].message.content or ""

    def complete_stream(
        self, prompt: str, *, system: str | None = None, **kwargs: Any
    ) -> Iterator[str]:
        yield self.complete(prompt, system=system, **kwargs)


class LLMProviderFactory:
    """Factory that builds :class:`LLMPort` instances by provider name."""

    _registry: ClassVar[dict[str, type[BaseLLMProvider]]] = {
        "mock": MockLLMProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
        "azure_openai": AzureOpenAIProvider,
    }

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseLLMProvider]) -> None:
        """Register a new provider class."""
        cls._registry[name] = provider_cls

    @classmethod
    def create(cls, name: str, model: str, **options: Any) -> LLMPort:
        """Create a provider instance by name.

        Args:
            name: Provider name (``mock``, ``openai``, ...).
            model: Model identifier.
            **options: Provider-specific options (e.g. ``api_key``).

        Raises:
            AIException: If the provider is unknown.
        """
        provider_cls = cls._registry.get(name)
        if provider_cls is None:
            raise AIException(
                f"Unknown LLM provider: {name!r}. Registered: {sorted(cls._registry)}",
                provider=name,
                model=model,
            )
        return provider_cls(model=model, **options)

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return the list of registered provider names."""
        return sorted(cls._registry)


__all__ = [
    "BaseLLMProvider",
    "MockLLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OpenRouterProvider",
    "OllamaProvider",
    "AzureOpenAIProvider",
    "LLMProviderFactory",
]
