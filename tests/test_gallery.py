import json
from html.parser import HTMLParser
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from knots_grid import Point, trefoil_candidate
from knots_grid.catalog import CatalogEntry, generate_catalog, write_catalog
from knots_grid.gallery import render_gallery


def embedded_records(html):
    return json.loads(re.search(
        r'/\* KNOT_DATA_START \*/(.*?)/\* KNOT_DATA_END \*/', html, re.DOTALL,
    ).group(1))


class GalleryTests(unittest.TestCase):
    def test_old_template_address_links_to_a_generated_gallery(self):
        root = Path(__file__).resolve().parents[1]
        old_address = root / "src" / "knots_grid" / "gallery.html"
        redirect = old_address.read_text(encoding="utf-8")
        self.assertNotIn("__KNOT_DATA__", redirect)
        href = re.search(r'<a href="([^"]+)"', redirect).group(1)
        target = (old_address.parent / href).resolve()
        self.assertEqual(target, root / "examples" / "knot_gallery.html")
        output = target.read_text(encoding="utf-8")
        self.assertNotRegex(output, r"__[A-Z_]+__")
        self.assertEqual(len(embedded_records(output)), 8)

    def test_list_and_previews_exist_before_any_javascript_runs(self):
        class StaticGallery(HTMLParser):
            def __init__(self):
                super().__init__()
                self.targets = set()
                self.links = []
                self.images = 0

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "id" in attrs:
                    self.targets.add(attrs["id"])
                if tag == "a" and attrs.get("class") == "knot-card":
                    self.links.append(attrs["href"])
                if tag == "svg":
                    self.images += 1

        entries = generate_catalog(3, mode="systematic")
        with TemporaryDirectory() as directory:
            html = render_gallery(entries, Path(directory) / "gallery.html").read_text(encoding="utf-8")
        parser = StaticGallery()
        parser.feed(html)
        self.assertEqual(len(parser.links), 3)
        self.assertEqual(parser.images, 7)  # Three cards, selected preview, three targets.
        for target in parser.links:
            self.assertIn(target[1:], parser.targets)
        self.assertIn('id="count">3 Knoten', html)

    def test_template_tokens_in_names_are_preserved_as_data(self):
        name = '__KNOT_CARDS__ & "Beispiel"'
        entry = CatalogEntry(0, 0, trefoil_candidate().points, name)
        with TemporaryDirectory() as directory:
            html = render_gallery([entry], Path(directory) / "gallery.html").read_text(encoding="utf-8")
        self.assertEqual(embedded_records(html)[0]["name"], name)
        self.assertIn('__KNOT_CARDS__ &amp; &quot;Beispiel&quot;', html)

    def test_gallery_embeds_exact_closed_two_layer_paths(self):
        entries = generate_catalog(3, mode="systematic")
        with TemporaryDirectory() as directory:
            target = render_gallery(iter(entries), Path(directory) / "nested" / "gallery.html")
            html = target.read_text(encoding="utf-8")
        data = embedded_records(html)
        self.assertEqual(len(data), len(entries))
        for record, entry in zip(data, entries):
            self.assertEqual(record["points"], [[p.x, p.y, p.z] for p in entry.points])
            self.assertEqual(record["points"][0], record["points"][-1])
            self.assertEqual(record["name"], entry.knot_name)
            self.assertEqual(record["determinant"], entry.determinant)
        self.assertEqual(data[1]["crossings"], 3)
        self.assertNotIn("__KNOT_DATA__", html)
        self.assertNotIn("JSON.parse", html)
        self.assertNotIn('id="knot-data"', html)
        self.assertNotRegex(html, r'<script[^>]+src=|<link[^>]+href=|fetch\(')

    def test_names_cannot_inject_markup_or_scripts(self):
        name = '</script><script>alert("x")</script>&<b>'
        entry = CatalogEntry(0, 0, trefoil_candidate().points, name)
        with TemporaryDirectory() as directory:
            html = render_gallery([entry], Path(directory) / "gallery.html").read_text(encoding="utf-8")
        self.assertNotIn(name, html)
        self.assertEqual(embedded_records(html)[0]["name"], name)

    def test_empty_catalog_and_invalid_cycles_are_rejected(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "gallery.html"
            with self.assertRaises(ValueError):
                render_gallery([], target)
            with self.assertRaises(ValueError):
                render_gallery([CatalogEntry(0, 0, (Point(0, 0, 0), Point(1, 0, 0)))], target)
            self.assertFalse(target.exists())

    def test_catalog_export_adds_gallery_and_still_supports_empty_catalog(self):
        with TemporaryDirectory() as directory:
            manifest = write_catalog(iter(generate_catalog(2, mode="systematic")), directory)
            self.assertTrue(manifest.is_file())
            self.assertTrue((Path(directory) / "index.html").is_file())
        with TemporaryDirectory() as directory:
            manifest = write_catalog([], directory)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8")), [])
            self.assertFalse((Path(directory) / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
