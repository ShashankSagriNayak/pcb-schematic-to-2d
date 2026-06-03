"""
placer.py
Places components on a grid within the board boundaries.
Returns a dict mapping component_id -> (x, y) position in mm.
"""

from __future__ import annotations
import math
from typing import NamedTuple
from src.parser import Circuit, Component


class Position(NamedTuple):
    x: float   # mm from left edge
    y: float   # mm from top edge


# Approximate bounding box for each component type (width x height in mm)
COMPONENT_SIZE: dict[str, tuple[float, float]] = {
    "resistor":  (10.0, 5.0),
    "capacitor": (6.0,  8.0),
    "ic":        (18.0, 14.0),
    "led":       (5.0,  5.0),
    "connector": (12.0, 8.0),
}

MARGIN_MM = 8.0     # board edge margin
GAP_MM    = 6.0     # gap between components


def place_components(circuit: Circuit) -> dict[str, Position]:
    """
    Arrange components left-to-right, top-to-bottom on a grid.
    Returns {component_id: Position(x, y)} where x,y is top-left corner.
    """
    board_w = circuit.board.width_mm
    board_h = circuit.board.height_mm

    positions: dict[str, Position] = {}
    cursor_x = MARGIN_MM
    cursor_y = MARGIN_MM
    row_height = 0.0

    for comp in circuit.components:
        w, h = COMPONENT_SIZE.get(comp.type, (10.0, 8.0))

        # wrap to next row if component doesn't fit
        if cursor_x + w > board_w - MARGIN_MM:
            cursor_x = MARGIN_MM
            cursor_y += row_height + GAP_MM
            row_height = 0.0

        # if we've run off the bottom, just stack (won't happen with 5-10 components)
        if cursor_y + h > board_h - MARGIN_MM:
            cursor_y = MARGIN_MM  # reset — rare edge case

        positions[comp.id] = Position(x=cursor_x, y=cursor_y)
        cursor_x += w + GAP_MM
        row_height = max(row_height, h)

    return positions


def get_pin_position(
    comp: Component,
    pin_name: str,
    positions: dict[str, Position],
) -> tuple[float, float]:
    """
    Return the (x, y) centre coordinate of a specific pin in mm.
    Pins are evenly distributed along the bottom edge of the component.
    """
    pos = positions[comp.id]
    w, h = COMPONENT_SIZE.get(comp.type, (10.0, 8.0))

    pins = comp.pins
    if pin_name not in pins:
        # default to component centre if pin not found
        return (pos.x + w / 2, pos.y + h / 2)

    idx = pins.index(pin_name)
    n = len(pins)

    if comp.type == "ic":
        # ICs: left-side pins on left edge, right-side pins on right edge
        half = math.ceil(n / 2)
        if idx < half:
            px = pos.x
            py = pos.y + (idx + 1) * h / (half + 1)
        else:
            px = pos.x + w
            py = pos.y + (idx - half + 1) * h / (half + 1)
    else:
        # All other types: pins along the bottom edge
        spacing = w / (n + 1)
        px = pos.x + spacing * (idx + 1)
        py = pos.y + h

    return (px, py)
