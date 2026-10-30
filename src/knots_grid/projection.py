"""Explainable aesthetic scores for the unshifted grid projection.

These heuristics compare drawings, not knot types or minimal representatives.
Higher totals are preferred; all component measurements remain available.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields
from math import isfinite

from .core import Point
from .reidemeister import find_crossings
from .validator import validate_cycle


@dataclass(frozen=True, slots=True)
class ProjectionWeights:
    """Non-negative rewards and penalties used by :func:`score_projection`."""

    crossings: float = 2.0
    length: float = 0.05
    symmetry: float = 1.0
    area_utilization: float = 1.0
    layer_switches: float = 0.1
    degeneracies: float = 1.0

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{field.name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class ProjectionMetrics:
    """Raw drawing measurements, independent of scoring weights.

    Symmetry is the mean fraction of projected vertices preserved by horizontal
    reflection, vertical reflection and a half turn about the bounding box
    center. Area utilization is occupied projected vertices / bounding-box grid
    vertices. Both lie in [0, 1]. Degeneracies count overlapping projected edges
    and double visits that are neither transverse crossings nor layer switches.
    """

    crossings: int
    length: int
    symmetry: float
    area_utilization: float
    layer_switches: int
    degeneracies: int


@dataclass(frozen=True, slots=True)
class ProjectionScore:
    """Weighted total (higher is better) and its explainable components."""

    total: float
    metrics: ProjectionMetrics


def score_projection(
    points: tuple[Point, ...] | list[Point],
    *,
    weights: ProjectionWeights = ProjectionWeights(),
) -> ProjectionScore:
    """Score a validated closed cycle without modifying its representation.

    Rewards: crossings, symmetry, area utilization. Penalties: edge count,
    layer switches, degeneracies. Translation, cyclic start, reversal and the
    eight symmetries of the square leave the score unchanged. This uses the
    unshifted (x, y) projection, not the renderer's diagonal layer offset.
    """

    pts = tuple(points)
    validate_cycle(pts).raise_for_errors()
    body = pts[:-1]
    projected = {(p.x, p.y) for p in body}
    min_x = min(x for x, _ in projected)
    max_x = max(x for x, _ in projected)
    min_y = min(y for _, y in projected)
    max_y = max(y for _, y in projected)
    center_x = min_x + max_x
    center_y = min_y + max_y
    preserved = sum(
        ((center_x - x, y) in projected)
        + ((x, center_y - y) in projected)
        + ((center_x - x, center_y - y) in projected)
        for x, y in projected
    )

    crossings = find_crossings(pts)
    crossing_coordinates = {crossing.coordinate for crossing in crossings}
    switch_coordinates: set[tuple[int, int]] = set()
    edges: Counter[tuple[tuple[int, int], tuple[int, int]]] = Counter()
    layer_switches = 0
    for start, end in zip(pts, pts[1:]):
        a, b = (start.x, start.y), (end.x, end.y)
        if start.z != end.z:
            layer_switches += 1
            switch_coordinates.add(a)
        else:
            edges[tuple(sorted((a, b)))] += 1

    visits = Counter((p.x, p.y) for p in body)
    regular_visits = crossing_coordinates | switch_coordinates
    ambiguous_visits = sum(
        count - 1 for coordinate, count in visits.items()
        if coordinate not in regular_visits
    )
    degeneracies = ambiguous_visits + sum(count - 1 for count in edges.values())
    metrics = ProjectionMetrics(
        crossings=len(crossings),
        length=len(body),
        symmetry=preserved / (3 * len(projected)),
        area_utilization=len(projected) / ((max_x - min_x + 1) * (max_y - min_y + 1)),
        layer_switches=layer_switches,
        degeneracies=degeneracies,
    )
    total = (
        weights.crossings * metrics.crossings
        - weights.length * metrics.length
        + weights.symmetry * metrics.symmetry
        + weights.area_utilization * metrics.area_utilization
        - weights.layer_switches * metrics.layer_switches
        - weights.degeneracies * metrics.degeneracies
    )
    return ProjectionScore(total, metrics)
