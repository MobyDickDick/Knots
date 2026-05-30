"""Core turtle tracing for paths in Z^2 x {0, 1}."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Point:
    """A grid point (x, y, z) with z in {0, 1}."""

    x: int
    y: int
    z: int

    def switched_layer(self) -> "Point":
        if self.z not in (0, 1):
            raise ValueError(f"invalid layer z={self.z!r}")
        return Point(self.x, self.y, 1 - self.z)


class Direction(Enum):
    """Cardinal direction in the lower grid coordinates."""

    EAST = (1, 0)
    NORTH = (0, 1)
    WEST = (-1, 0)
    SOUTH = (0, -1)

    def left(self) -> "Direction":
        order = [Direction.EAST, Direction.NORTH, Direction.WEST, Direction.SOUTH]
        return order[(order.index(self) + 1) % 4]

    def right(self) -> "Direction":
        order = [Direction.EAST, Direction.SOUTH, Direction.WEST, Direction.NORTH]
        return order[(order.index(self) + 1) % 4]

    @property
    def step(self) -> tuple[int, int]:
        return self.value


@dataclass(frozen=True, slots=True)
class TraceResult:
    """Result of expanding a turtle code."""

    code: str
    points: tuple[Point, ...]
    final_direction: Direction


def _move(point: Point, direction: Direction) -> Point:
    dx, dy = direction.step
    return Point(point.x + dx, point.y + dy, point.z)


def trace_turtle(
    code: str | Iterable[str],
    *,
    start: Point = Point(0, 0, 0),
    direction: Direction = Direction.EAST,
) -> TraceResult:
    """Expand a turtle code into a point sequence.

    Commands:

    - ``0``: move one step forward.
    - ``1``: turn left, then move one step forward.
    - ``2``: turn right, then move one step forward.
    - ``3``: switch layer at the same ``(x, y)``.
    """

    if start.z not in (0, 1):
        raise ValueError("start point must have z in {0, 1}")

    code_str = "".join(code) if not isinstance(code, str) else code
    point = start
    current_direction = direction
    points = [point]

    for index, command in enumerate(code_str):
        if command == "0":
            point = _move(point, current_direction)
        elif command == "1":
            current_direction = current_direction.left()
            point = _move(point, current_direction)
        elif command == "2":
            current_direction = current_direction.right()
            point = _move(point, current_direction)
        elif command == "3":
            point = point.switched_layer()
        else:
            raise ValueError(f"invalid turtle command {command!r} at index {index}")
        points.append(point)

    return TraceResult(code=code_str, points=tuple(points), final_direction=current_direction)
