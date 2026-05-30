"""SVG visualization for lattice knots."""

from __future__ import annotations

from html import escape
from pathlib import Path

from .model import Knot, PathLike

_LAYER_COLOR = {0: "#276ef1", 1: "#f05a28"}


def to_svg(knot: Knot, *, scale: int = 36, padding: int = 32) -> str:
    """Render a knot projection as a compact SVG string."""

    if not knot.points:
        raise ValueError("Cannot render an empty knot.")
    xs = [point[0] for point in knot.points]
    ys = [point[1] for point in knot.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = (max_x - min_x) * scale + 2 * padding
    height = (max_y - min_y) * scale + 2 * padding

    def project(point: tuple[int, int, int]) -> tuple[int, int]:
        x, y, _ = point
        return ((x - min_x) * scale + padding, (max_y - y) * scale + padding)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{escape(knot.name)}</title>",
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        '<g stroke="#e5e0d8" stroke-width="1">',
    ]
    for x in range(min_x, max_x + 1):
        x1, _ = project((x, min_y, 0))
        parts.append(f'<line x1="{x1}" y1="{padding}" x2="{x1}" y2="{height - padding}"/>')
    for y in range(min_y, max_y + 1):
        _, y1 = project((min_x, y, 0))
        parts.append(f'<line x1="{padding}" y1="{y1}" x2="{width - padding}" y2="{y1}"/>')
    parts.append("</g>")

    for a, b in knot.cyclic_edges():
        ax, ay = project(a)
        bx, by = project(b)
        color = _LAYER_COLOR[a[2]] if a[2] == b[2] else "#555555"
        dash = ' stroke-dasharray="5 5"' if a[2] != b[2] else ""
        parts.append(
            f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{color}" '
            f'stroke-width="7" stroke-linecap="round" fill="none"{dash}/>'
        )

    for index, point in enumerate(knot.points):
        cx, cy = project(point)
        fill = _LAYER_COLOR[point[2]]
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{fill}" stroke="#1f1f1f" stroke-width="1"/>')
        if index == 0:
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="9" fill="none" stroke="#111" stroke-width="2"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def save_svg(knot: Knot, path: PathLike, *, scale: int = 36, padding: int = 32) -> None:
    Path(path).write_text(to_svg(knot, scale=scale, padding=padding), encoding="utf-8")
