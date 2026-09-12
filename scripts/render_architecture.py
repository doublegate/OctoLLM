#!/usr/bin/env python3
"""
Render the OctoLLM architecture diagram to SVG, in light and dark variants.

Why this is not a Mermaid block
-------------------------------
The architecture's whole point is that the eight arms form a *ring* and talk to
each other without the head. Mermaid cannot draw that. Radial and circular layout
has been an open request since 2019 (mermaid-js/mermaid#938, #2130, #3228), and
its dagre engine routes every edge independently between node borders, so eight
arms "in a ring" come out as eight unrelated splines at inconsistent angles —
measured across six attempts here, including every `curve:` value.

ELK routes far better and supports `nodePlacementAlignment: BALANCED`, which
would fix it — but ELK is not bundled in GitHub's Markdown renderer. Since
Mermaid v11 the minified build excludes it and it must be installed as
`@mermaid-js/layout-elk`; enabling it on GitHub is still an open community
request. A README that requires it would simply fail to render.

So the diagram is computed: the eight arms are placed at eight evenly spaced
points on one real ellipse, and that same ellipse is stroked underneath them.
The ring is therefore a single continuous curve the boxes sit on, rather than
eight connectors pretending to be one.

This is a generator rather than a checked-in blob so the diagram stays editable,
reviewable as a diff, and reproducible: `make diagram` regenerates both files.

Usage:
    python scripts/render_architecture.py            # write both SVGs
    python scripts/render_architecture.py --check    # fail if they are stale
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs" / "images"

W, H = 1480, 1060

# The ring. Everything about the eight arms derives from this one ellipse.
CX, CY = 700.0, 640.0
RX, RY = 370.0, 290.0

# The arms sit at HALF-STEP offsets, so the ellipse's top, right, bottom and
# left are gaps between arms rather than arms themselves. Those four gaps are
# the channels the tentacles, the response and the reflex bypass pass through,
# which is what keeps edges from colliding with boxes.
ARM_ANGLE_OFFSET_DEG = -112.5

HEAD_XY = (700.0, 152.0)
REFLEX_XY = (210.0, 152.0)
CLIENT_XY = (210.0, 42.0)
RESPONSE_XY = (1300.0, 640.0)


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    ink: str
    muted: str
    ring_fill: str
    ring_stroke: str
    ring_label: str
    head_fill: str
    head_stroke: str
    head_ink: str
    live_fill: str
    live_stroke: str
    live_ink: str
    stub_fill: str
    stub_stroke: str
    stub_ink: str
    todo_fill: str
    todo_stroke: str
    todo_ink: str
    io_fill: str
    io_stroke: str
    tentacle: str
    flow: str


LIGHT = Palette(
    name="light",
    bg="#ffffff",
    ink="#1c2530",
    muted="#5b6b7c",
    ring_fill="#e8f3fd",
    ring_stroke="#7fb5e6",
    ring_label="#1b5a96",
    head_fill="#f8d2d2",
    head_stroke="#d4696c",
    head_ink="#8e2225",
    live_fill="#d3ecd5",
    live_stroke="#5fa968",
    live_ink="#1d5426",
    stub_fill="#e0d6d1",
    stub_stroke="#a58c80",
    stub_ink="#4d352b",
    todo_fill="#ffffff",
    todo_stroke="#93a7b8",
    todo_ink="#31414f",
    io_fill="#f4f6f8",
    io_stroke="#9aa8b5",
    tentacle="#c2536a",
    flow="#2f3e4d",
)

DARK = Palette(
    name="dark",
    bg="#0d1117",
    ink="#e6edf3",
    muted="#9aa7b4",
    ring_fill="#132635",
    ring_stroke="#3e7ca8",
    ring_label="#7cc0f0",
    head_fill="#4a1f24",
    head_stroke="#c96b70",
    head_ink="#ffc9cc",
    live_fill="#17351f",
    live_stroke="#5da368",
    live_ink="#bfe6c4",
    stub_fill="#33271f",
    stub_stroke="#a0836f",
    stub_ink="#e2cdbd",
    todo_fill="#161d26",
    todo_stroke="#5a6c7d",
    todo_ink="#c3d0dc",
    io_fill="#171d25",
    io_stroke="#5f6d7b",
    tentacle="#a8465c",
    flow="#93a6b8",
)


@dataclass(frozen=True)
class Arm:
    key: str
    name: str
    port: str
    role: str
    state: str  # "stub" | "todo"


# Ring order is the real peer topology, not the port order. Going clockwise from
# the top: Memory feeds the Planner, the Planner drives the Executor, Red Team
# delegates its probing to that same sandbox, its output is screened by the
# Guardian; and up the other side the Guardian sits beside the Judge, the Judge
# and Coder are the validation loop, the Retriever feeds the Coder, and Memory is
# the Retriever's corpus. Every adjacency in the drawing is an edge in the design.
ARMS: tuple[Arm, ...] = (
    Arm("MEM", "Memory / Curator", "8007", "episodic + semantic", "todo"),
    Arm("PLAN", "Planner", "8001", "decomposition", "todo"),
    Arm("EXEC", "Executor", "8006", "sandboxed", "stub"),
    Arm("RED", "Red Team", "8008", "external targets", "todo"),
    Arm("SAFE", "Safety Guardian", "8005", "egress gate", "todo"),
    Arm("JUDGE", "Judge", "8004", "validate · score", "todo"),
    Arm("CODE", "Coder", "8003", "generate · refactor", "todo"),
    Arm("RETR", "Retriever", "8002", "rank + fuse", "todo"),
)

ARM_W, ARM_H = 186.0, 64.0
FONT = "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def arm_centre(index: int) -> tuple[float, float]:
    """The i-th arm's centre, on the ellipse, going clockwise from the upper left."""
    theta = math.radians(ARM_ANGLE_OFFSET_DEG + index * 45)
    return CX + RX * math.cos(theta), CY + RY * math.sin(theta)


def rounded_rect(
    x: float, y: float, w: float, h: float, r: float, fill: str, stroke: str, sw: float = 2.0
) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def text(
    x: float,
    y: float,
    s: str,
    *,
    fill: str,
    size: float = 13,
    weight: str = "400",
    anchor: str = "middle",
    family: str = FONT,
    style: str = "normal",
    spacing: str = "0",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
        f'letter-spacing="{spacing}" fill="{fill}">{esc(s)}</text>'
    )


def ellipse_point(theta: float) -> tuple[float, float]:
    return CX + RX * math.cos(theta), CY + RY * math.sin(theta)


def render(p: Palette) -> str:
    out: list[str] = []
    add = out.append

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="OctoLLM architecture: a reflex layer, '
        f'an orchestrator head, and eight arms arranged in a ring">'
    )
    add(f'<rect width="{W}" height="{H}" fill="{p.bg}"/>')

    # ---- arrow markers -----------------------------------------------------
    add("<defs>")
    for ident, colour in (("flow", p.flow), ("tentacle", p.tentacle)):
        add(
            f'<marker id="arrow-{ident}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{colour}"/></marker>'
        )
    add("</defs>")

    # ---- the ring: one real ellipse, drawn before the boxes that sit on it --
    add(
        f'<ellipse cx="{CX}" cy="{CY}" rx="{RX}" ry="{RY}" fill="{p.ring_fill}" '
        f'stroke="{p.ring_stroke}" stroke-width="3" stroke-opacity="0.55"/>'
    )
    add(
        f'<ellipse cx="{CX}" cy="{CY}" rx="{RX}" ry="{RY}" fill="none" '
        f'stroke="{p.ring_stroke}" stroke-width="11" stroke-opacity="0.95" '
        f'stroke-linecap="round"/>'
    )

    # Direction-of-travel ticks on the ring, midway between each pair of arms.
    for i in range(len(ARMS)):
        theta = math.radians(ARM_ANGLE_OFFSET_DEG + (i + 0.5) * 45)
        x, y = ellipse_point(theta)
        # Tangent of the ellipse at theta.
        tx, ty = -RX * math.sin(theta), RY * math.cos(theta)
        norm = math.hypot(tx, ty)
        tx, ty = tx / norm, ty / norm
        add(
            f'<path d="M {x - tx * 9:.1f} {y - ty * 9:.1f} L {x + tx * 9:.1f} {y + ty * 9:.1f}" '
            f'stroke="{p.bg}" stroke-width="4" stroke-linecap="round" opacity="0.85"/>'
        )

    add(
        text(
            CX,
            CY - 14,
            "THE EIGHT ARMS",
            fill=p.ring_label,
            size=19,
            weight="700",
            spacing="3.5",
        )
    )
    add(text(CX, CY + 10, "~350M neurons", fill=p.muted, size=13, style="italic"))
    add(
        text(
            CX,
            CY + 32,
            "each acts locally, and talks to its neighbours",
            fill=p.muted,
            size=12.5,
        )
    )
    add(text(CX, CY + 50, "without asking the head", fill=p.muted, size=12.5))

    # ---- tentacles: head to each arm ---------------------------------------
    hx, hy = HEAD_XY
    for i, arm in enumerate(ARMS):
        if arm.key == "SAFE":
            # The Guardian is an egress gate the answer passes through, not an
            # arm the head hands work to. Drawing a delegation edge to it would
            # assert a relationship the design does not have.
            continue
        ax, ay = arm_centre(i)
        # Splay the control points outward so the curves read as limbs rather
        # than as the shortest path between two rectangles.
        # Each tentacle leaves its own point along the head's underside, spread in
        # the same left-to-right order as the arms it reaches, so they splay like
        # limbs instead of radiating from one puncture point.
        spread = sorted(range(len(ARMS)), key=lambda j: arm_centre(j)[0])
        slot = spread.index(i)
        ox = hx - 150 + slot * (300 / (len(ARMS) - 2))
        # A simple splay from the head's underside. An earlier version routed each
        # tentacle around the outside of the rim to keep it off the ring's label;
        # that put eight near-parallel curves in the same channel and they crossed
        # each other. Legibility beats the one label overlap it avoided.
        mx, my = (ox + ax) / 2, (hy + ay) / 2
        bow = 1.0 if ax >= hx else -1.0
        c1x, c1y = ox + bow * 18, hy + 120
        c2x, c2y = mx + bow * 70, my + 40
        add(
            f'<path d="M {ox:.1f} {hy + 46:.1f} C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, '
            f'{ax:.1f} {ay:.1f}" fill="none" stroke="{p.tentacle}" stroke-width="2.2" '
            f'stroke-opacity="0.45" stroke-dasharray="8 7" stroke-linecap="round"/>'
        )

    # ---- the arms ----------------------------------------------------------
    for i, arm in enumerate(ARMS):
        x, y = arm_centre(i)
        fill, stroke, ink = {
            "stub": (p.stub_fill, p.stub_stroke, p.stub_ink),
            "todo": (p.todo_fill, p.todo_stroke, p.todo_ink),
        }[arm.state]
        add(
            f'<g><rect x="{x - ARM_W / 2:.1f}" y="{y - ARM_H / 2:.1f}" width="{ARM_W}" '
            f'height="{ARM_H}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        add(text(x, y - 12, arm.name, fill=ink, size=13.5, weight="700"))
        add(text(x, y + 6, f":{arm.port}", fill=p.muted, size=12, family=MONO))
        add(text(x, y + 23, arm.role, fill=p.muted, size=11.5))
        add("</g>")

    # ---- client -> reflex --------------------------------------------------
    cx_, cy_ = CLIENT_XY
    add(rounded_rect(cx_ - 90, cy_ - 20, 180, 40, 20, p.io_fill, p.io_stroke))
    add(text(cx_, cy_ + 5, "Client request", fill=p.ink, size=13.5, weight="600"))

    rx_, ry_ = REFLEX_XY
    add(
        f'<path d="M {cx_:.1f} {cy_ + 22:.1f} L {rx_:.1f} {ry_ - 54:.1f}" '
        f'stroke="{p.flow}" stroke-width="3" marker-end="url(#arrow-flow)"/>'
    )

    add(rounded_rect(rx_ - 150, ry_ - 52, 300, 104, 12, p.live_fill, p.live_stroke, 2.5))
    add(text(rx_, ry_ - 26, "REFLEX LAYER", fill=p.live_ink, size=15, weight="700", spacing="1.5"))
    add(text(rx_, ry_ - 7, ":8080 · Rust", fill=p.muted, size=12, family=MONO))
    add(
        text(
            rx_,
            ry_ + 13,
            "the reflex arc — no LLM in the path",
            fill=p.live_ink,
            size=11.5,
            style="italic",
        )
    )
    add(text(rx_, ry_ + 31, "PII · prompt injection · cache · rate limit", fill=p.muted, size=11))

    # ---- reflex -> head (escalate) ----------------------------------------
    add(
        f'<path d="M {rx_ + 152:.1f} {ry_:.1f} L {hx - 232:.1f} {hy:.1f}" '
        f'stroke="{p.flow}" stroke-width="3" marker-end="url(#arrow-flow)"/>'
    )
    # This label has to fit the gap between the reflex box and the head box; it is
    # deliberately two short lines rather than one long one that would run under
    # the head's left edge.
    mid = (rx_ + 152 + hx - 232) / 2
    add(text(mid, ry_ - 16, "novel or", fill=p.ink, size=11, weight="600"))
    add(text(mid, ry_ - 4, "complex", fill=p.ink, size=11, weight="600"))
    add(text(mid, ry_ + 22, "escalate", fill=p.muted, size=11, style="italic"))

    # ---- the head ----------------------------------------------------------
    add(rounded_rect(hx - 230, hy - 46, 460, 92, 14, p.head_fill, p.head_stroke, 3))
    add(
        text(
            hx,
            hy - 20,
            "ORCHESTRATOR — THE HEAD",
            fill=p.head_ink,
            size=16,
            weight="700",
            spacing="1.5",
        )
    )
    add(text(hx, hy - 1, ":8000 · ~40M neurons", fill=p.muted, size=12, family=MONO))
    add(
        text(
            hx,
            hy + 19,
            "plans and delegates, never executes",
            fill=p.head_ink,
            size=12,
            style="italic",
        )
    )
    add(text(hx, hy + 36, "sole signer of capability tokens", fill=p.muted, size=11.5))

    # ---- reflex bypass -> ring (dotted, design intent) ---------------------
    add(
        f'<path d="M {rx_:.1f} {ry_ + 54:.1f} C {rx_ - 20:.1f} {CY - 200:.1f}, '
        f'{CX - RX - 150:.1f} {CY - 120:.1f}, {CX - RX - 10:.1f} {CY:.1f}" '
        f'fill="none" stroke="{p.flow}" stroke-width="2.5" stroke-dasharray="3 7" '
        f'stroke-linecap="round" stroke-opacity="0.85" marker-end="url(#arrow-flow)"/>'
    )
    add(
        text(60, CY - 96, "cached / routine —", fill=p.ink, size=11.5, weight="600", anchor="start")
    )
    add(text(60, CY - 79, "the arms react", fill=p.muted, size=11.5, anchor="start"))
    add(text(60, CY - 62, "without the head", fill=p.muted, size=11.5, anchor="start"))

    # ---- ring -> response --------------------------------------------------
    resp_x, resp_y = RESPONSE_XY
    add(
        f'<path d="M {CX + RX + 10:.1f} {CY:.1f} L {resp_x - 96:.1f} {resp_y:.1f}" '
        f'stroke="{p.flow}" stroke-width="3" marker-end="url(#arrow-flow)"/>'
    )
    add(rounded_rect(resp_x - 92, resp_y - 34, 184, 68, 16, p.io_fill, p.io_stroke))
    add(text(resp_x, resp_y - 10, "Response", fill=p.ink, size=13.5, weight="700"))
    add(text(resp_x, resp_y + 9, "screened on the way", fill=p.muted, size=11))
    add(text(resp_x, resp_y + 24, "out by the Guardian", fill=p.muted, size=11))

    # ---- reflex cache-hit -> response (the shortest arc) -------------------
    # Crest above the head rather than across it: the head's top edge is at
    # hy - 46, so this arc is held clear of it for its whole span.
    add(
        f'<path d="M {rx_ + 152:.1f} {ry_ - 30:.1f} C {rx_ + 300:.1f} 0, '
        f'{resp_x + 300:.1f} 0, {resp_x:.1f} {resp_y - 38:.1f}" '
        f'fill="none" stroke="{p.flow}" stroke-width="2.5" stroke-dasharray="3 7" '
        f'stroke-linecap="round" stroke-opacity="0.85" marker-end="url(#arrow-flow)"/>'
    )
    add(text(resp_x - 120, 26, "cache hit — answered", fill=p.ink, size=11.5, weight="600"))
    add(text(resp_x - 120, 42, "without cognition", fill=p.muted, size=11.5))

    # ---- legend ------------------------------------------------------------
    ly = H - 46
    swatches = (
        ("the head", p.head_fill, p.head_stroke),
        ("implemented", p.live_fill, p.live_stroke),
        ("a 21-line stub", p.stub_fill, p.stub_stroke),
        ("not started", p.todo_fill, p.todo_stroke),
    )
    lx = 60.0
    for label, fill, stroke in swatches:
        add(rounded_rect(lx, ly - 11, 22, 15, 4, fill, stroke, 1.6))
        add(text(lx + 30, ly + 1, label, fill=p.muted, size=12, anchor="start"))
        lx += 34 + len(label) * 6.9 + 26

    add(
        text(
            W - 60,
            ly + 1,
            "solid = runs today   ·   dashed = designed, not yet built",
            fill=p.muted,
            size=12,
            anchor="end",
        )
    )

    add("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed SVGs differ from what this script renders",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stale: list[str] = []

    for palette in (LIGHT, DARK):
        path = OUT_DIR / f"architecture-{palette.name}.svg"
        rendered = render(palette)
        if args.check:
            current = path.read_text() if path.is_file() else ""
            if current != rendered:
                stale.append(str(path.relative_to(REPO_ROOT)))
            continue
        path.write_text(rendered)
        print(f"  wrote {path.relative_to(REPO_ROOT)}  ({len(rendered):,} bytes)")

    if args.check:
        if stale:
            print("::error::architecture SVGs are stale: " + ", ".join(stale))
            print("Run `make diagram` and commit the result.")
            return 1
        print("architecture SVGs are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
