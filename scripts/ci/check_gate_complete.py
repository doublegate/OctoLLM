#!/usr/bin/env python3
"""
Assert that every job in a workflow is wired into its aggregating gate job.

Branch protection can only require named checks. When `ci-gate` is the single required
check, a job that is not in `ci-gate.needs` is advisory: it can fail while the gate goes
green and the pull request merges. Nothing about that is visible in the UI -- the failed
job and the passing gate sit next to each other in the same check list.

That is not hypothetical for this repository. Before this script existed, `test.yml`'s
summary job depended on three test jobs that were themselves `continue-on-error: true`,
so the aggregate reported success unconditionally and announced "Phase 0: No tests exist
yet" over a tree holding 240 Rust and 178 Python tests.

So the rule is enforced mechanically rather than remembered: add a job, add it to
`needs`, or CI fails and tells you which one you forgot.

Usage:
    python scripts/ci/check_gate_complete.py .github/workflows/ci.yml [--gate ci-gate]

Exit status is 0 when every job is wired in, 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment problem, not a gate failure
    sys.exit("check_gate_complete.py requires PyYAML (pip install pyyaml)")


def check(workflow_path: Path, gate_job: str) -> list[str]:
    """Return a list of problems; empty means the gate is complete."""
    document = yaml.safe_load(workflow_path.read_text())
    if not isinstance(document, dict):
        return [f"{workflow_path}: not a YAML mapping"]

    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        return [f"{workflow_path}: no jobs found"]

    if gate_job not in jobs:
        return [f"{workflow_path}: no job named {gate_job!r} (jobs: {', '.join(sorted(jobs))})"]

    needs = jobs[gate_job].get("needs", [])
    if isinstance(needs, str):  # `needs: some-job` is legal YAML for a single dependency
        needs = [needs]
    declared = set(needs)

    expected = set(jobs) - {gate_job}
    problems = []

    for missing in sorted(expected - declared):
        problems.append(
            f"job {missing!r} is not in {gate_job}.needs -- it can fail while the gate passes"
        )
    for unknown in sorted(declared - expected):
        problems.append(f"{gate_job}.needs lists {unknown!r}, which is not a job in this workflow")

    if not problems:
        print(f"{workflow_path}: {gate_job} requires all {len(expected)} jobs")
        for name in sorted(expected):
            print(f"  - {name}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", type=Path, help="path to the workflow YAML file")
    parser.add_argument(
        "--gate",
        default="ci-gate",
        help="name of the aggregating job that must depend on every other job",
    )
    args = parser.parse_args()

    if not args.workflow.is_file():
        print(f"::error::no such workflow file: {args.workflow}", file=sys.stderr)
        return 1

    problems = check(args.workflow, args.gate)
    for problem in problems:
        print(f"::error file={args.workflow}::{problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
