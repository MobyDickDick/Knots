"""Local, dependency-free browser interface for the existing knot generators."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import webbrowser

from .classification import classify_knot
from .generator import (
    SearchConfig, TravelConfig, figure_eight_candidate, search_candidate,
    torus_knot_candidate, travel_candidate, trefoil_candidate,
)
from .projection import score_projection
from .svg import render_svg
from .validator import validate_cycle

PRESETS = {"trefoil", "figure-eight", "torus", "travel", "ornamental"}
ASSETS = {
    "/": ("studio.html", "text/html; charset=utf-8"),
    "/studio.css": ("studio.css", "text/css; charset=utf-8"),
    "/studio.js": ("studio.js", "text/javascript; charset=utf-8"),
}


def _integer(value, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{label} muss eine ganze Zahl sein.")
    if isinstance(value, str) and (len(value) > 20 or not value.lstrip("-").isascii()
                                  or not value.lstrip("-").isdigit()):
        raise ValueError(f"{label} muss eine ganze Zahl sein.")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} muss zwischen {minimum} und {maximum} liegen.")
    return number


def generate_record(options: dict) -> dict:
    """Generate, validate and describe a cycle. Seeds remain exact strings in JS."""
    if not isinstance(options, dict):
        raise ValueError("Die Parameter müssen ein JSON-Objekt sein.")
    if set(options) - {"preset", "seed", "point_count", "crossings", "steps"}:
        raise ValueError("Unbekannter Generatorparameter.")
    preset = options.get("preset", "trefoil")
    if not isinstance(preset, str) or preset not in PRESETS:
        raise ValueError("Unbekannter Knotengenerator.")
    seed = _integer(options.get("seed", "2026"), "Seed", 0, 2**63 - 1)
    size = _integer(options.get("point_count", 10), "Markerpaare", 4, 24)
    crossings = _integer(options.get("crossings", 5), "Toruskreuzungen", 3, 15)
    steps = _integer(options.get("steps", 18), "Suchschritte", 0, 60)
    if crossings % 2 == 0:
        raise ValueError("Die Toruskreuzungszahl muss ungerade sein.")

    if preset == "trefoil":
        candidate = trefoil_candidate()
    elif preset == "figure-eight":
        candidate = figure_eight_candidate()
    elif preset == "torus":
        candidate = torus_knot_candidate(crossings)
    elif preset == "travel":
        candidate = travel_candidate(seed=seed, config=TravelConfig(point_count=size))
    else:
        candidate = search_candidate(seed=seed, config=SearchConfig(
            min_search_steps=steps, max_search_steps=steps,
        ))

    validate_cycle(candidate.points).raise_for_errors()
    classification = classify_knot(candidate.points)
    score = score_projection(candidate.points)
    with TemporaryDirectory(prefix="knot-studio-") as folder:
        target = Path(folder) / "knot.svg"
        render_svg(candidate.points, target)
        svg = target.read_text(encoding="utf-8")
    return {
        "schema_version": 1,
        "parameters": {"preset": preset, "seed": str(seed), "point_count": size,
                       "crossings": crossings, "steps": steps},
        "name": classification.name,
        "classification": {"status": classification.status,
                           "evidence": classification.evidence,
                           "determinant": classification.determinant},
        "valid": True,
        "closed": True,
        "point_convention": "closed: last point repeats first point",
        "points": [[p.x, p.y, p.z] for p in candidate.points],
        "code": candidate.code,
        "metrics": asdict(score.metrics),
        "svg": svg,
    }


class StudioHandler(BaseHTTPRequestHandler):
    """Serve only bundled UI assets and bounded generation requests on loopback."""

    def log_message(self, format, *args):
        pass

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; "
                         "script-src 'self'; style-src 'self'; object-src 'none'; "
                         "base-uri 'none'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data, ensure_ascii=True).encode(),
                   "application/json; charset=utf-8")

    def _allowed_host(self) -> bool:
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def do_GET(self):
        if not self._allowed_host():
            self._json(403, {"error": "Nur lokale Zugriffe sind erlaubt."})
            return
        asset = ASSETS.get(urlsplit(self.path).path)
        if asset is None:
            self._json(404, {"error": "Nicht gefunden."})
            return
        filename, content_type = asset
        self._send(200, Path(__file__).with_name(filename).read_bytes(), content_type)

    def do_POST(self):
        port = self.server.server_port
        origin = self.headers.get("Origin")
        if not self._allowed_host() or (origin is not None and origin not in {
            f"http://127.0.0.1:{port}", f"http://localhost:{port}",
        }):
            self._json(403, {"error": "Nur lokale Zugriffe sind erlaubt."})
            return
        if self.path != "/api/generate":
            self._json(404, {"error": "Nicht gefunden."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError("Die Anfrage muss zwischen 1 und 8192 Bytes enthalten.")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Die Anfrage muss JSON enthalten.")
            options = json.loads(self.rfile.read(length))
            record = generate_record(options)
        except (ValueError, UnicodeError) as error:
            self._json(400, {"error": str(error)})
            return
        except RuntimeError:
            self._json(422, {"error": "Innerhalb des Versuchslimits wurde kein geschlossener "
                        "Kandidat gefunden. Bitte einen anderen Seed wählen."})
            return
        self._json(200, record)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open the browser on startup")
    args = parser.parse_args(argv)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), StudioHandler)
    except OSError as error:
        parser.exit(1, f"Der Generator konnte nicht starten: {error}\n"
                       "Versuche einen anderen Port mit --port 8766.\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Knotengenerator: {url}\nBeenden mit Strg+C.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
