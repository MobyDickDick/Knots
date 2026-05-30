import unittest

from knots import Knot, check_knot, generate, optimize, rectangle, to_svg


class KnotTests(unittest.TestCase):
    def test_rectangle_is_valid(self):
        knot = rectangle(4, 3)
        report = check_knot(knot)
        self.assertTrue(report.valid, report.errors)

    def test_duplicate_point_is_invalid(self):
        knot = Knot([(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 0)])
        report = check_knot(knot)
        self.assertFalse(report.valid)
        self.assertTrue(any("Duplicate" in error for error in report.errors))

    def test_generator_outputs_valid_layered_knot(self):
        knot = generate("layered", seed=3)
        report = check_knot(knot)
        self.assertTrue(report.valid, report.errors)
        self.assertGreater(len(knot), len(rectangle()))

    def test_optimizer_removes_generated_detours(self):
        knot = generate("layered", seed=5)
        result = optimize(knot)
        self.assertTrue(check_knot(result.knot).valid)
        self.assertLess(len(result.knot), len(knot))
        self.assertGreater(result.saved_points, 0)

    def test_svg_contains_layer_colours(self):
        svg = to_svg(generate("layered", seed=9))
        self.assertIn("<svg", svg)
        self.assertIn("#276ef1", svg)
        self.assertIn("#f05a28", svg)


if __name__ == "__main__":
    unittest.main()
