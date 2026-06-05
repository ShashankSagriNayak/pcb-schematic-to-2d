"""
renderer.py
Renders placed components and routed traces to an SVG file.
Supports component rotation (0 or 90 degrees).
1mm = 4px scale factor.
"""

from __future__ import annotations
import svgwrite
from svgwrite.container import Group
from src.parser import Circuit, Component
from src.placer import Position, COMPONENT_SIZE, get_effective_size
from src.router import Trace

SCALE = 4.0
STROKE_W = 0.8
TRACE_W  = 1.4
FONT     = "monospace"


def mm(val: float) -> float:
    """Convert mm to px."""
    return val * SCALE


def render_svg(
    circuit: Circuit,
    positions: dict[str, Position],
    traces: list[Trace],
    output_path: str,
) -> None:
    """Write the complete PCB 2D drawing to an SVG file."""
    bw = mm(circuit.board.width_mm)
    bh = mm(circuit.board.height_mm)

    dwg = svgwrite.Drawing(
        filename=output_path,
        size=(f"{bw}px", f"{bh}px"),
        viewBox=f"0 0 {bw} {bh}",
    )

    # background + board outline
    dwg.add(dwg.rect(insert=(0, 0), size=(bw, bh), fill="#1a1a2e"))
    dwg.add(dwg.rect(
        insert=(mm(2), mm(2)),
        size=(bw - mm(4), bh - mm(4)),
        fill="none", stroke="#4CAF50",
        stroke_width=1.5, stroke_dasharray="6,3",
    ))

    # board title
    dwg.add(dwg.text(
        circuit.board.title,
        insert=(mm(3), mm(5.5)),
        fill="#90CAF9", font_size="9px",
        font_family=FONT, font_weight="bold",
    ))

    # corner mounting holes
    for cx, cy in [
        (6, 6),
        (circuit.board.width_mm - 6, 6),
        (6, circuit.board.height_mm - 6),
        (circuit.board.width_mm - 6, circuit.board.height_mm - 6),
    ]:
        dwg.add(dwg.circle(center=(mm(cx), mm(cy)), r=mm(1.6),
                           fill="none", stroke="#78909C", stroke_width=1))
        dwg.add(dwg.circle(center=(mm(cx), mm(cy)), r=mm(0.6), fill="#546E7A"))

    # traces — drawn under components
    for trace in traces:
        pts = trace.points
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            dwg.add(dwg.line(
                start=(mm(x1), mm(y1)), end=(mm(x2), mm(y2)),
                stroke=trace.color, stroke_width=TRACE_W, stroke_opacity=0.8,
            ))
        # pin dots at start and end only
        dwg.add(dwg.circle(center=(mm(pts[0][0]),  mm(pts[0][1])),  r=1.8,
                           fill=trace.color, opacity=0.9))
        dwg.add(dwg.circle(center=(mm(pts[-1][0]), mm(pts[-1][1])), r=1.8,
                           fill=trace.color, opacity=0.9))

    # components
    for comp in circuit.components:
        pos = positions.get(comp.id)
        if pos is None:
            continue
        g = _draw_component(dwg, comp, pos)
        dwg.add(g)

    # net legend
    _draw_legend(dwg, circuit, bw, bh)

    dwg.save()
    print(f"  [ok] saved → {output_path}")


def _draw_component(dwg: svgwrite.Drawing, comp: Component, pos: Position) -> Group:
    """Draw a single component, applying rotation transform if needed."""
    g = dwg.g(id=comp.id)
    w, h = get_effective_size(comp)
    x, y = mm(pos.x), mm(pos.y)
    W, H = mm(w), mm(h)

    # inner group — draw at origin, then rotate + translate
    inner = dwg.g()
    base_w, base_h = COMPONENT_SIZE.get(comp.type, (10.0, 8.0))
    BW, BH = mm(base_w), mm(base_h)

    if comp.type == "resistor":
        inner = _draw_resistor(dwg, inner, 0, 0, BW, BH)
    elif comp.type == "capacitor":
        inner = _draw_capacitor(dwg, inner, 0, 0, BW, BH)
    elif comp.type == "ic":
        inner = _draw_ic(dwg, inner, 0, 0, BW, BH, comp)
    elif comp.type == "led":
        inner = _draw_led(dwg, inner, 0, 0, BW, BH)
    elif comp.type == "connector":
        inner = _draw_connector(dwg, inner, 0, 0, BW, BH, comp)

    if pos.rotation == 90:
        # rotate 90° clockwise around component centre, then translate
        cx, cy = BW / 2, BH / 2
        inner["transform"] = (
            f"translate({x + H/2 - cx},{y + W/2 - cy}) "
            f"rotate(90,{cx},{cy})"
        )
    else:
        inner["transform"] = f"translate({x},{y})"

    g.add(inner)

    # labels always horizontal, outside the rotated block
    g.add(dwg.text(comp.id,
        insert=(x + W / 2, y - 3),
        fill="#E0E0E0", font_size="7px",
        font_family=FONT, text_anchor="middle",
    ))
    g.add(dwg.text(comp.value,
        insert=(x + W / 2, y + H + 7),
        fill="#BDBDBD", font_size="6px",
        font_family=FONT, text_anchor="middle",
    ))
    return g


def _draw_resistor(dwg, g, x, y, W, H):
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#FFF176", stroke="#F9A825",
                   stroke_width=STROKE_W, rx=2))
    mid_y = y + H / 2
    g.add(dwg.line(start=(x + W * 0.15, mid_y), end=(x + W * 0.85, mid_y),
                   stroke="#F9A825", stroke_width=0.6))
    return g


def _draw_capacitor(dwg, g, x, y, W, H):
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#B3E5FC", stroke="#0288D1",
                   stroke_width=STROKE_W, rx=2))
    mid_x = x + W / 2
    g.add(dwg.line(start=(mid_x - 2, y + 3), end=(mid_x - 2, y + H - 3),
                   stroke="#0288D1", stroke_width=1.5))
    g.add(dwg.line(start=(mid_x + 2, y + 3), end=(mid_x + 2, y + H - 3),
                   stroke="#0288D1", stroke_width=1.5))
    return g


def _draw_ic(dwg, g, x, y, W, H, comp: Component):
    import math
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#212121", stroke="#78909C",
                   stroke_width=STROKE_W, rx=3))
    g.add(dwg.circle(center=(x + 4, y + 4), r=1.5,
                     fill="none", stroke="#78909C", stroke_width=0.7))
    g.add(dwg.text(comp.value[:8],
        insert=(x + W / 2, y + H / 2 + 3),
        fill="#90CAF9", font_size="6px",
        font_family=FONT, text_anchor="middle",
    ))
    n = len(comp.pins)
    half = math.ceil(n / 2)
    for i in range(half):
        py = y + (i + 1) * H / (half + 1)
        g.add(dwg.line(start=(x - 4, py), end=(x, py),
                       stroke="#B0BEC5", stroke_width=0.8))
    for i in range(n - half):
        py = y + (i + 1) * H / (n - half + 1)
        g.add(dwg.line(start=(x + W, py), end=(x + W + 4, py),
                       stroke="#B0BEC5", stroke_width=0.8))
    return g


def _draw_led(dwg, g, x, y, W, H):
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#FF8A65", stroke="#E64A19",
                   stroke_width=STROKE_W, rx=W / 2))
    g.add(dwg.circle(center=(x + W / 2, y + H / 2), r=1.5, fill="#FFCCBC"))
    return g


def _draw_connector(dwg, g, x, y, W, H, comp: Component):
    g.add(dwg.rect(insert=(x, y), size=(W, H),
                   fill="#37474F", stroke="#90A4AE",
                   stroke_width=STROKE_W, rx=2))
    n = len(comp.pins)
    if n > 0:
        pin_w = W / (n + 1)
        for i in range(n):
            px = x + pin_w * (i + 1) - 2
            g.add(dwg.rect(insert=(px, y + H * 0.2), size=(4, H * 0.6),
                           fill="#B0BEC5", rx=1))
    return g


def _draw_legend(dwg: svgwrite.Drawing, circuit: Circuit, bw: float, bh: float) -> None:
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


# ---------------------------------------------------------------------------
# PNG / PDF renderer — draws directly with matplotlib, identical to SVG output
# ---------------------------------------------------------------------------

def render_png(
    circuit: Circuit,
    positions: dict[str, Position],
    traces: list[Trace],
    output_path: str,
    dpi: int = 150,
) -> None:
    """
    Render the PCB drawing directly to PNG or PDF using matplotlib.
    Produces output identical to the SVG — no SVG-to-image conversion needed.
    Works on Windows without any system-level Cairo installation.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, Circle, FancyArrow
    from matplotlib.lines import Line2D

    BG   = "#1a1a2e"
    bw   = circuit.board.width_mm
    bh   = circuit.board.height_mm

    fig, ax = plt.subplots(figsize=(bw / 25.4 * 2.5, bh / 25.4 * 2.5), dpi=dpi)
    ax.set_xlim(0, bw)
    ax.set_ylim(bh, 0)      # flip Y to match SVG (0,0 = top-left)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # board outline (dashed green border)
    border = FancyBboxPatch(
        (2, 2), bw - 4, bh - 4,
        boxstyle="square,pad=0",
        facecolor="none", edgecolor="#4CAF50",
        linewidth=1.5, linestyle=(0, (6, 3)), zorder=1,
    )
    ax.add_patch(border)

    # board title
    ax.text(3, 5.5, circuit.board.title,
            color="#90CAF9", fontsize=7, fontfamily="monospace",
            fontweight="bold", va="top", zorder=5)

    # corner mounting holes
    for cx, cy in [(6, 6), (bw - 6, 6), (6, bh - 6), (bw - 6, bh - 6)]:
        ax.add_patch(Circle((cx, cy), 1.6, facecolor="none",
                            edgecolor="#78909C", linewidth=0.8, zorder=2))
        ax.add_patch(Circle((cx, cy), 0.6, facecolor="#546E7A", zorder=2))

    # traces
    for trace in traces:
        pts = trace.points
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            ax.plot([x1, x2], [y1, y2],
                    color=trace.color, linewidth=1.2,
                    alpha=0.8, solid_capstyle="round", zorder=3)
        ax.add_patch(Circle(pts[0],  0.9, facecolor=trace.color, zorder=4))
        ax.add_patch(Circle(pts[-1], 0.9, facecolor=trace.color, zorder=4))

    # components
    comp_lookup = {c.id: c for c in circuit.components}
    for comp in circuit.components:
        pos = positions.get(comp.id)
        if pos is None:
            continue
        _mpl_draw_component(ax, comp, pos)

    # net legend
    _mpl_draw_legend(ax, circuit, bw, bh)

    fmt = "pdf" if output_path.endswith(".pdf") else "png"
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight",
                facecolor=BG, format=fmt)
    plt.close(fig)
    print(f"  [ok] {'PDF' if fmt == 'pdf' else 'PNG'} saved → {output_path}")


def _mpl_draw_component(ax, comp: Component, pos: Position) -> None:
    """Draw one component onto a matplotlib axes."""
    from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
    from src.placer import get_effective_size

    w, h = get_effective_size(comp)
    x, y = pos.x, pos.y

    COLORS = {
        "resistor":  ("#FFF176", "#F9A825"),
        "capacitor": ("#B3E5FC", "#0288D1"),
        "ic":        ("#212121", "#78909C"),
        "led":       ("#FF8A65", "#E64A19"),
        "connector": ("#37474F", "#90A4AE"),
    }
    face, edge = COLORS.get(comp.type, ("#444", "#888"))

    # component body
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3",
        facecolor=face, edgecolor=edge,
        linewidth=0.8, zorder=5,
    ))

    # type-specific interior details
    if comp.type == "resistor":
        mid_y = y + h / 2
        ax.plot([x + w * 0.15, x + w * 0.85], [mid_y, mid_y],
                color="#F9A825", linewidth=0.5, zorder=6)

    elif comp.type == "capacitor":
        mid_x = x + w / 2
        ax.plot([mid_x - 0.5, mid_x - 0.5], [y + 1, y + h - 1],
                color="#0288D1", linewidth=1.2, zorder=6)
        ax.plot([mid_x + 0.5, mid_x + 0.5], [y + 1, y + h - 1],
                color="#0288D1", linewidth=1.2, zorder=6)

    elif comp.type == "ic":
        # pin 1 dot
        ax.add_patch(Circle((x + 1.5, y + 1.5), 0.5,
                            facecolor="none", edgecolor="#78909C",
                            linewidth=0.5, zorder=6))
        # chip name
        ax.text(x + w / 2, y + h / 2, comp.value[:8],
                color="#90CAF9", fontsize=4.5, fontfamily="monospace",
                ha="center", va="center", zorder=6)
        # pin stubs
        import math
        n    = len(comp.pins)
        half = math.ceil(n / 2)
        for i in range(half):
            py = y + (i + 1) * h / (half + 1)
            ax.plot([x - 1.5, x], [py, py],
                    color="#B0BEC5", linewidth=0.7, zorder=6)
        for i in range(n - half):
            py = y + (i + 1) * h / (n - half + 1)
            ax.plot([x + w, x + w + 1.5], [py, py],
                    color="#B0BEC5", linewidth=0.7, zorder=6)

    elif comp.type == "led":
        ax.add_patch(Circle((x + w / 2, y + h / 2), 0.8,
                            facecolor="#FFCCBC", zorder=6))

    elif comp.type == "connector":
        n = len(comp.pins)
        if n > 0:
            pin_w = w / (n + 1)
            for i in range(n):
                px = x + pin_w * (i + 1) - 0.5
                ax.add_patch(Rectangle(
                    (px, y + h * 0.2), 1.0, h * 0.6,
                    facecolor="#B0BEC5", zorder=6,
                ))

    # labels
    ax.text(x + w / 2, y - 1.5, comp.id,
            color="#E0E0E0", fontsize=4.5, fontfamily="monospace",
            ha="center", va="bottom", zorder=7)
    ax.text(x + w / 2, y + h + 1.5, comp.value,
            color="#BDBDBD", fontsize=4.0, fontfamily="monospace",
            ha="center", va="top", zorder=7)


def _mpl_draw_legend(ax, circuit, bw: float, bh: float) -> None:
    """Draw net color legend in bottom-right corner."""
    from src.router import NET_COLORS
    nets = circuit.nets
    if not nets:
        return
    lx = bw - 22
    ly = bh - 4 - len(nets) * 3.5
    ax.text(lx, ly - 1.5, "nets",
            color="#90CAF9", fontsize=4, fontfamily="monospace", va="top")
    for i, net in enumerate(nets):
        color = NET_COLORS[i % len(NET_COLORS)]
        row_y = ly + i * 3.5
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((lx, row_y), 2.5, 1.8,
                               facecolor=color, alpha=0.9))
        ax.text(lx + 3.2, row_y + 0.9, net.name[:14],
                color="#E0E0E0", fontsize=3.5,
                fontfamily="monospace", va="center")