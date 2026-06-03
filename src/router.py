"""
router.py
Routes traces between connected pins for each net.
Returns a list of Trace objects (straight-line segments between pin pairs).
"""

from __future__ import annotations
from dataclasses import dataclass
from src.parser import Circuit, Net
from src.placer import Position, get_pin_position


# Assign a distinct color to each net for visual clarity
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
    points: list[tuple[float, float]]   # list of (x, y) in mm — straight line segments


def route_nets(
    circuit: Circuit,
    positions: dict[str, Position],
) -> list[Trace]:
    """
    For each net, draw a direct trace from each connected pin to the next.
    Uses a simple star topology: first pin is the hub, others connect to it.
    Returns a list of Trace objects.
    """
    # build a lookup: component_id -> Component
    comp_lookup = {c.id: c for c in circuit.components}
    traces: list[Trace] = []

    for net_idx, net in enumerate(circuit.nets):
        color = NET_COLORS[net_idx % len(NET_COLORS)]

        # resolve all pin positions for this net
        pin_coords: list[tuple[float, float]] = []
        for comp_id, pin_name in net.connections:
            comp = comp_lookup.get(comp_id)
            if comp is None:
                print(f"  [warning] Net '{net.name}' references unknown component '{comp_id}' — skipping")
                continue
            xy = get_pin_position(comp, pin_name, positions)
            pin_coords.append(xy)

        if len(pin_coords) < 2:
            continue  # nothing to connect

        # star topology: connect every pin back to the first pin
        hub = pin_coords[0]
        for spoke in pin_coords[1:]:
            traces.append(Trace(
                net_name=net.name,
                color=color,
                points=[hub, spoke],
            ))

    return traces
