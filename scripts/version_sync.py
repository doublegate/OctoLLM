#!/usr/bin/env python3
"""
Propagate the version in `VERSION` to every place that states one, and fail when
any of them disagrees.

Before this existed the repository stated its version in twenty-two places and they
held six different answers at once: 0.1.0 (root, orchestrator, both its defaults),
0.3.0 (six OpenAPI specs), 0.4.0 (both SDKs), 0.9.0 (two telemetry fallbacks that
would have labelled every emitted span), 1.0.0 and 1.1.0 (two more specs), and 1.2.0
(the README badge). None of them was right, because **none of them had ever been
released**: the repository has zero git tags, and neither `octollm-sdk` on PyPI nor
`octollm-sdk` on npm exists. Every one of those numbers was a claim about an artifact
that was never built.

Usage:
    python scripts/version_sync.py            # rewrite every site from VERSION
    python scripts/version_sync.py --check    # report drift, exit 1 (what CI runs)

Adding a site is the point of this file: if you write a version anywhere, add it to
SITES. A site that is not listed here is a number that will silently rot.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"

# A released version must be a plain SemVer core. Pre-release and build metadata are
# rejected on purpose: several of the sites below (a Cargo workspace version, an npm
# `version` field) have their own opinions about what suffixes are legal, and a value
# that is valid in one and not another is how a release breaks halfway through.
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class Site:
    """One place that states the version.

    `pattern` must match exactly once in the file and capture the version -- and only
    the version -- in group 1. Matching exactly once is asserted rather than assumed:
    a pattern that silently starts matching two places would rewrite the wrong one,
    and a pattern that stops matching would report success having changed nothing.
    """

    path: str
    pattern: str
    why: str


SITES: tuple[Site, ...] = (
    # --- Python manifests -------------------------------------------------------
    Site("pyproject.toml", r'(?m)^version = "([^"]+)"', "root poetry project"),
    Site(
        "services/orchestrator/pyproject.toml",
        r'(?m)^version = "([^"]+)"',
        "orchestrator distribution",
    ),
    Site(
        "sdks/python/octollm-sdk/pyproject.toml",
        r'(?m)^version = "([^"]+)"',
        "Python SDK distribution",
    ),
    # --- Python source ----------------------------------------------------------
    Site(
        "services/orchestrator/app/__init__.py",
        r'(?m)^__version__ = "([^"]+)"',
        "orchestrator package attribute",
    ),
    Site(
        "sdks/python/octollm-sdk/octollm_sdk/__init__.py",
        r'(?m)^__version__ = "([^"]+)"',
        "Python SDK package attribute",
    ),
    Site(
        "services/orchestrator/app/config.py",
        r'version: str = Field\(default="([^"]+)"',
        "orchestrator settings default",
    ),
    Site(
        "services/orchestrator/app/models.py",
        r'version: str = Field\(default="([^"]+)"',
        "HealthResponse payload -- what /health actually reports",
    ),
    Site(
        "services/orchestrator/app/telemetry.py",
        r'os\.getenv\("APP_VERSION", "([^"]+)"\)',
        "orchestrator span attribute fallback",
    ),
    # --- Rust -------------------------------------------------------------------
    Site("Cargo.toml", r'(?m)^version = "([^"]+)"', "cargo workspace, inherited by all 5 members"),
    Site(
        "services/reflex-layer/src/telemetry.rs",
        r'env::var\("APP_VERSION"\)\.unwrap_or_else\(\|_\| "([^"]+)"\.to_string\(\)\)',
        "reflex span attribute fallback",
    ),
    # --- TypeScript -------------------------------------------------------------
    Site(
        "sdks/typescript/octollm-sdk/package.json",
        r'(?m)^  "version": "([^"]+)"',
        "TypeScript SDK package",
    ),
    # npm derives the lockfile from package.json, but it does NOT rewrite these two on
    # its own unless something re-resolves the tree -- so a bump that touched only
    # package.json left the lockfile stating the previous version, which is the exact
    # drift this tool exists to catch. `npm install --package-lock-only` is the
    # canonical regeneration; these patterns make the disagreement visible either way.
    Site(
        "sdks/typescript/octollm-sdk/package-lock.json",
        r'(?m)\A\{\n  "name": "octollm-sdk",\n  "version": "([^"]+)"',
        "TypeScript SDK lockfile, top level",
    ),
    Site(
        "sdks/typescript/octollm-sdk/package-lock.json",
        r'(?m)^      "name": "octollm-sdk",\n      "version": "([^"]+)"',
        "TypeScript SDK lockfile, root package entry",
    ),
    # --- Documentation ----------------------------------------------------------
    Site(
        "README.md",
        r"badge/Version-([0-9][^-]*)-brightgreen",
        "README badge -- the version a reader sees first",
    ),
    # --- OpenAPI specs ----------------------------------------------------------
    # These are deliberately pinned to the repository version rather than versioned
    # independently. Independent API versioning is a real practice, but it requires
    # the specs to describe something: four mutually incompatible descriptions of
    # these APIs exist right now, and three different `info.version` values among
    # them communicated nothing. They move together until the specs are generated
    # from the implementations and the contract is frozen.
    *(
        Site(f"docs/api/openapi/{name}.yaml", r"(?m)^  version: (\S+)", f"{name} OpenAPI info")
        for name in (
            "coder",
            "executor",
            "judge",
            "orchestrator",
            "planner",
            "reflex-layer",
            "retriever",
            "safety-guardian",
        )
    ),
)


def read_version() -> str:
    if not VERSION_FILE.is_file():
        sys.exit(f"no VERSION file at {VERSION_FILE}")
    version = VERSION_FILE.read_text().strip()
    if not SEMVER.match(version):
        sys.exit(f"VERSION is {version!r}; expected a plain SemVer core such as 1.0.0")
    return version


def find(site: Site) -> tuple[str, re.Match[str], str]:
    """Return (file text, the single match, the version it currently states)."""
    path = REPO_ROOT / site.path
    if not path.is_file():
        sys.exit(f"{site.path}: no such file (listed in SITES as {site.why})")

    text = path.read_text()
    matches = list(re.finditer(site.pattern, text))
    if len(matches) != 1:
        sys.exit(
            f"{site.path}: pattern matched {len(matches)} times, expected exactly 1.\n"
            f"  site: {site.why}\n"
            f"  pattern: {site.pattern}\n"
            "  Fix the pattern rather than the file -- a pattern that matches the wrong "
            "number of places will rewrite the wrong line or silently rewrite nothing."
        )
    return text, matches[0], matches[0].group(1)


def run(*, check_only: bool) -> int:
    version = read_version()
    width = max(len(site.path) for site in SITES)
    drifted: list[tuple[Site, str]] = []

    for site in SITES:
        text, match, current = find(site)
        if current == version:
            print(f"  ok      {site.path:<{width}}  {current}")
            continue

        drifted.append((site, current))
        if check_only:
            print(f"  DRIFT   {site.path:<{width}}  {current}  (VERSION says {version})")
            continue

        start, end = match.span(1)
        (REPO_ROOT / site.path).write_text(text[:start] + version + text[end:])
        print(f"  updated {site.path:<{width}}  {current} -> {version}")

    print()
    if not drifted:
        print(f"All {len(SITES)} sites state {version}.")
        return 0

    if check_only:
        print(
            f"::error::{len(drifted)} of {len(SITES)} sites disagree with VERSION ({version}). "
            "Run `make version-sync` and commit the result."
        )
        return 1

    print(f"Updated {len(drifted)} of {len(SITES)} sites to {version}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero instead of rewriting (what CI runs)",
    )
    args = parser.parse_args()
    return run(check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
