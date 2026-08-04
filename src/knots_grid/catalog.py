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

from .core import Point
from .generator import SearchConfig, search_candidate
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


def canonicalize_cycle(points: Iterable[Point]) -> tuple[Point, ...]:
    """Return the smallest translated D4/cyclic representation of a cycle.

    Input may repeat the start point at the end; output always does so.  Layer
    values are retained because swapping layers may change over/under data.
    """

    pts = tuple(points)
    validation = validate_cycle(pts)
    validation.raise_for_errors()
    body = pts[:-1]

    variants: list[tuple[tuple[int, tuple[int, ...]], tuple[Point, ...]]] = []
    for transform in _square_symmetries():
        transformed = tuple(Point(*transform(point.x, point.y), point.z) for point in body)
        normalized = _translate_non_negative(transformed)
        for oriented in (normalized, tuple(reversed(normalized))):
            for offset in range(len(oriented)):
                rotated = oriented[offset:] + oriented[:offset]
                closed = rotated + (rotated[0],)
                variants.append((sequence_measure(rotated), closed))

    return min(variants, key=lambda item: item[0])[1]


def canonical_key(points: Iterable[Point]) -> CanonicalKey:
    """Return a hashable key for exact grid-symmetry deduplication."""

    return tuple((point.x, point.y, point.z) for point in canonicalize_cycle(points)[:-1])


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

    @property
    def measure(self) -> tuple[int, tuple[int, ...]]:
        return sequence_measure(self.points[:-1])


def generate_catalog(
    count: int = 100,
    *,
    mode: str = "random",
    seed: int | None = None,
    config: SearchConfig = SearchConfig(),
    max_attempts: int | None = None,
) -> tuple[CatalogEntry, ...]:
    """Generate distinct canonical candidates randomly or by ascending seeds.

    ``systematic`` means deterministic exploration of generator seeds 0, 1,
    2, ...; it is not an exhaustive enumeration of all mathematical knots.
    """

    if count < 0:
        raise ValueError("count must be non-negative")
    if mode not in {"random", "systematic"}:
        raise ValueError("mode must be 'random' or 'systematic'")
    limit = max_attempts if max_attempts is not None else max(1000, count * 200)
    if limit < 0:
        raise ValueError("max_attempts must be non-negative")

    seeds = _candidate_seeds(mode, seed)
    seen: set[CanonicalKey] = set()
    entries: list[CatalogEntry] = []
    for _ in range(limit):
        candidate_seed = next(seeds)
        candidate = search_candidate(seed=candidate_seed, config=config)
        canonical = canonicalize_cycle(candidate.points)
        key = tuple((point.x, point.y, point.z) for point in canonical[:-1])
        if key in seen:
            continue
        seen.add(key)
        entries.append(CatalogEntry(len(entries), candidate_seed, canonical))
        if len(entries) == count:
            return tuple(entries)

    raise RuntimeError(f"found only {len(entries)} distinct candidates in {limit} attempts")


def write_catalog(entries: Iterable[CatalogEntry], directory: str | Path) -> Path:
    """Write one SVG per entry plus a machine-readable JSON manifest."""

    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for entry in entries:
        filename = f"knot_{entry.index:03d}.svg"
        render_svg(entry.points, target / filename)
        records.append(
            {
                "index": entry.index,
                "seed": entry.seed,
                "svg": filename,
                "point_count": len(entry.points) - 1,
                "measure": [entry.measure[0], list(entry.measure[1])],
                "points": [[p.x, p.y, p.z] for p in entry.points[:-1]],
            }
        )
    manifest = target / "catalog.json"
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
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
    parser.add_argument("--output", type=Path, default=Path("knot_catalog"))
    args = parser.parse_args(argv)
    entries = generate_catalog(args.count, mode=args.mode, seed=args.seed)
    manifest = write_catalog(entries, args.output)
    print(f"Wrote {len(entries)} canonical candidates to {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
