"""
Authentication helpers for OctoLLM SDK.

Supports two authentication methods:
1. API Key authentication (X-API-Key header) - for external clients
2. Bearer token authentication (Authorization header) - for inter-service communication
"""

from typing import Dict, Optional


def get_auth_headers(
    api_key: Optional[str] = None, bearer_token: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate authentication headers for API requests.

    Args:
        api_key: API key for external authentication (X-API-Key header)
        bearer_token: JWT token for inter-service authentication (Authorization header)

    Returns:
        Dictionary of HTTP headers for authentication

    Examples:
        >>> get_auth_headers(api_key="sk-12345")
        {'X-API-Key': 'sk-12345'}

        >>> get_auth_headers(bearer_token="eyJ0eXAiOi...")
        {'Authorization': 'Bearer eyJ0eXAiOi...'}

    Note:
        If both api_key and bearer_token are provided, bearer_token takes precedence.
    """
    headers: Dict[str, str] = {}

    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    elif api_key:
        headers["X-API-Key"] = api_key

    return headers


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if API key format is valid

    Note:
        This only validates format, not whether the key is active/valid.
        Actual authentication happens on the server side.
    """
    if not api_key:
        return False

    # API keys should start with 'sk-' and be at least 20 characters
    if not api_key.startswith("sk-"):
        return False

    if len(api_key) < 20:
        return False

    return True


def validate_bearer_token(token: str) -> bool:
    """
    Validate JWT bearer token format.

    Args:
        token: Bearer token to validate

    Returns:
        True if token format is valid

    Note:
        This only validates format (JWT structure), not signature or expiration.
        Actual token validation happens on the server side.
    """
    if not token:
        return False

    # Basic JWT format check: three parts separated by dots
    parts = token.split(".")
    if len(parts) != 3:
        return False

    # Each part should be non-empty base64
    if not all(parts):
        return False

    return True
