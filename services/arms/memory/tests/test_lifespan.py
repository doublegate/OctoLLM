"""
Tests for the arm's startup and shutdown.

Every other test in this suite injects the stores. This one runs the **real lifespan**,
which is the code that builds them — the engine, the Qdrant client, the provider, and
the ring consumer — and wires them together.

That matters because the lifespan is where a container starts broken. Five arm images in
this repository crash-looped for an entire phase on a `CMD` naming a module that never
existed, and nothing caught it because nothing ever started them. A suite that injects
its dependencies can pass over an arm that cannot boot.

These need Postgres, Qdrant and Redis all reachable, which is the same set the compose
stack provides.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
async def started_app(monkeypatch, engine, qdrant):
    """
    The real app, through its real lifespan, with the ring switched on.

    `engine` and `qdrant` are requested so this skips for the same reason the rest of
    the suite does when the services are absent, rather than failing obscurely inside
    startup.
    """
    from src import config, main

    monkeypatch.setenv("MEMORY_RING_ENABLED", "true")
    monkeypatch.setenv("MEMORY_REDIS_URL", REDIS_URL)
    config.reset_settings()

    transport = ASGITransport(app=main.app)
    async with main.app.router.lifespan_context(main.app):
        async with AsyncClient(transport=transport, base_url="http://memory") as client:
            yield client, main

    config.reset_settings()


async def test_the_arm_boots_and_reports_both_stores_reachable(started_app) -> None:
    """
    The container-actually-works test.

    `/ready` is built from live checks, so a `True` here means the lifespan opened a
    usable connection to each store — not that a constructor returned.
    """
    client, _ = started_app

    response = await client.get("/ready")
    body = response.json()

    assert response.status_code == 200
    assert body["ready"] is True
    assert body["checks"]["postgres"] is True
    assert body["checks"]["qdrant"] is True
    assert isinstance(body["checks"]["artifacts"], int)


async def test_the_ring_consumer_attaches_on_startup(started_app) -> None:
    """
    Memory's whole purpose is ingesting what other arms publish.

    An arm that boots healthy with no ring attached would silently remember nothing,
    which is why `ring_attached` is a readiness check rather than a log line.
    """
    client, main = started_app

    body = (await client.get("/ready")).json()
    assert body["checks"]["ring_attached"] is True
    assert main.RUNTIME.consumer is not None
    assert "ring_stored" in body["checks"]


async def test_a_missing_ring_does_not_stop_the_arm_from_starting(
    monkeypatch, engine, qdrant
) -> None:
    """
    The HTTP surface is independently useful.

    An arm that refused to start because Redis was slow to come up would make the
    compose stack's startup order load-bearing — and startup order is the thing least
    likely to hold on the machine where it matters.
    """
    from src import config, main

    monkeypatch.setenv("MEMORY_RING_ENABLED", "true")
    monkeypatch.setenv("MEMORY_REDIS_URL", "redis://127.0.0.1:1/0")
    config.reset_settings()

    try:
        async with main.app.router.lifespan_context(main.app):
            transport = ASGITransport(app=main.app)
            async with AsyncClient(transport=transport, base_url="http://memory") as client:
                body = (await client.get("/ready")).json()

        assert body["checks"]["ring_attached"] is False
        assert body["checks"]["postgres"] is True, "the stores still came up"
    finally:
        config.reset_settings()


async def test_shutdown_stops_the_consumer(started_app) -> None:
    """
    A background task that outlives its process is a task writing to a closed engine.

    `stop()` waits for the in-flight batch rather than cancelling mid-write.
    """
    client, main = started_app
    consumer = main.RUNTIME.consumer
    assert consumer is not None

    await consumer.stop()

    assert consumer._task is None


async def test_the_consumer_loop_survives_a_failing_iteration(monkeypatch) -> None:
    """
    A Redis blip must not kill the consumer.

    The task dying silently would leave an arm that reports healthy and remembers
    nothing — the exact shape of failure this repository keeps finding.

    Driven on a consumer this test owns, never on the one the lifespan started. Two
    `while True` loops sharing a patched method and a Redis connection is a race, and a
    test that races a background loop fails on a slow machine and passes on review.
    """
    import asyncio

    from src.consumer import ArtifactConsumer

    calls = {"n": 0}

    async def sometimes_fails() -> int:
        # Yields, because the real `drain_once` blocks on a Redis read and therefore
        # gives the event loop a turn. A fake that returns without awaiting turns the
        # consumer loop into a tight spin that starves whatever would stop it -- which
        # is a property of this test, not of the code under it.
        await asyncio.sleep(0.05)
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("redis went away")
        return 0

    # The collaborators are never reached: `drain_once` is replaced outright, and this
    # test is about the loop that calls it.
    consumer = ArtifactConsumer(service=None, consumer=None, publisher=None)  # type: ignore[arg-type]
    monkeypatch.setattr(consumer, "drain_once", sometimes_fails)

    task = asyncio.create_task(consumer._run())
    # The loop sleeps 1s after a failure before retrying, so this window covers the
    # failure, the sleep, and at least one successful iteration after it.
    await asyncio.sleep(1.4)
    consumer._stopping.set()
    await asyncio.wait_for(task, timeout=5)

    assert calls["n"] >= 2, "the loop stopped after the first failure"
