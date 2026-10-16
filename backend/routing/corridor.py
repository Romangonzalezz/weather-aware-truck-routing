from datetime import datetime, timedelta
from math import ceil, cos, floor, hypot, radians, sqrt

from .clients.weather import check_departure, check_forecast_window, fetch_hourly
from .planner import iso
from .risk import weather_score
from .sampling import KM_PER_MILE, LatLon, haversine_mi

MAX_CELLS = 300
CORRIDOR_RADIUS_KM = 50
# The forecast models are about 0.1 degrees (a few miles) at best; finer cells add requests, not detail.
MIN_SPACING_DEG = 0.1
SPACING_GROWTH = 1.1
KM_PER_DEGREE = 111.2


def corridor_points(
    routes: list[list[LatLon]], radius_km: float = CORRIDOR_RADIUS_KM, max_cells: int = MAX_CELLS
) -> tuple[float, list[LatLon]]:
    """Grid points within radius_km of any route, coarsened until there are at most max_cells.

    Returns the nominal spacing in degrees and the points, row by row from the south.
    """
    origin = (
        min(lat for route in routes for lat, _ in route) - radius_km / KM_PER_DEGREE,
        min(lon for route in routes for _, lon in route) - radius_km / KM_PER_DEGREE,
    )
    longest_km = max(_length_mi(route) for route in routes) * KM_PER_MILE
    spacing = max(MIN_SPACING_DEG, sqrt(longest_km * 2 * radius_km / max_cells) / KM_PER_DEGREE)
    while True:
        cells = _cells_near(routes, origin, spacing, radius_km)
        if len(cells) <= max_cells:
            break
        spacing *= SPACING_GROWTH
    return spacing, [(origin[0] + row * spacing, origin[1] + column * spacing) for row, column in sorted(cells)]


def _length_mi(route: list[LatLon]) -> float:
    return sum(haversine_mi(a, b) for a, b in zip(route, route[1:]))


def _cells_near(routes: list[list[LatLon]], origin: LatLon, spacing: float, radius_km: float) -> set[tuple[int, int]]:
    """Grid cells within radius_km of a route, visiting only the cells around each segment."""
    cells = set()
    for route in routes:
        for start, end in zip(route, route[1:]) if len(route) > 1 else [(route[0], route[0])]:
            x_scale = cos(radians((start[0] + end[0]) / 2))
            radius_lat = radius_km / KM_PER_DEGREE
            radius_lon = radius_lat / max(x_scale, 0.01)
            first_row = ceil((min(start[0], end[0]) - radius_lat - origin[0]) / spacing)
            last_row = floor((max(start[0], end[0]) + radius_lat - origin[0]) / spacing)
            first_column = ceil((min(start[1], end[1]) - radius_lon - origin[1]) / spacing)
            last_column = floor((max(start[1], end[1]) + radius_lon - origin[1]) / spacing)
            for row in range(first_row, last_row + 1):
                for column in range(first_column, last_column + 1):
                    point = (origin[0] + row * spacing, origin[1] + column * spacing)
                    if _km_to_segment(point, start, end, x_scale) <= radius_km:
                        cells.add((row, column))
    return cells


def _km_to_segment(point: LatLon, start: LatLon, end: LatLon, x_scale: float) -> float:
    def flat(p: LatLon) -> tuple[float, float]:
        return p[1] * x_scale * KM_PER_DEGREE, p[0] * KM_PER_DEGREE

    (px, py), (ax, ay), (bx, by) = flat(point), flat(start), flat(end)
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    t = 0.0 if length_squared == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_squared))
    return hypot(px - (ax + t * dx), py - (ay + t * dy))


def corridor_forecast(routes: list[list[LatLon]], departure: datetime, load_lb: int, hours: int, now: datetime) -> dict:
    """Severity score (0-4) per grid cell for each forecast hour starting at the hour nearest departure."""
    check_departure(departure, now)
    first_hour = departure.replace(minute=0, second=0, microsecond=0)
    if departure.minute >= 30:
        first_hour += timedelta(hours=1)
    times = [first_hour + timedelta(hours=step) for step in range(hours)]
    check_forecast_window(times[-1], now)

    spacing, points = corridor_points(routes)
    series = fetch_hourly(points, times[0], times[-1])

    return {
        "times": [iso(moment) for moment in times],
        "spacing_deg": round(spacing, 3),
        "cells": [
            {
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "score": [_score_at(hourly.at(moment), load_lb) for moment in times],
            }
            for (lat, lon), hourly in zip(points, series)
        ],
    }


def _score_at(weather, load_lb: int) -> float:
    return round(weather_score(weather.wind_mph, weather.rain_in_hr, weather.snow_in_hr, load_lb), 2)
