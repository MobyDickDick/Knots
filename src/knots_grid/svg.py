"""Exact SVG rendering for two-layer grid paths."""

from __future__ import annotations

from math import sqrt
from pathlib import Path

from .core import Point

_OFFSET = sqrt(2) / 2


def project(point: Point) -> tuple[float, float]:
    """Project a point to the shifted two-layer drawing plane."""

    return (point.x + _OFFSET * point.z, point.y + _OFFSET * point.z)


def _svg_point(point: Point, *, min_x: float, max_y: float, scale: float, margin: float) -> tuple[float, float]:
    x, y = project(point)
    return (margin + (x - min_x) * scale, margin + (max_y - y) * scale)


def render_svg(
    points: tuple[Point, ...] | list[Point],
    filename: str | Path,
    *,
    scale: float = 64.0,
    margin: float = 32.0,
    stroke_width: float = 5.0,
    show_grid: bool = True,
) -> None:
    """Render a point path as SVG.

    Colors:

    - z = 0 edges: blue
    - z = 1 edges: green
    - layer switches: red
    """

    pts = tuple(points)
    if not pts:
        raise ValueError("cannot render an empty point sequence")

    projected = [project(p) for p in pts]
    min_x = min(x for x, _ in projected) - 1
    max_x = max(x for x, _ in projected) + 1
    min_y = min(y for _, y in projected) - 1
    max_y = max(y for _, y in projected) + 1

    width = margin * 2 + (max_x - min_x) * scale
    height = margin * 2 + (max_y - min_y) * scale

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">')
    lines.append('<rect width="100%" height="100%" fill="white"/>')

    if show_grid:
        x0 = int(min_x) - 1
        x1 = int(max_x) + 1
        y0 = int(min_y) - 1
        y1 = int(max_y) + 1

        for x in range(x0, x1 + 1):
            a = Point(x, y0, 0)
            b = Point(x, y1, 0)
            ax, ay = _svg_point(a, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            bx, by = _svg_point(b, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            lines.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="#555" stroke-width="1" opacity="0.25"/>')

        for y in range(y0, y1 + 1):
            a = Point(x0, y, 0)
            b = Point(x1, y, 0)
            ax, ay = _svg_point(a, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            bx, by = _svg_point(b, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            lines.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="#555" stroke-width="1" opacity="0.25"/>')

        for x in range(x0, x1 + 1):
            a = Point(x, y0, 1)
            b = Point(x, y1, 1)
            ax, ay = _svg_point(a, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            bx, by = _svg_point(b, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            lines.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="#aaa" stroke-width="1" opacity="0.30"/>')

        for y in range(y0, y1 + 1):
            a = Point(x0, y, 1)
            b = Point(x1, y, 1)
            ax, ay = _svg_point(a, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            bx, by = _svg_point(b, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
            lines.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="#aaa" stroke-width="1" opacity="0.30"/>')

    for a, b in zip(pts, pts[1:]):
        ax, ay = _svg_point(a, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
        bx, by = _svg_point(b, min_x=min_x, max_y=max_y, scale=scale, margin=margin)

        if a.z != b.z:
            color = "#d62728"
            width_edge = stroke_width * 0.75
        elif a.z == 0:
            color = "#1f77b4"
            width_edge = stroke_width
        else:
            color = "#2ca02c"
            width_edge = stroke_width

        lines.append(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="{color}" stroke-width="{width_edge:.2f}" stroke-linecap="round"/>')

    for point in pts[:-1]:
        cx, cy = _svg_point(point, min_x=min_x, max_y=max_y, scale=scale, margin=margin)
        fill = "#1f77b4" if point.z == 0 else "#2ca02c"
        lines.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="3.2" fill="{fill}"/>')

    lines.append("</svg>")
    Path(filename).write_text("\n".join(lines), encoding="utf-8")
