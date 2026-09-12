#!/usr/bin/env bash
#
# Prove that .gitleaks.toml actually detects secrets, and that the configuration it
# replaced did not.
#
# A secret scanner reports the same "no leaks found" whether it inspected everything
# or nothing. The previous config inspected close to nothing: it discarded gitleaks'
# ~170 built-in rules (no `[extend] useDefault = true`) and path-exempted every
# markdown file, all of docs/, all of tests/, .github/workflows/*.yml and
# infrastructure/*.sh. It had been reporting clean for months.
#
# So this plants four secrets, one in each location the OLD config exempted, and
# asserts:
#
#   * the CURRENT config finds all four              -- the control works
#   * the OLD config finds none of them              -- the control can fail
#
# The second assertion is the point. Without it, "the scanner found four secrets"
# could just mean the secrets were easy; with it, the four are demonstrably invisible
# to what was running before.
#
# The planted values are ASSEMBLED AT RUNTIME from fragments rather than written as
# literals. A file containing a literal well-formed credential is itself blocked by
# GitHub push protection -- which happened to this repository once already, on a
# synthetic Stripe key in a Rust test. Fragments keep this script committable.
#
# Everything happens in a scratch git repository under a temporary directory. Nothing
# is written into the working tree, and the trap removes it on any exit path.
#
# Usage: scripts/gitleaks-selftest.sh          (or: make secrets-selftest)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_CONFIG="${REPO_ROOT}/.gitleaks.toml"

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "gitleaks is not installed. https://github.com/gitleaks/gitleaks#installing" >&2
  exit 127
fi

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

# ---------------------------------------------------------------------------
# The four planted secrets, assembled so no literal credential lives in this file.
#
# Each is a shape gitleaks' BUILT-IN rules detect and the old custom ruleset did
# not, so they test both defects at once: the missing built-ins and the path
# exemptions.
# ---------------------------------------------------------------------------
aws_key="AKIA$(printf '%s' 'Q7NJ4XKD2MPLZR3V')"
gitlab_pat="glpat-$(printf '%s' 'xQ7nJ4zKd2MpLzR3vB8t')"
slack_token="xoxb-$(printf '%s' '2094857362-3948571029384-KdJ2nQ7xLzR3vB8tMpQ4')"
# A complete PEM block, not just a header: gitleaks' private-key rule requires the
# BEGIN marker, a body and the END marker, so a lone header produces no finding. The
# body is deterministic sha256 output, which is key-shaped and is not a key.
private_key="$(
  printf -- '-----BEGIN RSA PRIVATE%s-----\n' ' KEY'
  python3 -c "
import base64, hashlib
blob = b''.join(hashlib.sha256(str(i).encode()).digest() for i in range(12))
b64 = base64.b64encode(blob).decode()
print('\n'.join(b64[i:i + 64] for i in range(0, len(b64), 64)))
"
  printf -- '-----END RSA PRIVATE%s-----\n' ' KEY'
)"

mkdir -p "${WORK}/repo"/{docs,tests,.github/workflows,infrastructure}
cd "${WORK}/repo"

# One secret per location the old config path-exempted.
#   docs/*.md                  <- '''docs/.*''' and '''.*\.md$'''
#   tests/*.py                 <- '''tests/.*'''
#   .github/workflows/*.yml    <- '''\.github/workflows/.*\.yml$'''
#   infrastructure/*.sh        <- '''infrastructure/.*\.sh$'''
printf 'Deployment notes.\n\n    AWS_ACCESS_KEY_ID=%s\n' "${aws_key}" > docs/deploy.md
printf 'GITLAB_TOKEN = "%s"\n' "${gitlab_pat}" > tests/test_fixture.py
printf 'env:\n  SLACK_BOT_TOKEN: %s\n' "${slack_token}" > .github/workflows/notify.yml
printf '#!/bin/sh\ncat <<EOF\n%s\nEOF\n' "${private_key}" > infrastructure/provision.sh

git init -q .
git -c user.email=selftest@invalid -c user.name=selftest add -A
git -c user.email=selftest@invalid -c user.name=selftest commit -q -m "planted secrets"

# ---------------------------------------------------------------------------
# The old configuration, reconstructed to its two load-bearing properties: no
# [extend] block (so the built-ins are discarded) and the blanket path allowlist.
# Reconstructed rather than read from git history so this test keeps working after
# the old file is gone, and so what it demonstrates is legible here.
# ---------------------------------------------------------------------------
cat > "${WORK}/old.toml" <<'OLDCONFIG'
title = "OctoLLM Gitleaks Config (pre-2026-09 reconstruction)"

[allowlist]
  paths = [
    '''docs/.*''',
    '''tests/.*''',
    '''.*\.md$''',
    '''\.github/workflows/.*\.yml$''',
    '''infrastructure/.*\.sh$''',
  ]

# One custom rule is enough to reproduce the defect: defining ANY [[rules]] without
# [extend] useDefault = true discards all ~170 built-in rules.
[[rules]]
  id = "openai-api-key-raw"
  description = "OpenAI API Key (raw format)"
  regex = '''sk-proj-[a-zA-Z0-9_-]{100,}'''
  tags = ["key", "openai", "api"]
OLDCONFIG

count_findings() {
  local config="$1" report="$2"
  gitleaks detect --source . --config "${config}" \
    --report-format json --report-path "${report}" >/dev/null 2>&1 || true
  python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "${report}" 2>/dev/null || echo 0
}

echo "Planted 4 secrets in locations the old config exempted:"
echo "    docs/deploy.md                  AWS access key id"
echo "    tests/test_fixture.py           GitLab personal access token"
echo "    .github/workflows/notify.yml    Slack bot token"
echo "    infrastructure/provision.sh     RSA private key (complete PEM block)"
echo

old_count="$(count_findings "${WORK}/old.toml" "${WORK}/old.json")"
new_count="$(count_findings "${CURRENT_CONFIG}" "${WORK}/new.json")"

echo "  old config (.gitleaks.toml before 2026-09):  ${old_count} findings"
echo "  current config:                              ${new_count} findings"
echo

status=0

if [ "${old_count}" -ne 0 ]; then
  echo "FAIL: the reconstructed old config found ${old_count} secrets, expected 0." >&2
  echo "      This test's negative control is broken -- it no longer demonstrates" >&2
  echo "      that those four secrets were invisible to the previous scanner." >&2
  status=1
else
  echo "  ok   negative control: the old config finds none of the four."
fi

if [ "${new_count}" -lt 4 ]; then
  echo "FAIL: the current config found ${new_count} of 4 planted secrets." >&2
  echo "      Check that .gitleaks.toml still sets [extend] useDefault = true and" >&2
  echo "      has not re-acquired a broad path allowlist." >&2
  python3 - "${WORK}/new.json" <<'PY' >&2 || true
import json, sys
found = {(f["File"], f["RuleID"]) for f in json.load(open(sys.argv[1]))}
print("      found:", sorted(found) or "nothing")
PY
  status=1
else
  echo "  ok   current config: found ${new_count} findings across the four files."
fi

# Every planted file must be represented, not just four findings in total -- four
# hits in one file would otherwise pass while three locations stayed invisible.
missing="$(python3 - "${WORK}/new.json" <<'PY'
import json, sys
expected = {
    "docs/deploy.md",
    "tests/test_fixture.py",
    ".github/workflows/notify.yml",
    "infrastructure/provision.sh",
}
seen = {f["File"] for f in json.load(open(sys.argv[1]))}
print(" ".join(sorted(expected - seen)))
PY
)"

if [ -n "${missing}" ]; then
  echo "FAIL: no finding in: ${missing}" >&2
  echo "      A path exemption has come back for those locations." >&2
  status=1
else
  echo "  ok   all four planted locations produced a finding."
fi

echo
if [ "${status}" -eq 0 ]; then
  echo "gitleaks self-test PASSED"
else
  echo "gitleaks self-test FAILED" >&2
fi
exit "${status}"
