"""
Tests for BaseClient error-response handling.

_handle_error_response has to cope with three shapes of error body: a JSON object
(the documented contract), a body that is not JSON at all, and a body that is valid
JSON but not an object. Only the first was covered before.
"""

import httpx
import pytest

from octollm_sdk.client import BaseClient
from octollm_sdk.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


@pytest.fixture
def client() -> BaseClient:
    return BaseClient(base_url="https://octollm.invalid")


def _response(
    status_code: int, *, text: str, content_type: str = "application/json"
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers={"Content-Type": content_type},
        content=text.encode(),
        request=httpx.Request("GET", "https://octollm.invalid/x"),
    )


def test_json_object_body_supplies_message_and_details(client: BaseClient) -> None:
    """The documented shape: message and details are taken from the body."""
    response = _response(404, text='{"message": "no such task", "details": {"task_id": "t1"}}')

    with pytest.raises(NotFoundError) as excinfo:
        client._handle_error_response(response, request_id="req-1")

    assert excinfo.value.message == "no such task"
    assert excinfo.value.details == {"task_id": "t1"}
    assert excinfo.value.request_id == "req-1"


def test_non_json_body_falls_back_to_response_text(client: BaseClient) -> None:
    """A gateway returning HTML must not blow up the client."""
    response = _response(401, text="<html>502 Bad Gateway</html>", content_type="text/html")

    with pytest.raises(AuthenticationError) as excinfo:
        client._handle_error_response(response, request_id="req-2")

    assert excinfo.value.message == "<html>502 Bad Gateway</html>"
    assert excinfo.value.details == {}


def test_empty_body_falls_back_to_the_status_code(client: BaseClient) -> None:
    """With no body at all there is nothing to report but the status."""
    response = _response(422, text="")

    with pytest.raises(ValidationError) as excinfo:
        client._handle_error_response(response, request_id="req-3")

    assert excinfo.value.message == "HTTP 422"
    assert excinfo.value.details == {}


@pytest.mark.parametrize("body", ['["not", "an", "object"]', '"a bare string"', "42", "null"])
def test_json_body_that_is_not_an_object_is_not_treated_as_one(
    client: BaseClient, body: str
) -> None:
    """
    Valid JSON that is not a mapping has no .get(); the client checks the type rather
    than catching the resulting AttributeError, so it degrades to the raw text.
    """
    response = _response(404, text=body)

    with pytest.raises(NotFoundError) as excinfo:
        client._handle_error_response(response, request_id="req-4")

    assert excinfo.value.message == body
    assert excinfo.value.details == {}


def test_json_object_without_a_message_key_falls_back(client: BaseClient) -> None:
    """An object that omits "message" still yields something useful."""
    response = _response(404, text='{"details": {"hint": "check the id"}}')

    with pytest.raises(NotFoundError) as excinfo:
        client._handle_error_response(response, request_id="req-5")

    assert excinfo.value.message == '{"details": {"hint": "check the id"}}'
    assert excinfo.value.details == {"hint": "check the id"}


def test_rate_limit_carries_retry_after(client: BaseClient) -> None:
    """429 is the one status that reads a header as well as the body."""
    response = _response(429, text='{"message": "slow down"}')
    response.headers["Retry-After"] = "30"

    with pytest.raises(RateLimitError) as excinfo:
        client._handle_error_response(response, request_id="req-6")

    assert excinfo.value.message == "slow down"


@pytest.mark.parametrize("status_code", [400, 422])
def test_validation_error_reports_the_status_it_was_given(
    client: BaseClient, status_code: int
) -> None:
    """
    Regression test. ValidationError hardcoded status_code=422 positionally into
    super().__init__, so the client passing status_code= as well raised
    `TypeError: got multiple values for keyword argument 'status_code'`. Every 400 and
    422 response therefore surfaced as a TypeError instead of a ValidationError, and a
    400 must report 400 rather than the class default.
    """
    response = _response(status_code, text='{"message": "bad field"}')

    with pytest.raises(ValidationError) as excinfo:
        client._handle_error_response(response, request_id="req-7")

    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == "bad field"
