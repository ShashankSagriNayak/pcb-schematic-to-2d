"""
llm_input.py
Optional AI module: converts a plain-English circuit description into
the project's JSON format using the Anthropic API.

This is the AI-assisted layer of the pipeline. It allows a user to describe
a circuit in natural language and have it automatically converted to the
structured JSON format that the offline pipeline understands.

Requires ANTHROPIC_API_KEY environment variable.
Falls back gracefully if the key is not set — the rest of the pipeline
is fully offline and unaffected.
"""

from __future__ import annotations
import json
import os
import re


SYSTEM_PROMPT = """You are a PCB component parser. The user will describe a circuit in plain English.
You must return ONLY a valid JSON object — no explanation, no markdown, no backticks.

The JSON must follow this exact schema:
{
  "board": { "width_mm": 80, "height_mm": 55, "title": "<short title>" },
  "components": [
    { "id": "<ref designator>", "type": "<type>", "value": "<value>", "pins": ["<pin>", ...] }
  ],
  "nets": [
    { "name": "<net name>", "connections": [["<comp_id>", "<pin>"], ...] }
  ]
}

Rules:
- Supported types: resistor, capacitor, ic, led, connector
- Use standard reference designators: R1, R2, C1, U1, D1, J1 etc.
- Every component must appear in at least one net
- Return ONLY the JSON. No other text whatsoever."""


def text_to_json(description: str) -> dict:
    """
    Send a plain-English circuit description to Claude and return
    the parsed JSON dict.

    This is the AI step in the pipeline:
      user text → Claude API → structured JSON → parser → placer → renderer

    Raises RuntimeError if API key is missing or response is not valid JSON.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Set it to use --text mode, or use --input with a JSON file instead.\n"
            "Get a key at: https://console.anthropic.com/"
        )

    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed.\n"
            "Run: pip install anthropic"
        )

    print("  [ai] sending description to Claude...")
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description}],
    )

    raw_text: str = message.content[0].text.strip()

    # strip any accidental markdown fences
    raw_text = re.sub(r"^```json\s*", "", raw_text)
    raw_text = re.sub(r"^```\s*",     "", raw_text)
    raw_text = re.sub(r"\s*```$",     "", raw_text)

    try:
        data = json.loads(raw_text)
        print(f"  [ai] generated {len(data.get('components', []))} components, "
              f"{len(data.get('nets', []))} nets")
        return data
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude returned invalid JSON: {e}\n\nRaw output:\n{raw_text}"
        )


def save_json(data: dict, path: str) -> None:
    """Save a dict as a formatted JSON file for inspection."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [ai] generated JSON saved → {path}")