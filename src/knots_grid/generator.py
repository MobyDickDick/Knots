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
