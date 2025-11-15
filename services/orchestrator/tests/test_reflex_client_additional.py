"""
Additional tests for reflex_client to increase coverage.

Tests edge cases and less common code paths.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.reflex_client import (
    CircuitBreaker,
    ProcessStatus,
    ReflexClient,
)


class TestCircuitBreakerEdgeCases:
    """Additional circuit breaker tests for edge cases."""

    def test_should_not_attempt_reset_too_early(self):
        """Test circuit doesn't reset before timeout."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=60)
        cb._on_failure()
        cb._on_failure()
        assert cb.state == "open"

        # Not enough time has passed
        assert cb._should_attempt_reset() is False

    def test_success_in_closed_state_resets_failure_count(self):
        """Test successful call in closed state resets failure count."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.failure_count = 2
        cb._on_success()
        assert cb.failure_count == 0


class TestReflexClientEdgeCases:
    """Additional ReflexClient tests for edge cases."""

    @pytest.mark.asyncio
    async def test_process_with_empty_context(self):
        """Test processing with empty context dict."""
        client = ReflexClient(base_url="http://localhost:8080")

        mock_response = {
            "request_id": "req-200",
            "status": "Success",
            "pii_detected": False,
            "pii_matches": [],
            "injection_detected": False,
            "injection_matches": [],
            "cache_hit": False,
            "processing_time_ms": 2.5,
        }

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            response = await client.process("Test", context={})
            assert response.status == ProcessStatus.SUCCESS

        await client.close()

    @pytest.mark.asyncio
    async def test_metrics_with_zero_requests(self):
        """Test metrics calculation with zero requests."""
        client = ReflexClient(base_url="http://localhost:8080")

        metrics = client.get_metrics()
        assert metrics["average_latency_ms"] == 0.0
        assert metrics["success_rate"] == 0.0
        assert metrics["total_requests"] == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_cache_hit_metric(self):
        """Test cache hit metric is incremented."""
        client = ReflexClient(base_url="http://localhost:8080")

        mock_response = {
            "request_id": "req-201",
            "status": "Success",
            "pii_detected": False,
            "pii_matches": [],
            "injection_detected": False,
            "injection_matches": [],
            "cache_hit": True,
            "processing_time_ms": 0.3,
        }

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await client.process("Test")

            metrics = client.get_metrics()
            assert metrics["cache_hits"] == 1

        await client.close()

    @pytest.mark.asyncio
    async def test_update_metrics_blocked_request(self):
        """Test metrics are updated for blocked requests."""
        client = ReflexClient(base_url="http://localhost:8080")

        mock_response = {
            "request_id": "req-202",
            "status": "Blocked",
            "pii_detected": False,
            "pii_matches": [],
            "injection_detected": True,
            "injection_matches": [],
            "cache_hit": False,
            "processing_time_ms": 4.0,
        }

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await client.process("Malicious text")

            metrics = client.get_metrics()
            assert metrics["blocked_requests"] == 1
            assert metrics["injection_detections"] == 1

        await client.close()

    @pytest.mark.asyncio
    async def test_failed_request_metric(self):
        """Test failed request metric is incremented."""
        client = ReflexClient(base_url="http://localhost:8080")

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Network error")

            try:
                await client.process("Test")
            except Exception:
                pass

            metrics = client.get_metrics()
            assert metrics["failed_requests"] > 0

        await client.close()
