from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_MI = 3958.8
KM_PER_MILE = 1.609344

LatLon = tuple[float, float]


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    lat: float
    lon: float
    eta: datetime


def haversine_mi(a: LatLon, b: LatLon) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * asin(sqrt(h))


def _cumulative_miles(points: list[LatLon], total_mi: float) -> list[float]:
    """Miles from the start at each point, scaled so the last one equals the router's distance."""
    cumulative = [0.0]
    for previous, current in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + haversine_mi(previous, current))
    straight_line = cumulative[-1]
    scale = total_mi / straight_line if straight_line else 1.0
    return [miles * scale for miles in cumulative]


def _interpolate(xs: list[float], ys: list[float], x: float) -> float:
    i = min(max(bisect_right(xs, x) - 1, 0), len(xs) - 2)
    span = xs[i + 1] - xs[i]
    fraction = (x - xs[i]) / span if span else 0.0
    return ys[i] + fraction * (ys[i + 1] - ys[i])


def _checkpoint_miles(total_mi: float, interval_mi: float) -> list[float]:
    count = int(total_mi // interval_mi)
    miles = [interval_mi * step for step in range(1, count + 1)]
    if not miles or total_mi - miles[-1] > 1e-6:
        miles.append(total_mi)
    else:
        miles[-1] = total_mi
    return miles


def sample_checkpoints(
    points: list[LatLon],
    distance_mi: float,
    knots: list[tuple[int, float]],
    departure: datetime,
    interval_mi: float,
) -> list[Checkpoint]:
    """Checkpoints every interval_mi along the route plus one at the destination.

    knots are (index into points, elapsed seconds) pairs from the router's maneuvers;
    ETAs interpolate between them so slow stretches cost the time the router predicts.
    """
    if len(points) < 2:
        lat, lon = points[0]
        return [Checkpoint(0.0, lat, lon, departure)]

    miles_at_point = _cumulative_miles(points, distance_mi)
    knot_miles = [miles_at_point[index] for index, _ in knots]
    knot_seconds = [seconds for _, seconds in knots]
    lats = [lat for lat, _ in points]
    lons = [lon for _, lon in points]

    return [
        Checkpoint(
            mile=mile,
            lat=_interpolate(miles_at_point, lats, mile),
            lon=_interpolate(miles_at_point, lons, mile),
            eta=departure + timedelta(seconds=_interpolate(knot_miles, knot_seconds, mile)),
        )
        for mile in _checkpoint_miles(distance_mi, interval_mi)
    ]
