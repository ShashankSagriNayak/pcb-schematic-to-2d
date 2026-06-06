# PCB Schematic to 2D Drawing

A Python tool that converts a circuit description into a structured 2D PCB layout drawing. Supports both **AI-assisted input** (plain English via Claude API) and **fully offline input** (structured JSON). Outputs SVG, PNG, and PDF. Built for the UST SEMICON Data Science Internship — June 2026, Problem Statement 3.

---

## What I Built

This project implements **Option B**: structured input → 2D board layout drawing.

The pipeline has two input modes:

**AI-assisted mode** — describe your circuit in plain English. Claude converts it to structured JSON automatically, then the offline pipeline takes over:
```
"a 555 timer LED flasher with two 47k resistors..."
        ↓  Claude API (src/llm_input.py)
        ↓  structured JSON
        ↓  offline pipeline
        →  SVG / PNG / PDF
```

**Offline mode** — provide a JSON netlist directly. No internet, no API key needed:
```
circuit.json  →  parser  →  placer  →  router  →  renderer  →  SVG / PNG / PDF
```

Both modes produce identical output. The AI layer is cleanly isolated in `src/llm_input.py` and the core pipeline runs entirely offline.

**Why Option B over Option A (image parsing):**
Option A requires a trained vision model and a labeled schematic dataset — a meaningful ML project on its own, well outside a 5-day scope. For Option A, the approach would be to fine-tune YOLOv8 on a labeled schematic dataset (e.g. RoboFlow's circuit symbol dataset) to detect component bounding boxes offline, then feed detected types and positions directly into the existing parser pipeline — the placer, router, and renderer would require zero changes.

---

## Features

- **AI-assisted input** via Claude API — describe a circuit in plain English
- **Fully offline core pipeline** — JSON → SVG/PNG/PDF, no internet needed
- 5 component types with distinct visual symbols: resistor, capacitor, IC, LED, connector
- Manhattan (L-shaped) trace routing — no diagonal crossing lines
- One color per net with a legend
- Auto-expands board size to fit all components — no overlaps
- Component rotation support (`"rotation": 90` in JSON)
- Offline Design Rule Check (DRC) with a 0–100 quality score
- 6 built-in real-world circuit examples

---

## Assumptions

- **Single-layer board only.** Multi-layer representation is out of scope.
- **Grid-based placement.** Components are placed row by row. No advanced auto-routing — traces are Manhattan-routed with star topology per net.
- **5 component types supported:** resistor, capacitor, ic, led, connector. Unknown types are skipped with a warning.
- **Board auto-sizing.** If the JSON specifies a board smaller than needed, the tool expands it automatically to fit all components without overlap.
- **AI mode requires an Anthropic API key.** The core pipeline runs fully offline without it.
- **No EDA tool integration.** No KiCad, FreeRouting, or EDA software required.

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
anthropic>=0.25
```

> `anthropic` is only needed for `--text` mode. The offline pipeline works without it.

---

## How to Run

### Offline mode — JSON input (no API key needed)
```bash
python run.py --input examples/led_blink.json
python run.py --input examples/led_blink.json --format png
python run.py --input examples/led_blink.json --format pdf
python run.py --input examples/led_blink.json --drc
python run.py --all-examples
python run.py --all-examples --format png --drc
```

### AI-assisted mode — plain English input (requires Anthropic API key)

> **Note:** This mode is implemented but not demonstrated live in this submission as it requires a paid Anthropic API key. The code is fully working in `src/llm_input.py`. To use it, set your API key and run:

```bash
export ANTHROPIC_API_KEY=your_key_here       # Linux / Mac
set ANTHROPIC_API_KEY=your_key_here          # Windows

python run.py --text "a 555 timer LED flasher with two 47k resistors, a 10uF capacitor and a yellow LED"
python run.py --text "an ESP32 circuit with a 3.3V regulator, decoupling caps and a USB connector" --format png
```

The generated JSON is saved alongside the output as `_generated.json` for inspection.

All example outputs in this repository were produced using the **offline `--input` mode**.

### Specify output path
```bash
python run.py --input examples/led_blink.json --output output/my_board.svg
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

| Field | Required | Description |
|---|---|---|
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
| `arduino_uno_core.json` | Arduino Uno (ATmega328P + ATmega16U2) | 12 | 10 |
| `esp32_devkit.json` | ESP32 DevKit (ESP32-WROOM + CP2102) | 13 | 11 |

---

## DRC — Design Rule Check

Run with `--drc` to validate the layout against 6 offline rules:

| Rule | Severity | Description |
|---|---|---|
| `UNCONNECTED_NET` | Error | Net has fewer than 2 valid connections |
| `MISSING_COMPONENT` | Error | Net references a component ID not in the list |
| `OUT_OF_BOUNDS` | Error | Component extends outside board boundary |
| `COMPONENT_OVERLAP` | Warning | Two components closer than 2mm clearance |
| `SHORT_TRACE` | Warning | Trace length under 1mm |
| `FLOATING_COMPONENT` | Warning | Component has no net connections |

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
│   ├── llm_input.py        # AI layer — plain English → JSON via Claude API
│   ├── parser.py           # JSON → typed Circuit / Component / Net model
│   ├── placer.py           # grid-based placement with auto board sizing
│   ├── router.py           # Manhattan L-shaped trace routing
│   ├── renderer.py         # SVG (svgwrite) + PNG/PDF (matplotlib)
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

---

## Architecture

```
[AI-assisted mode]                    [Offline mode]
plain English description             circuit JSON file
        ↓                                    ↓
  Claude API                          parse_json()
  (src/llm_input.py)                       ↓
        ↓                             Circuit model
  generated JSON           ──────────────→ ↓
                                     place_components()
                                           ↓
                                     route_nets()
                                           ↓
                                     render_svg()  →  board.svg
                                     render_png()  →  board.png
                                           ↓
                                     run_drc()     →  DRC report
```

---

## What Works

- JSON netlist → 2D drawing, fully offline, no API key needed
- AI-assisted input implemented in `src/llm_input.py` — converts plain English to JSON via Claude API (requires API key to run)
- Auto-sizing board — components never overlap regardless of circuit size
- Manhattan routing — clean L-shaped traces, no diagonal crossings
- Distinct visual symbols for all 5 component types
- DRC catches: unconnected nets, missing refs, out-of-bounds, floating components
- PNG and PDF match the SVG exactly — no Cairo dependency on Windows
- All 6 examples run clean with `python run.py --all-examples`

---

## Known Limitations

- **Trace routing is star topology.** Every pin connects back to the first pin of the net. A real PCB router uses constraint-based algorithms to minimise crossing on dense boards.
- **Single layer only.** Real PCBs use 2–16 layers for complex designs.
- **No DRC on trace clearance.** Checks component spacing but not trace-to-trace clearance, which requires EDA-grade tooling.
- **AI mode not demonstrated live.** The `--text` mode is implemented in `src/llm_input.py` and calls the Anthropic API, but was not run for this submission due to API key cost. All example outputs were produced with the offline pipeline. The AI code can be verified by reading `src/llm_input.py` directly.
- **LLM output for complex circuits can be imperfect.** The Claude prompt is tuned for 5–15 component circuits. Very complex descriptions may produce JSON that needs manual correction.
- **Option A not implemented.** Image → component detection requires a trained vision model (e.g. fine-tuned YOLOv8 on labeled schematic data). The existing pipeline would accept such output directly via JSON.

---

## What I Would Improve With More Time

1. **Lee maze router** — replace star topology with a grid-based router to eliminate trace crossings on dense boards.
2. **Option A image input** — fine-tune YOLOv8 on a labeled schematic dataset to detect component bounding boxes offline, feeding results into the existing JSON pipeline.
3. **More component types** — transistors, inductors, crystals, fuses.
4. **KiCad `.kicad_pcb` export** — use the `pcbnew` Python API (bundled with KiCad 6+) to export a real editable PCB file with proper SMD footprints.
5. **Interactive HTML output** — hover over a net to highlight all connected traces and pins.

---

## Dependencies

| Library | Version | License | Used for |
|---|---|---|---|
| matplotlib | ≥3.8 | PSF/BSD | PNG and PDF rendering |
| svgwrite | ≥1.4 | MIT | SVG file generation |
| Pillow | ≥10.0 | HPND | Image handling support |
| anthropic | ≥0.25 | MIT | AI input mode (optional) |

No API keys are included in the repository. Set `ANTHROPIC_API_KEY` as an environment variable to use `--text` mode. All other functionality works without it.

---

## Author
Shashank Sagri Nayak
Submitted for UST SEMICON Data Science Internship — June 2026
Problem 3: PCB Schematic to 2D Drawing