"""Two-layer grid experiments for knot diagrams."""

from .core import Direction, Point, TraceResult, trace_turtle
from .generator import (
    GeneratorConfig,
    SearchConfig,
    generate_candidate,
    generate_candidates,
    make_candidate,
    search_candidate,
    search_candidates,
    search_best_candidate,
    trefoil_candidate,
    torus_knot_candidate,
)
from .png import render_png
from .projection import ProjectionMetrics, ProjectionScore, ProjectionWeights, score_projection
from .reidemeister import Crossing, ReidemeisterReport, find_crossings, reidemeister_conditions
from .svg import render_svg
from .validator import ValidationResult, validate_cycle

__all__ = [
    "Direction",
    "Crossing",
    "GeneratorConfig",
    "Point",
    "ProjectionMetrics",
    "ProjectionScore",
    "ProjectionWeights",
    "ReidemeisterReport",
    "SearchConfig",
    "TraceResult",
    "ValidationResult",
    "generate_candidate",
    "generate_candidates",
    "find_crossings",
    "make_candidate",
    "search_candidate",
    "search_candidates",
    "search_best_candidate",
    "score_projection",
    "trefoil_candidate",
    "torus_knot_candidate",
    "reidemeister_conditions",
    "render_svg",
    "render_png",
    "trace_turtle",
    "validate_cycle",
]
