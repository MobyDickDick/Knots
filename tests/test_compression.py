from dataclasses import asdict, replace
import json
import unittest

from knots_grid import Point, figure_eight_candidate, trace_turtle, trefoil_candidate, validate_cycle
from knots_grid.classification import knot_determinant, signed_gauss_key
from knots_grid.optimization import (
    SlabContraction, apply_move, coordinate_compression, move_from_dict, optimize_cycle,
)
from knots_grid.studio import minimize_record


REPORTED_CODE = (
    "001000002000000000031000000000000000100300000000010000000000000000000031000000000000000000000000000"
    "31000000000000000000000000310000000000000000000100001003002000000000000000230000000000000100003"
)


def stretched(points, x_scale=7, y_scale=5):
    targets = [Point(p.x*x_scale, p.y*y_scale, p.z) for p in points]
    path = [targets[0]]
    for target in targets[1:]:
        while path[-1] != target:
            p = path[-1]
            path.append(Point(p.x+(target.x > p.x)-(target.x < p.x),
                              p.y+(target.y > p.y)-(target.y < p.y),
                              p.z+(target.z > p.z)-(target.z < p.z)))
    return tuple(path)


class CoordinateCompressionTests(unittest.TestCase):
    def test_reported_194_step_knot_is_shortened_with_same_signed_diagram(self):
        points = trace_turtle(REPORTED_CODE).points
        self.assertEqual(len(points)-1, 194)
        compact = apply_move(points, coordinate_compression(points))
        self.assertEqual(len(compact)-1, 62)
        self.assertTrue(validate_cycle(compact).is_valid)
        self.assertEqual(signed_gauss_key(compact), signed_gauss_key(points))
        self.assertEqual(knot_determinant(compact), 5)
        self.assertEqual(max(p.x for p in compact), 8)
        self.assertEqual(max(p.y for p in compact), 6)

    def test_studio_minimizes_the_reported_knot_and_keeps_an_exact_code(self):
        points = trace_turtle(REPORTED_CODE).points
        result = minimize_record({"points": [[p.x, p.y, p.z] for p in points]})
        self.assertEqual(result["name"], "4_1")
        self.assertEqual(result["metrics"]["length"], 52)
        self.assertEqual(result["layer_lengths"], [22, 22])
        self.assertEqual(result["classification"]["determinant"], 5)
        self.assertEqual(trace_turtle(result["code"]).points,
                         tuple(Point(*p) for p in result["points"]))
        replay = points
        for move in result["optimization"]["moves"]:
            replay = apply_move(replay, move_from_dict(json.loads(json.dumps(move))))
        self.assertEqual(len(replay), len(result["points"]))

    def test_stretched_reference_knots_preserve_crossing_and_height_order(self):
        for reference in (trefoil_candidate(), figure_eight_candidate()):
            with self.subTest(code=reference.code):
                points = stretched(reference.points)
                compact = apply_move(points, coordinate_compression(points))
                self.assertLess(len(compact), len(points))
                self.assertEqual(signed_gauss_key(compact), signed_gauss_key(points))
                self.assertEqual(knot_determinant(compact), knot_determinant(points))

    def test_start_in_the_middle_of_a_straight_edge_is_not_pinned(self):
        rectangle = trace_turtle("000000000010000000100000000010000000").points
        self.assertTrue(validate_cycle(rectangle).is_valid)
        body = rectangle[:-1]
        rotated = body[3:]+body[:3]+(body[3],)
        result = apply_move(rotated, coordinate_compression(rotated))
        self.assertEqual(len(result)-1, 4)
        self.assertTrue(validate_cycle(result).is_valid)

    def test_log_roundtrip_and_tampering_checks(self):
        points = trace_turtle(REPORTED_CODE).points
        move = coordinate_compression(points)
        decoded = move_from_dict(json.loads(json.dumps(asdict(move))))
        self.assertEqual(apply_move(points, move), apply_move(points, decoded))
        with self.assertRaises(ValueError):
            apply_move(points, replace(move, x_levels=move.x_levels[:-1]))
        with self.assertRaises(ValueError):
            move_from_dict({"kind": "coordinate_compression", "x_levels": [True], "y_levels": [0]})

    def test_global_compression_is_optional_for_legacy_local_search(self):
        points = trace_turtle(REPORTED_CODE).points
        old = optimize_cycle(points, max_moves=1, balance_layers=True)
        improved = optimize_cycle(points, max_moves=1, balance_layers=True, compress_coordinates=True)
        self.assertEqual(old.status, "local_minimum")
        self.assertFalse(old.moves)
        self.assertEqual(improved.moves[0].kind, "coordinate_compression")
        self.assertLess(len(improved.points), len(old.points))

    def test_slab_can_merge_active_levels_without_merging_separate_strands(self):
        original = trace_turtle(REPORTED_CODE).points
        points = apply_move(original, coordinate_compression(original))
        move = SlabContraction(0, 4)
        decoded = move_from_dict(json.loads(json.dumps(asdict(move))))
        result = apply_move(points, decoded)
        self.assertEqual(len(result)-1, 56)
        self.assertEqual(signed_gauss_key(result), signed_gauss_key(points))
        self.assertTrue(validate_cycle(result).is_valid)

    def test_slab_rejects_collisions_or_collapse_of_the_entire_cycle(self):
        points = trace_turtle("0111").points
        with self.assertRaises(ValueError):
            apply_move(points, SlabContraction(0, 0))
        with self.assertRaises(ValueError):
            apply_move(points, SlabContraction(2, 0))
        with self.assertRaises(ValueError):
            apply_move(points, SlabContraction(0, 50))
        with self.assertRaises(ValueError):
            move_from_dict({"kind": "grid_slab_contraction", "axis": True, "coordinate": 0})

    def test_accepted_slabs_preserve_reference_determinants(self):
        for reference in (trefoil_candidate(), figure_eight_candidate()):
            points = reference.points
            rejected = 0
            for axis in (0, 1):
                levels = [(p.x, p.y)[axis] for p in points]
                for level in range(min(levels), max(levels)):
                    try:
                        result = apply_move(points, SlabContraction(axis, level))
                    except ValueError:
                        rejected += 1
                        continue
                    self.assertTrue(validate_cycle(result).is_valid)
                    determinant = knot_determinant(result)
                    if determinant is not None:
                        self.assertEqual(determinant, knot_determinant(points))
            self.assertGreater(rejected, 0)
