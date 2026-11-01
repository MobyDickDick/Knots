"""Geometric move fixtures, including obstructions and a genuine III slide."""

from dataclasses import asdict, replace
import json
import unittest

from knots_grid import Point, find_crossings, trefoil_candidate
from knots_grid.classification import knot_determinant, signed_gauss_key
from knots_grid.generator import travel_candidate
from knots_grid.optimization import apply_move, move_from_dict, optimize_cycle
from knots_grid.projection import score_projection
from knots_grid.reidemeister_moves import (
    ReidemeisterMove, analyze_reidemeister_moves, apply_reidemeister_move,
)
from knots_grid.validator import validate_cycle


def cycle(waypoints):
    """Expand axis-aligned fixture segments into unit edges, then close."""
    corners = [Point(*p) for p in waypoints]
    points = []
    for a, b in zip(corners, corners[1:] + corners[:1]):
        delta = tuple((v > u) - (v < u) for u, v in zip((a.x, a.y, a.z), (b.x, b.y, b.z)))
        assert sum(v != 0 for v in delta) == 1
        for k in range(abs(b.x - a.x) + abs(b.y - a.y) + abs(b.z - a.z)):
            points.append(Point(a.x + k * delta[0], a.y + k * delta[1], a.z + k * delta[2]))
    result = tuple(points) + (points[0],)
    validate_cycle(result).raise_for_errors()
    assert not score_projection(result).metrics.degeneracies
    return result


def curl():
    return cycle([(-2, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0),
                  (0, 2, 1), (0, -2, 1), (-2, -2, 1), (-2, -2, 0)])


def bigon():
    return cycle([(-2, -2, 1), (0, -2, 1), (0, 2, 1), (4, 2, 1),
                  (4, -2, 1), (8, -2, 1), (8, 0, 1), (8, 0, 0),
                  (-4, 0, 0), (-4, -2, 0), (-4, -2, 1)])


def triangle():
    # A nonalternating three-crossing unknot, with enough room for a slide.
    # The stationary middle strand changes layer away from its crossings.
    return cycle([(0, 0, 0), (12, 0, 0), (12, 0, 1), (12, 12, 1),
                  (12, 12, 0), (6, 12, 0), (6, 12, 1), (6, 3, 1),
                  (6, 3, 0), (3, 3, 0), (3, 3, 1), (3, 15, 1),
                  (3, 15, 0), (15, 15, 0), (15, 15, 1), (15, 6, 1),
                  (15, 6, 0), (9, 6, 0), (9, 6, 1), (9, 9, 1),
                  (9, 9, 0), (0, 9, 0), (0, 9, 1), (0, 0, 1)])


class GeometricReidemeisterTests(unittest.TestCase):
    def test_each_type_executes_and_replays_with_regular_two_layer_results(self):
        for kind, fixture, difference in (("I", curl, -1), ("II", bigon, -2),
                                           ("III", triangle, 0)):
            with self.subTest(kind=kind):
                points = fixture()
                analysis = analyze_reidemeister_moves(points)
                moves = [m for m in analysis.moves if m.kind == "reidemeister_" + kind]
                self.assertTrue(moves, analysis.rejections)
                self.assertTrue(any(r.move_type == kind for r in analysis.regions))
                for move in moves:
                    after = apply_reidemeister_move(points, move)
                    self.assertTrue(validate_cycle(after).is_valid)
                    self.assertEqual(score_projection(after).metrics.degeneracies, 0)
                    self.assertEqual(len(find_crossings(after)), len(find_crossings(points)) + difference)
                    self.assertEqual(knot_determinant(after), knot_determinant(points))
                    self.assertEqual(apply_move(points, move_from_dict(json.loads(json.dumps(asdict(move))))), after)
                    if kind == "III":
                        self.assertNotEqual(signed_gauss_key(points), signed_gauss_key(after))

    def test_optimizer_uses_direct_reductions_and_keeps_length_primary(self):
        for points in (curl(), bigon()):
            result = optimize_cycle(points, max_moves=1)
            self.assertTrue(result.moves[0].kind.startswith("reidemeister_"))
            self.assertLess(len(result.points), len(points))
            self.assertEqual(apply_move(points, result.moves[0]), result.points)
        # This legal III requires more room/length. The optimizer cannot take
        # it merely to improve a diagram or its aesthetic score.
        points = triangle()
        result = optimize_cycle(points, max_moves=1)
        self.assertLessEqual(len(result.points), len(points))

    def test_cyclic_start_reversal_mirrors_and_layer_exchange(self):
        for fixture, kind in ((curl, "I"), (bigon, "II"), (triangle, "III")):
            points = fixture()
            variants = [points[5:-1] + points[:5] + (points[5],), tuple(reversed(points)),
                        tuple(Point(-p.x + 7, p.y - 4, p.z) for p in points),
                        tuple(Point(p.x, p.y, 1 - p.z) for p in points),
                        tuple(Point(-p.y, p.x, p.z) for p in points)]
            for variant in variants:
                with self.subTest(kind=kind, first=variant[0]):
                    moves = [m for m in analyze_reidemeister_moves(variant).moves
                             if m.kind == "reidemeister_" + kind]
                    self.assertTrue(moves)
                    for move in moves:
                        after = apply_reidemeister_move(variant, move)
                        self.assertEqual(knot_determinant(after), knot_determinant(variant))

    def test_cyclic_over_under_triangle_is_not_a_type_iii(self):
        analysis = analyze_reidemeister_moves(trefoil_candidate().points)
        self.assertFalse(analysis.moves)
        self.assertTrue(any("cyclic over/under" in r.reason for r in analysis.rejections))

    def test_enclosed_strand_blocks_a_gauss_curl(self):
        # The exterior continuation enters the apparent curl through its
        # crossing's remaining ray and occupies its interior. Gauss adjacency
        # alone must not certify that larger polygon as an empty move disk.
        points = cycle([(0, 0, 0), (4, 0, 0), (4, -4, 0), (-4, -4, 0),
                        (-4, 4, 0), (0, 4, 0), (0, 4, 1), (0, -2, 1),
                        (-2, -2, 1), (-2, 0, 1), (-2, 0, 0)])
        crossing = next(c for c in find_crossings(points) if c.coordinate == (0, 0))
        report = analyze_reidemeister_moves(points)
        fake = ReidemeisterMove(crossing.lower_index,
                                points[crossing.lower_index:crossing.upper_index + 1],
                                (points[crossing.lower_index], points[crossing.upper_index]),
                                "reidemeister_I")
        self.assertTrue(report.moves)  # The *inner* lobe is an allowed curl.
        self.assertNotIn(fake, report.moves)
        with self.assertRaises(ValueError):
            apply_reidemeister_move(points, fake)

    def test_nonregular_projection_and_routing_limits_have_reasons(self):
        nonregular = (Point(0, 0, 0), Point(1, 0, 0), Point(1, 0, 1), Point(0, 0, 1), Point(0, 0, 0))
        result = analyze_reidemeister_moves(nonregular)
        self.assertEqual(result.rejections[0].reason, "nonregular projection")
        limited = analyze_reidemeister_moves(triangle(), max_route_states=1)
        self.assertFalse(any(m.kind == "reidemeister_III" for m in limited.moves))
        self.assertTrue(any("state limit" in r.reason for r in limited.rejections))
        for limit in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                analyze_reidemeister_moves(triangle(), max_route_states=limit)

    def test_tampered_region_kind_endpoints_path_and_layer_are_rejected(self):
        for fixture, kind in ((curl, "I"), (bigon, "II"), (triangle, "III")):
            points = fixture()
            move = next(m for m in analyze_reidemeister_moves(points).moves
                        if m.kind == "reidemeister_" + kind)
            for bad in (replace(move, start_index=len(points)), replace(move, kind="reidemeister_IV"),
                        replace(move, before=tuple(reversed(move.before))),
                        replace(move, after=(move.after[0], move.after[-1])),
                        replace(move, after=tuple(Point(p.x, p.y, 2) for p in move.after))):
                if bad == move:
                    continue
                with self.subTest(kind=kind, bad=bad.kind), self.assertRaises(ValueError):
                    apply_reidemeister_move(points, bad)

    def test_generated_moves_all_replay_and_preserve_determinants(self):
        for seed in range(20):
            points = travel_candidate(seed=seed).points
            analysis = analyze_reidemeister_moves(points)
            self.assertEqual(analysis, analyze_reidemeister_moves(points))
            for move in analysis.moves:
                after = apply_reidemeister_move(points, move)
                self.assertEqual(knot_determinant(after), knot_determinant(points))


if __name__ == "__main__":
    unittest.main()
