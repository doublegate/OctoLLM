"""
Base HTTP client with retry logic for OctoLLM SDK.
"""

import asyncio
import uuid
from typing import Any

import httpx

from .auth import get_auth_headers
from .config import OctoLLMConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    OctoLLMError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError,
)


class BaseClient:
    """
    Base HTTP client with retry logic and error handling.

    Provides common functionality for all service clients including:
    - Automatic retry with exponential backoff
    - Authentication header management
    - Request ID tracking for distributed tracing
    - Consistent error handling
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        bearer_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True,
    ):
        """
        Initialize base client.

        Args:
            base_url: Service base URL
            api_key: API key for authentication
            bearer_token: JWT bearer token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

    @classmethod
    def from_config(cls, config: OctoLLMConfig, base_url: str) -> BaseClient:
        """
        Create client from configuration object.

        Args:
            config: OctoLLM configuration
            base_url: Service base URL (overrides config base_url)

        Returns:
            BaseClient instance
        """
        return cls(
            base_url=base_url,
            api_key=config.api_key,
            bearer_token=config.bearer_token,
            timeout=config.timeout,
            max_retries=config.max_retries,
            verify_ssl=config.verify_ssl,
        )

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracing."""
        return f"req_{uuid.uuid4().hex[:16]}"

    def _get_headers(self, additional_headers: dict[str, str] | None = None) -> dict[str, str]:
        """
        Build request headers with authentication and tracing.

        Args:
            additional_headers: Additional headers to include

        Returns:
            Complete headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OctoLLM-Python-SDK/0.4.0",
            "X-Request-ID": self._generate_request_id(),
        }

        # Add authentication headers
        auth_headers = get_auth_headers(self.api_key, self.bearer_token)
        headers.update(auth_headers)

        # Add any additional headers
        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _handle_error_response(self, response: httpx.Response, request_id: str) -> None:
        """
        Handle HTTP error responses and raise appropriate exceptions.

        Args:
            response: HTTP response object
            request_id: Request ID for tracking

        Raises:
            Appropriate OctoLLM exception based on status code
        """
        # Only a non-JSON body is exceptional. A body that parses but is not an object
        # (a bare list or string) is checked with isinstance rather than by catching the
        # AttributeError that .get() would raise, so a genuine AttributeError raised from
        # somewhere else is not silently swallowed.
        try:
            error_data = response.json()
        except ValueError:  # json.JSONDecodeError subclasses ValueError
            error_data = None

        message = response.text or f"HTTP {response.status_code}"
        details = None
        if isinstance(error_data, dict):
            message = error_data.get("message") or message
            details = error_data.get("details")

        # Map status codes to exceptions
        if response.status_code == 401:
            raise AuthenticationError(
                message=message,
                details=details,
                request_id=request_id,
            )
        elif response.status_code == 403:
            raise AuthorizationError(
                message=message,
                details=details,
                request_id=request_id,
            )
        elif response.status_code == 404:
            raise NotFoundError(
                message=message,
                details=details,
                request_id=request_id,
            )
        elif response.status_code == 422 or response.status_code == 400:
            raise ValidationError(
                message=message,
                status_code=response.status_code,
                details=details,
                request_id=request_id,
            )
        elif response.status_code == 429:
            retry_after = None
            if "retry_after" in error_data:
                retry_after = error_data["retry_after"]
            elif "Retry-After" in response.headers:
                retry_after = int(response.headers["Retry-After"])

            raise RateLimitError(
                message=message,
                retry_after=retry_after,
                details=details,
                request_id=request_id,
            )
        elif response.status_code == 503:
            raise ServiceUnavailableError(
                message=message,
                details=details,
                request_id=request_id,
            )
        else:
            raise APIError(
                message=message,
                status_code=response.status_code,
                details=details,
                request_id=request_id,
            )

    async def _request(
        self,
        method: str,
        path: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /tasks)
            timeout: Request timeout (overrides default)
            **kwargs: Additional arguments for httpx.request()

        Returns:
            Response JSON as dictionary

        Raises:
            OctoLLM exceptions on errors
        """
        url = f"{self.base_url}{path}"
        headers = self._get_headers(kwargs.pop("headers", None))
        request_timeout = timeout or self.timeout
        request_id = headers["X-Request-ID"]

        # Annotated explicitly: the loop assigns both TimeoutError and APIError to this,
        # and the bare `= None` inferred the first of those and made the other an error.
        last_exception: OctoLLMError | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        timeout=request_timeout,
                        **kwargs,
                    )

                    # Handle error responses
                    if not response.is_success:
                        self._handle_error_response(response, request_id)

                    # Return successful response
                    payload: dict[str, Any] = response.json()
                    return payload

            except httpx.TimeoutException:
                last_exception = TimeoutError(
                    message=f"Request timeout after {request_timeout}s",
                    request_id=request_id,
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                raise last_exception

            except httpx.RequestError as e:
                # Network errors, connection errors, etc.
                last_exception = APIError(
                    message=f"Request failed: {e!s}",
                    request_id=request_id,
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                raise last_exception

            except RateLimitError as e:
                # For rate limits, respect retry_after if provided
                if attempt < self.max_retries - 1:
                    wait_time = e.retry_after or (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except (
                AuthenticationError,
                AuthorizationError,
                NotFoundError,
                ValidationError,
            ):
                # Don't retry these errors
                raise

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise APIError("Request failed after retries", request_id=request_id)

    async def get(self, path: str, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
        """Make GET request."""
        return await self._request("GET", path, timeout=timeout, **kwargs)

    async def post(self, path: str, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
        """Make POST request."""
        return await self._request("POST", path, timeout=timeout, **kwargs)

    async def put(self, path: str, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
        """Make PUT request."""
        return await self._request("PUT", path, timeout=timeout, **kwargs)

    async def delete(
        self, path: str, timeout: float | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Make DELETE request."""
        return await self._request("DELETE", path, timeout=timeout, **kwargs)
