from math import sin

from routing.simplify import simplify, thin


def wavy_line(count: int) -> list[tuple[float, float]]:
    return [(32.0 + 0.001 * i, -97.0 + 0.1 * sin(i / 40)) for i in range(count)]


def test_collinear_points_collapse_to_the_endpoints():
    line = [(32.0 + 0.01 * i, -97.0) for i in range(50)]

    assert simplify(line, tolerance_m=10) == [line[0], line[-1]]


def test_a_corner_larger_than_the_tolerance_is_kept():
    corner = [(32.0, -97.0), (32.0, -96.9), (32.1, -96.9)]

    assert simplify(corner, tolerance_m=100) == corner


def test_a_bump_smaller_than_the_tolerance_is_dropped():
    bump = [(32.0, -97.0), (32.0005, -96.95), (32.0, -96.9)]  # about 55 m off the chord

    assert simplify(bump, tolerance_m=100) == [bump[0], bump[-1]]


def test_short_lines_come_back_unchanged():
    assert simplify([(32.0, -97.0)], tolerance_m=50) == [(32.0, -97.0)]
    assert simplify([(32.0, -97.0), (33.0, -97.0)], tolerance_m=50) == [(32.0, -97.0), (33.0, -97.0)]


def test_the_result_is_an_ordered_subset_that_keeps_both_ends():
    line = wavy_line(3000)

    result = simplify(line, tolerance_m=75)

    assert result[0] == line[0] and result[-1] == line[-1]
    assert len(result) < len(line)
    positions = [line.index(point) for point in result]
    assert positions == sorted(positions)


def test_thin_loosens_the_tolerance_until_the_line_fits():
    line = wavy_line(6000)

    result = thin(line, max_points=100, tolerance_m=1)

    assert 2 <= len(result) <= 100
    assert result[0] == line[0] and result[-1] == line[-1]


def test_thin_leaves_a_line_that_already_fits_alone():
    line = [(32.0, -97.0), (32.0, -96.9), (32.1, -96.9)]

    assert thin(line, max_points=1500) == line
