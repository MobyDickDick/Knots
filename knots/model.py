"""Core data structures for lattice knots in Z^2 x {0, 1}.

A knot is stored as a cyclic tuple of turtle-step points.  The closing edge is
implicit: the last point must be one turtle step away from the first point.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Iterator, Sequence, TypeAlias

Point: TypeAlias = tuple[int, int, int]
PathLike: TypeAlias = str | Path


@dataclass(frozen=True)
class Knot:
    """A cyclic turtle-step knot in ``Z^2 x {0, 1}``.

    The point list does not repeat the starting point at the end.  This keeps
    duplicate-point checks simple: a valid knot has pairwise different points,
    and the closing turtle step is checked separately.
    """

    points: tuple[Point, ...]
    name: str = "knot"

    def __init__(self, points: Iterable[Sequence[int]], name: str = "knot") -> None:
        normalized: list[Point] = []
        for point in points:
            if len(point) != 3:
                msg = f"Every point must have exactly three coordinates, got {point!r}."
                raise ValueError(msg)
            x, y, z = point
            normalized.append((int(x), int(y), int(z)))
        object.__setattr__(self, "points", tuple(normalized))
        object.__setattr__(self, "name", name)

    def __len__(self) -> int:
        return len(self.points)

    def __iter__(self) -> Iterator[Point]:
        return iter(self.points)

    def cyclic_edges(self) -> Iterator[tuple[Point, Point]]:
        """Yield all consecutive edges, including the implicit closing edge."""

        if not self.points:
            return
        for index, point in enumerate(self.points):
            yield point, self.points[(index + 1) % len(self.points)]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "points": [list(point) for point in self.points]}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Knot":
        points = payload.get("points")
        if not isinstance(points, list):
            raise ValueError("Knot JSON must contain a list field named 'points'.")
        name = payload.get("name", "knot")
        return cls(points, name=str(name))

    def save_json(self, path: PathLike) -> None:
        target = Path(path)
        target.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load_json(cls, path: PathLike) -> "Knot":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Knot JSON must be an object.")
        return cls.from_dict(payload)


def turtle_distance(a: Point, b: Point) -> int:
    """Return the Manhattan distance in ``Z^2 x {0, 1}``."""

    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def is_turtle_step(a: Point, b: Point) -> bool:
    """Return whether ``a`` and ``b`` differ by exactly one turtle step."""

    return turtle_distance(a, b) == 1


def add_point(a: Point, delta: Point) -> Point:
    return (a[0] + delta[0], a[1] + delta[1], a[2] + delta[2])
