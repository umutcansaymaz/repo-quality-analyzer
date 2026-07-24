"""AI / LLM-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import RecoverableError, TransientError


class AIException(RecoverableError):
    """An AI / LLM operation failed.

    Recoverable: the report can still be produced without the AI review.
    """

    code = "GRA_AI_001"
    default_message = "AI operation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if provider:
            ctx["provider"] = provider
        if model:
            ctx["model"] = model
        super().__init__(message, context=ctx, **kwargs)
        self.provider = provider
        self.model = model


class AIRateLimitException(AIException, TransientError):
    """The LLM provider returned a rate-limit response."""

    code = "GRA_AI_002"
    default_message = "AI provider rate limit exceeded."
    retryable = True


class AIContextLengthException(AIException):
    """The prompt exceeded the model's context window."""

    code = "GRA_AI_003"
    default_message = "Prompt exceeds model context length."


class AIResponseParsingException(AIException):
    """The LLM response could not be parsed into the expected schema."""

    code = "GRA_AI_004"
    default_message = "Failed to parse AI response."


__all__ = [
    "AIContextLengthException",
    "AIException",
    "AIRateLimitException",
    "AIResponseParsingException",
]
