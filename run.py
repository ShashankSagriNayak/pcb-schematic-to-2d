"""
run.py
Main entry point for the PCB schematic to 2D drawing tool.

Usage:
  python run.py --input examples/led_blink.json
  python run.py --input examples/led_blink.json --output output/led_blink.svg
  python run.py --input examples/led_blink.json --format png
  python run.py --input examples/led_blink.json --format pdf
  python run.py --input examples/led_blink.json --drc
  python run.py --text "a 555 timer with two resistors, a capacitor and an LED"
  python run.py --all-examples
  python run.py --all-examples --format png --drc
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import parse_json, Circuit, Board, Component, Net
from src.placer import place_components
from src.router import route_nets
from src.renderer import render_svg, render_png
from src.drc import run_drc, print_report


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


def run_from_text(
    description: str,
    output_path: str,
    fmt: str = "svg",
    run_drc_check: bool = False,
) -> None:
    """
    AI-assisted mode: convert plain-English description to JSON via Claude,
    then run the standard offline pipeline on the result.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    from src.llm_input import text_to_json, save_json
    from src.parser import SUPPORTED_TYPES
    import math

    print(f"\n[1/4] AI input  '{description[:60]}...' " if len(description) > 60
          else f"\n[1/4] AI input  '{description}'")

    # --- AI step: text → JSON ---
    data = text_to_json(description)

    # save generated JSON for inspection
    json_path = output_path.replace(".svg", "_generated.json")
    save_json(data, json_path)

    # --- parse AI output into Circuit model ---
    print(f"[2/4] parsing   generated JSON")
    b = data.get("board", {})
    board = Board(
        width_mm=float(b.get("width_mm", 80)),
        height_mm=float(b.get("height_mm", 55)),
        title=str(b.get("title", "Generated Circuit")),
    )
    components = []
    for c in data.get("components", []):
        if c.get("type", "").lower() in SUPPORTED_TYPES:
            components.append(Component(
                id=str(c["id"]),
                type=str(c["type"]).lower(),
                value=str(c.get("value", "")),
                pins=[str(p) for p in c.get("pins", [])],
                rotation=int(c.get("rotation", 0)),
            ))
    nets = [
        Net(
            name=str(n["name"]),
            connections=[(str(cn[0]), str(cn[1])) for cn in n.get("connections", [])],
        )
        for n in data.get("nets", [])
    ]
    circuit = Circuit(board=board, components=components, nets=nets)

    print(f"[3/4] placing   {len(circuit.components)} components")
    print(f"[4/4] rendering → {output_path}")
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
    group.add_argument("--input",        metavar="JSON",
                       help="path to a circuit JSON file (offline)")
    group.add_argument("--text",         metavar="DESCRIPTION",
                       help="plain-English circuit description — uses Claude API "
                            "(set ANTHROPIC_API_KEY)")
    group.add_argument("--all-examples", action="store_true",
                       help="run all JSON files in examples/ and save to output/")

    parser.add_argument("--output", metavar="PATH",
                        default="output/circuit.svg",
                        help="output SVG path (default: output/circuit.svg)")
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
    elif args.text:
        run_from_text(
            args.text, args.output,
            fmt=args.format, run_drc_check=args.drc,
        )


if __name__ == "__main__":
    main()