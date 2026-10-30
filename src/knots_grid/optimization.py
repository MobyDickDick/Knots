"""Replayable ambient isotopies across empty unit lattice faces.

Replace three sides of a face by the fourth (3 -> 1), or two sides by
the other two (2 -> 2). Unit lattice edges cannot pierce the interior of
a unit lattice face. Checking the unused boundary vertices therefore certifies
that the swept disk is disjoint from the rest of the knot. This is a spatial
isotopy certificate even if the flat projection is degenerate. No move leaves
the two-layer lattice. This deliberately bounded engine is not a general
Reidemeister solver and does not claim global minimality.
"""

from dataclasses import dataclass

from .catalog import canonicalize_cycle, sequence_measure
from .core import Point
from .validator import validate_cycle


@dataclass(frozen=True, slots=True)
class FaceMove:
    start_index: int
    before: tuple[Point, ...]
    after: tuple[Point, ...]
    kind: str = "empty_unit_face"


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    points: tuple[Point, ...]
    moves: tuple[FaceMove, ...]
    status: str


def _face_boundary(before, after):
    boundary = before + tuple(reversed(after[1:-1]))
    if len(boundary) != 4 or len(set(boundary)) != 4:
        return False
    coordinates = [(p.x, p.y, p.z) for p in boundary]
    spans = [max(p[axis] for p in coordinates) - min(p[axis] for p in coordinates)
             for axis in range(3)]
    return sorted(spans) == [0, 1, 1]


def apply_face_move(points, move: FaceMove) -> tuple[Point, ...]:
    """Verify the empty disk certificate afresh, then execute a logged move."""
    pts = tuple(points)
    validate_cycle(pts).raise_for_errors()
    body = pts[:-1]
    if move.kind != "empty_unit_face" or not 0 <= move.start_index < len(body):
        raise ValueError("invalid face move")
    rotated = body[move.start_index:] + body[:move.start_index]
    if len(move.before) not in (3, 4) or len(move.after) != 6 - len(move.before):
        raise ValueError("only 3->1 and 2->2 face moves are supported")
    if rotated[:len(move.before)] != move.before:
        raise ValueError("move does not match this path")
    if (move.after[0], move.after[-1]) != (move.before[0], move.before[-1]):
        raise ValueError("move endpoints differ")
    if not _face_boundary(move.before, move.after):
        raise ValueError("move does not bound a unit face")
    if set(move.after[1:-1]) & set(body):
        raise ValueError("face boundary is occupied by another strand")
    result = move.after + rotated[len(move.before):] + (rotated[0],)
    validate_cycle(result).raise_for_errors()
    return result


def _moves(points):
    body = points[:-1]
    n = len(body)
    for length in (4, 3):  # Prefer reductions before equal-length slides.
        if n <= length:
            continue
        for i in range(n):
            before = tuple(body[(i + j) % n] for j in range(length))
            a, b = before[0], before[-1]
            if length == 4:
                after = (a, b)
            else:
                corner = Point(a.x + b.x - before[1].x,
                               a.y + b.y - before[1].y,
                               a.z + b.z - before[1].z)
                after = (a, corner, b)
            if _face_boundary(before, after):
                move = FaceMove(i, before, after)
                try:
                    result = apply_face_move(points, move)
                except ValueError:
                    continue
                yield move, result


def optimize_cycle(points, *, max_moves: int = 100) -> OptimizationResult:
    """Strictly improve (point count, canonical Cantor order) within a budget.

    Canonical comparison uses rotations only, so no reflection can silently
    change the knot's chirality. Returned coordinates retain the exact move
    endpoints, allowing replay from the unmodified original.
    """
    if max_moves < 0:
        raise ValueError("max_moves must be non-negative")
    current = tuple(points)
    validate_cycle(current).raise_for_errors()
    log = []
    for _ in range(max_moves):
        measure = sequence_measure(canonicalize_cycle(current, include_reflections=False)[:-1])
        best = None
        best_measure = measure
        for move, candidate in _moves(current):
            candidate_measure = sequence_measure(
                canonicalize_cycle(candidate, include_reflections=False)[:-1])
            if candidate_measure < best_measure:
                best = move, candidate
                best_measure = candidate_measure
        if best is None:
            return OptimizationResult(current, tuple(log), "local_minimum")
        move, current = best
        log.append(move)
    return OptimizationResult(current, tuple(log), "move_limit")
