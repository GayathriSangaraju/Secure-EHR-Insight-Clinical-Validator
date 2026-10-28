"""Deterministic checks applied to the model's answer before it is returned.

These complement the NeMo Guardrails input rails: they need no LLM call and are
fully unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A number optionally followed by a clinical unit, e.g. "40mg", "2.5 mL", "10 units".
_FIGURE = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*"
    r"(mg|mcg|µg|g|kg|ml|l|iu|units?|meq|mmol|%|mmhg|bpm)?(?!\w)",
    re.IGNORECASE,
)
# Bare numbers below this are treated as list markers / counts, not clinical claims.
_MIN_BARE_CLAIM = 10


@dataclass
class GroundingResult:
    grounded: bool
    ungrounded: list[str] = field(default_factory=list)


def _normalise(number: str, unit: str | None) -> str:
    number = number.replace(",", ".")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    return f"{number}{(unit or '').lower()}"


def _context_figures(text: str) -> set[str]:
    """Every figure in the context, both with its unit and as a bare number."""
    found: set[str] = set()
    for m in _FIGURE.finditer(text):
        found.add(_normalise(m.group(1), m.group(2)))
        found.add(_normalise(m.group(1), None))
    return found


def check_grounding(answer: str, context: str) -> GroundingResult:
    """Flag numeric clinical figures in `answer` that do not appear in `context`.

    A lexical heuristic, not a proof of faithfulness: it cheaply catches the most
    dangerous failure, an invented dose or lab value.
    """
    supported = _context_figures(context)
    ungrounded: set[str] = set()
    for m in _FIGURE.finditer(answer):
        number, unit = m.group(1), m.group(2)
        if unit is None and float(number.replace(",", ".")) < _MIN_BARE_CLAIM:
            continue
        key = _normalise(number, unit)
        if key not in supported:
            ungrounded.add(key)
    ordered = sorted(ungrounded)
    return GroundingResult(grounded=not ordered, ungrounded=ordered)


def grounding_warning(result: GroundingResult) -> str | None:
    if result.grounded:
        return None
    return (
        "Some figures in this answer were not found in the retrieved records "
        f"({', '.join(result.ungrounded)}). Verify against the source chart."
    )
