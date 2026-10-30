"""Local simplifier for turtle-step lattice knots."""

from __future__ import annotations

from dataclasses import dataclass

from .checker import check_knot
from .model import Knot, Point, is_turtle_step


@dataclass(frozen=True)
class OptimizationStep:
    kind: str
    index: int
    removed: int


@dataclass(frozen=True)
class OptimizationResult:
    knot: Knot
    steps: tuple[OptimizationStep, ...]

    @property
    def saved_points(self) -> int:
        return sum(step.removed for step in self.steps)


def optimize(knot: Knot, *, max_rounds: int = 10_000) -> OptimizationResult:
    """Simplify a knot with equivalence-preserving local lattice moves.

    The optimizer repeatedly removes two patterns introduced by the generator:

    * a three-edge rectangular detour around a unit edge; and
    * a lifted edge ``a0 -> a1 -> b1 -> b0`` that can be projected back to
      ``a0 -> b0``.

    This is intentionally conservative.  It never claims to solve minimality
    for arbitrary knots, but it creates a practical search loop and a clear
    place for future Reidemeister/grid moves.
    """

    check_knot(knot).raise_for_errors()
    current = knot
    steps: list[OptimizationStep] = []

    for _ in range(max_rounds):
        move = _find_layer_lift(current) or _find_rectangular_detour(current)
        if move is None:
            break
        kind, index = move
        points = _remove_two_after(current.points, index)
        current = Knot(points, name=f"{knot.name}-optimized")
        check_knot(current).raise_for_errors()
        steps.append(OptimizationStep(kind=kind, index=index, removed=2))
    else:
        raise RuntimeError(f"optimizer did not converge after {max_rounds} rounds")

    return OptimizationResult(knot=current, steps=tuple(steps))


def _window(points: tuple[Point, ...], index: int) -> tuple[Point, Point, Point, Point]:
    size = len(points)
    return tuple(points[(index + offset) % size] for offset in range(4))  # type: ignore[return-value]


def _find_layer_lift(knot: Knot) -> tuple[str, int] | None:
    points = knot.points
    for index in range(len(points)):
        a, p, q, b = _window(points, index)
        same_projection = a[:2] == p[:2] and q[:2] == b[:2]
        opposite_layers = a[2] != p[2] and q[2] != b[2] and p[2] == q[2] and a[2] == b[2]
        if same_projection and opposite_layers and is_turtle_step(a, b):
            return ("remove-layer-lift", index)
    return None


def _find_rectangular_detour(knot: Knot) -> tuple[str, int] | None:
    points = knot.points
    for index in range(len(points)):
        a, p, q, b = _window(points, index)
        if a[2] != p[2] or p[2] != q[2] or q[2] != b[2]:
            continue
        if not is_turtle_step(a, b):
            continue
        if not (is_turtle_step(a, p) and is_turtle_step(p, q) and is_turtle_step(q, b)):
            continue
        detour_vector = (p[0] - a[0], p[1] - a[1])
        if detour_vector == (q[0] - b[0], q[1] - b[1]) and abs(detour_vector[0]) + abs(detour_vector[1]) == 1:
            return ("remove-rectangular-detour", index)
    return None


def _remove_two_after(points: tuple[Point, ...], index: int) -> list[Point]:
    """Return a point list with the two cyclic successors of ``index`` removed."""

    size = len(points)
    remove = {((index + 1) % size), ((index + 2) % size)}
    return [point for point_index, point in enumerate(points) if point_index not in remove]
