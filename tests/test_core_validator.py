import unittest

from knots_grid import Point, trace_turtle, validate_cycle
from knots_grid.validator import is_valid_edge


class TurtleCoreTests(unittest.TestCase):
    def test_square_trace_is_closed(self):
        result = trace_turtle("1111")
        self.assertEqual(result.points[0], result.points[-1])
        self.assertEqual(result.points[0], Point(0, 0, 0))

    def test_layer_switch(self):
        result = trace_turtle("3")
        self.assertEqual(result.points, (Point(0, 0, 0), Point(0, 0, 1)))

    def test_invalid_command(self):
        with self.assertRaises(ValueError):
            trace_turtle("9")


class ValidatorTests(unittest.TestCase):
    def test_valid_square(self):
        points = trace_turtle("1111").points
        result = validate_cycle(points)
        self.assertTrue(result.is_valid, result.errors)

    def test_unclosed_path_is_invalid(self):
        points = trace_turtle("0").points
        result = validate_cycle(points)
        self.assertFalse(result.is_valid)

    def test_duplicate_point_is_invalid(self):
        points = (Point(0, 0, 0), Point(1, 0, 0), Point(0, 0, 0), Point(0, 0, 0))
        result = validate_cycle(points)
        self.assertFalse(result.is_valid)

    def test_edge_rules(self):
        self.assertTrue(is_valid_edge(Point(0, 0, 0), Point(1, 0, 0)))
        self.assertTrue(is_valid_edge(Point(0, 0, 0), Point(0, 0, 1)))
        self.assertFalse(is_valid_edge(Point(0, 0, 0), Point(1, 1, 0)))
        self.assertFalse(is_valid_edge(Point(0, 0, 0), Point(1, 0, 1)))


class CompactCodecTests(unittest.TestCase):
    def test_number_examples_match_digit_continuation_scheme(self):
        from knots_grid.compact import decode_number, encode_number

        self.assertEqual(encode_number(4), "110100")
        self.assertEqual(encode_number(7), "111110")
        self.assertEqual(decode_number("110100"), (4, 6))
        self.assertEqual(decode_number("111110"), (7, 6))

    def test_known_unknot_round_trip_and_compression(self):
        from knots_grid.compact import decode_turtle, encode_turtle, trace_compact

        # Rectangular diagram of the classical unknot 0_1: east 5, north 3,
        # west 5, south 3, returning to the start.
        code = "00000" + "1" + "00" + "1" + "0000" + "1" + "00"
        packed = encode_turtle(code)
        unpacked = decode_turtle(packed)

        self.assertEqual(unpacked, code)
        self.assertEqual(trace_compact(packed).points, trace_turtle(code).points)
        self.assertEqual(trace_turtle(unpacked).points[0], trace_turtle(unpacked).points[-1])
        self.assertLess(len(packed), len(code) * 2)

    def test_layer_switch_with_zero_steps_round_trips(self):
        from knots_grid.compact import decode_turtle, encode_turtle, trace_compact

        packed = encode_turtle("3")
        self.assertEqual(packed, "11" + "00")
        self.assertEqual(decode_turtle(packed), "3")
        self.assertEqual(trace_compact(packed).points, trace_turtle("3").points)


class GeneratorTests(unittest.TestCase):
    def test_trefoil_is_valid_and_has_real_crossings(self):
        from knots_grid import find_crossings, trefoil_candidate

        candidate = trefoil_candidate()

        self.assertTrue(validate_cycle(candidate.points).is_valid)
        self.assertEqual(len(find_crossings(candidate.points)), 3)
        self.assertEqual({point.z for point in candidate.points}, {0, 1})

    def test_seeded_generation_is_reproducible_and_valid(self):
        from knots_grid import generate_candidate

        first = generate_candidate(seed=2026)
        second = generate_candidate(seed=2026)

        self.assertEqual(first, second)
        self.assertTrue(validate_cycle(first.points).is_valid)

    def test_layered_generation_adds_two_layer_switches(self):
        from knots_grid import GeneratorConfig, generate_candidate

        candidate = generate_candidate(
            seed=7,
            config=GeneratorConfig(
                min_side_length=2,
                max_side_length=2,
                layer_probability=1.0,
            ),
        )

        self.assertEqual(candidate.code.count("3"), 2)
        self.assertEqual({point.z for point in candidate.points}, {0, 1})
        self.assertTrue(validate_cycle(candidate.points).is_valid)

    def test_planar_generation_stays_on_lower_layer(self):
        from knots_grid import GeneratorConfig, generate_candidate

        candidate = generate_candidate(
            seed=7,
            config=GeneratorConfig(layer_probability=0.0),
        )

        self.assertNotIn("3", candidate.code)
        self.assertEqual({point.z for point in candidate.points}, {0})

    def test_candidate_batch_uses_one_reproducible_stream(self):
        from knots_grid import generate_candidates

        batch = generate_candidates(4, seed=99)

        self.assertEqual(batch, generate_candidates(4, seed=99))
        self.assertEqual(len(batch), 4)
        self.assertTrue(all(validate_cycle(candidate.points).is_valid for candidate in batch))

    def test_generator_rejects_invalid_configuration(self):
        from knots_grid import GeneratorConfig, generate_candidates

        with self.assertRaises(ValueError):
            GeneratorConfig(min_side_length=0)
        with self.assertRaises(ValueError):
            GeneratorConfig(min_side_length=5, max_side_length=4)
        with self.assertRaises(ValueError):
            GeneratorConfig(layer_probability=1.1)
        with self.assertRaises(ValueError):
            generate_candidates(-1)

    def test_search_is_reproducible_varied_and_valid(self):
        from knots_grid import SearchConfig, search_candidate

        config = SearchConfig(
            min_side_length=3,
            max_side_length=3,
            min_search_steps=5,
            max_search_steps=5,
            layer_probability=0.0,
        )
        first = search_candidate(seed=2026, config=config)
        second = search_candidate(seed=2026, config=config)

        self.assertEqual(first, second)
        self.assertEqual(len(first.points), 4 * 3 + 1 + 2 * 5)
        self.assertTrue(validate_cycle(first.points).is_valid)

    def test_search_can_lift_local_edges(self):
        from knots_grid import SearchConfig, search_candidate

        candidate = search_candidate(
            seed=7,
            config=SearchConfig(
                min_side_length=3,
                max_side_length=3,
                min_search_steps=3,
                max_search_steps=3,
                layer_probability=1.0,
            ),
        )

        self.assertEqual(candidate.code.count("3"), 6)
        self.assertEqual({point.z for point in candidate.points}, {0, 1})
        self.assertTrue(validate_cycle(candidate.points).is_valid)

    def test_search_batch_uses_one_reproducible_stream(self):
        from knots_grid import search_candidates

        batch = search_candidates(4, seed=99)

        self.assertEqual(batch, search_candidates(4, seed=99))
        self.assertEqual(len(batch), 4)
        self.assertTrue(all(validate_cycle(candidate.points).is_valid for candidate in batch))

    def test_search_rejects_invalid_configuration(self):
        from knots_grid import SearchConfig, search_candidates

        with self.assertRaises(ValueError):
            SearchConfig(min_search_steps=-1)
        with self.assertRaises(ValueError):
            SearchConfig(min_search_steps=5, max_search_steps=4)
        with self.assertRaises(ValueError):
            SearchConfig(layer_probability=-0.1)
        with self.assertRaises(ValueError):
            search_candidates(-1)


class ReidemeisterTests(unittest.TestCase):
    def test_trefoil_has_no_reidemeister_one_or_two_candidate(self):
        from knots_grid import reidemeister_conditions, trefoil_candidate

        report = reidemeister_conditions(trefoil_candidate().points)

        self.assertEqual(len(report.crossings), 3)
        self.assertEqual(report.type_i, ())
        self.assertEqual(report.type_ii, ())
        self.assertEqual(report.type_iii, ((0, 1, 2),))

    def test_layer_switch_is_not_misclassified_as_crossing(self):
        from knots_grid import GeneratorConfig, find_crossings, generate_candidate

        candidate = generate_candidate(
            seed=7,
            config=GeneratorConfig(
                min_side_length=2, max_side_length=2, layer_probability=1.0
            ),
        )
        self.assertEqual(find_crossings(candidate.points), ())


class CatalogTests(unittest.TestCase):
    def test_canonicalization_removes_translation_start_and_reversal(self):
        from knots_grid import Point
        from knots_grid.catalog import canonicalize_cycle

        square = (
            Point(3, 4, 0), Point(4, 4, 0), Point(4, 5, 0),
            Point(3, 5, 0), Point(3, 4, 0),
        )
        shifted_reversed = tuple(reversed(square))
        first = canonicalize_cycle(square)
        second = canonicalize_cycle(shifted_reversed)

        self.assertEqual(first, second)
        self.assertEqual(min(point.x for point in first), 0)
        self.assertEqual(min(point.y for point in first), 0)

    def test_sequence_measure_does_not_collapse_equal_coordinate_sums(self):
        from knots_grid import Point
        from knots_grid.catalog import sequence_measure

        first = (Point(0, 0, 0), Point(1, 1, 0))
        second = (Point(1, 0, 0), Point(0, 1, 0))
        self.assertNotEqual(sequence_measure(first), sequence_measure(second))

    def test_shorter_equivalent_wins_before_cantor_measure(self):
        from knots_grid import Point
        from knots_grid.catalog import choose_shortest_equivalent

        square = (
            Point(0, 0, 0), Point(1, 0, 0), Point(1, 1, 0),
            Point(0, 1, 0), Point(0, 0, 0),
        )
        square_with_detour = (
            Point(0, 0, 0), Point(1, 0, 0), Point(1, -1, 0),
            Point(2, -1, 0), Point(2, 0, 0), Point(2, 1, 0),
            Point(1, 1, 0), Point(0, 1, 0), Point(0, 0, 0),
        )

        chosen = choose_shortest_equivalent((square_with_detour, square))
        self.assertEqual(len(chosen) - 1, 4)

    def test_shortest_equivalent_requires_a_candidate(self):
        from knots_grid.catalog import choose_shortest_equivalent

        with self.assertRaises(ValueError):
            choose_shortest_equivalent(())

    def test_systematic_catalog_is_reproducible_unique_and_valid(self):
        from knots_grid import SearchConfig
        from knots_grid.catalog import canonical_key, generate_catalog

        config = SearchConfig(min_search_steps=1, max_search_steps=3)
        first = generate_catalog(8, mode="systematic", config=config)
        second = generate_catalog(8, mode="systematic", config=config)

        self.assertEqual(first, second)
        self.assertEqual(len({canonical_key(entry.points) for entry in first}), 8)
        self.assertTrue(all(validate_cycle(entry.points).is_valid for entry in first))


if __name__ == "__main__":
    unittest.main()
