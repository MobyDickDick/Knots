"""Turtle-compatible, certified minimization for the interactive studio."""

from .core import Point
from .generator import _points_to_code, make_candidate
from .optimization import OptimizationResult, optimize_cycle, redistribute_layers
from .reidemeister import find_crossings
from .validator import validate_cycle


def _encode_xy(points):
    """Normalize within the current layer frame, with a valid cyclic seam."""
    body = tuple(points)[:-1]
    bottom = min(p.z for p in body)
    planar = [(i, (body[(i+1) % len(body)].x-p.x, body[(i+1) % len(body)].y-p.y))
              for i, p in enumerate(body) if p.z == body[(i+1) % len(body)].z]
    reversals = [j for j, (_, direction) in enumerate(planar)
                 if direction == tuple(-v for v in planar[j-1][1])]
    if len(reversals) > 1:
        raise ValueError("Der Pfad enthält mehrere nicht codierbare Richtungsumkehrungen.")
    if reversals:
        index, (dx, dy) = planar[reversals[0]]
        if body[index].z != bottom:
            index = (index-1) % len(body)  # Begin at the switch preceding this edge.
        if body[index].z != bottom:
            raise ValueError("Kein Turtle-Start in der unteren Ebene.")
    else:
        index, (dx, dy) = next((i, d) for i, d in planar if body[i].z == bottom)
    origin = body[index]
    rotated = body[index:] + body[:index] + (origin,)
    transformed = [Point(dx*(p.x-origin.x) + dy*(p.y-origin.y),
                         -dy*(p.x-origin.x) + dx*(p.y-origin.y), p.z-bottom)
                   for p in rotated]
    trace = make_candidate(_points_to_code(transformed))
    if trace.points != tuple(transformed):
        raise ValueError("Der Turtle-Code rekonstruiert die Punkte nicht exakt.")
    return trace, {"cyclic_start": index, "origin": [origin.x, origin.y, bottom],
                   "east": [dx, dy]}


def encode_cycle(points):
    """Translate/rotate into an exact turtle frame, never reflect or rescale.

    Prefer the existing XY frame. If it cannot encode the cycle, try proper
    spatial rotations making X or Y the new vertical axis. Only rotations
    whose resulting height span is at most one are allowed. This admits short
    vertical rectangles without changing the code alphabet or the knot type.
    """
    try:
        return _encode_xy(points)
    except (ValueError, StopIteration):
        pass
    rotations = (
        ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
        ((0, 1, 0), (0, 0, -1), (-1, 0, 0)),
        ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
        ((0, 0, 1), (-1, 0, 0), (0, -1, 0)),
    )
    for matrix in rotations:
        rotated = tuple(Point(*(sum(c*v for c, v in zip(row, (p.x, p.y, p.z)))
                                for row in matrix)) for p in points)
        if max(p.z for p in rotated)-min(p.z for p in rotated) > 1:
            continue
        try:
            trace, transform = _encode_xy(rotated)
        except (ValueError, StopIteration):
            continue
        dx, dy = transform["east"]
        combined = [[dx*a+dy*b for a, b in zip(matrix[0], matrix[1])],
                    [-dy*a+dx*b for a, b in zip(matrix[0], matrix[1])], list(matrix[2])]
        index = transform["cyclic_start"]
        origin = points[index]
        return trace, {"cyclic_start": index, "origin": [origin.x, origin.y, origin.z],
                       "matrix": combined}
    raise ValueError("Der Pfad ist in keiner unterstützten Zweiebenen-Ausrichtung im Turtle-Format darstellbar.")


def apply_turtle_normalization(points, transform):
    """Replay a logged proper rigid rotation and translation, checking its frame."""
    body = tuple(points)[:-1]
    index = transform["cyclic_start"]
    origin = transform["origin"]
    if type(index) is not int or not 0 <= index < len(body):
        raise ValueError("invalid cyclic start")
    if not isinstance(origin, (list, tuple)) or len(origin) != 3 or any(type(v) is not int for v in origin):
        raise ValueError("invalid normalization origin")
    if "matrix" in transform:
        matrix = transform["matrix"]
    else:
        dx, dy = transform["east"]
        matrix = [[dx, dy, 0], [-dy, dx, 0], [0, 0, 1]]
    if (not isinstance(matrix, (list, tuple)) or len(matrix) != 3
            or any(not isinstance(row, (list, tuple)) or len(row) != 3 for row in matrix)
            or any(type(v) is not int for row in matrix for v in row)):
        raise ValueError("invalid rotation matrix")
    determinant = (matrix[0][0]*(matrix[1][1]*matrix[2][2]-matrix[1][2]*matrix[2][1])
                   - matrix[0][1]*(matrix[1][0]*matrix[2][2]-matrix[1][2]*matrix[2][0])
                   + matrix[0][2]*(matrix[1][0]*matrix[2][1]-matrix[1][1]*matrix[2][0]))
    if determinant != 1 or any(sum(a*b for a,b in zip(matrix[i],matrix[j])) != int(i == j)
                               for i in range(3) for j in range(3)):
        raise ValueError("normalization must be a proper rigid rotation, never a reflection")
    result = tuple(Point(*(sum(c*(v-o) for c,v,o in zip(row,(p.x,p.y,p.z),origin))
                           for row in matrix)) for p in body[index:]+body[:index]+(body[index],))
    validate_cycle(result).raise_for_errors()
    return result


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
    if apply_turtle_normalization(result.points, transform) != trace.points:
        raise RuntimeError("Die Normalisierung lässt sich nicht exakt wiederholen.")
    if len(trace.points) == 5:
        result = OptimizationResult(result.points, result.moves, "global_minimum", result.reidemeister_rejections)
    return points, result, trace, transform
