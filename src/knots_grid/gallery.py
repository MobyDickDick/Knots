"""Offline HTML gallery for validated two-layer knot catalogs."""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re
from typing import Iterable, TYPE_CHECKING

from .reidemeister import find_crossings
from .svg import project
from .validator import validate_cycle

if TYPE_CHECKING:
    from .catalog import CatalogEntry


def _preview_svg(points, name: str) -> str:
    """Include a real drawing in the document before JavaScript starts."""

    projected = [project(point) for point in points]
    left = min(x for x, _ in projected) - 0.5
    bottom = min(y for _, y in projected) - 0.5
    width = max(x for x, _ in projected) - left + 0.5
    height = max(y for _, y in projected) - bottom + 0.5
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {bottom} {width} {height}" '
        f'role="img" aria-label="{escape(name, quote=True)}">',
        f'<g transform="translate(0 {2 * bottom + height}) scale(1 -1)" '
        'fill="none" stroke-linecap="round" stroke-width="0.08">',
    ]
    for a, b in zip(points, points[1:]):
        ax, ay = project(a)
        bx, by = project(b)
        color = "#d62728" if a.z != b.z else ("#1f77b4" if a.z == 0 else "#2ca02c")
        lines.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{color}"/>')
    return "".join(lines) + "</g></svg>"


def _display_name(entry, index):
    if entry.knot_name == "unknown":
        return f"Kandidat {index + 1:03d} · ungeklärt"
    return "0₁ · Unknoten" if entry.knot_name == "0_1" else entry.knot_name


def render_gallery(entries: Iterable[CatalogEntry], filename: str | Path) -> Path:
    """Write a self-contained, rotatable gallery without changing knot points.

    The 2-D view uses the existing renderer's sqrt(2)/2 layer shift. The 3-D
    view uses the actual (x, y, z) coordinates, with a display-only layer gap.
    Input cycles must repeat their start at the end, as in knots_grid.
    """

    entries = tuple(entries)
    records = []
    for entry in entries:
        validate_cycle(entry.points).raise_for_errors()
        records.append({
            "name": entry.knot_name,
            "determinant": entry.determinant,
            "crossings": len(find_crossings(entry.points)),
            "points": [[p.x, p.y, p.z] for p in entry.points],
        })
        metadata = entry.metadata
        if metadata:
            if "provenance" in metadata:
                # Generator seeds use 63 bits; JavaScript numbers only retain
                # 53 integer bits. Keep their displayed provenance exact.
                provenance = dict(metadata["provenance"])
                for key in ("seed", "candidate_seed"):
                    if provenance.get(key) is not None:
                        provenance[key] = str(provenance[key])
                metadata = {**metadata, "provenance": provenance}
            records[-1]["metadata"] = metadata
        if entry.original_points is not None:
            validate_cycle(entry.original_points).raise_for_errors()
            records[-1].update({
                "original_points": [[p.x, p.y, p.z] for p in entry.original_points],
                "original_crossings": len(find_crossings(entry.original_points)),
                "metadata": metadata,
            })
    if not records:
        raise ValueError("a gallery needs at least one knot")

    # Data is a JavaScript array literal, so HTML closing tags must not pass
    # through, even when a caller supplies an untrusted catalog name.
    data = json.dumps(records, ensure_ascii=True).replace("<", "\\u003c").replace(
        ">", "\\u003e"
    ).replace("&", "\\u0026")
    template = Path(__file__).with_name("gallery.html.template").read_text(encoding="utf-8")
    selected = 1 if len(entries) > 1 else 0
    previews = [_preview_svg(entry.points, entry.knot_name) for entry in entries]
    cards = []
    static_catalog = []
    for index, (entry, record, preview) in enumerate(zip(entries, records, previews)):
        name = escape(_display_name(entry, index))
        cards.append(
            f'<a class="knot-card" href="#static-knot-{index}" '
            f'aria-label="{escape(entry.knot_name, quote=True)} auswählen">{preview}'
            f'<span class="knot-name">{name}</span>'
            f'<span class="knot-caption">{record["crossings"]} Kreuzungen</span></a>'
        )
        static_catalog.append(
            f'<section id="static-knot-{index}"><h3>{name}</h3>{preview}</section>'
        )
        if entry.original_points is not None:
            original_preview = _preview_svg(entry.original_points, entry.knot_name + " · Original")
            static_catalog[-1] = (
                f'<section id="static-knot-{index}"><h3>{name} · Original</h3>'
                f'{original_preview}<h3>{name} · Beste gefundene Darstellung</h3>{preview}</section>'
            )
    replacements = {
        "__KNOT_DATA__": data,
        "__KNOT_CARDS__": "".join(cards),
        "__KNOT_COUNT__": str(len(entries)),
        "__SELECTED_NAME__": escape(
            _display_name(entries[selected], selected)
        ),
        "__SELECTED_PREVIEW__": previews[selected],
        "__STATIC_CATALOG__": "".join(static_catalog),
    }
    # Replace source tokens in one pass: a catalog name containing a token
    # must not be interpreted as another template instruction.
    rendered = re.sub(r"__[A-Z_]+__", lambda match: replacements[match[0]], template)
    target = Path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8", newline="\n")
    return target


def main(argv: list[str] | None = None) -> int:
    from .catalog import generate_catalog

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--mode", choices=("systematic", "random"), default="systematic")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path, default=Path("knot_gallery.html"))
    args = parser.parse_args(argv)
    entries = generate_catalog(args.count, mode=args.mode, seed=args.seed)
    target = render_gallery(entries, args.output)
    print(f"Wrote {len(entries)} knots to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
