from datetime import datetime, timedelta
from math import floor, sqrt

from .clients.weather import check_departure, check_forecast_window, fetch_hourly
from .planner import iso
from .risk import weather_score
from .sampling import LatLon

MAX_CELLS = 300
# The forecast models are about 0.1 degrees (a few miles) at best; finer cells add requests, not detail.
MIN_SPACING_DEG = 0.1
SPACING_GROWTH = 1.05


def grid_points(bbox: list[float], max_cells: int = MAX_CELLS) -> tuple[float, list[LatLon]]:
    """Evenly spread points over bbox, coarsened until there are at most max_cells.

    Returns the nominal spacing in degrees and the points, row by row from the south-west.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    width, height = max_lon - min_lon, max_lat - min_lat

    def count(extent: float, spacing: float) -> int:
        return floor(extent / spacing + 1e-9) + 1  # the epsilon keeps 0.2 / 0.1 from rounding down to 1

    spacing = max(MIN_SPACING_DEG, sqrt(width * height / max_cells))
    while count(width, spacing) * count(height, spacing) > max_cells:
        spacing *= SPACING_GROWTH
    columns, rows = count(width, spacing), count(height, spacing)

    def position(start: float, extent: float, index: int, count: int) -> float:
        return start + extent / 2 if count == 1 else start + extent * index / (count - 1)

    points = [
        (position(min_lat, height, row, rows), position(min_lon, width, column, columns))
        for row in range(rows)
        for column in range(columns)
    ]
    return spacing, points


def corridor_forecast(bbox: list[float], departure: datetime, load_lb: int, hours: int, now: datetime) -> dict:
    """Severity score (0-4) per grid cell for each forecast hour starting at the hour nearest departure."""
    check_departure(departure, now)
    first_hour = departure.replace(minute=0, second=0, microsecond=0)
    if departure.minute >= 30:
        first_hour += timedelta(hours=1)
    times = [first_hour + timedelta(hours=step) for step in range(hours)]
    check_forecast_window(times[-1], now)

    spacing, points = grid_points(bbox)
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
