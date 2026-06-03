"""
run.py
Main entry point for the PCB schematic to 2D drawing tool.

Usage:
  python run.py --input examples/led_blink.json --output output/led_blink.svg
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
    


if __name__ == "__main__":
    main()
