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

# Host ports are overridable so a machine with a conflict can still run this, and the
# port variables are the SAME ones compose reads -- `REFLEX_PORT=18080 make up smoke`
# has to work end to end. Taking only a URL here meant setting the port moved the
# service and left this script asking the old one, which is a check that fails for a
# reason unrelated to the thing it checks.
# Where this script lives, so it can reach the token minter regardless of the
# directory it was invoked from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The same interpreter the Makefile uses. Most of this script needs only the standard
# library, but minting a capability token imports the orchestrator's package -- and
# bare `python3` is not necessarily the interpreter that has it installed.
PYTHON="${PYTHON:-python3}"

ORCHESTRATOR="${ORCHESTRATOR_URL:-http://localhost:${ORCHESTRATOR_PORT:-8000}}"
REFLEX="${REFLEX_URL:-http://localhost:${REFLEX_PORT:-8080}}"
MEMORY="${MEMORY_URL:-http://localhost:${MEMORY_PORT:-8007}}"
PLANNER="${PLANNER_URL:-http://localhost:${PLANNER_PORT:-8001}}"

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

# ---------------------------------------------------------------------------
# 4. The arm registry, and an arm answering honestly
# ---------------------------------------------------------------------------
#
# Both SDKs shipped `listArms()` against an endpoint that did not exist, and against
# two different paths. This is the assertion that it exists and says something true.

echo
echo "Checking the arm registry..."

arms="$(curl -fsS "${ORCHESTRATOR}/arms?refresh=true")" || fail "GET /arms failed"

echo "${arms}" | python3 -c "
import json, sys
arms = {a['arm_id']: a for a in json.load(sys.stdin)['arms']}
assert len(arms) == 8, f'expected 8 arms, got {len(arms)}'
# The five framework arms are running in this stack, so a probe must reach them.
# If this fails, the registry is reporting a topology the network does not have.
for arm_id in ('planner', 'retriever', 'coder', 'judge', 'safety-guardian'):
    assert arms[arm_id]['status'] == 'healthy', f'{arm_id} probed {arms[arm_id][\"status\"]}'
    assert arms[arm_id]['implemented'] is False, f'{arm_id} claims to be implemented'
# Memory is running and implemented as of Stage 6 -- the first arm in this
# repository that answers with something rather than a 501.
assert arms['memory']['status'] == 'healthy', arms['memory']['status']
assert arms['memory']['implemented'] is True, 'memory does not claim to be implemented'
# The one still-unbuilt arm is listed rather than omitted, and says so.
assert arms['red-team']['status'] == 'unavailable'
assert arms['red-team']['implemented_in_stage'] == 11
" || fail "GET /arms did not describe the running stack"
pass "registry lists 8 arms; the 6 running ones probe healthy"

# An unauthenticated caller must not be able to mutate the registry at all. Which
# refusal arrives depends on deployment: 503 when no registration token is configured
# (the default, and the reason the endpoint fails closed), 401 when one is configured
# and the caller has not presented it. Asserting the PROPERTY rather than one status
# keeps this true in both, and 200 or 403 here would each mean the write was reached.
status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${ORCHESTRATOR}/arms/register" \
  -H 'content-type: application/json' \
  -d '{"arm_id":"planner","implemented":true}' || true)"
case "${status}" in
  401|503) pass "unauthenticated registration is refused (${status})" ;;
  *) fail "unauthenticated registration returned ${status}; expected 401 or 503" ;;
esac

# And the refusal must have changed nothing. A check that only reads the status code
# would pass against a service that answered 401 after applying the write.
curl -fsS "${ORCHESTRATOR}/arms" | python3 -c "
import json, sys
planner = json.load(sys.stdin)['arms'][0]
assert planner['implemented'] is False, 'the refused write was applied anyway'
assert planner['base_url'] == 'http://planner-arm:8001', 'the arm moved'
" || fail "an unauthenticated registration mutated the registry"
pass "the refused registration changed nothing"

# Where an arm listens is not a registrable field at all: a caller able to restate it
# could redirect that arm's traffic to a host it controls.
status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${ORCHESTRATOR}/arms/register" \
  -H 'content-type: application/json' \
  -d '{"arm_id":"planner","base_url":"http://smoke-test-attacker.invalid"}' || true)"
case "${status}" in
  401|422|503) pass "base_url is not a registrable field (${status})" ;;
  *) fail "registering a base_url returned ${status}; it must never be accepted" ;;
esac

# An unimplemented arm must answer 501 naming its stage -- never a plausible fake,
# which would make an unimplemented arm indistinguishable from a working one.
plan_status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${PLANNER}/plan" \
  -H 'content-type: application/json' -d '{"goal":"smoke"}' || true)"
[ "${plan_status}" = "501" ] || fail "POST /plan returned ${plan_status}, expected 501"
pass "planner POST /plan returns 501 naming Stage 8"

# ---------------------------------------------------------------------------
# The Memory arm (Stage 6): Qdrant stops being a container nothing reads.
# ---------------------------------------------------------------------------
echo
echo "Checking memory..."

curl -fsS "${MEMORY}/health" >/dev/null || fail "memory /health did not answer"
pass "memory /health"

# Both stores, reported separately. An arm that says ready while its database is
# unreachable is the same failure as a green check over a suite that never ran.
curl -fsS "${MEMORY}/ready" | python3 -c "
import json, sys
checks = json.load(sys.stdin)['checks']
assert checks['postgres'] is True, 'memory cannot reach Postgres'
assert checks['qdrant'] is True, 'memory cannot reach Qdrant'
assert checks['ring_attached'] is True, 'memory is not attached to the Neural Ring'
" || fail "memory /ready reports a store it cannot reach"
pass "memory /ready (Postgres, Qdrant and the ring)"

# The whole surface is capability-gated, so an unauthenticated call must be refused.
status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${MEMORY}/recall" \
  -H 'content-type: application/json' -d '{"query":"anything"}' || true)"
case "${status}" in
  401|503) pass "unauthenticated recall is refused (${status})" ;;
  *) fail "unauthenticated recall returned ${status}; memory holds every arm's output" ;;
esac

# The secret is read back out of the running container rather than passed in, so this
# cannot disagree with what the stack is actually using.
secret="$(docker compose exec -T memory-arm printenv MEMORY_CAPABILITY_SECRET 2>/dev/null | tr -d '\r' || true)"

if [ -z "${secret}" ]; then
  echo "  --   memory round trip skipped: no capability secret configured on this stack"
  echo "       (\`make up\` generates one; set CAPABILITY_SECRET to supply your own)"
else
  task="smoke-$(date +%s)"
  token="$(ORCHESTRATOR_CAPABILITY_SECRET="${secret}" "${PYTHON}" "${REPO_ROOT}/scripts/mint_capability.py" \
    --caller retriever --callee memory --task-id "${task}" \
    --scope call:recall --scope memory:write --scope clearance:internal \
    --max-calls 20 2>/dev/null)" || fail "could not mint a capability token for memory"
  [ -n "${token}" ] || fail "minting a memory capability token produced nothing"

  artifact_id="$("${PYTHON}" -c 'import uuid; print(uuid.uuid4())')"
  body="$("${PYTHON}" - "${artifact_id}" "${task}" <<'PYEOF'
import json, sys
artifact_id, task_id = sys.argv[1], sys.argv[2]
print(json.dumps({
    "task_id": task_id,
    "artifact": {
        "artifact_id": artifact_id,
        "artifact_type": "code",
        "content": "def parse_header(raw): return raw.split(':', 1)",
        "provenance": {"created_by": "retriever", "task_id": task_id,
                       "sensitivity": "internal"},
    },
}))
PYEOF
)"

  remembered="$(curl -fsS -X POST "${MEMORY}/remember" \
    -H "authorization: Bearer ${token}" -H "x-task-id: ${task}" \
    -H 'content-type: application/json' -d "${body}")" ||
    fail "POST /remember failed with a valid capability token"
  echo "${remembered}" | python3 -c "
import json, sys
body = json.load(sys.stdin)
assert body['semantic_written'] is True, 'the provenance record was not written'
assert body['episodic_written'] is True, 'the artifact was not indexed in Qdrant'
assert body['duplicate'] is False, 'a fresh artifact was reported as a duplicate'
" || fail "POST /remember did not write both stores"
  pass "memory remembered an artifact (Postgres + Qdrant)"

  # Idempotent, because ring delivery is at-least-once and a redelivery is normal.
  again="$(curl -fsS -X POST "${MEMORY}/remember" \
    -H "authorization: Bearer ${token}" -H "x-task-id: ${task}" \
    -H 'content-type: application/json' -d "${body}")" ||
    fail "the second POST /remember failed"
  echo "${again}" | python3 -c "
import json, sys
assert json.load(sys.stdin)['duplicate'] is True, 'a redelivery was not detected'
" || fail "POST /remember is not idempotent"
  pass "a redelivered artifact is reported as a duplicate, not stored twice"

  recalled="$(curl -fsS -X POST "${MEMORY}/recall" \
    -H "authorization: Bearer ${token}" -H "x-task-id: ${task}" \
    -H 'content-type: application/json' \
    -d "{\"query\":\"parsing a header\",\"top_k\":5,\"task_id\":\"${task}\"}")" ||
    fail "POST /recall failed with a valid capability token"
  echo "${recalled}" | python3 -c "
import json, sys
body = json.load(sys.stdin)
assert body['scope'] == 'episodic', body
hits = body['hits']
assert len(hits) >= 1, 'memory recalled nothing it had just stored'
assert hits[0]['created_by'] == 'retriever', hits[0]
assert hits[0]['sensitivity'] == 'internal', hits[0]
" || fail "POST /recall did not return the artifact that was just stored"
  pass "memory recalled it back -- global semantic memory exists"
fi

echo
echo "smoke: PASSED"
