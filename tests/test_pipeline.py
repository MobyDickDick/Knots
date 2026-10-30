from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from knots_grid import Point, TravelConfig, figure_eight_candidate, trace_turtle, trefoil_candidate
from knots_grid.catalog import canonical_key
from knots_grid.classification import classify_knot, knot_determinant, signed_gauss_key
from knots_grid.generator import torus_knot_candidate, travel_candidate
from knots_grid.optimization import FaceMove, apply_face_move, optimize_cycle
from knots_grid.pipeline import generate_collection, write_collection
from knots_grid.validator import validate_cycle


def shifted(points):
    return tuple(Point(p.x + 7, p.y - 3, p.z) for p in reversed(points))


class ClassificationTests(unittest.TestCase):
    def test_reference_names_have_full_diagram_evidence(self):
        for name, points, determinant in (
            ("0_1", trace_turtle("0111").points, 1),
            ("T(2,3)", trefoil_candidate().points, 3),
            ("4_1", figure_eight_candidate().points, 5),
            ("T(2,5)", torus_knot_candidate(5).points, 5),
        ):
            with self.subTest(name=name):
                result = classify_knot(points)
                self.assertEqual((result.name, result.status, result.determinant),
                                 (name, "certified", determinant))
                self.assertTrue(result.evidence)
                self.assertEqual(classify_knot(shifted(points)).name, name)

    def test_mirror_and_orientation_policy(self):
        points = trefoil_candidate().points
        mirror = tuple(Point(-p.x, p.y, p.z) for p in points)
        self.assertNotEqual(signed_gauss_key(points), signed_gauss_key(mirror))
        self.assertEqual(classify_knot(mirror).name, "mirror(T(2,3))")
        self.assertNotEqual(canonical_key(points, include_reflections=False),
                            canonical_key(mirror, include_reflections=False))
        self.assertEqual(knot_determinant(points), knot_determinant(mirror))
        self.assertEqual(signed_gauss_key(points), signed_gauss_key(shifted(points)))

    def test_torus_family_exact_determinants(self):
        for q in (3, 5, 7, 9, 11, 13, 15):
            self.assertEqual(knot_determinant(torus_knot_candidate(q).points), q)

    def test_unknown_is_not_named_from_determinant(self):
        points = travel_candidate(seed=5893448777124979737).points
        result = classify_knot(points)
        self.assertEqual(result.determinant, 1)
        self.assertEqual((result.name, result.status), ("unknown", "unknown"))

    def test_nonregular_projection_has_no_asserted_invariant(self):
        points = (Point(0, 0, 0), Point(1, 0, 0), Point(1, 0, 1),
                  Point(0, 0, 1), Point(0, 0, 0))
        result = classify_knot(points)
        self.assertIsNone(result.determinant)
        self.assertEqual(result.status, "unknown")


class OptimizationTests(unittest.TestCase):
    def test_every_move_replays_and_strictly_improves_measure(self):
        from knots_grid.catalog import canonicalize_cycle, sequence_measure

        original = travel_candidate(seed=2026).points
        result = optimize_cycle(original, max_moves=30)
        self.assertTrue(result.moves)
        points = original
        measure = lambda p: sequence_measure(canonicalize_cycle(p, include_reflections=False)[:-1])
        for move in result.moves:
            after = apply_face_move(points, move)
            self.assertTrue(validate_cycle(after).is_valid)
            self.assertLess(measure(after), measure(points))
            self.assertLessEqual(len(after), len(points))
            self.assertTrue(all(p.z in (0, 1) for p in after))
            points = after
        self.assertEqual(points, result.points)
        self.assertEqual(optimize_cycle(original, max_moves=30), result)

    def test_empty_face_contraction_and_cyclic_seam(self):
        # Use a simple planar rectangle with a one-square detour.
        points = (Point(0, 0, 0), Point(1, 0, 0), Point(1, -1, 0),
                  Point(2, -1, 0), Point(2, 0, 0), Point(2, 1, 0),
                  Point(1, 1, 0), Point(0, 1, 0), Point(0, 0, 0))
        result = optimize_cycle(points)
        self.assertEqual(len(result.points) - 1, 4)
        rotated = points[3:-1] + points[:3] + (points[3],)
        self.assertEqual(canonical_key(optimize_cycle(rotated).points), canonical_key(result.points))

    def test_occupied_face_and_tampered_log_rejected(self):
        square = trace_turtle("0111").points
        # The opposite corner belongs to the remainder of the square.
        move = FaceMove(0, square[:3], (square[0], square[3], square[2]))
        with self.assertRaisesRegex(ValueError, "occupied"):
            apply_face_move(square, move)
        with self.assertRaises(ValueError):
            apply_face_move(square, replace(move, start_index=99))
        with self.assertRaises(ValueError):
            apply_face_move(square, replace(move, after=(Point(0, 0, 2),)))

    def test_zero_move_budget_preserves_original_and_negative_fails(self):
        points = trefoil_candidate().points
        self.assertEqual(optimize_cycle(points, max_moves=0).points, points)
        self.assertEqual(optimize_cycle(points, max_moves=0).status, "move_limit")
        with self.assertRaises(ValueError):
            optimize_cycle(points, max_moves=-1)

    def test_validator_rejects_noninteger_points_and_retraced_edge(self):
        self.assertFalse(validate_cycle((Point(0, 0, 0), Point(1, 0, 0), Point(0, 0, 0))).is_valid)
        square = trace_turtle("0111").points
        invalid = tuple(Point(float(p.x), p.y, p.z) for p in square)
        self.assertFalse(validate_cycle(invalid).is_valid)


class CollectionTests(unittest.TestCase):
    def test_same_seed_gives_identical_collection_and_report(self):
        args = dict(seed=2026, config=TravelConfig(7, 100), max_attempts=8, max_moves=12)
        first = generate_collection(3, **args)
        self.assertEqual(first, generate_collection(3, **args))
        self.assertLessEqual(first.attempts, 8)
        for entry in first.entries:
            self.assertTrue(validate_cycle(entry.original_points).is_valid)
            self.assertTrue(validate_cycle(entry.points).is_valid)
            self.assertLessEqual(len(entry.points), len(entry.original_points))
            self.assertEqual(entry.metadata["provenance"]["generator_parameters"],
                             {"point_count": 7, "max_attempts": 100})
            self.assertEqual(entry.determinant, entry.metadata["original_classification"]["determinant"])

    def test_exact_and_proven_equivalents_have_separate_counters(self):
        square = trace_turtle("0111").points
        rectangle = trace_turtle("001101").points
        source = [SimpleNamespace(points=p) for p in (square, shifted(square), rectangle)]
        with patch("knots_grid.pipeline.travel_candidates", side_effect=[[s] for s in source]):
            result = generate_collection(2, max_attempts=3, max_moves=0)
        self.assertEqual(result.status, "attempt_limit")
        self.assertEqual(len(result.entries), 1)
        self.assertEqual((result.exact_duplicates, result.equivalent_duplicates), (1, 1))

    def test_equal_determinants_do_not_merge_different_known_knots(self):
        source = [figure_eight_candidate(), torus_knot_candidate(5)]
        with patch("knots_grid.pipeline.travel_candidates", side_effect=[[s] for s in source]):
            result = generate_collection(2, max_attempts=2, max_moves=0)
        self.assertEqual([e.knot_name for e in result.entries], ["4_1", "T(2,5)"])
        self.assertEqual([e.determinant for e in result.entries], [5, 5])

    def test_shorter_proven_equivalent_replaces_the_representative(self):
        source = [trace_turtle("001101"), trace_turtle("0111")]
        with patch("knots_grid.pipeline.travel_candidates", side_effect=[[s] for s in source]):
            result = generate_collection(2, max_attempts=2, max_moves=0)
        self.assertEqual(len(result.entries[0].points) - 1, 4)
        self.assertEqual(result.events[-1]["outcome"], "better_equivalent")
        self.assertEqual(result.equivalent_duplicates, 1)

    def test_unknown_equal_invariants_are_retained(self):
        source = [travel_candidate(seed=s) for s in (5893448777124979737, 7758976353826416361)]
        with patch("knots_grid.pipeline.travel_candidates", side_effect=[[s] for s in source]):
            result = generate_collection(2, max_attempts=2, max_moves=0)
        self.assertEqual([e.knot_name for e in result.entries], ["unknown", "unknown"])
        self.assertEqual([e.determinant for e in result.entries], [1, 1])
        self.assertEqual(result.report()["unknown_candidates"], 2)

    def test_generator_exhaustion_returns_report_and_never_loops(self):
        with patch("knots_grid.pipeline.travel_candidates", side_effect=RuntimeError("budget exhausted")) as generate:
            result = generate_collection(1, max_attempts=3)
        self.assertEqual(generate.call_count, 3)
        self.assertEqual((result.status, result.generator_failures), ("attempt_limit", 3))
        self.assertEqual(len(result.events), 3)
        self.assertEqual(generate_collection(0).status, "complete")
        self.assertEqual(generate_collection(1, max_attempts=0).status, "attempt_limit")

    def test_export_preserves_original_result_provenance_and_replay_log(self):
        result = generate_collection(2, seed=2026, max_attempts=3, max_moves=10)
        with TemporaryDirectory() as directory:
            manifest = write_collection(result, directory)
            records = json.loads(manifest.read_text(encoding="utf-8"))
            report = json.loads((Path(directory) / "report.json").read_text(encoding="utf-8"))
            html = (Path(directory) / "index.html").read_text(encoding="utf-8")
            self.assertEqual(report["retained"], len(result.entries))
            self.assertIn('id="version-original"', html)
            for entry, record in zip(result.entries, records):
                self.assertEqual(record["original_point_count"], len(entry.original_points) - 1)
                self.assertTrue((Path(directory) / record["original_svg"]).is_file())
                points = tuple(Point(*p) for p in record["original_points"])
                points += (points[0],)
                for item in record["metadata"]["moves"]:
                    move = FaceMove(item["start_index"], tuple(Point(**p) for p in item["before"]),
                                    tuple(Point(**p) for p in item["after"]), item["kind"])
                    points = apply_face_move(points, move)
                self.assertEqual(points, entry.points)
                self.assertEqual(record["points"], [[p.x, p.y, p.z] for p in points[:-1]])
            # End-to-end reproducibility includes every exported artifact.
            second = Path(directory) / "second"
            write_collection(result, second)
            for artifact in second.iterdir():
                self.assertEqual(artifact.read_bytes(), (Path(directory) / artifact.name).read_bytes())


if __name__ == "__main__":
    unittest.main()
