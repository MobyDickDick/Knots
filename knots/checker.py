"""Validation for cyclic lattice knots."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter

from .model import Knot, Point, is_turtle_step


@dataclass(frozen=True)
class CheckReport:
    """Human- and machine-readable validation result."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def raise_for_errors(self) -> None:
        if not self.valid:
            raise ValueError("Invalid knot: " + "; ".join(self.errors))


def check_knot(knot: Knot, *, min_points: int = 4) -> CheckReport:
    """Check whether a point tuple is a valid cyclic turtle-step knot.

    The criterion intentionally matches the simple representation described in
    the project notes: after resolving the curve into turtle steps, no point in
    ``Z^2 x {0, 1}`` may occur twice, and all cyclic neighbours must be unit
    turtle steps.
    """

    errors: list[str] = []
    warnings: list[str] = []
    points = knot.points

    if len(points) < min_points:
        errors.append(f"Need at least {min_points} points, got {len(points)}.")

    for index, (x, y, z) in enumerate(points):
        if z not in (0, 1):
            errors.append(f"Point {index} has layer z={z}; expected 0 or 1.")
        if not all(isinstance(value, int) for value in (x, y, z)):
            errors.append(f"Point {index} is not integral: {(x, y, z)!r}.")

    duplicates = [point for point, count in Counter(points).items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate points are forbidden: {duplicates!r}.")

    if points:
        for index, (a, b) in enumerate(knot.cyclic_edges()):
            if not is_turtle_step(a, b):
                errors.append(f"Edge {index} is not a turtle step: {a!r} -> {b!r}.")

    projected_counts = Counter((x, y) for x, y, _ in points)
    crossings = sum(1 for count in projected_counts.values() if count > 1)
    if crossings:
        warnings.append(f"Projection contains {crossings} occupied coordinate(s) on both layers.")

    return CheckReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))
