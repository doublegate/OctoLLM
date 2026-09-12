"""
One error envelope, including FastAPI's 422.

The orchestrator returned `{"error": {...}}` for `HTTPException` and FastAPI's default
`{"detail": [...]}` for request-validation failures, so the shape a client saw depended
on which kind of error occurred. That is not a design; it is what happens when you
install a handler for one path and not the other.

Every error from every service now looks the same:

```json
{"error": {"code": "validation_error", "message": "...", "details": {...},
           "request_id": "...", "timestamp": "..."}}
```

`request_id` is always present. An error a user can quote back is the difference
between a support conversation and a guessing game.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

__all__ = ["error_body", "install_error_handlers"]


def error_body(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the one envelope. Never leaks a value, only what failed and where."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    }


def _request_id(request: Request) -> str:
    """Prefer the inbound correlation id; mint one rather than omit the field."""
    return (
        request.headers.get("x-request-id")
        or getattr(request.state, "request_id", None)
        or str(uuid.uuid4())
    )


def install_error_handlers(app: FastAPI) -> None:
    """Install handlers so every error path produces the same envelope."""

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The handler that was missing. Without it FastAPI answers 422 with its own
        # `{"detail": [...]}`, and a client has to branch on status code to know
        # which shape to parse.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_body(
                code="validation_error",
                message="The request body failed validation.",
                request_id=_request_id(request),
                # Pydantic's errors carry the offending input. Echoing it back would
                # put a rejected credential into a log the client can read, so only
                # the location and the reason survive.
                details={
                    "errors": [
                        {"field": ".".join(str(p) for p in err["loc"]), "reason": err["msg"]}
                        for err in exc.errors()
                    ]
                },
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        # A handler may already have raised the envelope; do not wrap it twice.
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                code=_CODES.get(exc.status_code, "http_error"),
                message=str(detail),
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # The message is generic on purpose: an unhandled exception's text routinely
        # contains a connection string or a fragment of the input. The request id is
        # what ties this response to the traceback in the logs.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body(
                code="internal_error",
                message="An internal error occurred.",
                request_id=_request_id(request),
                details={"type": type(exc).__name__},
            ),
        )


_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    501: "not_implemented",
    503: "unavailable",
}
