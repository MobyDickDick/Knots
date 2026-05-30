"""Generators for beautiful cyclic lattice knots."""

from __future__ import annotations

import random
from typing import Literal

from .checker import check_knot
from .model import Knot, Point

PresetName = Literal["unknot", "ornamental", "layered"]


def rectangle(width: int = 6, height: int = 4, *, z: int = 0, name: str = "unknot") -> Knot:
    """Create a rectangular unknot as a turtle-step cycle."""

    if width < 2 or height < 2:
        raise ValueError("width and height must be at least 2.")
    if z not in (0, 1):
        raise ValueError("z must be 0 or 1.")

    points: list[Point] = []
    points.extend((x, 0, z) for x in range(width))
    points.extend((width - 1, y, z) for y in range(1, height))
    points.extend((x, height - 1, z) for x in range(width - 2, -1, -1))
    points.extend((0, y, z) for y in range(height - 2, 0, -1))
    knot = Knot(points, name=name)
    check_knot(knot).raise_for_errors()
    return knot


def ornamental(seed: int = 7, *, expansions: int = 18, lifts: int = 0) -> Knot:
    """Create a deterministic ornamental knot by adding rectangular detours."""

    knot = rectangle(7, 5, name="ornamental")
    rng = random.Random(seed)
    for _ in range(expansions):
        knot = _try_expand_random_edge(knot, rng) or knot
    for _ in range(lifts):
        knot = _try_lift_random_edge(knot, rng) or knot
    return knot


def layered(seed: int = 11, *, expansions: int = 10, lifts: int = 10) -> Knot:
    """Create a two-layer example with visible over/under information."""

    knot = ornamental(seed, expansions=expansions, lifts=0)
    for _ in range(lifts):
        knot = _try_lift_random_edge(knot, random.Random(seed + 10_000 + _)) or knot
    return Knot(knot.points, name="layered")


def generate(preset: PresetName = "layered", *, seed: int = 11) -> Knot:
    """Generate one of the named example families."""

    if preset == "unknot":
        return rectangle(name="unknot")
    if preset == "ornamental":
        return ornamental(seed=seed)
    if preset == "layered":
        return layered(seed=seed)
    raise ValueError(f"Unknown preset: {preset!r}.")


def _try_expand_random_edge(knot: Knot, rng: random.Random) -> Knot | None:
    points = list(knot.points)
    occupied = set(points)
    indices = list(range(len(points)))
    rng.shuffle(indices)

    for index in indices:
        a = points[index]
        b = points[(index + 1) % len(points)]
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        if a[2] != b[2] or abs(dx) + abs(dy) != 1:
            continue
        normals = [(-dy, dx, 0), (dy, -dx, 0)]
        rng.shuffle(normals)
        for nx, ny, nz in normals:
            p = (a[0] + nx, a[1] + ny, a[2] + nz)
            q = (b[0] + nx, b[1] + ny, b[2] + nz)
            if p in occupied or q in occupied or p == q:
                continue
            candidate = points[: index + 1] + [p, q] + points[index + 1 :]
            generated = Knot(candidate, name=knot.name)
            if check_knot(generated).valid:
                return generated
    return None


def _try_lift_random_edge(knot: Knot, rng: random.Random) -> Knot | None:
    points = list(knot.points)
    occupied = set(points)
    indices = list(range(len(points)))
    rng.shuffle(indices)

    for index in indices:
        a = points[index]
        b = points[(index + 1) % len(points)]
        if a[2] != b[2] or abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            continue
        lifted_a = (a[0], a[1], 1 - a[2])
        lifted_b = (b[0], b[1], 1 - b[2])
        if lifted_a in occupied or lifted_b in occupied:
            continue
        candidate = points[: index + 1] + [lifted_a, lifted_b] + points[index + 1 :]
        generated = Knot(candidate, name=knot.name)
        if check_knot(generated).valid:
            return generated
    return None
