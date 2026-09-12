#!/usr/bin/env bash
#
# Assert that the running stack is actually working.
#
# `docker compose up` reporting success has never meant much here: five arm
# containers used to crash-loop on a CMD pointing at a module that was never
# written, and compose reported that as a started stack. So this checks three
# things that "started" does not imply.
#
#   1. Every service reports HEALTHY, not merely running.
#   2. The reflex layer's POST /process -- the one endpoint with business logic --
#      answers, and detects something it should detect. It returned 500 on every
#      request for the whole life of the service, because the router was served
#      without connect-info and the ConnectInfo extractor was rejected before any
#      handler ran.
#   3. A task round-trips through the orchestrator: submitted, then readable back
#      with the same id.
#
# Item 3 is deliberately modest about what it proves. The orchestrator does not yet
# call an arm -- the execution engine is Stage 7 -- so a submitted task stays
# `pending`, and this asserts exactly that rather than pretending otherwise. When
# Stage 7 lands, this assertion changes to `completed` and becomes the real gate.
#
# Usage: scripts/smoke.sh          (or: make smoke, after make up)

set -euo pipefail

ORCHESTRATOR="${ORCHESTRATOR_URL:-http://localhost:8000}"
REFLEX="${REFLEX_URL:-http://localhost:8080}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() { printf '  ok   %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Every service healthy
# ---------------------------------------------------------------------------
echo "Checking service health..."

unhealthy="$(docker compose ps --format '{{.Service}} {{.Health}}' |
  awk '$2 != "healthy" && $2 != "" { print $1 " (" $2 ")" }' || true)"

no_health="$(docker compose ps --format '{{.Service}} {{.Health}}' |
  awk '$2 == "" { print $1 }' || true)"

if [ -n "${unhealthy}" ]; then
  fail "these services are not healthy: ${unhealthy}"
fi
pass "every service reporting a health state is healthy"

if [ -n "${no_health}" ]; then
  # Not fatal, but worth naming: a container with no healthcheck cannot be
  # distinguished from one that is wedged.
  echo "  note no healthcheck defined for: $(echo "${no_health}" | tr '\n' ' ')"
fi

# ---------------------------------------------------------------------------
# 2. The reflex layer's real endpoint
# ---------------------------------------------------------------------------
echo "Checking the reflex layer..."

curl -fsS "${REFLEX}/health" >/dev/null || fail "reflex layer /health did not answer"
pass "reflex /health"

reflex_body="$(curl -fsS -X POST "${REFLEX}/process" \
  -H 'content-type: application/json' \
  -d '{"text":"my email is alice@example.com"}')" ||
  fail "POST /process failed. If the body mentions ConnectInfo, serve() has stopped
      calling into_make_service_with_connect_info and every request is 500ing again."

echo "${reflex_body}" | grep -q '"pii_detected":true' ||
  fail "POST /process answered but did not detect the email: ${reflex_body}"
pass "reflex POST /process detects PII"

echo "${reflex_body}" | grep -q '"pii_type":"email"' ||
  fail "pii_type is not the snake_case wire value: ${reflex_body}"
pass "reflex emits the snake_case wire format"

# ---------------------------------------------------------------------------
# 3. A task round-trips through the orchestrator
# ---------------------------------------------------------------------------
echo "Checking the orchestrator..."

curl -fsS "${ORCHESTRATOR}/health" >/dev/null || fail "orchestrator /health did not answer"
pass "orchestrator /health"

curl -fsS "${ORCHESTRATOR}/ready" >/dev/null || fail "orchestrator /ready did not answer"
pass "orchestrator /ready (database and reflex layer reachable)"

submit_body="$(curl -fsS -X POST "${ORCHESTRATOR}/submit" \
  -H 'content-type: application/json' \
  -d '{"goal":"smoke test: confirm a task round-trips"}')" ||
  fail "POST /submit failed"

task_id="$(echo "${submit_body}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["task_id"])')"
[ -n "${task_id}" ] || fail "POST /submit returned no task_id: ${submit_body}"
pass "task submitted (${task_id})"

fetched="$(curl -fsS "${ORCHESTRATOR}/tasks/${task_id}")" ||
  fail "GET /tasks/${task_id} failed -- the task did not persist"

echo "${fetched}" | python3 -c "
import json, sys
task = json.load(sys.stdin)
assert task['task_id'] == '${task_id}', f'wrong task returned: {task[\"task_id\"]}'
# Stage 7 changes this to 'completed'. Until the execution engine exists, a task
# that stays pending is the correct outcome, and asserting it keeps this honest.
assert task['status'] == 'pending', f'expected pending before Stage 7, got {task[\"status\"]}'
" || fail "the task did not read back correctly"
pass "task reads back by id, status pending (no execution engine until Stage 7)"

echo
echo "smoke: PASSED"
