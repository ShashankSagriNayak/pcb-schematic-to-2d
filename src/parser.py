"""
parser.py
Reads a JSON circuit description and returns typed Component and Net objects.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_TYPES = {"resistor", "capacitor", "ic", "led", "connector"}


@dataclass
class Component:
    id: str              # reference designator e.g. "R1", "U1"
    type: str            # one of SUPPORTED_TYPES
    value: str           # e.g. "330R", "100nF", "ATmega328P"
    pins: list[str]      # list of pin names
    rotation: int = 0    # 0 or 90 degrees — optional in JSON


@dataclass
class Net:
    name: str
    connections: list[tuple[str, str]]   # [(component_id, pin_name), ...]


@dataclass
class Board:
    width_mm: float = 80.0
    height_mm: float = 55.0
    title: str = "PCB Layout"


@dataclass
class Circuit:
    board: Board
    components: list[Component]
    nets: list[Net]


def parse_json(path: str | Path) -> Circuit:
    """
    Load a circuit JSON file and return a Circuit object.
    Raises ValueError for missing required fields.
    Unknown component types are skipped with a warning.
    """
    raw: dict[str, Any] = json.loads(Path(path).read_text())

    # board
    b = raw.get("board", {})
    board = Board(
        width_mm=float(b.get("width_mm", 80)),
        height_mm=float(b.get("height_mm", 55)),
        title=str(b.get("title", "PCB Layout")),
    )

    # components
    components: list[Component] = []
    for c in raw.get("components", []):
        ctype = str(c["type"]).lower()
        if ctype not in SUPPORTED_TYPES:
            print(f"  [warning] Unknown type '{ctype}' for {c['id']} — skipping")
            continue
        rotation = int(c.get("rotation", 0))
        if rotation not in (0, 90):
            print(f"  [warning] rotation must be 0 or 90 for {c['id']} — defaulting to 0")
            rotation = 0
        components.append(Component(
            id=str(c["id"]),
            type=ctype,
            value=str(c.get("value", "")),
            pins=[str(p) for p in c.get("pins", [])],
            rotation=rotation,
        ))

    # nets
    nets: list[Net] = []
    for n in raw.get("nets", []):
        connections = [(str(conn[0]), str(conn[1])) for conn in n.get("connections", [])]
        nets.append(Net(name=str(n["name"]), connections=connections))

    return Circuit(board=board, components=components, nets=nets)