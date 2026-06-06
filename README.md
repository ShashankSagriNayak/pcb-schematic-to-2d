# PCB Schematic to 2D Drawing

A lightweight, fully offline Python tool that converts a JSON circuit description into a structured 2D PCB layout drawing. Outputs SVG, PNG, and PDF. Built for the UST SEMICON Data Science Internship — June 2026, Problem Statement 3.

---

## What I Built

This project implements **Option B**: a structured JSON input → 2D board layout drawing pipeline.

The tool takes a JSON file describing PCB components (type, value, pin names) and their net connections, automatically places them on a virtual board, routes L-shaped (Manhattan) traces between nets, runs an offline Design Rule Check (DRC), and exports a clean SVG and PNG drawing showing component placement and connectivity.

**Why Option B over Option A (image parsing):**
Option A requires a trained vision model and a labeled schematic dataset — a meaningful ML project on its own that is well outside a 5-day scope. Option B delivers a complete, working end-to-end pipeline that can be verified, extended, and reproduced.

---

## Features

- JSON → SVG + PNG + PDF output, fully offline
- 5 component types with distinct visual symbols: resistor, capacitor, IC, LED, connector
- Manhattan (L-shaped) trace routing — no diagonal crossing lines
- One color per net with a legend
- Auto-expands board size to fit all components cleanly — no overlaps
- Component rotation support (`"rotation": 90` in JSON)
- Offline Design Rule Check (DRC) with a 0–100 quality score
- 6 built-in real-world circuit examples

---

## Assumptions

- **Single-layer board only.** All components and traces are on one layer. Multi-layer is out of scope.
- **Grid-based placement.** Components are placed row by row. No advanced auto-routing — traces are Manhattan-routed (horizontal then vertical) with star topology per net.
- **5 component types supported:** resistor, capacitor, ic, led, connector. Unknown types are skipped with a warning.
- **Board auto-sizing.** If the JSON specifies a board smaller than needed, the tool expands it automatically to fit all components without overlap.
- **Fully offline.** No internet connection, no API calls, no cloud dependencies at any stage.
- **No EDA tool integration.** No KiCad, FreeRouting, or EDA software. All rendering uses Python (svgwrite + matplotlib).

---

## Installation

Requires **Python 3.11+**

```bash
git clone https://github.com/ShashankSagriNayak/pcb-schematic-to-2d
cd pcb-schematic-to-2d
pip install -r requirements.txt
```

`requirements.txt`:
```
matplotlib>=3.8
svgwrite>=1.4
Pillow>=10.0
```

No system-level dependencies. Works on Windows, Mac, and Linux.

---

## How to Run

### Run all 6 built-in examples
```bash
python run.py --all-examples
```

### Run a single JSON file
```bash
python run.py --input examples/led_blink.json
```

### Export as PNG
```bash
python run.py --input examples/led_blink.json --format png
```

### Export as PDF
```bash
python run.py --input examples/led_blink.json --format pdf
```

### Run with Design Rule Check
```bash
python run.py --input examples/led_blink.json --drc
```

### Specify output path
```bash
python run.py --input examples/led_blink.json --output output/my_board.svg
```

### Full options
```bash
python run.py --all-examples --format png --drc
```

Output files are saved to the `output/` folder.

---

## JSON Input Format

```json
{
  "board": {
    "width_mm": 80,
    "height_mm": 55,
    "title": "LED Blink Circuit"
  },
  "components": [
    {
      "id": "U1",
      "type": "ic",
      "value": "ATmega328P",
      "pins": ["VCC", "GND", "PB5", "PB4"],
      "rotation": 0
    },
    {
      "id": "R1",
      "type": "resistor",
      "value": "330R",
      "pins": ["A", "B"]
    },
    {
      "id": "D1",
      "type": "led",
      "value": "LED-RED",
      "pins": ["anode", "cathode"]
    }
  ],
  "nets": [
    { "name": "VCC",      "connections": [["U1", "VCC"], ["R1", "A"]] },
    { "name": "GND",      "connections": [["U1", "GND"], ["D1", "cathode"]] },
    { "name": "LED_LINE", "connections": [["U1", "PB5"], ["R1", "A"]] },
    { "name": "LED_ANODE","connections": [["R1", "B"],   ["D1", "anode"]] }
  ]
}
```

**Fields:**

| Field | Required | Description |
|---|---|---|
| `board.width_mm` | No | Board width in mm (auto-expanded if too small) |
| `board.height_mm` | No | Board height in mm (auto-expanded if too small) |
| `board.title` | No | Title shown on the drawing |
| `component.id` | Yes | Reference designator: R1, C1, U1, D1, J1 |
| `component.type` | Yes | One of: resistor, capacitor, ic, led, connector |
| `component.value` | No | Part value or name: "330R", "ATmega328P" |
| `component.pins` | Yes | List of pin names |
| `component.rotation` | No | 0 (default) or 90 degrees |
| `net.name` | Yes | Net label shown in the legend |
| `net.connections` | Yes | List of `[component_id, pin_name]` pairs |

---

## Example Runs

Six real-world inspired circuits are included in `examples/`:

| File | Circuit | Components | Nets |
|---|---|---|---|
| `led_blink.json` | ATmega328P driving an LED | 5 | 4 |
| `power_supply.json` | AMS1117 12V→5V regulator | 7 | 4 |
| `motor_driver.json` | L298N H-bridge | 8 | 8 |
| `555_timer_flasher.json` | NE555 astable LED flasher | 8 | 7 |
| `arduino_uno_core.json` | Arduino Uno core (ATmega328P + ATmega16U2) | 12 | 10 |
| `esp32_devkit.json` | ESP32 DevKit (ESP32-WROOM + CP2102 + AMS1117) | 13 | 11 |

---

## DRC — Design Rule Check

Run with `--drc` to validate the generated layout against 6 offline rules:

| Rule | Severity | Description |
|---|---|---|
| `UNCONNECTED_NET` | Error | Net has fewer than 2 valid connections |
| `MISSING_COMPONENT` | Error | Net references a component ID not in the list |
| `OUT_OF_BOUNDS` | Error | Component extends outside board boundary |
| `COMPONENT_OVERLAP` | Warning | Two components are closer than 2mm clearance |
| `SHORT_TRACE` | Warning | Trace length is under 1mm |
| `FLOATING_COMPONENT` | Warning | Component has no net connections at all |

Example output:
```
====================================================
  DRC REPORT
====================================================
  No violations found.
----------------------------------------------------
  DRC PASS | score: 100/100 | errors: 0 | warnings: 0
====================================================
```

---

## Project Structure

```
pcb-schematic-to-2d/
│
├── run.py                  # entry point — single command to run everything
├── requirements.txt
├── README.md
│
├── src/
│   ├── __init__.py
│   ├── parser.py           # JSON → typed Circuit / Component / Net model
│   ├── placer.py           # grid-based placement with auto board sizing
│   ├── router.py           # Manhattan L-shaped trace routing
│   ├── renderer.py         # SVG output (svgwrite) + PNG/PDF (matplotlib)
│   └── drc.py              # offline Design Rule Check, quality score 0–100
│
├── examples/
│   ├── led_blink.json
│   ├── power_supply.json
│   ├── motor_driver.json
│   ├── 555_timer_flasher.json
│   ├── arduino_uno_core.json
│   └── esp32_devkit.json
│
└── output/                 # generated SVG, PNG, PDF files
```

Every function in `src/` has full type hints on all arguments and return values.

---

## Architecture

```
JSON file
    ↓  [parser.py]
Circuit model: Board + List[Component] + List[Net]
    ↓  [placer.py]
Component positions on auto-sized board grid
    ↓  [router.py]
Manhattan traces between net pin pairs
    ↓  [renderer.py]
SVG  →  output/board.svg      (svgwrite)
PNG  →  output/board.png      (matplotlib, direct render)
PDF  →  output/board.pdf      (matplotlib, direct render)
    ↓  [drc.py]  (optional --drc flag)
DRC report + quality score printed to stdout
```

PNG and PDF are rendered directly from the placement and routing data using matplotlib — not converted from SVG. This means both outputs are always identical to each other.

---

## What Works

- JSON parsing with clear validation errors and warnings for unknown types
- Auto-sizing board so components never overlap regardless of circuit size
- Manhattan routing produces clean L-shaped traces with no diagonal crossings
- Distinct visual symbols for all 5 component types
- One color per net, consistent across SVG and PNG
- DRC catches real issues: unconnected nets, missing refs, out-of-bounds, floating components
- PNG and PDF output that exactly matches the SVG — no Cairo dependency needed on Windows
- All 6 example circuits run cleanly end-to-end with `python run.py --all-examples`

---

## Known Limitations

- **Trace routing is star topology.** Every pin connects back to the first pin of the net. A real PCB router uses constraint-based algorithms to minimise wire length and avoid crossings on dense boards.
- **No auto-routing.** Traces are Manhattan-routed but not optimised — on very dense boards some traces will still visually cross. FreeRouting or a Lee maze algorithm would fix this.
- **Single layer only.** All components and traces are on one layer. Real PCBs use 2–16 layers for complex designs.
- **No DRC on trace clearance.** The DRC checks component spacing but does not validate trace-to-trace or trace-to-pad clearance, which requires EDA-grade tooling.
- **Option A not implemented.** Converting a schematic image to a component list requires a trained object detection model (e.g. fine-tuned YOLOv8 on a labeled schematic dataset). The existing pipeline would accept the output of such a model directly via the JSON format — the placer, router, and renderer require zero changes.
- **5 component types only.** Transistors, inductors, crystals, and other types are not yet supported.

---

## What I Would Improve With More Time

1. **Lee maze router** — replace star topology with a proper grid-based router to eliminate all trace crossings on dense boards.
2. **Option A image input** — fine-tune YOLOv8 on a labeled schematic dataset (e.g. RoboFlow circuit symbol dataset) to detect component bounding boxes offline, feeding detected types and positions directly into the existing parser.
3. **More component types** — transistors (BJT/MOSFET), inductors, voltage regulators, crystals, fuses.
4. **KiCad `.kicad_pcb` export** — use the `pcbnew` Python API (bundled with KiCad 6+) to export a real editable PCB file with proper footprints from the KiCad standard library.
5. **Interactive HTML output** — hover over a net to highlight all connected traces and pins.

---

## Dependencies

| Library | Version | License | Used for |
|---|---|---|---|
| matplotlib | ≥3.8 | PSF/BSD | PNG and PDF rendering |
| svgwrite | ≥1.4 | MIT | SVG file generation |
| Pillow | ≥10.0 | HPND | Image handling support |

No API keys. No internet connection required. No system-level libraries required on any platform.

---

## Author
Shashank Sagri Nayak

Submitted for UST SEMICON Data Science Internship — June 2026
Problem 3: PCB Schematic to 2D Drawing