"""Validated candidate generation for two-layer grid paths."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .core import TraceResult, trace_turtle
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
