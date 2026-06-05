"""
router.py
Routes traces between connected pins for each net.
Uses Manhattan (L-shaped) routing: horizontal first, then vertical.
This avoids diagonal lines and looks much closer to a real PCB.
"""

from __future__ import annotations
from dataclasses import dataclass
from src.parser import Circuit, Net
from src.placer import Position, get_pin_position


# One distinct color per net
NET_COLORS = [
    "#1565C0",  # blue
    "#2E7D32",  # green
    "#C62828",  # red
    "#6A1B9A",  # purple
    "#E65100",  # orange
    "#00695C",  # teal
    "#4527A0",  # deep purple
    "#AD1457",  # pink
    "#558B2F",  # light green
    "#283593",  # indigo
]


@dataclass
class Trace:
    net_name: str
    color: str
    points: list[tuple[float, float]]   # (x, y) in mm — connected line segments


def _manhattan_points(
    x1: float, y1: float,
    x2: float, y2: float,
    bend: str = "h_first",
) -> list[tuple[float, float]]:
    """
    Return 3 points forming an L-shaped route between (x1,y1) and (x2,y2).
    bend='h_first' → go horizontal then vertical (default)
    bend='v_first' → go vertical then horizontal
    This gives traces a clean PCB-like appearance vs diagonal lines.
    """
    if bend == "h_first":
        mid = (x2, y1)   # corner: move horizontally first
    else:
        mid = (x1, y2)   # corner: move vertically first

    return [(x1, y1), mid, (x2, y2)]


def route_nets(
    circuit: Circuit,
    positions: dict[str, Position],
) -> list[Trace]:
    """
    For each net, route traces from the hub pin (first pin) to every
    other pin using Manhattan L-shaped segments.
    Alternates h_first / v_first per net to reduce visual overlap.
    Returns a list of Trace objects.
    """
    comp_lookup = {c.id: c for c in circuit.components}
    traces: list[Trace] = []

    for net_idx, net in enumerate(circuit.nets):
        color = NET_COLORS[net_idx % len(NET_COLORS)]
        # alternate bend direction per net to reduce overlap
        bend = "h_first" if net_idx % 2 == 0 else "v_first"

        # resolve all pin positions for this net
        pin_coords: list[tuple[float, float]] = []
        for comp_id, pin_name in net.connections:
            comp = comp_lookup.get(comp_id)
            if comp is None:
                print(f"  [warning] Net '{net.name}' references "
                      f"unknown component '{comp_id}' — skipping")
                continue
            xy = get_pin_position(comp, pin_name, positions)
            pin_coords.append(xy)

        if len(pin_coords) < 2:
            continue

        # star topology: every pin connects back to the hub (first pin)
        hub = pin_coords[0]
        for spoke in pin_coords[1:]:
            points = _manhattan_points(
                hub[0], hub[1],
                spoke[0], spoke[1],
                bend=bend,
            )
            traces.append(Trace(
                net_name=net.name,
                color=color,
                points=points,
            ))

    return traces