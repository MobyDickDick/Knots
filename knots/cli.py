"""Command line interface for generator, checker, optimizer and SVG output."""

from __future__ import annotations

import argparse
import json

from .checker import check_knot
from .generator import generate
from .model import Knot
from .optimizer import optimize
from .visualize import save_svg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="knots", description="Work with lattice knots in Z^2 x {0,1}.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="generate an example knot")
    generate_parser.add_argument("--preset", choices=["unknot", "ornamental", "layered"], default="layered")
    generate_parser.add_argument("--seed", type=int, default=11)
    generate_parser.add_argument("--json", default="examples/generated.json", help="output JSON path")
    generate_parser.add_argument("--svg", default="examples/generated.svg", help="output SVG path")

    check_parser = subparsers.add_parser("check", help="validate a knot JSON file")
    check_parser.add_argument("path")

    optimize_parser = subparsers.add_parser("optimize", help="simplify a knot JSON file")
    optimize_parser.add_argument("input")
    optimize_parser.add_argument("--json", default="examples/optimized.json", help="output JSON path")
    optimize_parser.add_argument("--svg", default="examples/optimized.svg", help="output SVG path")

    args = parser.parse_args(argv)

    if args.command == "generate":
        knot = generate(args.preset, seed=args.seed)
        knot.save_json(args.json)
        save_svg(knot, args.svg)
        print(f"generated {len(knot)} points: {args.json}, {args.svg}")
        return 0

    if args.command == "check":
        knot = Knot.load_json(args.path)
        report = check_knot(knot)
        print(json.dumps({"valid": report.valid, "errors": report.errors, "warnings": report.warnings}, indent=2))
        return 0 if report.valid else 1

    if args.command == "optimize":
        knot = Knot.load_json(args.input)
        result = optimize(knot)
        result.knot.save_json(args.json)
        save_svg(result.knot, args.svg)
        print(f"removed {result.saved_points} points in {len(result.steps)} steps: {args.json}, {args.svg}")
        return 0

    raise AssertionError(f"unhandled command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
