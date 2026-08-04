"""Crossings and combinatorial Reidemeister-move conditions.

The functions in this module deliberately report *candidates*.  Adjacency in
the Gauss word is necessary for a Reidemeister move; checking that the bounded
regions are empty is a separate geometric operation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .core import Point


@dataclass(frozen=True, slots=True)
class Crossing:
    """A transverse crossing of the two projected lattice layers."""

    coordinate: tuple[int, int]
    lower_index: int
    upper_index: int


@dataclass(frozen=True, slots=True)
class ReidemeisterReport:
    """Crossings satisfying the Gauss-word conditions for moves I--III."""

    crossings: tuple[Crossing, ...]
    type_i: tuple[int, ...]
    type_ii: tuple[tuple[int, int], ...]
    type_iii: tuple[tuple[int, int, int], ...]


def find_crossings(points: tuple[Point, ...] | list[Point]) -> tuple[Crossing, ...]:
    """Find genuine over/under crossings in the unshifted ``(x, y)`` projection.

    A layer-switch endpoint occupies both layers too, but is a bend of the
    embedded curve rather than a crossing and is therefore excluded.
    """

    pts = tuple(points)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    by_xy: dict[tuple[int, int], list[tuple[int, Point]]] = defaultdict(list)
    for index, point in enumerate(pts):
        by_xy[(point.x, point.y)].append((index, point))

    crossings: list[Crossing] = []
    for coordinate, occurrences in by_xy.items():
        if len(occurrences) != 2 or {point.z for _, point in occurrences} != {0, 1}:
            continue
        indices = {index for index, _ in occurrences}
        # Consecutive occurrences are the two ends of an actual layer switch.
        if any((index + 1) % len(pts) in indices for index in indices):
            continue
        axes: set[str] = set()
        transverse = True
        for index, point in occurrences:
            before = pts[(index - 1) % len(pts)]
            after = pts[(index + 1) % len(pts)]
            if before.z != point.z or after.z != point.z:
                transverse = False
                break
            if before.x == point.x == after.x and before.y != after.y:
                axes.add("vertical")
            elif before.y == point.y == after.y and before.x != after.x:
                axes.add("horizontal")
            else:
                transverse = False
                break
        if not transverse or axes != {"horizontal", "vertical"}:
            continue
        lower = next(index for index, point in occurrences if point.z == 0)
        upper = next(index for index, point in occurrences if point.z == 1)
        crossings.append(Crossing(coordinate, lower, upper))
    return tuple(sorted(crossings, key=lambda crossing: crossing.coordinate))


def reidemeister_conditions(
    points: tuple[Point, ...] | list[Point],
) -> ReidemeisterReport:
    """Evaluate the local Gauss-word conditions for Reidemeister I, II and III.

    Type I has two adjacent visits of one crossing.  Type II has two crossings
    adjacent on both participating arcs, with one arc over at both crossings.
    Type III has three crossings for which every pair is adjacent on an arc.
    The result is useful as a safe shortlist for a later geometric move engine.
    """

    crossings = find_crossings(points)
    events: list[tuple[int, int, bool]] = []
    for crossing_id, crossing in enumerate(crossings):
        events.extend(((crossing.lower_index, crossing_id, False),
                       (crossing.upper_index, crossing_id, True)))
    events.sort()
    if not events:
        return ReidemeisterReport(crossings, (), (), ())

    neighbours: dict[frozenset[int], list[tuple[bool, bool]]] = defaultdict(list)
    type_i: set[int] = set()
    for position, (_, first, first_over) in enumerate(events):
        _, second, second_over = events[(position + 1) % len(events)]
        if first == second:
            type_i.add(first)
        else:
            neighbours[frozenset((first, second))].append((first_over, second_over))

    type_ii: list[tuple[int, int]] = []
    for pair, status in neighbours.items():
        # Both boundary arcs must be present. On each, the same strand remains
        # over (or under) at the two crossings.
        if len(status) >= 2 and all(a == b for a, b in status[:2]):
            type_ii.append(tuple(sorted(pair)))

    adjacency = {pair for pair, status in neighbours.items() if status}
    type_iii: list[tuple[int, int, int]] = []
    count = len(crossings)
    for a in range(count):
        for b in range(a + 1, count):
            for c in range(b + 1, count):
                if all(frozenset(pair) in adjacency for pair in ((a, b), (a, c), (b, c))):
                    type_iii.append((a, b, c))

    return ReidemeisterReport(
        crossings,
        tuple(sorted(type_i)),
        tuple(sorted(set(type_ii))),
        tuple(type_iii),
    )
