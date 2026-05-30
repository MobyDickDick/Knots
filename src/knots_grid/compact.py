"""Compact bit codec for turtle paths.

The codec stores a path as instructions made from

* two command bits, followed by
* a self-delimiting non-negative integer.

The integer is written as binary digits.  Each digit is followed by one
continuation bit: ``1`` means another digit follows, ``0`` terminates the
number.  For example, ``4`` is binary ``100`` and becomes ``1 1 0 1 0 0``.

Command bits:

* ``00``: move forward ``n`` steps.
* ``01``: turn left, then move forward ``n`` steps.
* ``10``: turn right, then move forward ``n`` steps.
* ``11``: switch layer, then move forward ``n`` steps.  If ``n`` is zero,
  this is only a layer switch.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, Literal

from .core import Direction, Point, TraceResult, _move

CompactCommand = Literal["forward", "left", "right", "layer"]

_COMMAND_BITS: dict[CompactCommand, str] = {
    "forward": "00",
    "left": "01",
    "right": "10",
    "layer": "11",
}
_BITS_COMMAND = {bits: command for command, bits in _COMMAND_BITS.items()}
_LEGACY_TO_COMMAND: dict[str, CompactCommand] = {
    "0": "forward",
    "1": "left",
    "2": "right",
    "3": "layer",
}


@dataclass(frozen=True, slots=True)
class CompactInstruction:
    """One compact turtle instruction.

    ``steps`` is the number encoded after the two command bits.  For turn and
    layer commands it is the number of forward steps after the turn/switch.
    """

    command: CompactCommand
    steps: int

    def __post_init__(self) -> None:
        if self.command not in _COMMAND_BITS:
            raise ValueError(f"invalid compact command {self.command!r}")
        if self.steps < 0:
            raise ValueError("steps must be non-negative")


def encode_number(value: int) -> str:
    """Encode a non-negative integer as digit/continuation bit pairs.

    Examples:
        ``4`` -> ``110100`` and ``7`` -> ``111110``.
    """

    if value < 0:
        raise ValueError("only non-negative integers can be encoded")
    bits = bin(value)[2:]
    encoded: list[str] = []
    for index, bit in enumerate(bits):
        encoded.append(bit)
        encoded.append("1" if index < len(bits) - 1 else "0")
    return "".join(encoded)


def decode_number(bits: str, start: int = 0) -> tuple[int, int]:
    """Decode one number from ``bits[start:]``.

    Returns ``(value, next_index)`` where ``next_index`` points to the first bit
    after the encoded number.
    """

    digits: list[str] = []
    index = start
    while True:
        if index + 1 >= len(bits):
            raise ValueError("truncated compact number")
        digit = bits[index]
        continuation = bits[index + 1]
        if digit not in "01" or continuation not in "01":
            raise ValueError("compact numbers may contain only bits")
        digits.append(digit)
        index += 2
        if continuation == "0":
            return int("".join(digits), 2), index


def encode_instructions(instructions: Iterable[CompactInstruction]) -> str:
    """Encode compact instructions into a bit string."""

    return "".join(_COMMAND_BITS[item.command] + encode_number(item.steps) for item in instructions)


def decode_instructions(bits: str) -> tuple[CompactInstruction, ...]:
    """Decode a complete compact bit string into instructions."""

    if any(bit not in "01" for bit in bits):
        raise ValueError("compact turtle data may contain only '0' and '1'")
    instructions: list[CompactInstruction] = []
    index = 0
    while index < len(bits):
        if index + 1 >= len(bits):
            raise ValueError("truncated compact command")
        command_bits = bits[index : index + 2]
        try:
            command = _BITS_COMMAND[command_bits]
        except KeyError as exc:
            raise ValueError(f"invalid compact command bits {command_bits!r}") from exc
        steps, index = decode_number(bits, index + 2)
        instructions.append(CompactInstruction(command, steps))
    return tuple(instructions)


def turtle_to_instructions(code: str | Iterable[str]) -> tuple[CompactInstruction, ...]:
    """Convert legacy turtle commands (``0``, ``1``, ``2``, ``3``) to runs.

    Consecutive forward moves after a non-forward command are folded into that
    command's step count.  Thus ``100`` becomes ``left`` with ``3`` forward
    steps, because legacy ``1`` already includes the first step.
    """

    code_str = "".join(code) if not isinstance(code, str) else code
    instructions: list[CompactInstruction] = []
    index = 0
    while index < len(code_str):
        command_char = code_str[index]
        if command_char not in _LEGACY_TO_COMMAND:
            raise ValueError(f"invalid turtle command {command_char!r} at index {index}")
        if command_char == "0":
            end = _forward_run_end(code_str, index)
            instructions.append(CompactInstruction("forward", end - index))
            index = end
            continue

        end = _forward_run_end(code_str, index + 1)
        extra_forward = end - index - 1
        if command_char in "12":
            steps = 1 + extra_forward
        else:
            steps = extra_forward
        instructions.append(CompactInstruction(_LEGACY_TO_COMMAND[command_char], steps))
        index = end
    return tuple(instructions)


def _forward_run_end(code: str, start: int) -> int:
    index = start
    while index < len(code) and code[index] == "0":
        index += 1
    return index


def instructions_to_turtle(instructions: Iterable[CompactInstruction]) -> str:
    """Expand compact instructions to legacy turtle commands.

    A left or right turn with zero steps has no equivalent in the legacy command
    set and raises ``ValueError``.
    """

    chunks: list[str] = []
    for item in instructions:
        if item.command == "forward":
            chunks.append("0" * item.steps)
        elif item.command == "left":
            if item.steps == 0:
                raise ValueError("left turn with zero steps has no legacy turtle equivalent")
            chunks.append("1" + "0" * (item.steps - 1))
        elif item.command == "right":
            if item.steps == 0:
                raise ValueError("right turn with zero steps has no legacy turtle equivalent")
            chunks.append("2" + "0" * (item.steps - 1))
        elif item.command == "layer":
            chunks.append("3" + "0" * item.steps)
        else:  # pragma: no cover - dataclass validation protects this branch
            raise ValueError(f"invalid compact command {item.command!r}")
    return "".join(chunks)


def encode_turtle(code: str | Iterable[str]) -> str:
    """Convert legacy turtle code to compact bits."""

    return encode_instructions(turtle_to_instructions(code))


def decode_turtle(bits: str) -> str:
    """Convert compact bits back to legacy turtle code."""

    return instructions_to_turtle(decode_instructions(bits))


def trace_compact(
    bits: str,
    *,
    start: Point = Point(0, 0, 0),
    direction: Direction = Direction.EAST,
) -> TraceResult:
    """Trace compact bits directly without expanding to legacy text first."""

    if start.z not in (0, 1):
        raise ValueError("start point must have z in {0, 1}")

    point = start
    current_direction = direction
    points = [point]

    for item in decode_instructions(bits):
        if item.command == "left":
            current_direction = current_direction.left()
        elif item.command == "right":
            current_direction = current_direction.right()
        elif item.command == "layer":
            point = point.switched_layer()
            points.append(point)
        elif item.command != "forward":  # pragma: no cover
            raise ValueError(f"invalid compact command {item.command!r}")

        for _ in range(item.steps):
            point = _move(point, current_direction)
            points.append(point)

    return TraceResult(code=bits, points=tuple(points), final_direction=current_direction)


def _format_instructions(instructions: Iterable[CompactInstruction]) -> str:
    return " ".join(f"{item.command}:{item.steps}" for item in instructions)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Encode and decode compact turtle bit strings.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_parser = subparsers.add_parser("encode", help="encode legacy turtle commands to compact bits")
    encode_parser.add_argument("code")

    decode_parser = subparsers.add_parser("decode", help="decode compact bits to legacy turtle commands")
    decode_parser.add_argument("bits")

    inspect_parser = subparsers.add_parser("inspect", help="show decoded compact instructions")
    inspect_parser.add_argument("bits")

    args = parser.parse_args(argv)
    if args.command == "encode":
        print(encode_turtle(args.code))
    elif args.command == "decode":
        print(decode_turtle(args.bits))
    elif args.command == "inspect":
        print(_format_instructions(decode_instructions(args.bits)))
    else:  # pragma: no cover
        raise AssertionError(f"unhandled command {args.command!r}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
