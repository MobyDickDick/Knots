from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from knots_grid import Point, figure_eight_candidate, trace_turtle, trefoil_candidate, validate_cycle
from knots_grid.classification import classify_knot, signed_gauss_key
from knots_grid.image_tracer import (
    CrossingChoice, DiagramAnnotation, annotation_from_dict, annotation_to_dict,
    diagram_crossings, main, trace_annotation, write_traced_diagram, write_tracer_editor,
)
from knots_grid.projection import score_projection
from knots_grid.reidemeister import find_crossings


def annotate_grid_candidate(candidate):
    """Independent conversion of existing vertical-over grid fixtures to waypoints."""
    xy = []
    for p in candidate.points:
        if not xy or xy[-1] != (p.x, p.y):
            xy.append((p.x, p.y))
    xy.pop()
    pts = tuple(b for i, b in enumerate(xy)
                if (b[0] - xy[i-1][0], b[1] - xy[i-1][1]) !=
                (xy[(i+1) % len(xy)][0] - b[0], xy[(i+1) % len(xy)][1] - b[1]))
    choices = tuple(CrossingChoice(c, next(i for i in pair if pts[i][0] == pts[(i+1) % len(pts)][0]))
                    for c, pair in diagram_crossings(pts).items())
    return DiagramAnnotation(pts, choices)


class ImageTracerTests(unittest.TestCase):
    def test_planar_square_and_collinear_supports_roundtrip(self):
        annotation = DiagramAnnotation(((9, -4), (9, -2), (9, 0), (5, 0), (5, -4)))
        result = trace_annotation(annotation)
        self.assertEqual(result.points[0], Point(0, 0, 0))
        self.assertEqual(result.points[1], Point(1, 0, 0))
        self.assertEqual(trace_turtle(result.code), result)
        self.assertTrue(validate_cycle(result.points).is_valid)
        self.assertEqual(classify_knot(result.points).name, "0_1")
        self.assertEqual(len(result.points) - 1, 64)

    def test_trefoil_and_figure_eight_preserve_full_signed_diagrams(self):
        for original in (trefoil_candidate(), figure_eight_candidate()):
            with self.subTest(key=signed_gauss_key(original.points)):
                annotation = annotate_grid_candidate(original)
                result = trace_annotation(annotation)
                self.assertEqual(signed_gauss_key(result.points), signed_gauss_key(original.points))
                self.assertEqual(classify_knot(result.points).name, classify_knot(original.points).name)
                self.assertEqual(score_projection(result.points).metrics.degeneracies, 0)
                self.assertEqual(len(find_crossings(result.points)), len(annotation.crossings))
                self.assertEqual(set(p.z for p in result.points), {0, 1})
                self.assertEqual(trace_turtle(result.code).points, result.points)

    def test_each_crossing_choice_controls_the_correct_strand(self):
        annotation = annotate_grid_candidate(trefoil_candidate())
        # This fixture starts at the origin heading east: the transform is just * 4.
        for mask in range(8):
            choices = []
            pairs = diagram_crossings(annotation.waypoints)
            for i, (coordinate, pair) in enumerate(pairs.items()):
                choices.append(CrossingChoice(coordinate, pair[(mask >> i) & 1]))
            result = trace_annotation(replace(annotation, crossings=tuple(choices)))
            crossings = {c.coordinate: c for c in find_crossings(result.points)}
            for choice in choices:
                crossing = crossings[tuple(4 * v for v in choice.coordinate)]
                p, q = result.points[crossing.upper_index-1], result.points[crossing.upper_index+1]
                a = annotation.waypoints[choice.over_segment]
                b = annotation.waypoints[(choice.over_segment+1) % len(annotation.waypoints)]
                self.assertEqual(p.x == q.x, a[0] == b[0])

    def test_rotations_translations_start_and_reversal_keep_chirality(self):
        annotation = annotate_grid_candidate(trefoil_candidate())
        expected = classify_knot(trace_annotation(annotation).points).name
        for turn in range(4):
            def transform(p):
                x, y = p
                for _ in range(turn):
                    x, y = -y, x
                return x + 7, y - 12
            for reverse in (False, True):
                for start in range(len(annotation.waypoints)):
                    pts = annotation.waypoints[start:] + annotation.waypoints[:start]
                    if reverse:
                        pts = tuple(reversed(pts))
                    # The original diagram has vertical over-strands; after odd rotations horizontal.
                    pts = tuple(transform(p) for p in pts)
                    choices = tuple(CrossingChoice(c, next(i for i in pair
                        if (pts[i][0] == pts[(i+1) % len(pts)][0]) == (turn % 2 == 0)))
                        for c, pair in diagram_crossings(pts).items())
                    result = trace_annotation(DiagramAnnotation(pts, choices))
                    self.assertEqual(classify_knot(result.points).name, expected)
        mirror = replace(annotation,
                         waypoints=tuple((-x, y) for x, y in annotation.waypoints),
                         crossings=tuple(CrossingChoice((-c.coordinate[0], c.coordinate[1]), c.over_segment)
                                         for c in annotation.crossings))
        self.assertNotEqual(classify_knot(trace_annotation(mirror).points).name, expected)

    def test_invalid_and_ambiguous_projections_are_rejected(self):
        cases = [
            ((0, 0), (2, 0), (2, 2)),  # Too few supports; open diagonal closure.
            ((0, 0), (2, 1), (2, 2), (0, 2)),
            ((0, 0), (2, 0), (2, 2), (0, 2), (0, 0)),
            ((0, 0), (3, 0), (1, 0), (1, 2), (0, 2)),  # Backtrack.
            ((0, 0), (4, 0), (4, 4), (2, 4), (2, 0), (0, 0)),
            ((0, 0), (4, 0), (4, 4), (2, 4), (2, 0), (1, 0), (1, -2), (0, -2)),
        ]
        for pts in cases:
            with self.subTest(pts=pts), self.assertRaises(ValueError):
                trace_annotation(DiagramAnnotation(pts))

    def test_missing_extra_duplicate_or_unrelated_crossing_choices_are_rejected(self):
        annotation = annotate_grid_candidate(trefoil_candidate())
        c = annotation.crossings[0]
        for choices in ((), annotation.crossings[:-1], annotation.crossings + (c,),
                        annotation.crossings + (CrossingChoice((100, 100), 0),),
                        (replace(c, over_segment=99),) + annotation.crossings[1:]):
            with self.subTest(choices=choices), self.assertRaises(ValueError):
                trace_annotation(replace(annotation, crossings=choices))

    def test_strict_json_types_and_schema(self):
        record = annotation_to_dict(annotate_grid_candidate(trefoil_candidate()))
        self.assertEqual(annotation_to_dict(annotation_from_dict(json.loads(json.dumps(record)))), record)
        for bad in (None, [], {}, {**record, "schema_version": True}, {**record, "schema_version": 2},
                    {**record, "waypoints": [[0.0, 0]]}, {**record, "waypoints": [[False, 0]]},
                    {**record, "crossings": [{"coordinate": [1, 0], "over_segment": True}]},
                    {**record, "crossings": [None]}, {**record, "source_image": 42},
                    {**record, "editor_view": []}):
            with self.subTest(record=bad), self.assertRaises(ValueError):
                annotation_from_dict(bad)

    def test_editor_alignment_survives_json_export_and_import(self):
        record = annotation_to_dict(annotate_grid_candidate(trefoil_candidate()))
        record.update(source_image="Vorlage.png", editor_view={"spacing": 40, "offset": [4, 7], "width": 800, "height": 600})
        self.assertEqual(annotation_to_dict(annotation_from_dict(record)), record)

    def test_vertex_budget_precedes_expansion_and_counts_layer_switches(self):
        annotation = annotate_grid_candidate(trefoil_candidate())
        size = len(trace_annotation(annotation).points) - 1
        self.assertEqual(size, 102)
        trace_annotation(annotation, max_vertices=size)
        for limit in (size - 1, 0, True, 100.0):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                trace_annotation(annotation, max_vertices=limit)
        huge = DiagramAnnotation(((0, 0), (10**12, 0), (10**12, 2), (0, 2)))
        with self.assertRaisesRegex(ValueError, 'max_vertices'):
            trace_annotation(huge)

    def test_export_is_deterministic_and_connects_to_existing_gallery(self):
        annotation = annotate_grid_candidate(trefoil_candidate())
        with TemporaryDirectory() as a, TemporaryDirectory() as b:
            result = write_traced_diagram(annotation, a)
            write_traced_diagram(annotation, b)
            files = {p.name for p in Path(a).iterdir()}
            self.assertTrue({'trace.json', 'annotation.json', 'catalog.json', 'index.html', 'knot_000.svg', 'knot_000.png'} <= files)
            for name in files:
                self.assertEqual((Path(a) / name).read_bytes(), (Path(b) / name).read_bytes())
            record = json.loads(result.read_text(encoding="utf-8"))
            trace = trace_turtle(record["turtle_code"])
            self.assertEqual(record["points"], [[p.x, p.y, p.z] for p in trace.points])
            self.assertEqual(record["classification"]["name"], "T(2,3)")
            manifest = json.loads((Path(a) / 'catalog.json').read_text(encoding="utf-8"))
            self.assertEqual(manifest[0]['metadata']['annotation'], annotation_to_dict(annotation))
            self.assertEqual(annotation_from_dict(json.loads((Path(a) / 'annotation.json').read_text())), annotation)

    def test_cli_editor_trace_and_invalid_input(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), redirect_stderr(StringIO()) as error:
            target = Path(directory)
            editor = write_tracer_editor(target / "nested" / "editor.html")
            self.assertIn('const TracerModel', editor.read_text(encoding="utf-8"))
            self.assertNotRegex(editor.read_text(encoding="utf-8"), r'<script[^>]+src=|fetch\(')
            annotation = target / 'input.json'
            annotation.write_text(json.dumps(annotation_to_dict(annotate_grid_candidate(trefoil_candidate()))))
            self.assertEqual(main(['editor', '--output', str(target / 'editor.html')]), 0)
            self.assertEqual(main(['trace', str(annotation), '--output', str(target / 'result')]), 0)
            self.assertTrue((target / 'result' / 'trace.json').is_file())
            annotation.write_text('{')
            with self.assertRaises(SystemExit) as caught:
                main(['trace', str(annotation), '--output', str(target / 'invalid')])
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse((target / 'invalid').exists())
            self.assertIn('error:', error.getvalue())


if __name__ == '__main__':
    unittest.main()
