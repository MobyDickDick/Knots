"""Turtle-compatible, certified minimization for the interactive studio."""

from .core import Point
from .generator import _points_to_code, make_candidate
from .optimization import OptimizationResult, optimize_cycle, redistribute_layers
from .reidemeister import find_crossings
from .validator import validate_cycle


def encode_cycle(points):
    """Choose a cyclic start, translate and rotate (never reflect) for turtle.

    The returned transform describes the entire coordinate change. All-upper
    planar cycles may be translated down; mixed-layer cycles retain z exactly.
    Some valid spatial cycles cannot use commands 0..3 (a planar U-turn after
    a layer switch). The studio conservatively excludes those intermediate
    candidates so that every displayed/exported code remains exact.
    """
    body = tuple(points)[:-1]
    bottom = min(p.z for p in body)
    index = next(i for i, p in enumerate(body)
                 if p.z == bottom and p.z == body[(i + 1) % len(body)].z)
    origin = body[index]
    following = body[(index + 1) % len(body)]
    dx, dy = following.x - origin.x, following.y - origin.y
    rotated = body[index:] + body[:index] + (origin,)
    transformed = [Point(dx*(p.x-origin.x) + dy*(p.y-origin.y),
                         -dy*(p.x-origin.x) + dx*(p.y-origin.y), p.z-bottom)
                   for p in rotated]
    trace = make_candidate(_points_to_code(transformed))
    if trace.points != tuple(transformed):
        raise ValueError("Der Turtle-Code rekonstruiert die Punkte nicht exakt.")
    return trace, {"cyclic_start": index, "origin": [origin.x, origin.y, bottom],
                   "east": [dx, dy]}


def _encodable(points):
    try:
        encode_cycle(points)
    except (ValueError, StopIteration):
        return False
    return True


def minimize_points(raw_points, *, max_moves=120, max_seconds=8):
    """Validate bounded input, minimize and balance via replayable isotopies."""
    if not isinstance(raw_points, list) or not 5 <= len(raw_points) <= 6000:
        raise ValueError("Die Punktfolge muss 5 bis 6000 Einträge enthalten.")
    points = []
    for p in raw_points:
        if (not isinstance(p, list) or len(p) != 3 or any(type(v) is not int for v in p)
                or any(abs(v) > 10000 for v in p[:2]) or p[2] not in (0, 1)):
            raise ValueError("Ungültige Gitterkoordinaten.")
        points.append(Point(*p))
    points = tuple(points)
    validate_cycle(points).raise_for_errors()
    if len(find_crossings(points)) > 256:
        raise ValueError("Die interaktive Suche unterstützt höchstens 256 Kreuzungen.")
    if not _encodable(points):
        raise ValueError("Der Ausgangspfad ist nicht im Turtle-Format 0..3 darstellbar.")
    result = optimize_cycle(points, max_moves=max_moves, max_route_states=200,
                            balance_layers=True, max_seconds=max_seconds*0.75,
                            candidate_filter=_encodable, compress_coordinates=True)
    distribution = redistribute_layers(result.points, max_moves=max_moves-len(result.moves),
                                        max_seconds=max_seconds*0.25, candidate_filter=_encodable)
    status = result.status
    if len(result.moves)+len(distribution.moves) >= max_moves:
        status = "move_limit"
    if distribution.moves and status == "local_minimum":
        status = "redistributed"
    result = OptimizationResult(distribution.points, result.moves+distribution.moves, status,
                                result.reidemeister_rejections)
    trace, transform = encode_cycle(result.points)
    return points, result, trace, transform
