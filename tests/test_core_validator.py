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


if __name__ == "__main__":
    unittest.main()
