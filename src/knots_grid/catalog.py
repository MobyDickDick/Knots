"""Canonicalize, generate, and visualize catalogs of grid-knot candidates.

The canonicalization implemented here removes representation differences caused
by translation, a different cyclic start, traversal direction, and the eight
symmetries of the square.  It deliberately does *not* claim to decide ambient
isotopy (Reidemeister equivalence).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from random import Random
from typing import Iterable, Iterator

from .core import Point, trace_turtle
from .generator import SearchConfig, torus_knot_candidate
from .png import render_png
from .reidemeister import reidemeister_conditions
from .svg import render_svg
from .validator import validate_cycle


PointKey = tuple[int, int, int]
CanonicalKey = tuple[PointKey, ...]


def pseudo_cantor_index(point: Point) -> int:
    """Number a point in the non-negative two-layer grid bijectively."""

    if point.x < 0 or point.y < 0 or point.z not in (0, 1):
        raise ValueError("pseudo-Cantor indices require x >= 0, y >= 0, z in {0, 1}")
    diagonal = point.x + point.y
    pair = diagonal * (diagonal + 1) // 2 + point.y
    return 2 * pair + point.z


def sequence_measure(points: Iterable[Point]) -> tuple[int, tuple[int, ...]]:
    """Return a collision-free, lexicographically comparable path measure.

    Tuple comparison deliberately makes the number of elements the primary
    criterion. The pseudo-Cantor sequence is consulted only when two paths
    contain the same number of elements.
    """

    pts = tuple(points)
    return (len(pts), tuple(pseudo_cantor_index(point) for point in pts))


def canonicalize_cycle(
    points: Iterable[Point], *, include_reflections: bool = True,
) -> tuple[Point, ...]:
    """Return the smallest translated D4/cyclic representation of a cycle.

    Input may repeat the start point at the end; output always does so.  Layer
    values are retained because swapping layers may change over/under data.
    Set include_reflections=False to preserve chirality (the new pipeline).
    """

    pts = tuple(points)
    validation = validate_cycle(pts)
    validation.raise_for_errors()
    body = pts[:-1]

    variants: list[tuple[tuple[int, tuple[int, ...]], tuple[Point, ...]]] = []
    for transform in _square_symmetries()[:8 if include_reflections else 4]:
        transformed = tuple(Point(*transform(point.x, point.y), point.z) for point in body)
        normalized = _translate_non_negative(transformed)
        for oriented in (normalized, tuple(reversed(normalized))):
            # The bijective Cantor index has a unique minimum on a simple
            # cycle. Only that cyclic start can win lexicographically.
            offset = min(range(len(oriented)), key=lambda i: pseudo_cantor_index(oriented[i]))
            rotated = oriented[offset:] + oriented[:offset]
            closed = rotated + (rotated[0],)
            variants.append((sequence_measure(rotated), closed))

    return min(variants, key=lambda item: item[0])[1]


def canonical_key(points: Iterable[Point], *, include_reflections: bool = True) -> CanonicalKey:
    """Return a hashable key for exact grid-symmetry deduplication."""

    return tuple((point.x, point.y, point.z) for point in canonicalize_cycle(
        points, include_reflections=include_reflections,
    )[:-1])


def choose_shortest_equivalent(cycles: Iterable[Iterable[Point]]) -> tuple[Point, ...]:
    """Choose the canonical representative of a known equivalence class.

    The caller is responsible for establishing that the supplied cycles are
    equivalent, for example through proven Reidemeister moves. Candidates with
    fewer vertices always win; the pseudo-Cantor sequence only breaks ties.
    """

    canonical = tuple(canonicalize_cycle(cycle) for cycle in cycles)
    if not canonical:
        raise ValueError("at least one equivalent cycle is required")
    return min(canonical, key=lambda cycle: sequence_measure(cycle[:-1]))


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One canonical candidate and the seed that produced it."""

    index: int
    seed: int
    points: tuple[Point, ...]
    knot_name: str = "unknown"
    determinant: int | None = 0
    original_points: tuple[Point, ...] | None = None
    metadata: dict | None = None

    @property
    def measure(self) -> tuple[int, tuple[int, ...]]:
        return sequence_measure(canonicalize_cycle(self.points, include_reflections=False)[:-1])


def generate_catalog(
    count: int = 100,
    *,
    mode: str = "random",
    seed: int | None = None,
    config: SearchConfig = SearchConfig(),
    max_attempts: int | None = None,
) -> tuple[CatalogEntry, ...]:
    """Generate at most one unknot followed by pairwise distinct real knots.

    Real entries are reduced ``T(2, q)`` diagrams for distinct odd ``q``.
    Their different determinants prove that they are different knot types,
    rather than merely different drawings of the same knot.
    """

    if count < 0:
        raise ValueError("count must be non-negative")
    if mode not in {"random", "systematic"}:
        raise ValueError("mode must be 'random' or 'systematic'")
    limit = max_attempts if max_attempts is not None else max(1000, count * 200)
    if limit < 0:
        raise ValueError("max_attempts must be non-negative")

    if count == 0:
        return ()

    entries: list[CatalogEntry] = []
    unknot = canonicalize_cycle(trace_turtle("1111").points)
    entries.append(CatalogEntry(0, -1, unknot, "0_1", 1))
    if count == 1:
        return tuple(entries)

    seeds = _candidate_seeds(mode, seed)
    seen_crossings: set[int] = set()
    for _ in range(limit):
        candidate_seed = next(seeds)
        if mode == "systematic":
            crossings = 3 + 2 * len(seen_crossings)
        else:
            crossings = 3 + 2 * (candidate_seed % max(32, count * 4))
        if crossings in seen_crossings:
            continue
        candidate = torus_knot_candidate(crossings)
        report = reidemeister_conditions(candidate.points)
        if report.type_i or report.type_ii:
            continue
        canonical = canonicalize_cycle(candidate.points)
        seen_crossings.add(crossings)
        entries.append(
            CatalogEntry(
                len(entries), candidate_seed, canonical, f"T(2,{crossings})", crossings
            )
        )
        if len(entries) == count:
            return tuple(entries)

    raise RuntimeError(f"found only {len(entries)} distinct candidates in {limit} attempts")


def write_catalog(entries: Iterable[CatalogEntry], directory: str | Path) -> Path:
    """Write SVG/PNG files, a JSON manifest and an offline 2-D/3-D gallery."""

    target = Path(directory)
    entries = tuple(entries)
    target.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for entry in entries:
        validate_cycle(entry.points).raise_for_errors()
        if entry.original_points is not None:
            validate_cycle(entry.original_points).raise_for_errors()
        svg_filename = f"knot_{entry.index:03d}.svg"
        png_filename = f"knot_{entry.index:03d}.png"
        render_svg(entry.points, target / svg_filename)
        span = max(
            max(point.x for point in entry.points) - min(point.x for point in entry.points),
            max(point.y for point in entry.points) - min(point.y for point in entry.points),
        )
        # Keep large catalogs practical: high-crossing torus knots still get a
        # useful raster preview without creating quadratic multi-gigabyte PNGs.
        png_scale = max(4.0, min(32.0, 1024.0 / (span + 2)))
        render_png(entry.points, target / png_filename, scale=png_scale)
        records.append(
            {
                "index": entry.index,
                "seed": entry.seed,
                "name": entry.knot_name,
                "determinant": entry.determinant,
                "svg": svg_filename,
                "png": png_filename,
                "point_count": len(entry.points) - 1,
                "measure": [entry.measure[0], list(entry.measure[1])],
                "points": [[p.x, p.y, p.z] for p in entry.points[:-1]],
            }
        )
        if entry.original_points is not None:
            original_svg = f"knot_{entry.index:03d}_original.svg"
            render_svg(entry.original_points, target / original_svg)
            records[-1].update({
                "original_svg": original_svg,
                "original_points": [[p.x, p.y, p.z] for p in entry.original_points[:-1]],
                "original_point_count": len(entry.original_points) - 1,
                "metadata": entry.metadata,
            })
    manifest = target / "catalog.json"
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    if entries:
        from .gallery import render_gallery

        render_gallery(entries, target / "index.html")
    return manifest


def _candidate_seeds(mode: str, seed: int | None) -> Iterator[int]:
    if mode == "systematic":
        value = 0 if seed is None else seed
        while True:
            yield value
            value += 1
    else:
        random = Random(seed)
        while True:
            yield random.randrange(2**63)


def _translate_non_negative(points: tuple[Point, ...]) -> tuple[Point, ...]:
    min_x = min(point.x for point in points)
    min_y = min(point.y for point in points)
    return tuple(Point(point.x - min_x, point.y - min_y, point.z) for point in points)


def _square_symmetries():
    return (
        lambda x, y: (x, y),
        lambda x, y: (-y, x),
        lambda x, y: (-x, -y),
        lambda x, y: (y, -x),
        lambda x, y: (-x, y),
        lambda x, y: (x, -y),
        lambda x, y: (y, x),
        lambda x, y: (-y, -x),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--mode", choices=("random", "systematic"), default="random")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--source", choices=("torus", "travel"), default="torus")
    parser.add_argument("--point-count", type=int, default=10)
    parser.add_argument("--max-attempts", type=int)
    parser.add_argument("--travel-attempts", type=int, default=500)
    parser.add_argument("--max-moves", type=int, default=100)
    parser.add_argument("--route-states", type=int, default=5000,
                        help="bounded routing states per direct Reidemeister arc")
    parser.add_argument("--output", type=Path, default=Path("knot_catalog"))
    args = parser.parse_args(argv)
    if args.source == "travel":
        from .pipeline import generate_collection, write_collection
        from .generator import TravelConfig

        result = generate_collection(
            args.count, mode=args.mode, seed=args.seed,
            config=TravelConfig(args.point_count, args.travel_attempts),
            max_attempts=500 if args.max_attempts is None else args.max_attempts,
            max_moves=args.max_moves, max_route_states=args.route_states,
        )
        manifest = write_collection(result, args.output)
        print(f"{result.status}: {len(result.entries)}/{args.count} entries; "
              f"{result.attempts} attempts, {result.exact_duplicates} exact duplicates, "
              f"{result.equivalent_duplicates} proven equivalents, "
              f"{result.generator_failures} generator failures. Wrote {manifest}")
        return 0
    entries = generate_catalog(args.count, mode=args.mode, seed=args.seed,
                               max_attempts=args.max_attempts)
    manifest = write_catalog(entries, args.output)
    print(f"Wrote {len(entries)} canonical candidates to {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
