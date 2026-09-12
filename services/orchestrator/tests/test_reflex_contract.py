"""
Contract tests for the Reflex Layer client, against responses the real service sent.

These exist because the 39 tests in `test_reflex_client.py` all mock `httpx` with
dictionaries built from the client's own models. A mock written from the client's
shape can only ever confirm the client agrees with itself, and it did -- while the
real integration could not succeed for **any** input:

  * The service emitted `status: "success"`; the client's enum required `"Success"`,
    so every response failed validation, including clean ones with no detections.
  * The service emitted `start` / `end` / `matched_text`; the client required
    `position` / `value` / `context`, so every PII detection failed.
  * The client required a `context_analysis` object on every injection match. The
    service has never sent one, and sends `indicators` instead.

The fixtures in `tests/fixtures/` were captured from a running reflex layer with
`scripts/capture_reflex_fixtures.py`, with only `request_id` and
`processing_time_ms` normalised. Nothing here is hand-written from the Python side,
which is the whole point.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.reflex_client import ProcessStatus, ReflexResponse

FIXTURES = Path(__file__).parent / "fixtures"
CASES = sorted(p.name for p in FIXTURES.glob("*.json"))


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_fixtures_are_present():
    """A silently empty fixture directory would make every test below vacuous."""
    assert len(CASES) >= 4, f"expected at least 4 captured responses, found {CASES}"


@pytest.mark.parametrize("name", CASES)
def test_every_captured_response_parses(name: str):
    """
    The client must accept, unchanged, what the service actually sends.

    This is the assertion that was missing. Each of these fixtures fails to parse
    against the pre-Stage-3 models.
    """
    response = ReflexResponse.model_validate(load(name))
    assert response.request_id
    assert isinstance(response.status, ProcessStatus)


def test_pii_matches_carry_a_span_and_the_matched_text():
    response = ReflexResponse.model_validate(load("pii.json"))

    assert response.pii_detected is True
    assert len(response.pii_matches) == 2

    kinds = {m.pii_type for m in response.pii_matches}
    assert kinds == {"email", "ssn"}, "types are snake_case on the wire"

    for match in response.pii_matches:
        assert match.end > match.start, "a span, not a single offset"
        assert match.matched_text
        assert 0.0 <= match.confidence <= 1.0


def test_ssn_is_ssn_and_not_s_s_n():
    """
    Regression test for the enum renaming.

    serde's `rename_all = "snake_case"` inserts a separator before every capital, so
    `SSN` serialises as `s_s_n` and `IPv4` as `i_pv4` unless the variant is pinned
    with an explicit `#[serde(rename)]`. This asserts the pin is still there.
    """
    kinds = {m.pii_type for m in ReflexResponse.model_validate(load("pii.json")).pii_matches}
    assert "ssn" in kinds
    assert not any("_" in k and k.replace("_", "") == "ssn" for k in kinds)


def test_injection_matches_carry_indicators_not_a_context_analysis_object():
    response = ReflexResponse.model_validate(load("injection.json"))

    assert response.injection_detected is True
    assert response.status is ProcessStatus.BLOCKED, "a critical injection blocks"

    first = response.injection_matches[0]
    assert first.injection_type == "ignore_previous_instructions"
    assert first.severity == "critical"
    assert first.indicators, "the service sends the triggering tokens"
    assert first.end > first.start


def test_clean_text_produces_no_detections():
    response = ReflexResponse.model_validate(load("clean.json"))

    assert response.status is ProcessStatus.SUCCESS
    assert response.pii_detected is False
    assert response.injection_detected is False
    assert response.pii_matches == []
    assert response.injection_matches == []


def test_rate_limited_is_a_status_the_client_understands():
    """
    The client's enum had no rate-limited variant, so a 429-equivalent response was
    unparseable. The service emits `rate_limited` (snake_case): `lowercase` would
    have flattened it to `ratelimited`, which no consumer can split back into words.
    """
    payload = load("clean.json") | {"status": "rate_limited"}
    assert ReflexResponse.model_validate(payload).status is ProcessStatus.RATE_LIMITED


def test_an_unknown_status_is_rejected_rather_than_coerced():
    """A contract violation must be loud, not silently absorbed as a string."""
    with pytest.raises(ValidationError):
        ReflexResponse.model_validate(load("clean.json") | {"status": "Success"})
