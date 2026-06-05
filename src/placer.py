"""
placer.py
Places components on a grid within the board boundaries.
Supports optional component rotation (0 or 90 degrees).
Returns a dict mapping component_id -> Position.
"""

from __future__ import annotations
import math
from typing import NamedTuple
from src.parser import Circuit, Component


class Position(NamedTuple):
    x: float        # mm from left edge
    y: float        # mm from top edge
    rotation: int   # 0 or 90 degrees


# Base bounding box per component type (width x height in mm) at 0 degrees
COMPONENT_SIZE: dict[str, tuple[float, float]] = {
    "resistor":  (10.0, 5.0),
    "capacitor": (6.0,  8.0),
    "ic":        (18.0, 14.0),
    "led":       (5.0,  5.0),
    "connector": (12.0, 8.0),
}

MARGIN_MM = 8.0
GAP_MM    = 6.0


def get_effective_size(comp: Component) -> tuple[float, float]:
    """
    Return (width, height) accounting for rotation.
    A 90-degree rotation swaps width and height.
    """
    w, h = COMPONENT_SIZE.get(comp.type, (10.0, 8.0))
    rotation = getattr(comp, "rotation", 0)
    if rotation == 90:
        return h, w   # swap dimensions when rotated
    return w, h


def place_components(circuit: Circuit) -> dict[str, Position]:
    """
    Arrange components left-to-right, top-to-bottom on a grid.
    Respects per-component rotation from the JSON.
    Returns {component_id: Position(x, y, rotation)}.
    """
    board_w = circuit.board.width_mm
    board_h = circuit.board.height_mm

    positions: dict[str, Position] = {}
    cursor_x = MARGIN_MM
    cursor_y = MARGIN_MM
    row_height = 0.0

    for comp in circuit.components:
        w, h = get_effective_size(comp)
        rotation = getattr(comp, "rotation", 0)

        # wrap to next row if component doesn't fit horizontally
        if cursor_x + w > board_w - MARGIN_MM:
            cursor_x = MARGIN_MM
            cursor_y += row_height + GAP_MM
            row_height = 0.0

        # safety reset if we go off the bottom
        if cursor_y + h > board_h - MARGIN_MM:
            cursor_y = MARGIN_MM

        positions[comp.id] = Position(x=cursor_x, y=cursor_y, rotation=rotation)
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
    Accounts for component rotation.
    """
    pos = positions[comp.id]
    w, h = get_effective_size(comp)
    pins = comp.pins

    if pin_name not in pins:
        return (pos.x + w / 2, pos.y + h / 2)

    idx = pins.index(pin_name)
    n = len(pins)

    if comp.type == "ic":
        half = math.ceil(n / 2)
        if idx < half:
            px = pos.x
            py = pos.y + (idx + 1) * h / (half + 1)
        else:
            px = pos.x + w
            py = pos.y + (idx - half + 1) * h / (n - half + 1)
    else:
        spacing = w / (n + 1)
        px = pos.x + spacing * (idx + 1)
        py = pos.y + h

    return (px, py)