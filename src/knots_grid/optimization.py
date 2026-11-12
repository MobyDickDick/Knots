"""Replayable ambient isotopies across empty faces and Reidemeister regions.

Replace three sides of a face by the fourth (3 -> 1), or two sides by
the other two (2 -> 2). Unit lattice edges cannot pierce the interior of
a unit lattice face. Checking the unused boundary vertices therefore certifies
that the swept disk is disjoint from the rest of the knot. This is a spatial
isotopy certificate even if the flat projection is degenerate. No result leaves
the two-layer lattice. This deliberately bounded engine is not a general
Reidemeister solver and does not claim global minimality. Direct moves are
provided by reidemeister_moves; the same strict objective applies to both.
"""

from dataclasses import dataclass
from itertools import chain
from math import isfinite
from time import monotonic

from .catalog import canonicalize_cycle, sequence_measure
from .core import Point
from .reidemeister_moves import (
    MoveRejection, ReidemeisterMove, analyze_reidemeister_moves,
    apply_reidemeister_move,
)
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
    moves: tuple[FaceMove | ReidemeisterMove, ...]
    status: str
    reidemeister_rejections: tuple[MoveRejection, ...] = ()


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


def apply_move(points, move: FaceMove | ReidemeisterMove) -> tuple[Point, ...]:
    """Replay a logged face or direct Reidemeister move, rechecking geometry."""
    if move.kind == "empty_unit_face":
        return apply_face_move(points, move)
    return apply_reidemeister_move(points, move)


def move_from_dict(record: dict) -> FaceMove | ReidemeisterMove:
    """Read either log kind from the JSON representation used by the catalog."""
    kind = record["kind"]
    cls = FaceMove if kind == "empty_unit_face" else ReidemeisterMove
    return cls(record["start_index"], tuple(Point(**p) for p in record["before"]),
               tuple(Point(**p) for p in record["after"]), kind)


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


def layer_lengths(points) -> tuple[int, int]:
    """Count planar unit edges on each layer, excluding vertical switches."""
    lengths = [0, 0]
    for a, b in zip(points, points[1:]):
        if a.z == b.z:
            lengths[a.z] += 1
    return tuple(lengths)


def redistribute_layers(points, *, max_moves: int = 120, max_seconds: float = 2,
                        candidate_filter=None) -> OptimizationResult:
    """Slide switches across empty vertical faces without lengthening the knot.

    Each accepted 2->2 move transfers one planar edge to the less-used layer.
    Flat geometry and crossing order stay fixed; the occupied-vertex check
    prevents sliding a switch across another strand. This greedy phase ends
    at equal lengths, a blocked switch, or the supplied budget.
    """
    if type(max_moves) is not int or max_moves < 0:
        raise ValueError("max_moves must be a non-negative integer")
    if not isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("max_seconds must be positive and finite")
    current = tuple(points)
    validate_cycle(current).raise_for_errors()
    deadline = monotonic() + max_seconds
    log = []
    for _ in range(max_moves):
        low, high = layer_lengths(current)
        if abs(low-high) <= 1:
            return OptimizationResult(current, tuple(log), "balanced")
        majority = 0 if low > high else 1
        body = current[:-1]
        occupied = set(body)
        accepted = None
        for i, a in enumerate(body):
            if monotonic() >= deadline:
                return OptimizationResult(current, tuple(log), "time_limit")
            b, c = body[(i+1) % len(body)], body[(i+2) % len(body)]
            if a.z == c.z:
                continue
            planar_layer = a.z if a.z == b.z else b.z
            if planar_layer != majority:
                continue
            corner = Point(a.x+c.x-b.x, a.y+c.y-b.y, a.z+c.z-b.z)
            before, after = (a, b, c), (a, corner, c)
            if corner in occupied or not _face_boundary(before, after):
                continue
            move = FaceMove(i, before, after)
            candidate = apply_face_move(current, move)
            if candidate_filter is None or candidate_filter(candidate):
                accepted = move, candidate
                break
        if accepted is None:
            return OptimizationResult(current, tuple(log), "layer_local_minimum")
        move, current = accepted
        log.append(move)
    return OptimizationResult(current, tuple(log), "move_limit")


def optimize_cycle(points, *, max_moves: int = 100, max_route_states: int = 5000,
                   balance_layers: bool = False, max_seconds: float | None = None,
                   candidate_filter=None) -> OptimizationResult:
    """Strictly improve (point count, canonical Cantor order) within a budget.

    Canonical comparison uses rotations only, so no reflection can silently
    change the knot's chirality. Returned coordinates retain the exact move
    endpoints, allowing replay from the unmodified original.
    With balance_layers, the difference in planar lengths is minimized before
    the Cantor tie-breaker, but fewer points always take precedence. A filter
    may restrict the supported output representation. max_seconds bounds an
    interactive attempt; a partial, fully certified result is returned.
    """
    if max_moves < 0:
        raise ValueError("max_moves must be non-negative")
    if type(max_route_states) is not int or max_route_states < 1:
        raise ValueError("max_route_states must be a positive integer")
    if max_seconds is not None and (not isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError("max_seconds must be positive and finite")
    deadline = None if max_seconds is None else monotonic() + max_seconds

    def expired():
        return deadline is not None and monotonic() >= deadline

    def measure_of(path):
        count, cantor = sequence_measure(canonicalize_cycle(path, include_reflections=False)[:-1])
        if balance_layers:
            lower, upper = layer_lengths(path)
            return count, abs(lower - upper), cantor
        return count, cantor

    current = tuple(points)
    validate_cycle(current).raise_for_errors()
    log = []
    for _ in range(max_moves):
        if expired():
            return OptimizationResult(current, tuple(log), "time_limit")
        measure = measure_of(current)
        best = None
        best_measure = measure
        analysis = analyze_reidemeister_moves(current, max_route_states=max_route_states)
        candidates = ((move, apply_reidemeister_move(current, move)) for move in analysis.moves)
        for move, candidate in chain(candidates, _moves(current)):
            if expired():
                break
            if candidate_filter is not None and not candidate_filter(candidate):
                continue
            candidate_measure = measure_of(candidate)
            if candidate_measure < best_measure:
                best = move, candidate
                best_measure = candidate_measure
        if best is None:
            return OptimizationResult(current, tuple(log), "time_limit" if expired() else "local_minimum",
                                      analysis.rejections)
        move, current = best
        log.append(move)
        if expired():
            return OptimizationResult(current, tuple(log), "time_limit")
    rejections = (analyze_reidemeister_moves(current, max_route_states=max_route_states).rejections
                  if log and deadline is None else ())
    return OptimizationResult(current, tuple(log), "move_limit", rejections)
