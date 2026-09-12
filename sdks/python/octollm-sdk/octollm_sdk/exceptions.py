"""
OctoLLM SDK Exception Classes

Custom exceptions for clear error handling and debugging.
"""

from typing import Any


class OctoLLMError(Exception):
    """Base exception for all OctoLLM SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id

    def __str__(self) -> str:
        base = f"{self.__class__.__name__}: {self.message}"
        if self.status_code:
            base += f" (HTTP {self.status_code})"
        if self.request_id:
            base += f" [Request ID: {self.request_id}]"
        return base


class AuthenticationError(OctoLLMError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any):
        kwargs.setdefault("status_code", 401)
        super().__init__(message, **kwargs)


class AuthorizationError(OctoLLMError):
    """Raised when authorization fails (403)."""

    def __init__(self, message: str = "Insufficient permissions", **kwargs: Any):
        kwargs.setdefault("status_code", 403)
        super().__init__(message, **kwargs)


class ValidationError(OctoLLMError):
    """Raised when request validation fails (400, 422)."""

    def __init__(self, message: str = "Validation error", **kwargs: Any):
        kwargs.setdefault("status_code", 422)
        super().__init__(message, **kwargs)


class NotFoundError(OctoLLMError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any):
        kwargs.setdefault("status_code", 404)
        super().__init__(message, **kwargs)


class RateLimitError(OctoLLMError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ):
        kwargs.setdefault("status_code", 429)
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

    def __str__(self) -> str:
        base = super().__str__()
        if self.retry_after:
            base += f" (Retry after {self.retry_after}s)"
        return base


class ServiceUnavailableError(OctoLLMError):
    """Raised when a service is unavailable (503)."""

    def __init__(self, message: str = "Service temporarily unavailable", **kwargs: Any):
        kwargs.setdefault("status_code", 503)
        super().__init__(message, **kwargs)


class TimeoutError(OctoLLMError):
    """Raised when a request times out."""

    def __init__(self, message: str = "Request timeout", **kwargs: Any):
        kwargs.setdefault("status_code", 408)
        super().__init__(message, **kwargs)


class APIError(OctoLLMError):
    """Raised for general API errors (500+)."""

    def __init__(self, message: str = "API error occurred", **kwargs: Any):
        super().__init__(message, **kwargs)
