from datetime import datetime, timedelta, timezone

from .clients.geocode import resolve_place
from .clients.routes import Route, fetch_routes
from .clients.weather import HourlySeries, check_forecast_window, fetch_hourly
from .errors import InvalidRequest
from .geo import Place
from .risk import Level, classify_checkpoint
from .sampling import Checkpoint, sample_checkpoints
from .scoring import Candidate, RiskTotals, rank, summarize_risk

# A browser's "now" is already a little in the past by the time the request arrives.
PAST_DEPARTURE_GRACE = timedelta(hours=1)


def iso(moment: datetime) -> str:
    """UTC ISO timestamp rounded to the second."""
    rounded = (moment + timedelta(milliseconds=500)).replace(microsecond=0)
    return rounded.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def plan_trip(
    origin: str | dict,
    destination: str | dict,
    departure: datetime,
    load_lb: int,
    interval_miles: int,
    now: datetime,
) -> dict:
    if departure < now - PAST_DEPARTURE_GRACE:
        raise InvalidRequest("Departure is in the past")
    check_forecast_window(departure, now)

    start, end = resolve_place(origin), resolve_place(destination)
    routes = fetch_routes(start, end, load_lb)
    sampled = {
        route.id: sample_checkpoints(route.points, route.distance_mi, route.knots, departure, interval_miles)
        for route in routes
    }

    # One extra hour: the nearest forecast hour to the last ETA can fall on the next day.
    last_needed = max(checkpoint.eta for checkpoints in sampled.values() for checkpoint in checkpoints) + timedelta(hours=1)
    check_forecast_window(last_needed, now)
    all_checkpoints = [cp for route in routes for cp in sampled[route.id]]
    series = iter(fetch_hourly([(cp.lat, cp.lon) for cp in all_checkpoints], departure, last_needed))

    assessed = {}
    for route in routes:
        route_series = [next(series) for _ in sampled[route.id]]
        assessed[route.id] = _assess(sampled[route.id], route_series, load_lb)

    candidates = [Candidate(route.id, assessed[route.id][1], route.duration_s) for route in routes]
    ranking, reason = rank(candidates)
    best_id = ranking[0].route_id
    by_id = {route.id: route for route in routes}

    return {
        "origin": _place(start),
        "destination": _place(end),
        "departure": iso(departure),
        "load_lb": load_lb,
        "interval_miles": interval_miles,
        "recommended_route_id": best_id,
        "recommendation_reason": reason,
        "routes": [
            _route_payload(by_id[c.route_id], position, c.route_id == best_id, assessed[c.route_id], departure)
            for position, c in enumerate(ranking, 1)
        ],
    }


def _assess(
    checkpoints: list[Checkpoint], series: list[HourlySeries], load_lb: int
) -> tuple[list[dict], RiskTotals]:
    payloads = []
    segments = []
    previous_mile = 0.0
    for checkpoint, hourly in zip(checkpoints, series):
        weather = hourly.at(checkpoint.eta)
        risk = classify_checkpoint(weather.wind_mph, weather.rain_in_hr, weather.snow_in_hr, load_lb)
        segments.append((checkpoint.mile - previous_mile, risk.level))
        previous_mile = checkpoint.mile
        payloads.append(
            {
                "mile": round(checkpoint.mile, 1),
                "lat": round(checkpoint.lat, 4),
                "lon": round(checkpoint.lon, 4),
                "eta": iso(checkpoint.eta),
                "wind_mph": round(weather.wind_mph, 1),
                "rain_in_hr": round(weather.rain_in_hr, 3),
                "snow_in_hr": round(weather.snow_in_hr, 2),
                "level": risk.level.label,
                "reasons": risk.reasons,
            }
        )
    return payloads, summarize_risk(segments)


def _route_payload(route: Route, position: int, recommended: bool, assessment: tuple[list[dict], RiskTotals], departure: datetime) -> dict:
    checkpoints, totals = assessment
    return {
        "id": route.id,
        "rank": position,
        "recommended": recommended,
        "summary": {
            "distance_mi": round(route.distance_mi, 1),
            "duration_h": round(route.duration_s / 3600, 2),
            "arrival": iso(departure + timedelta(seconds=route.duration_s)),
            "no_travel_mi": round(totals.no_travel_mi, 1),
            "severe_mi": round(totals.severe_mi, 1),
            "high_mi": round(totals.high_mi, 1),
            "avg_risk": round(totals.avg_risk, 2),
            "max_level": totals.max_level.label,
        },
        "geometry": [[round(lon, 5), round(lat, 5)] for lat, lon in route.points],
        "checkpoints": checkpoints,
    }


def _place(place: Place) -> dict:
    return {"name": place.name, "lat": place.lat, "lon": place.lon}
