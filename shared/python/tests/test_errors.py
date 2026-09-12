"""
Tests for the one error envelope.

The defect these exist to prevent is subtle and was present: the app returned
`{"error": {...}}` for `HTTPException` and FastAPI's default `{"detail": [...]}` for
request-validation failures, so the shape a client saw depended on which kind of error
occurred. A client cannot parse that without branching on the status code.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from octollm_common.errors import error_body, install_error_handlers
from pydantic import BaseModel


class Body(BaseModel):
    goal: str
    api_key: str


def build_app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.post("/echo")
    async def echo(body: Body) -> dict[str, str]:
        return {"goal": body.goal}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("connection to postgresql://user:hunter2@db/octollm failed")

    @app.get("/teapot")
    async def teapot() -> None:
        raise HTTPException(status_code=404, detail="no such plan")

    @app.get("/prewrapped")
    async def prewrapped() -> None:
        raise HTTPException(
            status_code=409,
            detail=error_body(code="conflict", message="already running", request_id="fixed-id"),
        )

    return app


# ---------------------------------------------------------------------------
# 422 -- the handler that was missing
# ---------------------------------------------------------------------------


def test_a_validation_failure_uses_the_common_envelope():
    client = TestClient(build_app())

    response = client.post("/echo", json={"goal": "g"})  # api_key missing

    assert response.status_code == 422
    body = response.json()
    assert "detail" not in body, "FastAPI's default shape must not survive"
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["errors"][0]["field"] == "body.api_key"


def test_a_validation_failure_does_not_echo_the_rejected_value():
    """
    Pydantic's errors carry the offending input. Echoing it back would put a rejected
    credential into a response -- and then into the caller's logs -- which is why only
    the location and the reason survive.
    """
    client = TestClient(build_app())

    response = client.post("/echo", json={"goal": "g", "api_key": {"nested": "sk-live-SECRET"}})

    assert response.status_code == 422
    assert "SECRET" not in response.text


def test_every_error_carries_a_request_id_and_a_timestamp():
    client = TestClient(build_app())

    error = client.post("/echo", json={}).json()["error"]

    assert error["request_id"]
    assert error["timestamp"].startswith("20")


def test_the_inbound_request_id_is_preferred_over_a_minted_one():
    client = TestClient(build_app())

    error = client.post("/echo", json={}, headers={"x-request-id": "trace-9"}).json()["error"]

    assert error["request_id"] == "trace-9"


# ---------------------------------------------------------------------------
# HTTPException
# ---------------------------------------------------------------------------


def test_an_http_exception_maps_its_status_to_a_stable_code():
    client = TestClient(build_app())

    body = client.get("/teapot").json()

    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "no such plan"


def test_an_already_wrapped_envelope_is_not_wrapped_twice():
    """A handler that raised the envelope itself must reach the client unchanged."""
    client = TestClient(build_app())

    body = client.get("/prewrapped").json()

    assert body["error"]["code"] == "conflict"
    assert body["error"]["request_id"] == "fixed-id"
    assert "error" not in body["error"], "no envelope inside the envelope"


def test_an_unmapped_status_still_produces_an_envelope():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/gone")
    async def gone() -> None:
        raise HTTPException(status_code=410, detail="gone")

    body = TestClient(app).get("/gone").json()

    assert body["error"]["code"] == "http_error"


# ---------------------------------------------------------------------------
# Unhandled exceptions
# ---------------------------------------------------------------------------


def test_an_unhandled_exception_does_not_leak_its_message():
    """
    An unhandled exception's text routinely contains a connection string or a
    fragment of the input. The request id is what ties this response to the traceback
    in the logs; the text itself must not cross the boundary.
    """
    client = TestClient(build_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert "hunter2" not in response.text
    assert "postgresql" not in response.text
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["details"]["type"] == "RuntimeError"
    assert body["error"]["request_id"]


# ---------------------------------------------------------------------------
# The builder itself
# ---------------------------------------------------------------------------


def test_error_body_defaults_details_to_an_empty_object():
    """`details` is always present so a client never branches on its absence."""
    body = error_body(code="x", message="m", request_id="r")

    assert body["error"]["details"] == {}
