"""
renderer.py
Renders the placed components and routed traces to an SVG file.
Uses svgwrite. All coordinates are in px (1mm = 4px scale factor).
"""

from __future__ import annotations
import svgwrite
from svgwrite.container import Group
from src.parser import Circuit, Component
from src.placer import Position, COMPONENT_SIZE
from src.router import Trace

SCALE = 4.0          # px per mm
STROKE_W = 0.8       # component outline stroke width (px)
TRACE_W = 1.2        # trace stroke width (px)
FONT = "monospace"


def mm(val: float) -> float:
    """Convert mm to px."""
    return val * SCALE


def render_svg(
    circuit: Circuit,
    positions: dict[str, Position],
    traces: list[Trace],
    output_path: str,
) -> None:
    """
    Write the complete PCB 2D drawing to an SVG file.
    """
    bw = mm(circuit.board.width_mm)
    bh = mm(circuit.board.height_mm)

    dwg = svgwrite.Drawing(
        filename=output_path,
        size=(f"{bw}px", f"{bh}px"),
        viewBox=f"0 0 {bw} {bh}",
    )

    # --- background + board outline ---
    dwg.add(dwg.rect(insert=(0, 0), size=(bw, bh), fill="#1a1a2e"))
    dwg.add(dwg.rect(
        insert=(mm(2), mm(2)),
        size=(bw - mm(4), bh - mm(4)),
        fill="none",
        stroke="#4CAF50",
        stroke_width=1.5,
        stroke_dasharray="6,3",
    ))

    # board title
    dwg.add(dwg.text(
        circuit.board.title,
        insert=(mm(3), mm(5.5)),
        fill="#90CAF9",
        font_size="9px",
        font_family=FONT,
        font_weight="bold",
    ))

    # corner mounting holes
    for cx, cy in [(6, 6), (circuit.board.width_mm - 6, 6),
                   (6, circuit.board.height_mm - 6),
                   (circuit.board.width_mm - 6, circuit.board.height_mm - 6)]:
        dwg.add(dwg.circle(center=(mm(cx), mm(cy)), r=mm(1.6),
                            fill="none", stroke="#78909C", stroke_width=1))
        dwg.add(dwg.circle(center=(mm(cx), mm(cy)), r=mm(0.6),
                            fill="#546E7A"))

    # --- traces (drawn under components) ---
    for trace in traces:
        for i in range(len(trace.points) - 1):
            x1, y1 = trace.points[i]
            x2, y2 = trace.points[i + 1]
            dwg.add(dwg.line(
                start=(mm(x1), mm(y1)),
                end=(mm(x2), mm(y2)),
                stroke=trace.color,
                stroke_width=TRACE_W,
                stroke_opacity=0.75,
            ))
            # small dot at each pin endpoint
            dwg.add(dwg.circle(
                center=(mm(x1), mm(y1)), r=1.6,
                fill=trace.color, opacity=0.9,
            ))
            dwg.add(dwg.circle(
                center=(mm(x2), mm(y2)), r=1.6,
                fill=trace.color, opacity=0.9,
            ))

    # --- components ---
    comp_lookup = {c.id: c for c in circuit.components}
    for comp in circuit.components:
        pos = positions.get(comp.id)
        if pos is None:
            continue
        g = _draw_component(dwg, comp, pos)
        dwg.add(g)

    # --- net legend (bottom-right corner) ---
    _draw_legend(dwg, circuit, bw, bh)

    dwg.save()
    print(f"  [ok] saved → {output_path}")


def _draw_component(
    dwg: svgwrite.Drawing,
    comp: Component,
    pos: Position,
) -> Group:
    """Draw a single component symbol and return a Group."""
    g = dwg.g(id=comp.id)
    w, h = COMPONENT_SIZE.get(comp.type, (10.0, 8.0))
    x, y = mm(pos.x), mm(pos.y)
    W, H = mm(w), mm(h)

    if comp.type == "resistor":
        g = _draw_resistor(dwg, g, x, y, W, H)
    elif comp.type == "capacitor":
        g = _draw_capacitor(dwg, g, x, y, W, H)
    elif comp.type == "ic":
        g = _draw_ic(dwg, g, x, y, W, H, comp)
    elif comp.type == "led":
        g = _draw_led(dwg, g, x, y, W, H)
    elif comp.type == "connector":
        g = _draw_connector(dwg, g, x, y, W, H, comp)

    # reference designator label
    g.add(dwg.text(
        comp.id,
        insert=(x + W / 2, y - 3),
        fill="#E0E0E0",
        font_size="7px",
        font_family=FONT,
        text_anchor="middle",
    ))
    # value label
    g.add(dwg.text(
        comp.value,
        insert=(x + W / 2, y + H + 7),
        fill="#BDBDBD",
        font_size="6px",
        font_family=FONT,
        text_anchor="middle",
    ))
    return g


def _draw_resistor(dwg, g, x, y, W, H):
    # Rectangular body with zigzag suggestion
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#FFF176", stroke="#F9A825", stroke_width=STROKE_W, rx=2))
    # centre line
    mid_y = y + H / 2
    g.add(dwg.line(start=(x + W * 0.15, mid_y), end=(x + W * 0.85, mid_y),
                   stroke="#F9A825", stroke_width=0.6))
    return g


def _draw_capacitor(dwg, g, x, y, W, H):
    # Two vertical plates
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#B3E5FC", stroke="#0288D1", stroke_width=STROKE_W, rx=2))
    mid_x = x + W / 2
    g.add(dwg.line(start=(mid_x - 2, y + 3), end=(mid_x - 2, y + H - 3),
                   stroke="#0288D1", stroke_width=1.5))
    g.add(dwg.line(start=(mid_x + 2, y + 3), end=(mid_x + 2, y + H - 3),
                   stroke="#0288D1", stroke_width=1.5))
    return g


def _draw_ic(dwg, g, x, y, W, H, comp: Component):
    # Black IC body
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#212121", stroke="#78909C", stroke_width=STROKE_W, rx=3))
    # pin 1 notch (top-left)
    g.add(dwg.circle(center=(x + 4, y + 4), r=1.5,
                     fill="none", stroke="#78909C", stroke_width=0.7))
    # chip name inside
    g.add(dwg.text(
        comp.value[:8],   # truncate long names
        insert=(x + W / 2, y + H / 2 + 3),
        fill="#90CAF9",
        font_size="6px",
        font_family=FONT,
        text_anchor="middle",
    ))
    # draw pin stubs on left and right edges
    import math
    n = len(comp.pins)
    half = math.ceil(n / 2)
    for i in range(half):
        py = y + (i + 1) * H / (half + 1)
        # left pin stub
        g.add(dwg.line(start=(x - 4, py), end=(x, py),
                       stroke="#B0BEC5", stroke_width=0.8))
    for i in range(n - half):
        py = y + (i + 1) * H / (n - half + 1)
        # right pin stub
        g.add(dwg.line(start=(x + W, py), end=(x + W + 4, py),
                       stroke="#B0BEC5", stroke_width=0.8))
    return g


def _draw_led(dwg, g, x, y, W, H):
    # Triangle + bar (standard LED symbol shape approximated as rect with glow)
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#FF8A65", stroke="#E64A19", stroke_width=STROKE_W, rx=W / 2))
    # centre dot to suggest the die
    g.add(dwg.circle(center=(x + W / 2, y + H / 2), r=1.5,
                     fill="#FFCCBC"))
    return g


def _draw_connector(dwg, g, x, y, W, H, comp: Component):
    # Row of rectangular pins
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#37474F", stroke="#90A4AE", stroke_width=STROKE_W, rx=2))
    n = len(comp.pins)
    if n > 0:
        pin_w = W / (n + 1)
        for i in range(n):
            px = x + pin_w * (i + 1) - 2
            g.add(dwg.rect(insert=(px, y + H * 0.2), size=(4, H * 0.6),
                           fill="#B0BEC5", rx=1))
    return g


def _draw_legend(
    dwg: svgwrite.Drawing,
    circuit: Circuit,
    bw: float,
    bh: float,
) -> None:
    """Draw a small net color legend in the bottom-right corner."""
    from src.router import NET_COLORS
    nets = circuit.nets
    if not nets:
        return

    lx = bw - mm(22)
    ly = bh - mm(3) - len(nets) * 8 - 4
    dwg.add(dwg.text("nets", insert=(lx, ly - 2),
                     fill="#90CAF9", font_size="6px", font_family=FONT))

    for i, net in enumerate(nets):
        color = NET_COLORS[i % len(NET_COLORS)]
        row_y = ly + i * 8
        dwg.add(dwg.rect(insert=(lx, row_y), size=(8, 5),
                         fill=color, opacity=0.85, rx=1))
        dwg.add(dwg.text(net.name[:14], insert=(lx + 10, row_y + 5),
                         fill="#E0E0E0", font_size="5.5px", font_family=FONT))
