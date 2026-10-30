"""Analytic fixtures and selection contracts for projection scoring."""

import unittest
from dataclasses import fields

from knots_grid import (
    Point,
    ProjectionWeights,
    score_projection,
    search_best_candidate,
    search_candidate,
    search_candidates,
    trace_turtle,
    trefoil_candidate,
    validate_cycle,
)


class ProjectionTests(unittest.TestCase):
    def test_unit_square_has_known_metrics_and_total(self):
        score = score_projection(trace_turtle("1111").points)
        self.assertEqual(score.metrics.crossings, 0)
        self.assertEqual(score.metrics.length, 4)
        self.assertEqual(score.metrics.symmetry, 1)
        self.assertEqual(score.metrics.area_utilization, 1)
        self.assertEqual(score.metrics.layer_switches, 0)
        self.assertEqual(score.metrics.degeneracies, 0)
        self.assertAlmostEqual(score.total, 1.8)

    def test_area_utilization_counts_bounding_box_grid_vertices(self):
        # A 3x3 square occupies 12 of its 16 projected grid vertices.
        points = trace_turtle("000100100100").points
        score = score_projection(points)
        self.assertEqual(score.metrics.length, 12)
        self.assertEqual(score.metrics.symmetry, 1)
        self.assertEqual(score.metrics.area_utilization, 0.75)

    def test_trefoil_crossings_are_rewarded(self):
        weights = ProjectionWeights(
            crossings=1, length=0, symmetry=0, area_utilization=0,
            layer_switches=0, degeneracies=0,
        )
        score = score_projection(trefoil_candidate().points, weights=weights)
        self.assertEqual(score.metrics.crossings, 3)
        self.assertEqual(score.metrics.degeneracies, 0)
        self.assertEqual(score.total, 3)

    def test_layer_switches_and_overlapping_edges_are_distinguished(self):
        points = [
            Point(0, 0, 0), Point(1, 0, 0), Point(1, 0, 1),
            Point(0, 0, 1), Point(0, 0, 0),
        ]
        score = score_projection(points)
        self.assertEqual(score.metrics.crossings, 0)
        self.assertEqual(score.metrics.layer_switches, 2)
        self.assertEqual(score.metrics.degeneracies, 1)

    def test_score_is_invariant_under_representation_and_grid_symmetries(self):
        points = search_candidate(seed=2026).points
        expected = score_projection(points)
        for swap in (False, True):
            for sx in (-1, 1):
                for sy in (-1, 1):
                    transformed = tuple(
                        Point(sx * (p.y if swap else p.x) + 7,
                              sy * (p.x if swap else p.y) - 11, p.z)
                        for p in points[:-1]
                    )
                    for body in (transformed, tuple(reversed(transformed))):
                        body = body[3:] + body[:3]
                        with self.subTest(swap=swap, sx=sx, sy=sy):
                            self.assertEqual(score_projection(body + (body[0],)), expected)

    def test_non_transverse_double_visit_is_penalized(self):
        points = tuple(Point(*p) for p in (
            (0, 0, 0), (1, 0, 0), (1, 1, 0), (2, 1, 0),
            (2, 1, 1), (2, 0, 1), (1, 0, 1), (1, -1, 1),
            (0, -1, 1), (0, -1, 0), (0, 0, 0),
        ))
        score = score_projection(points)
        self.assertEqual(score.metrics.crossings, 0)
        self.assertEqual(score.metrics.degeneracies, 1)
        self.assertLess(score.metrics.symmetry, 1)

    def test_penalty_weights_subtract_and_do_not_change_metrics(self):
        points = [
            Point(0, 0, 0), Point(1, 0, 0), Point(1, 0, 1),
            Point(0, 0, 1), Point(0, 0, 0),
        ]
        weights = ProjectionWeights(
            crossings=0, length=2, symmetry=0, area_utilization=0,
            layer_switches=3, degeneracies=5,
        )
        score = score_projection(points, weights=weights)
        self.assertEqual(score.metrics, score_projection(points).metrics)
        self.assertEqual(score.total, -19)

    def test_invalid_paths_are_rejected(self):
        for points in ((), trace_turtle("0").points, trace_turtle("11111111").points):
            with self.subTest(points=points), self.assertRaises(ValueError):
                score_projection(points)

    def test_all_weights_must_be_finite_and_non_negative(self):
        for field in fields(ProjectionWeights):
            for value in (-1, float("nan"), float("inf")):
                with self.subTest(field=field.name, value=value), self.assertRaises(ValueError):
                    ProjectionWeights(**{field.name: value})


class ScoredSearchTests(unittest.TestCase):
    def test_best_search_matches_maximum_of_same_seeded_batch(self):
        batch = search_candidates(12, seed=2026)
        best = search_best_candidate(12, seed=2026)
        self.assertIn(best, batch)
        self.assertTrue(validate_cycle(best.points).is_valid)
        self.assertEqual(
            score_projection(best.points).total,
            max(score_projection(candidate.points).total for candidate in batch),
        )
        self.assertEqual(best, search_best_candidate(12, seed=2026))

    def test_length_only_weights_choose_shortest_candidate(self):
        weights = ProjectionWeights(
            crossings=0, length=1, symmetry=0, area_utilization=0,
            layer_switches=0, degeneracies=0,
        )
        batch = search_candidates(12, seed=7)
        best = search_best_candidate(12, seed=7, weights=weights)
        self.assertEqual(len(best.points), min(len(candidate.points) for candidate in batch))

    def test_ties_choose_first_candidate_and_single_sample_is_supported(self):
        weights = ProjectionWeights(**{field.name: 0 for field in fields(ProjectionWeights)})
        self.assertEqual(search_best_candidate(5, seed=7, weights=weights),
                         search_candidate(seed=7))
        self.assertEqual(search_best_candidate(1, seed=7), search_candidate(seed=7))

    def test_empty_sample_is_rejected(self):
        for count in (0, -1):
            with self.subTest(count=count), self.assertRaises(ValueError):
                search_best_candidate(count)


if __name__ == "__main__":
    unittest.main()
