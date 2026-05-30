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


if __name__ == "__main__":
    unittest.main()
