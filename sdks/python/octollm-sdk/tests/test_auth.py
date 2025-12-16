"""
Tests for authentication helpers.
"""

import pytest
from octollm_sdk.auth import get_auth_headers, validate_api_key, validate_bearer_token


def test_get_auth_headers_api_key():
    """Test API key authentication headers."""
    headers = get_auth_headers(api_key="sk-12345")
    assert headers == {"X-API-Key": "sk-12345"}


def test_get_auth_headers_bearer_token():
    """Test bearer token authentication headers."""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc"
    headers = get_auth_headers(bearer_token=token)
    assert headers == {"Authorization": f"Bearer {token}"}


def test_get_auth_headers_both():
    """Test that bearer token takes precedence over API key."""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc"
    headers = get_auth_headers(api_key="sk-12345", bearer_token=token)
    assert "Authorization" in headers
    assert "X-API-Key" not in headers


def test_get_auth_headers_none():
    """Test with no authentication."""
    headers = get_auth_headers()
    assert headers == {}


def test_validate_api_key_valid():
    """Test API key validation with valid keys."""
    assert validate_api_key("sk-12345abcdef67890") is True
    assert validate_api_key("sk-" + "a" * 20) is True


def test_validate_api_key_invalid():
    """Test API key validation with invalid keys."""
    assert validate_api_key("") is False
    assert validate_api_key("invalid") is False
    assert validate_api_key("sk-short") is False  # Too short
    assert validate_api_key("12345abcdef67890") is False  # No sk- prefix


def test_validate_bearer_token_valid():
    """Test bearer token validation with valid tokens."""
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc"
    assert validate_bearer_token(token) is True


def test_validate_bearer_token_invalid():
    """Test bearer token validation with invalid tokens."""
    assert validate_bearer_token("") is False
    assert validate_bearer_token("invalid") is False
    assert validate_bearer_token("part1.part2") is False  # Only 2 parts
    assert validate_bearer_token("..") is False  # Empty parts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
