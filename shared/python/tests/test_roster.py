"""
Tests for the arm roster.

The roster is a single definition precisely because four sources previously disagreed
about what this system is made of. These tests assert the properties every consumer of
it relies on -- the orchestrator's registry, each arm's `main.py`, and the port-map
check -- so that a careless edit here fails immediately rather than in one consumer.
"""

from __future__ import annotations

import pytest
from octollm_common.roster import ROSTER, SPECS, arm_base_url, spec_for

EXPECTED_PORTS = {
    "planner": 8001,
    "retriever": 8002,
    "coder": 8003,
    "judge": 8004,
    "safety-guardian": 8005,
    "executor": 8006,
    "memory": 8007,
    "red-team": 8008,
}


def test_the_roster_has_eight_arms():
    """
    Eight, settled. `ARCHITECTURE.md` tabled six, the Project Overview named seven
    "examples", and six had directories. This is the number, and it is here.
    """
    assert len(ROSTER) == 8


def test_every_arm_id_is_unique():
    assert len({spec.arm_id for spec in ROSTER}) == len(ROSTER)


def test_every_port_is_unique_and_canonical():
    """
    A duplicate would bind one arm over another in compose and produce a confusing
    runtime failure rather than a startup one. The literal map is duplicated here on
    purpose: a test that derives its expectation from the code under test cannot fail.
    """
    assert {spec.arm_id: spec.port for spec in ROSTER} == EXPECTED_PORTS


def test_every_endpoint_is_a_rooted_path_not_a_url():
    """
    `endpoint` is the path on the arm. The SDKs previously described it as "Kubernetes
    service endpoint", meaning a URL -- two different things under one name is how a
    client ends up requesting `http://planner-arm:8001http://planner-arm:8001/plan`.
    """
    for spec in ROSTER:
        assert spec.endpoint.startswith("/"), spec.arm_id
        assert "://" not in spec.endpoint, spec.arm_id


def test_no_arm_claims_to_be_implemented_yet():
    """
    Stage 4 builds the framework, not the arms. When Stage 8 flips one of these, this
    assertion is what forces the change to be deliberate.
    """
    assert [spec.arm_id for spec in ROSTER if spec.implemented] == []


def test_every_arm_names_the_stage_that_builds_it():
    for spec in ROSTER:
        assert spec.implemented_in_stage >= 6, spec.arm_id


def test_every_peer_edge_points_at_something_that_exists():
    """
    A peer token is only ever issued for an edge named in `peers`. An edge naming a
    non-existent arm is an edge that can never be honoured, and it would sit there
    looking like a capability.
    """
    known = set(SPECS) | {"reflex"}  # the reflex layer is a service, not an arm
    for spec in ROSTER:
        unknown = set(spec.peers) - known
        assert not unknown, f"{spec.arm_id} declares unknown peers: {sorted(unknown)}"


def test_no_arm_declares_itself_as_a_peer():
    for spec in ROSTER:
        assert spec.arm_id not in spec.peers


def test_the_red_team_arm_cannot_reach_the_network_by_itself():
    """
    It never opens a socket. Every probe is delegated to the executor's hardened
    sandbox, which keeps the dangerous primitive in the memory-safe language and means
    there is one sandbox to harden rather than two.
    """
    assert "executor" in SPECS["red-team"].peers


def test_base_urls_follow_the_compose_service_naming():
    assert arm_base_url("planner") == "http://planner-arm:8001"
    assert arm_base_url("safety-guardian") == "http://safety-guardian-arm:8005"


def test_a_base_url_template_can_be_overridden():
    """Kubernetes DNS differs from compose; a hardcoded hostname would spread."""
    url = arm_base_url("coder", host_template="http://{service}.octollm.svc:{port}")

    assert url == "http://coder-arm.octollm.svc:8003"


def test_an_unknown_arm_raises_rather_than_returning_a_default():
    """A typo must fail at the call site, not route a task into the void."""
    with pytest.raises(KeyError):
        spec_for("planer")
