from math import cos, hypot, radians

from .sampling import LatLon

METERS_PER_DEGREE = 111_195
TOLERANCE_GROWTH = 1.5


def simplify(points: list[LatLon], tolerance_m: float) -> list[LatLon]:
    """Douglas-Peucker: drop points that sit within tolerance_m of the line between kept neighbours."""
    if len(points) < 3:
        return list(points)

    x_scale = cos(radians(sum(lat for lat, _ in points) / len(points)))
    flat = [(lon * x_scale * METERS_PER_DEGREE, lat * METERS_PER_DEGREE) for lat, lon in points]

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    pending = [(0, len(points) - 1)]
    while pending:
        first, last = pending.pop()
        farthest, farthest_distance = None, tolerance_m
        for index in range(first + 1, last):
            distance = _distance_to_chord(flat[index], flat[first], flat[last])
            if distance > farthest_distance:
                farthest, farthest_distance = index, distance
        if farthest is not None:
            keep[farthest] = True
            pending += [(first, farthest), (farthest, last)]
    return [point for point, kept in zip(points, keep) if kept]


def thin(points: list[LatLon], max_points: int = 1500, tolerance_m: float = 75) -> list[LatLon]:
    """simplify with a tolerance that grows until the line has at most max_points."""
    result = simplify(points, tolerance_m)
    while len(result) > max_points:
        tolerance_m *= TOLERANCE_GROWTH
        result = simplify(result, tolerance_m)
    return result


def _distance_to_chord(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    if length == 0:
        return hypot(point[0] - start[0], point[1] - start[1])
    return abs(dx * (start[1] - point[1]) - dy * (start[0] - point[0])) / length
