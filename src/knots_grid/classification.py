"""Conservative recognition from regular diagrams, never determinant alone.

Fox matrix: 2 * over - incoming_under - outgoing_under = 0.
The absolute first minor is the determinant. See
https://math.uchicago.edu/~dannyc/notes/knot_theory.pdf .
Signed Gauss words retain the crossing rotation data as well as over/under.
Only complete reference-diagram matches certify a nontrivial name.
"""

from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache

from .core import Point
from .generator import figure_eight_candidate, torus_knot_candidate
from .projection import score_projection
from .reidemeister import find_crossings
from .validator import validate_cycle


@dataclass(frozen=True, slots=True)
class Classification:
    name: str
    status: str
    determinant: int | None
    crossings: int
    evidence: str
    diagram_key: tuple


def signed_gauss_key(points) -> tuple:
    """Canonical signed diagram, ignoring cyclic start and orientation.

    Reflection is deliberately NOT included: a mirror flips every crossing
    sign. This key is a diagram certificate, not a complete knot invariant.
    Requires a regular projection; callers must check degeneracies separately.
    """
    pts = tuple(points)[:-1]
    events = []
    for label, crossing in enumerate(find_crossings(points)):
        lower, upper = crossing.lower_index, crossing.upper_index
        a, b = pts[(upper + 1) % len(pts)], pts[(upper - 1) % len(pts)]
        c, d = pts[(lower + 1) % len(pts)], pts[(lower - 1) % len(pts)]
        cross = (a.x - b.x) * (c.y - d.y) - (a.y - b.y) * (c.x - d.x)
        sign = 1 if cross > 0 else -1
        events.extend(((lower, label, 0, sign), (upper, label, 1, sign)))
    events = [event[1:] for event in sorted(events)]
    if not events:
        return ()
    variants = []
    for oriented in (events, list(reversed(events))):
        for start in range(len(events)):
            labels = {}
            word = []
            for label, over, sign in oriented[start:] + oriented[:start]:
                labels.setdefault(label, len(labels))
                word.append((labels[label], over, sign))
            variants.append(tuple(word))
    return min(variants)


def _integer_determinant(matrix):
    """Fraction-free elimination with exact integer arithmetic and pivoting."""
    a = [row[:] for row in matrix]
    n = len(a)
    if n == 0:
        return 1
    previous, sign = 1, 1
    for k in range(n - 1):
        pivot_row = next((i for i in range(k, n) if a[i][k]), None)
        if pivot_row is None:
            return 0
        if pivot_row != k:
            a[k], a[pivot_row] = a[pivot_row], a[k]
            sign = -sign
        pivot = a[k][k]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                a[i][j] = (a[i][j] * pivot - a[i][k] * a[k][j]) // previous
            a[i][k] = 0
        previous = pivot
    return sign * a[-1][-1]


def knot_determinant(points) -> int | None:
    """Return an exact Fox determinant, or None for a nonregular projection."""
    validate_cycle(points).raise_for_errors()
    if score_projection(points).metrics.degeneracies:
        return None
    crossings = find_crossings(points)
    n = len(crossings)
    if n == 0:
        return 1
    under = sorted(c.lower_index for c in crossings)
    matrix = [[0] * n for _ in range(n)]
    for row, crossing in zip(matrix, crossings):
        outgoing = bisect_right(under, crossing.lower_index) - 1
        over = (bisect_right(under, crossing.upper_index) - 1) % n
        row[over] += 2
        row[outgoing] -= 1
        row[(outgoing - 1) % n] -= 1
    return abs(_integer_determinant([row[:-1] for row in matrix[:-1]]))


@lru_cache(maxsize=1)
def _references():
    references = {}
    candidates = [("4_1", figure_eight_candidate(), "Knot Atlas 4_1 six-arc presentation")]
    candidates.extend((f"T(2,{q})", torus_knot_candidate(q), f"standard T(2,{q}) grid")
                      for q in range(3, 16, 2))
    for name, candidate, source in candidates:
        references[signed_gauss_key(candidate.points)] = (name, source)
        mirror = tuple(Point(-p.x, p.y, p.z) for p in candidate.points)
        # 4_1 is amphichiral. Torus-knot mirrors remain separate classes.
        mirror_name = name if name == "4_1" else f"mirror({name})"
        references[signed_gauss_key(mirror)] = (mirror_name, source + "; mirrored")
    return references


def classify_knot(points) -> Classification:
    """Certify reference diagrams; retain every other case as unknown."""
    pts = tuple(points)
    validate_cycle(pts).raise_for_errors()
    crossings = len(find_crossings(pts))
    determinant = knot_determinant(pts)
    if determinant is None:
        return Classification("unknown", "unknown", None, crossings,
                              "nonregular projection; no invariant asserted", ())
    key = signed_gauss_key(pts)
    if not key:
        return Classification("0_1", "certified", 1, 0,
                              "regular crossing-free planar diagram", key)
    match = _references().get(key)
    if match:
        name, source = match
        return Classification(name, "certified", determinant, crossings,
                              "complete signed diagram match: " + source, key)
    return Classification("unknown", "unknown", determinant, crossings,
                          "no complete reference match; determinant does not prove equivalence", key)
