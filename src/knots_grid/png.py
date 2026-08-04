"""Small dependency-free PNG renderer for two-layer grid paths."""

from __future__ import annotations

from pathlib import Path
import struct
import zlib

from .core import Point
from .svg import project


def render_png(
    points: tuple[Point, ...] | list[Point],
    filename: str | Path,
    *,
    scale: float = 32.0,
    margin: float = 16.0,
    stroke_width: float = 4.0,
) -> None:
    """Render a knot as an RGB PNG without requiring an imaging package."""

    pts = tuple(points)
    if not pts:
        raise ValueError("cannot render an empty point sequence")
    projected = [project(point) for point in pts]
    min_x = min(x for x, _ in projected) - 1
    max_x = max(x for x, _ in projected) + 1
    min_y = min(y for _, y in projected) - 1
    max_y = max(y for _, y in projected) + 1
    width = max(1, round(margin * 2 + (max_x - min_x) * scale))
    height = max(1, round(margin * 2 + (max_y - min_y) * scale))
    pixels = bytearray(b"\xff\xff\xff" * width * height)

    def xy(point: Point) -> tuple[int, int]:
        x, y = project(point)
        return (round(margin + (x - min_x) * scale), round(margin + (max_y - y) * scale))

    def dot(x: int, y: int, radius: int, color: tuple[int, int, int]) -> None:
        radius2 = radius * radius
        for py in range(max(0, y - radius), min(height, y + radius + 1)):
            for px in range(max(0, x - radius), min(width, x + radius + 1)):
                if (px - x) ** 2 + (py - y) ** 2 <= radius2:
                    offset = (py * width + px) * 3
                    pixels[offset : offset + 3] = bytes(color)

    def line(a: tuple[int, int], b: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
        dx, dy = b[0] - a[0], b[1] - a[1]
        steps = max(abs(dx), abs(dy), 1)
        for step in range(steps + 1):
            dot(round(a[0] + dx * step / steps), round(a[1] + dy * step / steps), radius, color)

    radius = max(1, round(stroke_width / 2))
    for a, b in zip(pts, pts[1:]):
        color = (214, 39, 40) if a.z != b.z else ((31, 119, 180) if a.z == 0 else (44, 160, 44))
        line(xy(a), xy(b), radius, color)
    for point in pts[:-1]:
        dot(*xy(point), max(2, radius), (31, 119, 180) if point.z == 0 else (44, 160, 44))

    raw = b"".join(b"\x00" + pixels[row * width * 3 : (row + 1) * width * 3] for row in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, level=9)) + chunk(b"IEND", b"")
    Path(filename).write_bytes(png)
