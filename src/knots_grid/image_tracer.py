"""Tracing of reviewed rectilinear knot diagrams from the offline editor.

The offline editor supplies ordered grid waypoints and one over-strand choice
per crossing, optionally extracted from a raster in the browser. A fixed
fourfold refinement leaves room for local lifts without changing the diagram.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from .core import Direction, Point, TraceResult, trace_turtle
from .reidemeister import find_crossings
from .validator import validate_cycle


REFINEMENT = 4
MAX_SUPPORT_POINTS = 500
MAX_CROSSINGS = 500
DEFAULT_MAX_VERTICES = 100_000


@dataclass(frozen=True, slots=True)
class CrossingChoice:
    coordinate: tuple[int, int]
    over_segment: int


@dataclass(frozen=True, slots=True)
class DiagramAnnotation:
    """One cyclic component; waypoint zero is not repeated at the end.

    Coordinates are mathematical (y upwards). Segment i joins waypoint i to
    (i + 1) modulo n, so the closing segment has index n - 1.
    """

    waypoints: tuple[tuple[int, int], ...]
    crossings: tuple[CrossingChoice, ...] = ()
    source_image: str | None = None
    editor_view: dict | None = None
    recognition: dict | None = None
    draft: bool = False


def _coordinate(value, label):
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(type(v) is not int for v in value)):
        raise ValueError(f"{label} must contain two integer coordinates")
    return tuple(value)


def _cleanup_report(report, preprocessing, view):
    """Validate component accounting; replaying pixel isolation needs the image."""
    if (view is None or not isinstance(report, dict) or report.get("algorithm") != "isolated-components-v1"
            or type(report.get("max_area")) is not int or not 1 <= report["max_area"] <= 64
            or type(report.get("clearance")) is not int or report["clearance"] != 12
            or type(report.get("original_foreground_pixels")) is not int or report["original_foreground_pixels"] > 200_000
            or type(report.get("removed_pixels")) is not int or not 0 <= report["removed_pixels"] <= 1024
            or report["original_foreground_pixels"] != preprocessing["foreground_pixels"] + report["removed_pixels"]
            or not isinstance(report.get("components"), list) or len(report["components"]) > 32):
        raise ValueError("invalid scan cleanup report")
    components, seen = [], set()
    for item in report["components"]:
        if (not isinstance(item, dict) or type(item.get("pixels")) is not int or not 1 <= item["pixels"] <= report["max_area"]
                or not isinstance(item.get("bounds"), list) or len(item["bounds"]) != 4
                or any(type(v) is not int for v in item["bounds"])):
            raise ValueError("invalid scan cleanup report component")
        x0, y0, x1, y1 = item["bounds"]
        if (not 1 <= x0 <= x1 < view["width"] - 1 or not 1 <= y0 <= y1 < view["height"] - 1
                or not max(x1-x0+1, y1-y0+1) <= item["pixels"] <= (x1-x0+1)*(y1-y0+1)
                or tuple(item["bounds"]) in seen):
            raise ValueError("invalid scan cleanup report bounds")
        seen.add(tuple(item["bounds"]))
        components.append(dict(bounds=list(item["bounds"]), pixels=item["pixels"]))
    if sum(c["pixels"] for c in components) != report["removed_pixels"]:
        raise ValueError("invalid scan cleanup report count")
    return {**{k: report[k] for k in ("algorithm", "max_area", "clearance", "original_foreground_pixels", "removed_pixels")},
            "components": components}


def _crossing_gap_report(report, recognition, view, waypoints):
    """Validate stored local evidence; pixel rechecking requires the source image."""
    if (recognition["algorithm"] != "skeleton-orthogonal-v1" or not isinstance(report, dict)
            or report.get("algorithm") != "local-crossing-gaps-v1" or view is None
            or not isinstance(report.get("evidence"), list) or len(report["evidence"]) > 20
            or len(report["evidence"]) != recognition["inferred_crossings"]):
        raise ValueError("invalid crossing gap report")
    found = diagram_crossings(waypoints)
    if recognition["inferred_crossings"] + recognition["unresolved_crossings"] != len(found):
        raise ValueError("invalid crossing gap report counters")
    evidence, seen = [], set()
    for item in report["evidence"]:
        if not isinstance(item, dict) or not isinstance(item.get("endpoints"), list) or len(item["endpoints"]) != 2:
            raise ValueError("invalid crossing gap report endpoints")
        endpoints = [list(_coordinate(p, "crossing gap endpoints")) for p in item["endpoints"]]
        pixel = list(_coordinate(item.get("crossing_pixel"), "crossing gap pixel"))
        coordinate = _coordinate(item.get("coordinate"), "crossing gap coordinate")
        distance_squared = sum((a-b)**2 for a, b in zip(*endpoints))
        if (any(not 0 <= p[0] < view["width"] or not 0 <= p[1] < view["height"] for p in [*endpoints, pixel])
                or not 100 <= distance_squared <= 1600
                or type(item.get("added_pixels")) is not int or not 4 <= item["added_pixels"] <= 80
                or type(item.get("over_segment")) is not int or item["over_segment"] not in found.get(coordinate, ())
                or coordinate in seen):
            raise ValueError("invalid crossing gap report evidence")
        seen.add(coordinate)
        evidence.append(dict(endpoints=endpoints, crossing_pixel=pixel, coordinate=list(coordinate),
                             added_pixels=item["added_pixels"], over_segment=item["over_segment"]))
    return {"algorithm": report["algorithm"], "evidence": evidence}


def annotation_from_dict(record: dict) -> DiagramAnnotation:
    """Read the versioned JSON produced by the offline editor, without coercion."""
    if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise ValueError("annotation schema_version must be 1")
    if not isinstance(record.get("waypoints"), list) or not isinstance(record.get("crossings"), list):
        raise ValueError("annotation needs waypoints and crossings lists")
    draft = record.get("draft", False)
    if type(draft) is not bool:
        raise ValueError("annotation draft must be a boolean")
    choices = []
    for index, crossing in enumerate(record["crossings"]):
        if not isinstance(crossing, dict) or type(crossing.get("over_segment")) is not int:
            raise ValueError(f"crossing {index} needs an integer over_segment")
        choices.append(CrossingChoice(_coordinate(crossing.get("coordinate"), f"crossing {index}"),
                                      crossing["over_segment"]))
    source = record.get("source_image")
    if source is not None and not isinstance(source, str):
        raise ValueError("source_image must be a string or null")
    view = record.get("editor_view")
    if view is not None:
        if not isinstance(view, dict):
            raise ValueError("editor_view must be an object")
        keys = ("spacing", "width", "height")
        if any(type(view.get(key)) is not int for key in keys):
            raise ValueError("editor_view needs integer spacing, width and height")
        offset = _coordinate(view.get("offset"), "editor_view offset")
        if (not 1 <= view["spacing"] <= 100 or not 1 <= view["width"] <= 12000
                or not 1 <= view["height"] <= 12000 or view["width"] * view["height"] > 16_000_000):
            raise ValueError("editor_view dimensions are outside the supported limits")
        view = {**{key: view[key] for key in keys}, "offset": list(offset)}
        if "pixel_origin" in record["editor_view"]:
            origin = _coordinate(record["editor_view"]["pixel_origin"], "editor_view pixel_origin")
            if any(not 0 <= v < view["spacing"] for v in origin):
                raise ValueError("editor_view pixel_origin must be within one raster cell")
            view["pixel_origin"] = list(origin)
    recognition = record.get("recognition")
    if recognition is not None:
        counters = ("foreground_pixels", "grid_edges", "inferred_crossings", "unresolved_crossings")
        if (not isinstance(recognition, dict) or recognition.get("algorithm") not in ("grid-sampling-v1", "skeleton-orthogonal-v1")
                or type(recognition.get("threshold")) is not int or not 1 <= recognition["threshold"] <= 254
                or any(type(recognition.get(k)) is not int or not 0 <= recognition[k] <= 16_000_000
                       for k in counters)):
            raise ValueError("invalid raster recognition report")
        curve = recognition["algorithm"] == "skeleton-orthogonal-v1"
        curve_keys = ("sample_size", "skeleton_pixels", "thinning_iterations")
        if curve:
            if (type(recognition.get("sample_size")) is not int or recognition["sample_size"] not in (4, 8, 12)
                    or type(recognition.get("skeleton_pixels")) is not int or not 4 <= recognition["skeleton_pixels"] <= 100_000
                    or type(recognition.get("thinning_iterations")) is not int or not 1 <= recognition["thinning_iterations"] <= 128
                    or (recognition["inferred_crossings"] != 0 and "crossing_gaps" not in recognition)
                    or "grid_detection" in recognition):
                raise ValueError("invalid curve recognition report")
        gap_report = None
        if "crossing_gaps" in recognition:
            gap_report = _crossing_gap_report(recognition["crossing_gaps"], recognition, view, record["waypoints"])
        line_report = None
        if "line_gaps" in recognition:
            line_report = recognition["line_gaps"]
            extended = isinstance(line_report, dict) and line_report.get("algorithm") == "local-line-gaps-v2"
            limit = 64 if extended else 32
            crossing_evidence = gap_report["evidence"] if gap_report else []
            if (not curve or view is None or not isinstance(line_report, dict)
                    or line_report.get("algorithm") not in ("local-line-gaps-v1", "local-line-gaps-v2")
                    or (type(line_report.get("max_distance")) is not int or line_report["max_distance"] != 64
                        if extended else "max_distance" in line_report)
                    or not isinstance(line_report.get("evidence"), list)
                    or len(line_report["evidence"]) + len(crossing_evidence) > 20
                    or recognition["inferred_crossings"] + recognition["unresolved_crossings"] != len(diagram_crossings(record["waypoints"]))):
                raise ValueError("invalid line gap report")
            evidence, used = [], {tuple(p) for e in crossing_evidence for p in e["endpoints"]}
            if len(used) != 2 * len(crossing_evidence):
                raise ValueError("invalid line gap report: reused endpoints")
            for item in line_report["evidence"]:
                if not isinstance(item, dict) or not isinstance(item.get("endpoints"), list) or len(item["endpoints"]) != 2:
                    raise ValueError("invalid line gap report endpoints")
                endpoints = [_coordinate(p, "line gap endpoints") for p in item["endpoints"]]
                if (any(not 0 <= p[0] < view["width"] or not 0 <= p[1] < view["height"] or p in used for p in endpoints)
                        or not 100 <= sum((a-b)**2 for a, b in zip(*endpoints)) <= limit**2
                        or type(item.get("added_pixels")) is not int or not 3 <= item["added_pixels"] <= 2 * limit):
                    raise ValueError("invalid line gap report evidence")
                used.update(endpoints)
                evidence.append(dict(endpoints=[list(p) for p in endpoints], added_pixels=item["added_pixels"]))
            line_report = dict(algorithm=line_report["algorithm"], evidence=evidence)
            if extended:
                line_report["max_distance"] = 64
        preprocessing = recognition.get("preprocessing")
        cleanup = None
        if "preprocessing" in recognition:
            if (not curve or not isinstance(preprocessing, dict)
                    or preprocessing.get("algorithm") != "local-mean-v1"
                    or type(preprocessing.get("window_radius")) is not int or not 8 <= preprocessing["window_radius"] <= 80
                    or type(preprocessing.get("contrast")) is not int or not 5 <= preprocessing["contrast"] <= 100
                    or type(preprocessing.get("foreground_pixels")) is not int
                    or not 1 <= preprocessing["foreground_pixels"] <= 200_000
                    or preprocessing["foreground_pixels"] != recognition["foreground_pixels"]
                    or any(type(preprocessing.get(k)) is not int for k in ("background_min", "background_max"))
                    or not 0 <= preprocessing["background_min"] <= preprocessing["background_max"] <= 255):
                raise ValueError("invalid scan preprocessing report")
            if "cleanup" in preprocessing:
                cleanup = _cleanup_report(preprocessing["cleanup"], preprocessing, view)
        grid = recognition.get("grid_detection")
        if "grid_detection" in recognition:
            if (not isinstance(grid, dict) or grid.get("algorithm") != "line-bands-v1"
                    or type(grid.get("tested_grids")) is not int or not 1 <= grid["tested_grids"] <= 16
                    or any(type(grid.get(k)) is not int or not 2 <= grid[k] <= 1200
                           for k in ("horizontal_lines", "vertical_lines"))):
                raise ValueError("invalid automatic grid detection report")
        recognition = {k: recognition[k] for k in ("algorithm", "threshold", *counters, *(curve_keys if curve else ()))}
        if grid is not None:
            recognition["grid_detection"] = {k: grid[k] for k in
                                            ("algorithm", "tested_grids", "horizontal_lines", "vertical_lines")}
        if preprocessing is not None:
            recognition["preprocessing"] = {k: preprocessing[k] for k in
                                           ("algorithm", "window_radius", "contrast", "foreground_pixels",
                                            "background_min", "background_max")}
            if cleanup is not None:
                recognition["preprocessing"]["cleanup"] = cleanup
        if gap_report is not None:
            recognition["crossing_gaps"] = gap_report
        if line_report is not None:
            recognition["line_gaps"] = line_report
    return DiagramAnnotation(tuple(_coordinate(p, f"waypoint {i}")
                                   for i, p in enumerate(record["waypoints"])), tuple(choices), source, view, recognition, draft)


def annotation_to_dict(annotation: DiagramAnnotation) -> dict:
    result = {"schema_version": 1, "source_image": annotation.source_image,
              "waypoints": [list(p) for p in annotation.waypoints],
              "crossings": [{"coordinate": list(c.coordinate), "over_segment": c.over_segment}
                            for c in annotation.crossings]}
    if annotation.editor_view is not None:
        result["editor_view"] = annotation.editor_view
    if annotation.recognition is not None:
        result["recognition"] = annotation.recognition
    if annotation.draft:
        result["draft"] = True
    return result


def diagram_crossings(waypoints: Iterable[tuple[int, int]]) -> dict[tuple[int, int], tuple[int, int]]:
    """Validate a regular orthogonal projection and enumerate all crossings.

    Collinear overlap, endpoint contacts, repeated waypoints and U-turns are
    rejected. Only a transverse intersection strictly inside both segments is
    admitted. This checks the entire closing segment as well.
    """
    pts = tuple(_coordinate(p, f"waypoint {i}") for i, p in enumerate(waypoints))
    if not 4 <= len(pts) <= MAX_SUPPORT_POINTS:
        raise ValueError(f"need 4 to {MAX_SUPPORT_POINTS} waypoints")
    if len(set(pts)) != len(pts):
        raise ValueError("waypoints must be distinct; do not repeat the start point")
    segments = list(zip(pts, pts[1:] + pts[:1]))
    for i, (a, b) in enumerate(segments):
        if (a[0] == b[0]) == (a[1] == b[1]):
            raise ValueError(f"segment {i} must be nonzero and horizontal or vertical")
    found = {}
    for i, (a, b) in enumerate(segments):
        for j in range(i + 1, len(segments)):
            c, d = segments[j]
            horizontal = a[1] == b[1]
            if horizontal == (c[1] == d[1]):
                axis = 0 if horizontal else 1
                fixed = 1 - axis
                if a[fixed] != c[fixed]:
                    continue
                lo = max(min(a[axis], b[axis]), min(c[axis], d[axis]))
                hi = min(max(a[axis], b[axis]), max(c[axis], d[axis]))
                if lo > hi:
                    continue
                if lo < hi:
                    raise ValueError(f"segments {i} and {j} overlap or reverse")
                hit = (lo, a[1]) if horizontal else (a[0], lo)
            else:
                hit = (c[0], a[1]) if horizontal else (a[0], c[1])
                if not all(min(p[k], q[k]) <= hit[k] <= max(p[k], q[k])
                           for p, q in ((a, b), (c, d)) for k in (0, 1)):
                    continue
            adjacent = j == i + 1 or (i == 0 and j == len(segments) - 1)
            if adjacent and hit in (a, b) and hit in (c, d):
                continue
            if hit in (a, b, c, d):
                raise ValueError(f"segments {i} and {j} touch at an endpoint")
            if hit in found:
                raise ValueError(f"more than two strands meet at {hit}")
            found[hit] = (i, j)
            if len(found) > MAX_CROSSINGS:
                raise ValueError(f"at most {MAX_CROSSINGS} crossings are supported")
    return dict(sorted(found.items()))


def trace_annotation(annotation: DiagramAnnotation, *, max_vertices: int = DEFAULT_MAX_VERTICES) -> TraceResult:
    """Construct a validated turtle trace preserving every annotated crossing.

    Translate to the first waypoint, rotate the first segment to east (never
    reflect), and refine by four. All strands use z=0 except the three vertices
    centred on each overcrossing. Switches lie one refined unit to either side.
    The input's integer spacing ensures these lift windows cannot collide.
    """
    if type(max_vertices) is not int or max_vertices < 4:
        raise ValueError("max_vertices must be an integer of at least 4")
    pts = tuple(_coordinate(p, f"waypoint {i}") for i, p in enumerate(annotation.waypoints))
    found = diagram_crossings(pts)
    choices = {}
    for crossing in annotation.crossings:
        coordinate = _coordinate(crossing.coordinate, "crossing")
        if coordinate in choices:
            raise ValueError(f"duplicate crossing choice at {coordinate}")
        if coordinate not in found:
            raise ValueError(f"no transverse crossing at {coordinate}")
        if type(crossing.over_segment) is not int or crossing.over_segment not in found[coordinate]:
            raise ValueError(f"over_segment at {coordinate} must be one of {found[coordinate]}")
        choices[coordinate] = crossing.over_segment
    missing = found.keys() - choices.keys()
    if missing:
        raise ValueError(f"missing over/under choices at {sorted(missing)}")
    segments = list(zip(pts, pts[1:] + pts[:1]))
    vertex_count = REFINEMENT * sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in segments) + 2 * len(found)
    if vertex_count > max_vertices:
        raise ValueError(f"trace needs {vertex_count} vertices; max_vertices is {max_vertices}")
    first, second = pts[:2]
    east = (0 if first[0] == second[0] else (1 if second[0] > first[0] else -1),
            0 if first[1] == second[1] else (1 if second[1] > first[1] else -1))

    def transform(x, y):
        x, y = x - first[0] * REFINEMENT, y - first[1] * REFINEMENT
        return x * east[0] + y * east[1], -x * east[1] + y * east[0]

    lifts = [[] for _ in pts]
    for coordinate, segment in choices.items():
        a = pts[segment]
        distance = REFINEMENT * (abs(coordinate[0] - a[0]) + abs(coordinate[1] - a[1]))
        lifts[segment].append(distance)
    path = [Point(0, 0, 0)]
    for i, (a, b) in enumerate(segments):
        length = REFINEMENT * (abs(b[0] - a[0]) + abs(b[1] - a[1]))
        dx = 0 if a[0] == b[0] else (1 if b[0] > a[0] else -1)
        dy = 0 if a[1] == b[1] else (1 if b[1] > a[1] else -1)
        starts, ends = {d - 1 for d in lifts[i]}, {d + 1 for d in lifts[i]}
        for step in range(1, length + 1):
            x, y = transform(a[0] * REFINEMENT + step * dx, a[1] * REFINEMENT + step * dy)
            path.append(Point(x, y, path[-1].z))
            if step in starts or step in ends:
                path.append(path[-1].switched_layer())
    validate_cycle(path).raise_for_errors()
    direction = Direction.EAST
    code = []
    for a, b in zip(path, path[1:]):
        if a.z != b.z:
            code.append("3")
            continue
        following = Direction((b.x - a.x, b.y - a.y))
        if following == direction:
            code.append("0")
        elif following == direction.left():
            code.append("1")
        elif following == direction.right():
            code.append("2")
        else:
            raise ValueError("diagram contains a reversal that cannot be encoded")
        direction = following
    trace = trace_turtle("".join(code))
    if trace.points != tuple(path) or len(find_crossings(trace.points)) != len(found):
        raise RuntimeError("constructed trace does not match the annotated diagram")
    return trace


def write_traced_diagram(annotation: DiagramAnnotation, directory: str | Path,
                         *, max_vertices: int = DEFAULT_MAX_VERTICES) -> Path:
    """Export the source annotation, exact trace and existing offline gallery."""
    from .catalog import CatalogEntry, write_catalog
    from .classification import classify_knot

    trace = trace_annotation(annotation, max_vertices=max_vertices)
    classification = classify_knot(trace.points)
    source = "manual_image_annotation"
    if annotation.recognition:
        source = ("reviewed_line_gap_annotation" if "line_gaps" in annotation.recognition
                  else "reviewed_gap_annotation" if "crossing_gaps" in annotation.recognition
                  else "reviewed_scan_annotation" if "preprocessing" in annotation.recognition
                  else "reviewed_curve_annotation" if annotation.recognition["algorithm"] == "skeleton-orthogonal-v1"
                  else "reviewed_raster_annotation")
    metadata = {"source": source, "refinement": REFINEMENT,
                "annotation": annotation_to_dict(annotation), "turtle_code": trace.code,
                "classification": asdict(classification), "global_minimality_claimed": False}
    target = Path(directory)
    write_catalog([CatalogEntry(0, 0, trace.points, classification.name,
                               classification.determinant, metadata=metadata)], target)
    output = {"schema_version": 1, **metadata,
              "points": [[p.x, p.y, p.z] for p in trace.points],
              "point_count": len(trace.points) - 1}
    result = target / "trace.json"
    result.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    (target / "annotation.json").write_text(
        json.dumps(annotation_to_dict(annotation), indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    return result


def write_tracer_editor(filename: str | Path) -> Path:
    """Copy the self-contained editor; images are opened locally by its user."""
    target = Path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(Path(__file__).with_name("image_tracer.html").read_text(encoding="utf-8"),
                      encoding="utf-8", newline="\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    editor = commands.add_parser("editor", help="write the offline point/crossing editor")
    editor.add_argument("--output", type=Path, default=Path("image_tracer.html"))
    convert = commands.add_parser("trace", help="validate annotation and export turtle/grid/gallery")
    convert.add_argument("annotation", type=Path)
    convert.add_argument("--output", type=Path, default=Path("traced_knot"))
    convert.add_argument("--max-vertices", type=int, default=DEFAULT_MAX_VERTICES)
    args = parser.parse_args(argv)
    try:
        if args.command == "editor":
            result = write_tracer_editor(args.output)
        else:
            annotation = annotation_from_dict(json.loads(args.annotation.read_text(encoding="utf-8")))
            result = write_traced_diagram(annotation, args.output, max_vertices=args.max_vertices)
    except (ValueError, OSError) as error:
        parser.exit(2, f"error: {error}\n")
    print(f"Wrote {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
