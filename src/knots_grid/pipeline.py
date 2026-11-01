"""Bounded, reproducible travel generation through classification and gallery.

Orientation is ignored. Mirrors are kept separate unless a reference certifies
amphichirality (4_1, 0_1). Unknown candidates are never merged on invariants.
The resulting collection is not advertised as pairwise distinct knot types.
"""

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

from .catalog import CatalogEntry, _candidate_seeds, canonical_key, write_catalog
from .classification import classify_knot
from .generator import TravelConfig, travel_candidates
from .optimization import optimize_cycle
from .projection import score_projection
from .validator import validate_cycle


POLICY = {
    "orientation": "ignored",
    "mirrors": "separate except reference-certified amphichiral knots",
    "exact_duplicates": "translation, cyclic start, reversal and planar rotations; no reflections",
    "equivalence": "certified reference identity or identical result reached by logged geometric isotopies",
    "unknown": "retained even when determinants agree; distinct knot types not guaranteed",
}


@dataclass(frozen=True, slots=True)
class CollectionResult:
    entries: tuple[CatalogEntry, ...]
    requested: int
    attempts: int
    max_attempts: int
    exact_duplicates: int
    equivalent_duplicates: int
    generator_failures: int
    status: str
    provenance: dict
    events: tuple[dict, ...]

    def report(self):
        return {
            "schema_version": 1, "status": self.status,
            "requested": self.requested, "retained": len(self.entries),
            "attempts": self.attempts, "max_attempts": self.max_attempts,
            "exact_duplicates": self.exact_duplicates,
            "equivalent_duplicates": self.equivalent_duplicates,
            "generator_failures": self.generator_failures,
            "certified_types": sum(e.knot_name != "unknown" for e in self.entries),
            "unknown_candidates": sum(e.knot_name == "unknown" for e in self.entries),
            "distinct_knot_types_guaranteed": False,
            "policy": POLICY, "provenance": self.provenance,
            "events": self.events,
        }


def generate_collection(
    count: int = 8, *, seed: int | None = None, mode: str = "random",
    config: TravelConfig = TravelConfig(), max_attempts: int = 500,
    max_moves: int = 100, max_route_states: int = 5000,
) -> CollectionResult:
    """Try at most max_attempts seeds, each with its own bounded travel search.

    count is the target collection size, not a promise of distinct knot types.
    Exhaustion returns partial results and an explicit attempt_limit report.
    """
    if count < 0 or max_attempts < 0 or max_moves < 0:
        raise ValueError("count, max_attempts and max_moves must be non-negative")
    if type(max_route_states) is not int or max_route_states < 1:
        raise ValueError("max_route_states must be a positive integer")
    if mode not in {"random", "systematic"}:
        raise ValueError("mode must be 'random' or 'systematic'")
    provenance = {
        "algorithm": "travel-reidemeister-v2", "seed": seed, "mode": mode,
        "generator": "travel", "generator_parameters": asdict(config),
        "max_attempts": max_attempts, "max_moves": max_moves,
        "max_route_states": max_route_states,
    }
    seeds = _candidate_seeds(mode, seed)
    entries, events = [], []
    seen_originals, seen_results, seen_names = {}, {}, {}
    exact = equivalent = failures = attempts = 0
    while len(entries) < count and attempts < max_attempts:
        candidate_seed = next(seeds)
        attempts += 1
        event = {"attempt": attempts, "seed": candidate_seed}
        try:
            original = travel_candidates(1, seed=candidate_seed, config=config)[0].points
        except RuntimeError as error:
            failures += 1
            events.append({**event, "outcome": "generator_limit", "reason": str(error)})
            continue
        validate_cycle(original).raise_for_errors()
        original_key = canonical_key(original, include_reflections=False)
        if original_key in seen_originals:
            exact += 1
            events.append({**event, "outcome": "exact_duplicate",
                           "equivalent_to": seen_originals[original_key]})
            continue
        classification_before = classify_knot(original)
        optimized = optimize_cycle(original, max_moves=max_moves, max_route_states=max_route_states)
        validate_cycle(optimized.points).raise_for_errors()
        classification_after = classify_knot(optimized.points)
        classification = (classification_before if classification_before.status == "certified"
                          else classification_after)
        if (classification_before.determinant is not None
                and classification_after.determinant is not None
                and classification_before.determinant != classification_after.determinant):
            raise RuntimeError("determinant changed across certified geometric isotopies")
        if classification.determinant is None and classification_before.determinant is not None:
            classification = replace(
                classification, determinant=classification_before.determinant,
                evidence=classification.evidence + "; determinant inherited from original via logged isotopies",
            )
        result_key = canonical_key(optimized.points, include_reflections=False)
        duplicate_index = seen_results.get(result_key)
        reason = "identical optimized grid via logged isotopies"
        if classification.status == "certified" and classification.name in seen_names:
            duplicate_index = seen_names[classification.name]
            reason = "certified reference identity: " + classification.name
        replacement_event = None
        if duplicate_index is not None:
            equivalent += 1
            seen_originals[original_key] = duplicate_index
            duplicate_event = {
                **event, "outcome": "proven_equivalent",
                "equivalent_to": duplicate_index, "evidence": reason,
                "classification": asdict(classification),
                "original_points": [[p.x, p.y, p.z] for p in original],
                "moves": [asdict(m) for m in optimized.moves],
            }
            candidate_measure = CatalogEntry(0, candidate_seed, optimized.points).measure
            if candidate_measure >= entries[duplicate_index].measure:
                events.append(duplicate_event)
                continue
            replacement_event = {
                **duplicate_event, "outcome": "better_equivalent",
                "previous_representative": asdict(entries[duplicate_index]),
            }
        index = len(entries) if duplicate_index is None else duplicate_index
        metadata = {
            "classification": asdict(classification),
            "original_classification": asdict(classification_before),
            "result_classification": asdict(classification_after),
            "classification_transfer": "original and result equivalent by replayable geometric isotopies",
            "provenance": {**provenance, "candidate_seed": candidate_seed, "attempt": attempts},
            "point_count_before": len(original) - 1,
            "point_count_after": len(optimized.points) - 1,
            "moves": [asdict(move) for move in optimized.moves],
            "optimization_status": optimized.status,
            "reidemeister_rejections": [asdict(r) for r in optimized.reidemeister_rejections],
            "global_minimality_claimed": False,
            "aesthetic_before": asdict(score_projection(original)),
            "aesthetic_after": asdict(score_projection(optimized.points)),
        }
        entry = CatalogEntry(index, candidate_seed, optimized.points,
                             classification.name, classification.determinant,
                             original, metadata)
        if duplicate_index is None:
            entries.append(entry)
        else:
            entries[index] = entry
        seen_originals[original_key] = index
        seen_results[result_key] = index
        if classification.status == "certified":
            seen_names[classification.name] = index
        events.append(replacement_event or {**event, "outcome": "retained", "index": index})
    status = "complete" if len(entries) == count else "attempt_limit"
    return CollectionResult(tuple(entries), count, attempts, max_attempts, exact,
                            equivalent, failures, status, provenance, tuple(events))


def write_collection(result: CollectionResult, directory: str | Path) -> Path:
    """Write original/result artifacts, standalone gallery and search report."""
    manifest = write_catalog(result.entries, directory)
    (Path(directory) / "report.json").write_text(
        json.dumps(result.report(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    return manifest
