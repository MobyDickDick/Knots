"""Geometric, replayable Reidemeister reductions and triangle slides.

Bounded faces are traced in the *unshifted* unit-edge projection. Gauss-word
conditions only shortlist them; a simple polygon and an empty interior are
required. I contracts an empty curl to its vertical crossing fibre. II and
III reroute a flat top/bottom arc across a simple projected disk. That arc
can be lifted above (or below) the slab during the isotopy, swept over the
disk, then lowered. Only the resulting lattice paths, not the continuous
intermediate isotopy, are required to lie in Z² x {0,1}.

III requires a top/middle/bottom ordering, not a cyclic over/under triangle.
Routing is deliberately bounded and conservative: some legitimate moves
need more lattice room or a non-flat moving arc and are reported as rejected.
No diagram or invariant equality is used as an isotopy certificate.
"""

from collections import defaultdict, deque
from dataclasses import dataclass

from .core import Point
from .projection import score_projection
from .reidemeister import reidemeister_conditions
from .validator import validate_cycle


@dataclass(frozen=True, slots=True)
class ReidemeisterRegion:
    move_type: str
    crossing_ids: tuple[int, ...]
    polygon: tuple[tuple[int, int], ...]
    # Each side follows the original knot, forwards or backwards, including
    # the two crossing occurrences. Switch vertices remain in these indices.
    sides: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class MoveRejection:
    move_type: str
    crossing_ids: tuple[int, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class ReidemeisterMove:
    start_index: int
    before: tuple[Point, ...]
    after: tuple[Point, ...]
    kind: str


@dataclass(frozen=True, slots=True)
class ReidemeisterAnalysis:
    regions: tuple[ReidemeisterRegion, ...]
    moves: tuple[ReidemeisterMove, ...]
    rejections: tuple[MoveRejection, ...]


def _xy(p):
    return p.x, p.y


def _area(polygon):
    return sum(a[0] * b[1] - b[0] * a[1]
               for a, b in zip(polygon, polygon[1:] + polygon[:1]))


def _location(q, polygon):
    """Exact point-in-orthogonal-polygon: -1 outside, 0 boundary, 1 inside.

    Accepts integer or half-integer edge midpoints (both exact in binary).
    """
    x, y = q
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if ((a[0] == b[0] == x and min(a[1], b[1]) <= y <= max(a[1], b[1]))
                or (a[1] == b[1] == y and min(a[0], b[0]) <= x <= max(a[0], b[0]))):
            return 0
        if (a[1] > y) != (b[1] > y) and a[0] > x:
            inside = not inside
    return 1 if inside else -1


def _faces(body):
    graph = defaultdict(set)
    n = len(body)
    for i, a in enumerate(body):
        b = body[(i + 1) % n]
        if _xy(a) != _xy(b):
            graph[_xy(a)].add(_xy(b))
            graph[_xy(b)].add(_xy(a))
    directions = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}
    ordered = {a: sorted(bs, key=lambda b: directions[b[0] - a[0], b[1] - a[1]])
               for a, bs in graph.items()}
    seen = set()
    for a in sorted(graph):
        for b in ordered[a]:
            if (a, b) in seen:
                continue
            edge, polygon = (a, b), []
            while edge not in seen:
                seen.add(edge)
                u, v = edge
                polygon.append(u)
                neighbours = ordered[v]
                # Clockwise from the reverse edge keeps the bounded face left.
                edge = v, neighbours[(neighbours.index(u) - 1) % len(neighbours)]
            poly = tuple(polygon)
            if edge == (a, b) and len(poly) == len(set(poly)) and _area(poly) > 0:
                yield poly


def _side_indices(body, coordinates):
    """Recover an actual strand from a projected face side, including switches."""
    n = len(body)
    for start, p in enumerate(body):
        if _xy(p) != coordinates[0]:
            continue
        for direction in (1, -1):
            indices = [start]
            position = 0
            for step in range(1, n):
                index = (start + direction * step) % n
                xy = _xy(body[index])
                if xy != coordinates[position]:
                    position += 1
                    if position >= len(coordinates) or xy != coordinates[position]:
                        break
                indices.append(index)
                if position == len(coordinates) - 1:
                    return tuple(indices)
    return ()


def _regions(points):
    body = points[:-1]
    report = reidemeister_conditions(points)
    shortlist = {"I": {(a,) for a in report.type_i},
                 "II": set(report.type_ii), "III": set(report.type_iii)}
    if score_projection(points).metrics.degeneracies:
        return (), (MoveRejection("all", (), "nonregular projection"),)
    by_xy = {c.coordinate: i for i, c in enumerate(report.crossings)}
    regions, rejected, found = [], [], set()
    for polygon in _faces(body):
        positions = [i for i, xy in enumerate(polygon) if xy in by_xy]
        if len(positions) not in (1, 2, 3):
            continue
        kind = {1: "I", 2: "II", 3: "III"}[len(positions)]
        ids = tuple(sorted(by_xy[polygon[i]] for i in positions))
        if ids not in shortlist[kind]:
            continue
        found.add((kind, ids))
        sides = []
        for j, start in enumerate(positions):
            end = positions[(j + 1) % len(positions)]
            size = (end - start) % len(polygon) or len(polygon)
            coordinates = tuple(polygon[(start + k) % len(polygon)] for k in range(size + 1))
            sides.append(_side_indices(body, coordinates))
        reason = None
        if not all(sides):
            reason = "face boundary does not follow the participating strands"
        elif any(_location(_xy(p), polygon) == 1 for p in body):
            reason = "region contains another strand"
        elif any(_location(((a.x + b.x) / 2, (a.y + b.y) / 2), polygon) == 1
                 for a, b in zip(points, points[1:])):
            reason = "region contains another edge"
        elif kind == "II" and sorted((body[s[0]].z, body[s[-1]].z) for s in sides) != [(0, 0), (1, 1)]:
            reason = "bigon has inconsistent over/under information"
        elif kind == "III" and sorted(body[s[0]].z + body[s[-1]].z for s in sides) != [0, 1, 2]:
            reason = "triangle has cyclic over/under information; no top/middle/bottom ordering"
        if reason:
            rejected.append(MoveRejection(kind, ids, reason))
        else:
            regions.append(ReidemeisterRegion(kind, ids, polygon, tuple(sides)))
    for kind, candidates in shortlist.items():
        for ids in sorted(candidates):
            if (kind, ids) not in found:
                rejected.append(MoveRejection(kind, ids, "no simple empty bounded face"))
    return tuple(regions), tuple(rejected)


def _forward(side, n):
    return side if side[1] == (side[0] + 1) % n else tuple(reversed(side))


def _replace(points, move):
    body = points[:-1]
    if not 0 <= move.start_index < len(body):
        raise ValueError("invalid move start_index")
    rotated = body[move.start_index:] + body[:move.start_index]
    if (len(move.before) < 2 or len(move.before) >= len(body)
            or rotated[:len(move.before)] != move.before):
        raise ValueError("move does not match this path")
    if len(move.after) < 2 or (move.before[0], move.before[-1]) != (move.after[0], move.after[-1]):
        raise ValueError("move endpoints differ")
    result = move.after + rotated[len(move.before):] + (rotated[0],)
    validate_cycle(result).raise_for_errors()
    if score_projection(result).metrics.degeneracies:
        raise ValueError("result has a nonregular projection")
    return result


def _extended_side(body, side):
    side = _forward(side, len(body))
    indices = ((side[0] - 1) % len(body),) + side + ((side[-1] + 1) % len(body),)
    if len(set(indices)) != len(indices):
        return ()
    before = tuple(body[i] for i in indices)
    if len({p.z for p in before}) != 1 or len({_xy(p) for p in before}) != len(before):
        return ()
    return indices


def _cross_sign(body, index, direction, moving_layer):
    a, b = body[(index - 1) % len(body)], body[(index + 1) % len(body)]
    fixed = b.x - a.x, b.y - a.y
    cross = direction[0] * fixed[1] - direction[1] * fixed[0]
    return (1 if cross > 0 else -1) * (1 if moving_layer else -1)


def _route(points, region, indices, max_states):
    """Shortest supported flat reroute, bounded by states and a three-cell collar.

    Old arc interiors are forbidden so the swept polygon is simple. III may
    cross each stationary strand only *beyond* its central crossing, in the
    reverse order and with unchanged crossing signs.
    """
    body, n = points[:-1], len(points) - 1
    before = tuple(body[i] for i in indices)
    layer = before[0].z
    occupied = defaultdict(list)
    for i, p in enumerate(body):
        if i not in indices[1:-1]:
            occupied[_xy(p)].append(i)
    forbidden = {_xy(p) for p in before[1:-1]}
    allowed, expected = {}, []
    if region.move_type == "III":
        crossings = reidemeister_conditions(points).crossings
        selected = {_xy(before[1]), _xy(before[-2])}
        center = next(c for i, c in enumerate(crossings)
                      if i in region.crossing_ids and c.coordinate not in selected)
        events = {i for c in crossings for i in (c.lower_index, c.upper_index)}
        for role, old in enumerate((indices[1], indices[-2])):
            crossing = next(c for c in crossings if c.coordinate == _xy(body[old]))
            fixed = crossing.lower_index if layer else crossing.upper_index
            center_index = next((i for i in (center.lower_index, center.upper_index)
                                 if any(fixed in s and i in s for s in region.sides)), None)
            if center_index is None:
                return None, "stationary triangle sides cannot be reconstructed"
            side = next(s for s in region.sides if fixed in s and center_index in s)
            oriented = side if side[-1] == center_index else tuple(reversed(side))
            direction = 1 if oriented[1] == (oriented[0] + 1) % n else -1
            i = (center_index + direction) % n
            for _ in range(n):
                if i in events or i in indices:
                    break
                allowed[i] = role
                i = (i + direction) % n
            old_position = indices.index(old)
            a, b = before[old_position - 1], before[old_position + 1]
            tangent = ((b.x - a.x) // 2, (b.y - a.y) // 2)
            expected.append((role, _cross_sign(body, fixed, tangent, layer)))
        expected.reverse()
    start, end = _xy(before[0]), _xy(before[-1])
    min_x = min(x for x, _ in region.polygon) - 3
    max_x = max(x for x, _ in region.polygon) + 3
    min_y = min(y for _, y in region.polygon) - 3
    max_y = max(y for _, y in region.polygon) + 3
    # State includes the straight continuation forced by a transverse crossing.
    initial = (start, None, 0)
    queue, parents = deque([initial]), {initial: None}
    exhausted = False
    while queue:
        state = queue.popleft()
        xy, forced, progress = state
        if xy == end and progress == len(expected):
            path, cursor = [], state
            while cursor is not None:
                path.append(cursor[0])
                cursor = parents[cursor]
            path.reverse()
            if len(set(path)) == len(path):
                return tuple(Point(x, y, layer) for x, y in path), None
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            if forced is not None and forced != (dx, dy):
                continue
            q = xy[0] + dx, xy[1] + dy
            if not (min_x <= q[0] <= max_x and min_y <= q[1] <= max_y):
                continue
            if q == start or q in forbidden:
                continue
            new_progress, new_forced = progress, None
            if q in occupied and q != end:
                if len(occupied[q]) != 1 or progress == len(expected):
                    continue
                i = occupied[q][0]
                a, p, b = body[(i - 1) % n], body[i], body[(i + 1) % n]
                straight = (a.z == p.z == b.z and
                            (a.x + b.x, a.y + b.y) == (2 * p.x, 2 * p.y))
                if (not straight or p.z == layer or i not in allowed
                        or (b.x - a.x) * dx + (b.y - a.y) * dy != 0
                        or expected[progress] != (allowed[i], _cross_sign(body, i, (dx, dy), layer))):
                    continue
                new_progress += 1
                new_forced = dx, dy
            elif q == end and (forced is not None or progress != len(expected)):
                continue
            next_state = q, new_forced, new_progress
            if next_state not in parents:
                if len(parents) >= max_states:
                    exhausted = True
                    continue
                parents[next_state] = state
                queue.append(next_state)
    return None, ("route state limit reached" if exhausted else "no supported lattice route in three-cell collar")


def _certify_slide(points, region, indices, after):
    """Check the projected swept disk and its precise stationary tangle."""
    body, n = points[:-1], len(points) - 1
    before = tuple(body[i] for i in indices)
    if any(p.z != before[0].z for p in after):
        raise ValueError("moving arc must remain in one layer")
    polygon = tuple(_xy(p) for p in before + tuple(reversed(after[1:-1])))
    if len(set(polygon)) != len(polygon) or not _area(polygon):
        raise ValueError("reroute does not sweep a simple disk")
    move = ReidemeisterMove(indices[0], before, after, "reidemeister_" + region.move_type)
    result = _replace(points, move)
    old_crossings = reidemeister_conditions(points).crossings
    new_crossings = reidemeister_conditions(result).crossings
    old_coords = {c.coordinate for c in old_crossings}
    new_coords = {c.coordinate for c in new_crossings}
    selected = {_xy(before[1]), _xy(before[-2])}
    new_arc = {_xy(p) for p in after[1:-1]}
    added = new_coords - old_coords
    if old_coords - new_coords != selected:
        raise ValueError("reroute changes unrelated crossings")
    if region.move_type == "II":
        if added:
            raise ValueError("type II must remove exactly two crossings")
        expected_components = 1
        center = None
    else:
        center = next(old_crossings[i].coordinate for i in region.crossing_ids
                      if old_crossings[i].coordinate not in selected)
        if len(added) != 2 or not added <= new_arc or _location(center, polygon) != 1:
            raise ValueError("type III must slide across the central crossing")
        expected_components = 2
    # The fixed tangle must enter/leave this disk only at the prescribed
    # crossings, never along its boundary or through the attachment tails.
    boundary_crossings = selected | added
    fixed = set(range(n)) - set(indices[1:-1])
    inside = set()
    for i in fixed:
        xy = _xy(body[i])
        location = _location(xy, polygon)
        if i in (indices[0], indices[-1]):
            continue
        if location == 0 and xy not in boundary_crossings:
            raise ValueError("another strand touches the swept disk boundary")
        if location >= 0:
            inside.add(i)
    # Midpoints detect a unit edge entering the disk with both ends on its
    # boundary (including a chord between the fixed attachment vertices).
    for i in fixed:
        j = (i + 1) % n
        if j not in fixed:
            continue
        a, b = body[i], body[j]
        mid = ((a.x + b.x) / 2, (a.y + b.y) / 2)
        if _location(mid, polygon) >= 0 and (i not in inside or j not in inside):
            raise ValueError("an attachment tail enters the swept disk")
    components = []
    unseen = set(inside)
    while unseen:
        seed = min(unseen)
        component, stack = set(), [seed]
        while stack:
            i = stack.pop()
            if i not in unseen:
                continue
            unseen.remove(i)
            component.add(i)
            stack.extend(((i - 1) % n, (i + 1) % n))
        components.append(component)
    if len(components) != expected_components:
        raise ValueError("swept disk contains unrelated strands")
    for component in components:
        visits = [_xy(body[i]) for i in component if _xy(body[i]) in boundary_crossings]
        if len(visits) != 2:
            raise ValueError("stationary strand does not cross the disk twice")
        if center is not None and (sum(xy in selected for xy in visits) != 1
                                   or not any(_xy(body[i]) == center for i in component)):
            raise ValueError("stationary strands do not form the type III tangle")
    internal_crossings = {c.coordinate for c in old_crossings if _location(c.coordinate, polygon) == 1}
    if internal_crossings != ({center} if center is not None else set()):
        raise ValueError("swept disk contains unrelated crossings")
    if center is not None:
        # Compare crossing order/signs on each fixed strand. Pairing is fixed
        # by its disk component, not by coordinate-sorted crossing labels.
        layer = before[0].z
        roles = []
        for component in components:
            old_xy = next(_xy(body[i]) for i in component if _xy(body[i]) in selected)
            new_xy = next(_xy(body[i]) for i in component if _xy(body[i]) in added)
            old_i = next(i for i in indices if _xy(body[i]) == old_xy)
            new_i = next(i for i, p in enumerate(after) if _xy(p) == new_xy)
            fixed_i = next(i for i in component if _xy(body[i]) == old_xy)
            new_fixed = next(i for i in component if _xy(body[i]) == new_xy)
            k = indices.index(old_i)
            old_tangent = (before[k + 1].x - before[k].x, before[k + 1].y - before[k].y)
            new_tangent = (after[new_i + 1].x - after[new_i].x, after[new_i + 1].y - after[new_i].y)
            if _cross_sign(body, fixed_i, old_tangent, layer) != _cross_sign(body, new_fixed, new_tangent, layer):
                raise ValueError("type III changes a crossing sign")
            roles.append((k, new_i))
        roles.sort()
        if roles[0][1] <= roles[1][1]:
            raise ValueError("type III must reverse the moving crossing order")
    return result


def apply_reidemeister_move(points, move: ReidemeisterMove):
    """Reconstruct the region and verify the entire certificate on every replay."""
    pts = tuple(points)
    validate_cycle(pts).raise_for_errors()
    regions, _ = _regions(pts)
    body = pts[:-1]
    failures = []
    for region in regions:
        if move.kind != "reidemeister_" + region.move_type:
            continue
        for side in region.sides:
            if region.move_type == "I":
                indices = _forward(side, len(body))
                before = tuple(body[i] for i in indices)
                if (move.start_index == indices[0] and move.before == before
                        and move.after == (before[0], before[-1])):
                    return _replace(pts, move)
            else:
                indices = _extended_side(body, side)
                if (indices and move.start_index == indices[0]
                        and move.before == tuple(body[i] for i in indices)):
                    try:
                        return _certify_slide(pts, region, indices, move.after)
                    except ValueError as error:
                        # A strand may bound two different faces. The replay
                        # must try both certificates, not depend on face order.
                        failures.append(str(error))
    raise ValueError("no matching empty Reidemeister region or supported moving arc"
                     + (": " + "; ".join(dict.fromkeys(failures)) if failures else ""))


def analyze_reidemeister_moves(points, *, max_route_states: int = 5000):
    """Return verified regions, executable moves, and explicit rejection reasons.

    I and II are reductions only; III slides in either direction if a flat
    extreme strand and the bounded routing search support them. The optimizer
    separately enforces its point-count/Cantor objective.
    """
    if type(max_route_states) is not int or max_route_states < 1:
        raise ValueError("max_route_states must be a positive integer")
    pts = tuple(points)
    validate_cycle(pts).raise_for_errors()
    regions, rejected = _regions(pts)
    rejected, moves = list(rejected), []
    body = pts[:-1]
    for region in regions:
        reasons, found = [], False
        for side in region.sides:
            if region.move_type == "I":
                indices = _forward(side, len(body))
                before = tuple(body[i] for i in indices)
                after = before[0], before[-1]
            else:
                indices = _extended_side(body, side)
                if not indices:
                    reasons.append("moving arc and its collar are not flat in one layer")
                    continue
                before = tuple(body[i] for i in indices)
                after, reason = _route(pts, region, indices, max_route_states)
                if after is None:
                    reasons.append(reason)
                    continue
            move = ReidemeisterMove(indices[0], before, after, "reidemeister_" + region.move_type)
            try:
                if region.move_type == "I":
                    _replace(pts, move)
                else:
                    _certify_slide(pts, region, indices, after)
            except ValueError as error:
                reasons.append(str(error))
                continue
            if move not in moves:
                moves.append(move)
            found = True
        if not found:
            rejected.append(MoveRejection(region.move_type, region.crossing_ids,
                                          "; ".join(dict.fromkeys(reasons))))
    return ReidemeisterAnalysis(regions, tuple(moves), tuple(rejected))
