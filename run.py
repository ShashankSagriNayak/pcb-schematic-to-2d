"""
run.py
Main entry point for the PCB schematic to 2D drawing tool.

Usage:
  python run.py --input examples/led_blink.json --output output/led_blink.svg
  python run.py --text "a 555 timer circuit with two resistors and a capacitor"
  python run.py --all-examples
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

# ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.parser import parse_json, Circuit
from src.placer import place_components
from src.router import route_nets
from src.renderer import render_svg


def run_pipeline(circuit: Circuit, output_path: str) -> None:
    """Full pipeline: place → route → render."""
    t0 = time.time()
    positions = place_components(circuit)
    traces = route_nets(circuit, positions)
    render_svg(circuit, positions, traces, output_path)
    print(f"  [done] {len(circuit.components)} components, "
          f"{len(traces)} traces — {time.time() - t0:.2f}s")


def run_from_json(input_path: str, output_path: str) -> None:
    print(f"\n[1/3] parsing  {input_path}")
    circuit = parse_json(input_path)
    print(f"[2/3] placing  {len(circuit.components)} components")
    print(f"[3/3] rendering → {output_path}")
    run_pipeline(circuit, output_path)


def run_from_text(description: str, output_path: str) -> None:
    from src.llm_input import text_to_json, save_json

    print("\n[1/4] sending description to Claude API...")
    data = text_to_json(description)

    # save generated JSON alongside output for inspection
    json_path = output_path.replace(".svg", "_generated.json")
    save_json(data, json_path)
    print(f"[2/4] generated JSON saved → {json_path}")

    print(f"[3/4] placing components")
    from src.parser import Board, Component, Net, Circuit as C
    b = data.get("board", {})
    board = Board(
        width_mm=float(b.get("width_mm", 80)),
        height_mm=float(b.get("height_mm", 55)),
        title=str(b.get("title", "Generated Circuit")),
    )
    from src.parser import SUPPORTED_TYPES
    components = []
    for c in data.get("components", []):
        if c["type"].lower() in SUPPORTED_TYPES:
            components.append(Component(
                id=c["id"], type=c["type"].lower(),
                value=c.get("value", ""), pins=c.get("pins", []),
            ))
    nets = [
        Net(name=n["name"],
            connections=[(cn[0], cn[1]) for cn in n.get("connections", [])])
        for n in data.get("nets", [])
    ]
    circuit = C(board=board, components=components, nets=nets)
    print(f"[4/4] rendering → {output_path}")
    run_pipeline(circuit, output_path)


def run_all_examples() -> None:
    examples_dir = Path("examples")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    for json_file in sorted(examples_dir.glob("*.json")):
        out = output_dir / (json_file.stem + ".svg")
        run_from_json(str(json_file), str(out))

    print("\nAll examples done. SVG files are in output/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PCB Schematic to 2D Drawing — UST Internship Project 3"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", metavar="JSON",
                       help="path to a circuit JSON file")
    group.add_argument("--text", metavar="DESCRIPTION",
                       help="plain-English circuit description (requires ANTHROPIC_API_KEY)")
    group.add_argument("--all-examples", action="store_true",
                       help="run all JSON files in examples/ and save to output/")

    parser.add_argument("--output", metavar="SVG", default="output/circuit.svg",
                        help="output SVG path (default: output/circuit.svg)")

    args = parser.parse_args()
    Path("output").mkdir(exist_ok=True)

    if args.all_examples:
        run_all_examples()
    elif args.input:
        run_from_json(args.input, args.output)
    elif args.text:
        run_from_text(args.text, args.output)


if __name__ == "__main__":
    main()
