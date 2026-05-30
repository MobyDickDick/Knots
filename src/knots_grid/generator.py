"""First placeholder for future knot candidate generators."""

from __future__ import annotations

from .core import TraceResult, trace_turtle
from .validator import validate_cycle


def make_candidate(code: str) -> TraceResult:
    """Trace and validate a hand-written turtle code.

    This is intentionally minimal. The real random or search-based generator
    should be built on top of the core tracer and validator.
    """

    result = trace_turtle(code)
    validate_cycle(result.points).raise_for_errors()
    return result
