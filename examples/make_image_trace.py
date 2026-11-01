"""Rebuild the offline tracer and a hand-annotated, flat trefoil example.

Run from the repository root with PYTHONPATH=src (or after pip install -e .).
The small reference raster is drawn here without external imaging packages.
"""

import json
from pathlib import Path
import struct
import zlib

from knots_grid.image_tracer import (
    CrossingChoice, DiagramAnnotation, write_traced_diagram, write_tracer_editor,
)


def build_example():
    target = Path(__file__).resolve().parent / "image_trace"
    target.mkdir(parents=True, exist_ok=True)
    annotation = DiagramAnnotation(
        ((0, 0), (3, 0), (3, -2), (1, -2), (1, 1),
         (4, 1), (4, -1), (2, -1), (2, -3), (0, -3)),
        (CrossingChoice((1, 0), 3), CrossingChoice((2, -2), 7), CrossingChoice((3, -1), 1)),
        "trefoil_reference.png",
        {"spacing": 72, "offset": [2, 2], "width": 576, "height": 504},
    )
    width, height = 576, 504
    pixels = bytearray(b"\xff\xff\xff" * width * height)

    def screen(p):
        return round((p[0] + 2) * 72), round((2 - p[1]) * 72)

    def line(a, b, radius, color):
        ax, ay = screen(a)
        bx, by = screen(b)
        steps = max(abs(bx - ax), abs(by - ay), 1)
        for step in range(steps + 1):
            x, y = round(ax + (bx - ax) * step / steps), round(ay + (by - ay) * step / steps)
            for row in range(max(0, y - radius), min(height, y + radius + 1)):
                for col in range(max(0, x - radius), min(width, x + radius + 1)):
                    if (col - x)**2 + (row - y)**2 <= radius**2:
                        offset = (row * width + col) * 3
                        pixels[offset:offset+3] = bytes(color)

    pts = annotation.waypoints
    for a, b in zip(pts, pts[1:] + pts[:1]):
        line(a, b, 3, (30, 45, 60))
    for crossing in annotation.crossings:
        x, y = crossing.coordinate
        # All three over-strands in this hand-written fixture are vertical.
        a, b = (x, y - .25), (x, y + .25)
        line(a, b, 9, (255, 255, 255))
        line(a, b, 3, (30, 45, 60))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    raw = b"".join(b"\0" + pixels[row*width*3:(row+1)*width*3] for row in range(height))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    (target / annotation.source_image).write_bytes(png)
    write_traced_diagram(annotation, target)
    editor = write_tracer_editor(target.parent / "image_tracer.html")
    result = json.loads((target / "trace.json").read_text(encoding="utf-8"))
    print(f"Wrote {editor}; {result['classification']['name']}, "
          f"{result['point_count']} vertices, {result['classification']['crossings']} crossings")


if __name__ == "__main__":
    build_example()
