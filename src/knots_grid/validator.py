"""Validation for cyclic paths in Z^2 x {0, 1}."""

from __future__ import annotations

from dataclasses import dataclass, field

from .core import Point


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of validating a cyclic point sequence."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)

    def raise_for_errors(self) -> None:
        if not self.is_valid:
            raise ValueError("; ".join(self.errors))


def is_valid_edge(a: Point, b: Point) -> bool:
    """Return whether two consecutive points define an allowed edge."""

    if a.z not in (0, 1) or b.z not in (0, 1):
        return False

    dx = abs(a.x - b.x)
    dy = abs(a.y - b.y)
    dz = abs(a.z - b.z)

    same_layer_unit_grid_step = dz == 0 and ((dx == 1 and dy == 0) or (dx == 0 and dy == 1))
    layer_switch = dx == 0 and dy == 0 and dz == 1
    return same_layer_unit_grid_step or layer_switch


def validate_cycle(points: tuple[Point, ...] | list[Point]) -> ValidationResult:
    """Validate a closed simple cycle in the two-layer grid.

    A first valid cycle must satisfy:

    - the path has at least one edge,
    - first point equals last point,
    - all interior points are distinct,
    - every consecutive edge is allowed.
    """

    pts = tuple(points)
    errors: list[str] = []

    if len(pts) < 2:
        errors.append("path must contain at least two points")
        return ValidationResult(False, tuple(errors))

    if pts[0] != pts[-1]:
        errors.append("path is not closed: first point differs from last point")

    for index, point in enumerate(pts):
        if point.z not in (0, 1):
            errors.append(f"point {index} has invalid layer z={point.z!r}")

    seen: dict[Point, int] = {}
    interior = pts[:-1] if pts[0] == pts[-1] else pts
    for index, point in enumerate(interior):
        previous = seen.get(point)
        if previous is not None:
            errors.append(f"duplicate point at indices {previous} and {index}: {point}")
        else:
            seen[point] = index

    for index, (a, b) in enumerate(zip(pts, pts[1:])):
        if not is_valid_edge(a, b):
            errors.append(f"invalid edge {index}: {a} -> {b}")

    return ValidationResult(not errors, tuple(errors))
