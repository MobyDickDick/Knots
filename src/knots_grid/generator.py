"""Validated candidate generation for two-layer grid paths."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .core import Direction, Point, TraceResult, trace_turtle
from .validator import validate_cycle


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Bounds and layer settings for simple rectangular candidates.

    Width and height are selected independently and inclusively from
    ``min_side_length`` through ``max_side_length``.  A layered candidate lifts
    one complete side to the other layer, producing exactly two layer changes.
    """

    min_side_length: int = 2
    max_side_length: int = 8
    layer_probability: float = 0.5

    def __post_init__(self) -> None:
        if self.min_side_length < 1:
            raise ValueError("min_side_length must be at least 1")
        if self.max_side_length < self.min_side_length:
            raise ValueError("max_side_length must not be smaller than min_side_length")
        if not 0.0 <= self.layer_probability <= 1.0:
            raise ValueError("layer_probability must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Settings for randomized local search beyond plain rectangles.

    Search starts with a planar rectangle and applies a random number of local
    modifications.  A modification either replaces one edge with a rectangular
    three-edge detour or lifts that edge to the other layer.  If a requested
    lift is blocked, a detour is attempted instead so every successful search
    step still makes the candidate more varied.
    """

    min_side_length: int = 2
    max_side_length: int = 8
    min_search_steps: int = 4
    max_search_steps: int = 12
    layer_probability: float = 0.25

    def __post_init__(self) -> None:
        if self.min_side_length < 1:
            raise ValueError("min_side_length must be at least 1")
        if self.max_side_length < self.min_side_length:
            raise ValueError("max_side_length must not be smaller than min_side_length")
        if self.min_search_steps < 0:
            raise ValueError("min_search_steps must be non-negative")
        if self.max_search_steps < self.min_search_steps:
            raise ValueError("max_search_steps must not be smaller than min_search_steps")
        if not 0.0 <= self.layer_probability <= 1.0:
            raise ValueError("layer_probability must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class TravelConfig:
    """Settings for permutation-based grid-diagram generation.

    The generator chooses ``point_count`` X/O marker pairs on a square grid.
    Each marker row and each marker column is used exactly once, which is the
    grid-diagram analogue of assigning every prescribed waypoint its own x- and
    y-coordinate.  Random permutations are tried up to ``max_attempts`` times
    until their horizontal-then-vertical travel describes one closed component.
    """

    point_count: int = 10
    max_attempts: int = 500

    def __post_init__(self) -> None:
        if self.point_count < 2:
            raise ValueError("point_count must be at least 2")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


def trefoil_candidate() -> TraceResult:
    """Construct a genuine trefoil from its minimal 5x5 grid diagram.

    Horizontal grid segments use layer zero and vertical segments layer one,
    so every interior intersection has unambiguous under/over information.
    Unlike the local detours used by :func:`search_candidate`, this diagram is
    not obtained from an unknot by isotopy-preserving expansions.
    """

    # X and O columns by row for a standard grid-number-five trefoil.
    return _grid_diagram_candidate((0, 1, 2, 3, 4), (2, 3, 4, 0, 1))


def torus_knot_candidate(crossings: int) -> TraceResult:
    """Return the reduced grid diagram of the torus knot ``T(2, crossings)``.

    ``crossings`` must be odd and at least three.  These knots are prime and
    pairwise distinct: their determinants equal ``crossings``.  The grid size
    ``crossings + 2`` is the arc index of ``T(2, crossings)``, so this standard
    diagram cannot be destabilized further; it also contains no reducing
    Reidemeister-I or -II configuration.
    """

    if crossings < 3 or crossings % 2 == 0:
        raise ValueError("crossings must be an odd integer of at least 3")
    size = crossings + 2
    candidate = _grid_diagram_candidate(
        tuple(range(size)), tuple((column + 2) % size for column in range(size))
    )

    # Keep the mathematical construction and our combinatorial reducer in
    # lockstep.  A future change to either must not silently emit a reducible
    # catalog entry.
    from .reidemeister import reidemeister_conditions

    report = reidemeister_conditions(candidate.points)
    if report.type_i or report.type_ii:
        raise RuntimeError("standard torus-knot diagram unexpectedly became reducible")
    return candidate


def _grid_diagram_candidate(
    x_columns: tuple[int, ...], o_columns: tuple[int, ...]
) -> TraceResult:
    size = len(x_columns)
    if size < 2 or len(o_columns) != size:
        raise ValueError("a grid diagram needs equally many X and O markers")
    expected = set(range(size))
    if set(x_columns) != expected or set(o_columns) != expected:
        raise ValueError("X and O columns must each be a permutation of the grid columns")

    o_row_by_column = {column: row for row, column in enumerate(o_columns)}
    # Turtle traces start facing east, so choose an east-going horizontal arc
    # as the cyclic start. Every non-degenerate grid diagram has either such
    # an arc or can be reflected; requiring it here keeps encoding explicit.
    try:
        row = next(row for row in range(size) if o_columns[row] < x_columns[row])
    except StopIteration as error:
        raise ValueError("grid diagram has no east-going horizontal arc") from error
    points = [Point(o_columns[row], row, 0)]
    visited_rows: set[int] = set()
    while row not in visited_rows:
        visited_rows.add(row)
        x_column = x_columns[row]
        _append_axis_steps(points, x_column, row, 0)
        points.append(points[-1].switched_layer())
        row = o_row_by_column[x_column]
        _append_axis_steps(points, x_column, row, 1)
        points.append(points[-1].switched_layer())
    if len(visited_rows) != size or points[-1] != points[0]:
        raise ValueError("grid markers do not describe one closed knot component")

    code = _points_to_code(points)
    return make_candidate(code)


def _append_axis_steps(points: list[Point], x: int, y: int, z: int) -> None:
    target = Point(x, y, z)
    while points[-1] != target:
        current = points[-1]
        dx = 0 if current.x == x else (1 if x > current.x else -1)
        dy = 0 if current.y == y else (1 if y > current.y else -1)
        points.append(Point(current.x + dx, current.y + dy, z))


def make_candidate(code: str) -> TraceResult:
    """Trace a hand-written turtle code and require a valid cycle."""

    result = trace_turtle(code)
    validate_cycle(result.points).raise_for_errors()
    return result


def generate_candidate(
    *,
    seed: int | None = None,
    config: GeneratorConfig = GeneratorConfig(),
) -> TraceResult:
    """Generate one reproducible, validated rectangular candidate.

    The same ``seed`` and ``config`` always produce the same turtle code.  The
    generated rectangle may have unequal width and height.  Depending on
    ``layer_probability``, one randomly selected side is lifted to layer one.
    """

    return _generate_candidate(Random(seed), config)


def generate_candidates(
    count: int,
    *,
    seed: int | None = None,
    config: GeneratorConfig = GeneratorConfig(),
) -> tuple[TraceResult, ...]:
    """Generate ``count`` candidates from one reproducible random stream."""

    if count < 0:
        raise ValueError("count must be non-negative")

    random = Random(seed)
    return tuple(_generate_candidate(random, config) for _ in range(count))


def search_candidate(
    *,
    seed: int | None = None,
    config: SearchConfig = SearchConfig(),
) -> TraceResult:
    """Find one varied candidate through reproducible local modifications."""

    return _search_candidate(Random(seed), config)


def search_candidates(
    count: int,
    *,
    seed: int | None = None,
    config: SearchConfig = SearchConfig(),
) -> tuple[TraceResult, ...]:
    """Find ``count`` varied candidates using one reproducible random stream."""

    if count < 0:
        raise ValueError("count must be non-negative")

    random = Random(seed)
    return tuple(_search_candidate(random, config) for _ in range(count))


def travel_candidate(
    *,
    seed: int | None = None,
    config: TravelConfig = TravelConfig(),
) -> TraceResult:
    """Generate a closed candidate by trying random travels through markers.

    This strategy avoids the previous open-ended local modification loop.  It
    first creates two random permutations of ``point_count`` grid columns: one
    permutation for X markers and one for O markers.  Because both permutations
    use every row/column once, no two marker waypoints share an x- or
    y-coordinate.  The resulting grid diagram routes horizontally on layer 0
    and vertically on layer 1, so projected crossings get deterministic
    over/under information instead of invalid same-layer intersections.
    """

    return _travel_candidate(Random(seed), config)


def travel_candidates(
    count: int,
    *,
    seed: int | None = None,
    config: TravelConfig = TravelConfig(),
) -> tuple[TraceResult, ...]:
    """Generate ``count`` permutation-travel candidates from one random stream."""

    if count < 0:
        raise ValueError("count must be non-negative")

    random = Random(seed)
    return tuple(_travel_candidate(random, config) for _ in range(count))


def _generate_candidate(random: Random, config: GeneratorConfig) -> TraceResult:
    width = random.randint(config.min_side_length, config.max_side_length)
    height = random.randint(config.min_side_length, config.max_side_length)
    side_lengths = (width, height, width, height)

    lifted_side: int | None = None
    if random.random() < config.layer_probability:
        lifted_side = random.randrange(len(side_lengths))

    parts: list[str] = []
    for side, length in enumerate(side_lengths):
        # The first side continues east.  Every subsequent side starts with a
        # left turn and then continues straight for the remaining steps.
        side_code = ("0" if side == 0 else "1") + "0" * (length - 1)
        if side == lifted_side:
            parts.extend(("3", side_code, "3"))
        else:
            parts.append(side_code)

    return make_candidate("".join(parts))


def _travel_candidate(random: Random, config: TravelConfig) -> TraceResult:
    columns = list(range(config.point_count))

    for _ in range(config.max_attempts):
        x_columns = columns.copy()
        o_columns = columns.copy()
        random.shuffle(x_columns)
        random.shuffle(o_columns)

        if any(x_column == o_column for x_column, o_column in zip(x_columns, o_columns)):
            continue

        try:
            return _grid_diagram_candidate(tuple(x_columns), tuple(o_columns))
        except ValueError:
            continue

    raise RuntimeError(
        "could not find a one-component crossing-safe travel diagram "
        f"after {config.max_attempts} attempts"
    )


def _search_candidate(random: Random, config: SearchConfig) -> TraceResult:
    rectangle = _generate_candidate(
        random,
        GeneratorConfig(
            min_side_length=config.min_side_length,
            max_side_length=config.max_side_length,
            layer_probability=0.0,
        ),
    )
    points = list(rectangle.points)
    search_steps = random.randint(config.min_search_steps, config.max_search_steps)

    for _ in range(search_steps):
        modified: list[Point] | None = None
        if random.random() < config.layer_probability:
            modified = _try_lift_edge(points, random)
        if modified is None:
            modified = _try_expand_edge(points, random)
        if modified is None:
            # This is only expected for unusually saturated two-layer paths.
            # Returning the best candidate found so far keeps bounded search
            # deterministic instead of looping indefinitely.
            break
        points = modified

    code = _points_to_code(points)
    candidate = make_candidate(code)
    if candidate.points != tuple(points):
        raise RuntimeError("internal search encoding did not preserve the candidate path")
    return candidate


def _try_expand_edge(points: list[Point], random: Random) -> list[Point] | None:
    occupied = set(points[:-1])
    edge_indices = list(range(len(points) - 1))
    random.shuffle(edge_indices)

    for index in edge_indices:
        start = points[index]
        end = points[index + 1]
        dx = end.x - start.x
        dy = end.y - start.y
        if start.z != end.z or abs(dx) + abs(dy) != 1:
            continue

        normals = [(-dy, dx), (dy, -dx)]
        random.shuffle(normals)
        for nx, ny in normals:
            first = Point(start.x + nx, start.y + ny, start.z)
            second = Point(end.x + nx, end.y + ny, end.z)
            if first in occupied or second in occupied:
                continue
            candidate = points[: index + 1] + [first, second] + points[index + 1 :]
            if _is_encodable(candidate):
                return candidate

    return None


def _try_lift_edge(points: list[Point], random: Random) -> list[Point] | None:
    occupied = set(points[:-1])
    edge_indices = list(range(len(points) - 1))
    random.shuffle(edge_indices)

    for index in edge_indices:
        start = points[index]
        end = points[index + 1]
        if start.z != end.z or abs(start.x - end.x) + abs(start.y - end.y) != 1:
            continue

        lifted_start = start.switched_layer()
        lifted_end = end.switched_layer()
        if lifted_start in occupied or lifted_end in occupied:
            continue
        candidate = points[: index + 1] + [lifted_start, lifted_end] + points[index + 1 :]
        if _is_encodable(candidate):
            return candidate

    return None


def _is_encodable(points: list[Point]) -> bool:
    try:
        _points_to_code(points)
    except ValueError:
        return False
    return True


def _points_to_code(points: list[Point]) -> str:
    direction = Direction.EAST
    commands: list[str] = []

    for start, end in zip(points, points[1:]):
        if start.x == end.x and start.y == end.y and start.z != end.z:
            commands.append("3")
            continue

        step = (end.x - start.x, end.y - start.y)
        try:
            next_direction = Direction(step)
        except ValueError as error:
            raise ValueError(f"cannot encode non-unit grid edge {start!r} -> {end!r}") from error

        if next_direction == direction:
            commands.append("0")
        elif next_direction == direction.left():
            commands.append("1")
        elif next_direction == direction.right():
            commands.append("2")
        else:
            raise ValueError(f"cannot encode immediate reversal {start!r} -> {end!r}")
        direction = next_direction

    return "".join(commands)
