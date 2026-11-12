import http.client
import json
import threading
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from knots_grid import Point, find_crossings, trace_turtle, validate_cycle
from knots_grid.studio import StudioHandler, StudioServer, generate_record, minimize_record
from knots_grid.optimization import apply_move, layer_lengths, move_from_dict, optimize_cycle, redistribute_layers
from knots_grid.classification import signed_gauss_key
from knots_grid.catalog import canonicalize_cycle, sequence_measure


class StudioGenerationTests(unittest.TestCase):
    def test_every_preset_exports_a_valid_cycle_and_exact_turtle_roundtrip(self):
        for preset in ("trefoil", "figure-eight", "torus", "travel", "ornamental"):
            with self.subTest(preset=preset):
                record = generate_record({"preset": preset, "seed": "2026"})
                points = tuple(Point(*p) for p in record["points"])
                self.assertTrue(validate_cycle(points).is_valid)
                self.assertEqual(trace_turtle(record["code"]).points, points)
                self.assertEqual(record["metrics"]["length"], len(points) - 1)
                root = ElementTree.fromstring(record["svg"])
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_reference_knots_keep_their_certified_names(self):
        for preset, q, name, determinant in (
            ("trefoil", 5, "T(2,3)", 3),
            ("figure-eight", 5, "4_1", 5),
            ("torus", 15, "T(2,15)", 15),
        ):
            with self.subTest(preset=preset):
                record = generate_record({"preset": preset, "crossings": q})
                self.assertEqual(record["name"], name)
                self.assertEqual(record["classification"]["status"], "certified")
                self.assertEqual(record["classification"]["determinant"], determinant)

    def test_large_seed_is_exact_and_reproducible(self):
        options = {"preset": "travel", "seed": "9223372036854775807", "point_count": 12}
        first = generate_record(options)
        self.assertEqual(first, generate_record(options))
        self.assertEqual(first["parameters"]["seed"], options["seed"])

    def test_studio_defaults_to_mixed_crossings_and_exports_replayable_parameters(self):
        record = generate_record({"preset": "travel", "seed": "2026"})
        points = tuple(Point(*p) for p in record["points"])
        upper_axes = {points[c.upper_index - 1].y == points[c.upper_index + 1].y
                      for c in find_crossings(points)}
        self.assertEqual(upper_axes, {False, True})
        self.assertEqual(record["parameters"]["crossing_mode"], "mixed")
        self.assertEqual(record, generate_record(record["parameters"]))

    def test_malformed_or_unbounded_options_are_rejected(self):
        for options in (
            [], None, {"preset": []}, {"preset": "unknown"}, {"seed": True},
            {"seed": 2.5}, {"seed": -1}, {"seed": "1e5"}, {"seed": "--1"},
            {"seed": "9223372036854775808"}, {"seed": "9" * 1000},
            {"point_count": 3}, {"point_count": 25}, {"point_count": 4.0},
            {"crossings": 4}, {"crossings": 17}, {"steps": 61}, {"steps": -1},
            {"output": "unrequested-file"}, {"crossing_mode": "invalid"},
            {"crossing_mode": []},
        ):
            with self.subTest(options=str(options)[:100]):
                with self.assertRaises(ValueError):
                    generate_record(options)


class StudioHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = StudioServer(("127.0.0.1", 0), StudioHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_page_and_assets_are_served_without_exposing_other_files(self):
        for path, content_type in (("/", "text/html"), ("/studio.js", "text/javascript"),
                                   ("/studio.css", "text/css")):
            status, actual_type, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertTrue(actual_type.startswith(content_type))
            self.assertTrue(body)
        self.assertEqual(self.request("GET", "/../studio.py")[0], 404)
        self.assertEqual(self.request("GET", "/.git/config")[0], 404)

    def test_json_api_and_errors(self):
        headers = {"Content-Type": "application/json"}
        status, _, body = self.request("POST", "/api/generate", '{"preset":"trefoil"}', headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["name"], "T(2,3)")
        for body in ("[1,2]", "{", '{"point_count":99999}'):
            self.assertEqual(self.request("POST", "/api/generate", body, headers)[0], 400)
        self.assertEqual(self.request("POST", "/api/generate", "{}",
                                      {"Content-Type": "text/plain"})[0], 400)
        self.assertEqual(self.request("POST", "/api/generate", " " * 8193, headers)[0], 400)

    def test_minimization_endpoint_uses_displayed_points(self):
        original = generate_record({"preset": "travel", "point_count": 5})
        payload = {"points": original["points"], "parameters": original["parameters"], "max_moves": 3}
        status, _, body = self.request("POST", "/api/minimize", json.dumps(payload),
                                      {"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["optimization"]["input_points"], original["points"])
        self.assertLess(result["metrics"]["length"], original["metrics"]["length"])
        self.assertEqual(self.request("POST", "/api/minimize", '{"points":[]}',
                                      {"Content-Type": "application/json"})[0], 400)

    def test_foreign_host_and_origin_are_rejected(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "foreign.example"})[0], 403)
        headers = {"Content-Type": "application/json", "Origin": "https://foreign.example"}
        self.assertEqual(self.request("POST", "/api/generate", "{}", headers)[0], 403)

    def test_a_second_server_cannot_share_the_same_port(self):
        with self.assertRaises(OSError):
            second = StudioServer(("127.0.0.1", self.server.server_port), StudioHandler)
            second.server_close()

    def test_search_exhaustion_becomes_an_actionable_response(self):
        with patch("knots_grid.studio.travel_candidate", side_effect=RuntimeError("attempt limit")):
            status, _, body = self.request("POST", "/api/generate", '{"preset":"travel"}',
                                           {"Content-Type": "application/json"})
        self.assertEqual(status, 422)
        self.assertIn("Seed", json.loads(body)["error"])


class StudioMinimizationTests(unittest.TestCase):
    def test_shortening_replays_every_certificate_and_turtle_normalization(self):
        original = generate_record({"preset": "travel", "point_count": 5})
        result = minimize_record({"points": original["points"], "parameters": original["parameters"],
                                  "max_moves": 6})
        self.assertLess(result["metrics"]["length"], original["metrics"]["length"])
        points = tuple(Point(*p) for p in original["points"])

        def objective(path):
            length, cantor = sequence_measure(canonicalize_cycle(path, include_reflections=False)[:-1])
            low, high = layer_lengths(path)
            return length, abs(low-high), cantor

        for record in result["optimization"]["moves"]:
            after = apply_move(points, move_from_dict(record))
            self.assertTrue(validate_cycle(after).is_valid)
            self.assertLess(objective(after), objective(points))
            points = after
        transform = result["optimization"]["normalization"]
        i = transform["cyclic_start"]
        x, y, z = transform["origin"]
        dx, dy = transform["east"]
        body = points[:-1]
        normalized = [[dx*(p.x-x)+dy*(p.y-y), -dy*(p.x-x)+dx*(p.y-y), p.z-z]
                      for p in body[i:] + body[:i] + (body[i],)]
        self.assertEqual(normalized, result["points"])
        self.assertEqual(trace_turtle(result["code"]).points, tuple(Point(*p) for p in normalized))
        self.assertEqual(result["classification"]["determinant"], original["classification"]["determinant"])

    def test_minimization_shortens_and_improves_the_relative_layer_distribution(self):
        original = generate_record({"preset": "travel", "point_count": 8})
        result = minimize_record({"points": original["points"], "max_moves": 8,
                                  "parameters": original["parameters"]})
        self.assertLess(result["metrics"]["length"], original["metrics"]["length"])
        low, high = result["layer_lengths"]
        old_low, old_high = original["layer_lengths"]
        self.assertLess(abs(low-high)/max(1,low+high), abs(old_low-old_high)/(old_low+old_high))

    def test_continuation_operates_on_the_previous_result(self):
        original = generate_record({"preset": "travel", "point_count": 5})
        first = minimize_record({"points": original["points"], "max_moves": 2})
        second = minimize_record({"points": first["points"], "max_moves": 2})
        self.assertEqual(second["optimization"]["input_points"], first["points"])
        self.assertLessEqual(second["metrics"]["length"], first["metrics"]["length"])

    def test_distribution_preserves_crossings_and_replays_without_extra_points(self):
        original = generate_record({"preset": "travel", "point_count": 8})
        points = tuple(Point(*p) for p in original["points"])
        result = redistribute_layers(points, max_moves=40)
        self.assertEqual(len(result.points), len(points))
        self.assertEqual(signed_gauss_key(result.points), signed_gauss_key(points))
        self.assertGreater(layer_lengths(result.points)[1], layer_lengths(points)[1])
        for move in result.moves:
            before = abs(layer_lengths(points)[0]-layer_lengths(points)[1])
            points = apply_move(points, move)
            after = abs(layer_lengths(points)[0]-layer_lengths(points)[1])
            self.assertLess(after, before)
        self.assertEqual(points, result.points)

    def test_certified_reference_name_is_preserved(self):
        original = generate_record({"preset": "trefoil"})
        result = minimize_record({"points": original["points"], "parameters": original["parameters"],
                                  "max_moves": 2})
        self.assertEqual(result["name"], original["name"])
        self.assertEqual(result["classification"]["status"], "certified")
        self.assertEqual(result["classification"]["determinant"], 3)

    def test_invalid_inputs_and_budgets_are_rejected(self):
        for options in ([], {}, {"points": []}, {"points": [[0, 0, 0]] * 6001},
                        {"points": [[0, 0, True]] * 5}, {"points": [[0, 0, 0]] * 5},
                        {"max_moves": 0}, {"max_moves": 241}, {"max_moves": True}):
            with self.subTest(options=str(options)[:80]):
                with self.assertRaises(ValueError):
                    minimize_record(options)

    def test_time_budget_returns_a_valid_partial_result(self):
        points = trace_turtle("0111").points
        with patch("knots_grid.optimization.monotonic", side_effect=[0, 1]):
            result = optimize_cycle(points, max_seconds=0.1)
        self.assertEqual(result.status, "time_limit")
        self.assertEqual(result.points, points)
        self.assertFalse(result.moves)


if __name__ == "__main__":
    unittest.main()
