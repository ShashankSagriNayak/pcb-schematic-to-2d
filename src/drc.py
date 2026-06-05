"""
drc.py
Offline Design Rule Check (DRC) — validates the generated layout
against basic PCB manufacturing rules.

Rules checked:
  1. Minimum trace length (dangling stubs)
  2. Unconnected nets (net has only 1 pin — nothing to connect to)
  3. Component overlap (two components share the same grid cell)
  4. Out-of-bounds components (placed outside board boundary)
  5. Net with no valid components (references missing component IDs)

Returns a DRCReport with violations and a quality score (0–100).
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from src.parser import Circuit
from src.placer import Position, get_effective_size
from src.router import Trace

MIN_TRACE_MM   = 1.0    # traces shorter than this are flagged
MIN_CLEARANCE  = 2.0    # minimum mm between component bounding boxes


@dataclass
class DRCViolation:
    rule: str        # rule name
    severity: str    # "error" or "warning"
    message: str


@dataclass
class DRCReport:
    violations: list[DRCViolation] = field(default_factory=list)
    quality_score: float = 100.0   # starts at 100, deducted per violation

    def add(self, rule: str, severity: str, message: str) -> None:
        self.violations.append(DRCViolation(rule, severity, message))
        self.quality_score -= 10 if severity == "error" else 5
        self.quality_score = max(0.0, self.quality_score)

    def passed(self) -> bool:
        return not any(v.severity == "error" for v in self.violations)

    def summary(self) -> str:
        errors   = sum(1 for v in self.violations if v.severity == "error")
        warnings = sum(1 for v in self.violations if v.severity == "warning")
        status   = "PASS" if self.passed() else "FAIL"
        return (f"DRC {status} | score: {self.quality_score:.0f}/100 | "
                f"errors: {errors} | warnings: {warnings}")


def run_drc(
    circuit: Circuit,
    positions: dict[str, Position],
    traces: list[Trace],
) -> DRCReport:
    """
    Run all DRC rules and return a DRCReport.
    """
    report = DRCReport()
    comp_lookup = {c.id: c for c in circuit.components}

    # --- Rule 1: unconnected nets ---
    for net in circuit.nets:
        valid_conns = [
            (cid, pin) for cid, pin in net.connections
            if cid in comp_lookup
        ]
        if len(valid_conns) < 2:
            report.add(
                rule="UNCONNECTED_NET",
                severity="error",
                message=f"Net '{net.name}' has only {len(valid_conns)} valid "
                        f"connection(s) — needs at least 2 to form a trace.",
            )

    # --- Rule 2: missing component references in nets ---
    for net in circuit.nets:
        for cid, pin in net.connections:
            if cid not in comp_lookup:
                report.add(
                    rule="MISSING_COMPONENT",
                    severity="error",
                    message=f"Net '{net.name}' references component '{cid}' "
                            f"which does not exist in the component list.",
                )

    # --- Rule 3: component out of bounds ---
    for comp in circuit.components:
        pos = positions.get(comp.id)
        if pos is None:
            continue
        w, h = get_effective_size(comp)
        if (pos.x < 0 or pos.y < 0
                or pos.x + w > circuit.board.width_mm
                or pos.y + h > circuit.board.height_mm):
            report.add(
                rule="OUT_OF_BOUNDS",
                severity="error",
                message=f"Component '{comp.id}' ({comp.value}) extends outside "
                        f"the board boundary at ({pos.x:.1f}, {pos.y:.1f}).",
            )

    # --- Rule 4: component overlap ---
    comp_ids = list(positions.keys())
    for i in range(len(comp_ids)):
        for j in range(i + 1, len(comp_ids)):
            id_a, id_b = comp_ids[i], comp_ids[j]
            pa, pb = positions[id_a], positions[id_b]
            comp_a = comp_lookup.get(id_a)
            comp_b = comp_lookup.get(id_b)
            if comp_a is None or comp_b is None:
                continue
            wa, ha = get_effective_size(comp_a)
            wb, hb = get_effective_size(comp_b)

            # AABB overlap check with clearance
            overlap_x = (pa.x < pb.x + wb + MIN_CLEARANCE and
                         pa.x + wa + MIN_CLEARANCE > pb.x)
            overlap_y = (pa.y < pb.y + hb + MIN_CLEARANCE and
                         pa.y + ha + MIN_CLEARANCE > pb.y)
            if overlap_x and overlap_y:
                report.add(
                    rule="COMPONENT_OVERLAP",
                    severity="warning",
                    message=f"Components '{id_a}' and '{id_b}' are closer than "
                            f"{MIN_CLEARANCE}mm clearance.",
                )

    # --- Rule 5: dangling short traces ---
    for trace in traces:
        if len(trace.points) >= 2:
            p1, p2 = trace.points[0], trace.points[-1]
            length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if length < MIN_TRACE_MM:
                report.add(
                    rule="SHORT_TRACE",
                    severity="warning",
                    message=f"Net '{trace.net_name}' has a very short trace "
                            f"({length:.2f}mm < {MIN_TRACE_MM}mm minimum).",
                )

    # --- Rule 6: components with no net connections ---
    connected_ids = {cid for net in circuit.nets for cid, _ in net.connections}
    for comp in circuit.components:
        if comp.id not in connected_ids:
            report.add(
                rule="FLOATING_COMPONENT",
                severity="warning",
                message=f"Component '{comp.id}' ({comp.value}) has no net "
                        f"connections — it is electrically floating.",
            )

    return report


def print_report(report: DRCReport) -> None:
    """Pretty-print the DRC report to stdout."""
    print("\n" + "=" * 52)
    print("  DRC REPORT")
    print("=" * 52)
    if not report.violations:
        print("  No violations found.")
    else:
        for v in report.violations:
            icon = "✖" if v.severity == "error" else "⚠"
            print(f"  {icon} [{v.severity.upper()}] {v.rule}")
            print(f"      {v.message}")
    print("-" * 52)
    print(f"  {report.summary()}")
    print("=" * 52 + "\n")