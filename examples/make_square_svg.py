from knots_grid import render_svg, trace_turtle, validate_cycle


if __name__ == "__main__":
    trace = trace_turtle("1111")
    validation = validate_cycle(trace.points)
    validation.raise_for_errors()
    render_svg(trace.points, "square.svg")
    print("wrote square.svg")
