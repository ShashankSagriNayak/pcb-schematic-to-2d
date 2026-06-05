"""
run.py
Main entry point for the PCB schematic to 2D drawing tool.

Usage:
  python run.py --input examples/led_blink.json
  python run.py --input examples/led_blink.json --output output/led_blink.svg
  python run.py --input examples/led_blink.json --format png
  python run.py --input examples/led_blink.json --format pdf
  python run.py --input examples/led_blink.json --drc
  python run.py --all-examples
  python run.py --all-examples --format png --drc
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import parse_json, Circuit
from src.placer import place_components
from src.router import route_nets
from src.renderer import render_svg, render_png
from src.drc import run_drc, print_report


def convert_svg(svg_path: str, fmt: str) -> None:
    """
    Convert an SVG to PNG or PDF.
    Uses matplotlib to re-render the circuit directly — no Cairo, no system
    dependencies. Works on Windows, Mac, and Linux out of the box.
    PNG/PDF are rendered by re-running the draw logic, not by converting SVG.
    """
    if fmt not in ("png", "pdf"):
        return

    out_path = svg_path.replace(".svg", f".{fmt}")

    try:
        import matplotlib
        matplotlib.use("Agg")   # non-interactive backend, safe on all platforms
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch, Circle
        import xml.etree.ElementTree as ET

        # parse SVG viewBox for correct figure size
        tree = ET.parse(svg_path)
        root = tree.getroot()
        vb = root.get("viewBox", "0 0 320 220").split()
        w_px, h_px = float(vb[2]), float(vb[3])

        # create figure with correct aspect ratio
        dpi = 150
        fig, ax = plt.subplots(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
        ax.set_xlim(0, w_px)
        ax.set_ylim(h_px, 0)   # invert y to match SVG coordinate system
        ax.set_aspect("equal")
        ax.axis("off")
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#1a1a2e")

        # draw board outline from SVG rect elements
        ns = "http://www.w3.org/2000/svg"
        for elem in root.iter(f"{{{ns}}}rect"):
            x = float(elem.get("x", 0))
            y = float(elem.get("y", 0))
            rw = float(elem.get("width", 0))
            rh = float(elem.get("height", 0))
            fill  = elem.get("fill", "none")
            stroke = elem.get("stroke", "none")
            sw = float(elem.get("stroke-width", 1))
            rx = float(elem.get("rx", 0))
            if fill == "none":
                fill_c = "none"
            else:
                fill_c = fill
            edgecolor = stroke if stroke != "none" else "none"
            style = "round,pad=0" if rx > 0 else "square,pad=0"
            rect = FancyBboxPatch(
                (x, y), rw, rh,
                boxstyle=style,
                facecolor=fill_c, edgecolor=edgecolor,
                linewidth=sw, zorder=1,
            )
            ax.add_patch(rect)

        # draw lines (traces + pin stubs)
        for elem in root.iter(f"{{{ns}}}line"):
            x1 = float(elem.get("x1", 0))
            y1 = float(elem.get("y1", 0))
            x2 = float(elem.get("x2", 0))
            y2 = float(elem.get("y2", 0))
            stroke = elem.get("stroke", "#ffffff")
            sw = float(elem.get("stroke-width", 1))
            alpha = float(elem.get("stroke-opacity", 1.0))
            ax.plot([x1, x2], [y1, y2],
                    color=stroke, linewidth=sw, alpha=alpha, zorder=2)

        # draw circles (pin dots + mounting holes)
        for elem in root.iter(f"{{{ns}}}circle"):
            cx = float(elem.get("cx", 0))
            cy = float(elem.get("cy", 0))
            r  = float(elem.get("r",  2))
            fill   = elem.get("fill",   "none")
            stroke = elem.get("stroke", "none")
            sw = float(elem.get("stroke-width", 1))
            circle = Circle(
                (cx, cy), r,
                facecolor=fill if fill != "none" else "none",
                edgecolor=stroke if stroke != "none" else "none",
                linewidth=sw, zorder=3,
            )
            ax.add_patch(circle)

        # draw text labels
        for elem in root.iter(f"{{{ns}}}text"):
            x    = float(elem.get("x", 0))
            y    = float(elem.get("y", 0))
            fill = elem.get("fill", "#ffffff")
            fs   = elem.get("font-size", "8px").replace("px", "")
            text = elem.text or ""
            anchor = elem.get("text-anchor", "start")
            ha = {"start": "left", "middle": "center", "end": "right"}.get(anchor, "left")
            ax.text(x, y, text, color=fill,
                    fontsize=float(fs) * 0.75,
                    ha=ha, va="top",
                    fontfamily="monospace", zorder=4)

        plt.tight_layout(pad=0)
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight",
                    facecolor="#1a1a2e", format=fmt)
        plt.close(fig)
        print(f"  [ok] {fmt.upper()} saved → {out_path}")

    except Exception as e:
        print(f"  [warning] Could not convert to {fmt.upper()}: {e}")
        print(f"            SVG output is still at: {svg_path}")


def run_pipeline(
    circuit: Circuit,
    output_path: str,
    fmt: str = "svg",
    run_drc_check: bool = False,
) -> None:
    """Full pipeline: place → route → render → (drc)."""
    t0 = time.time()

    positions = place_components(circuit)
    traces    = route_nets(circuit, positions)

    # always render SVG (source of truth)
    render_svg(circuit, positions, traces, output_path)

    # PNG/PDF: render directly with matplotlib — identical to SVG, no conversion
    if fmt == "png":
        png_path = output_path.replace(".svg", ".png")
        render_png(circuit, positions, traces, png_path)
    elif fmt == "pdf":
        pdf_path = output_path.replace(".svg", ".pdf")
        render_png(circuit, positions, traces, pdf_path)

    if run_drc_check:
        report = run_drc(circuit, positions, traces)
        print_report(report)

    print(f"  [done] {len(circuit.components)} components, "
          f"{len(traces)} traces — {time.time() - t0:.2f}s")


def run_from_json(
    input_path: str,
    output_path: str,
    fmt: str = "svg",
    run_drc_check: bool = False,
) -> None:
    print(f"\n[1/3] parsing   {input_path}")
    circuit = parse_json(input_path)
    print(f"[2/3] placing   {len(circuit.components)} components")
    print(f"[3/3] rendering → {output_path}")
    run_pipeline(circuit, output_path, fmt=fmt, run_drc_check=run_drc_check)


def run_all_examples(fmt: str = "svg", run_drc_check: bool = False) -> None:
    examples_dir = Path("examples")
    output_dir   = Path("output")
    output_dir.mkdir(exist_ok=True)

    for json_file in sorted(examples_dir.glob("*.json")):
        out = output_dir / (json_file.stem + ".svg")
        run_from_json(
            str(json_file), str(out),
            fmt=fmt, run_drc_check=run_drc_check,
        )

    print("\nAll examples done. Files are in output/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PCB Schematic to 2D Drawing — UST Internship Project 3"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input",       metavar="JSON",
                       help="path to a circuit JSON file")
    group.add_argument("--all-examples", action="store_true",
                       help="run all JSON files in examples/ and save to output/")

    parser.add_argument("--output", metavar="PATH",
                        default="output/circuit.svg",
                        help="output file path (default: output/circuit.svg)")

    parser.add_argument("--format", metavar="FMT",
                        choices=["svg", "png", "pdf"],
                        default="svg",
                        help="output format: svg (default), png, or pdf")

    parser.add_argument("--drc", action="store_true",
                        help="run Design Rule Check after rendering")

    args = parser.parse_args()
    Path("output").mkdir(exist_ok=True)

    if args.all_examples:
        run_all_examples(fmt=args.format, run_drc_check=args.drc)
    elif args.input:
        run_from_json(
            args.input, args.output,
            fmt=args.format, run_drc_check=args.drc,
        )


if __name__ == "__main__":
    main()