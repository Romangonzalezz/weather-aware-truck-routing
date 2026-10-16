from dataclasses import dataclass, replace

from ..errors import InvalidRequest, UpstreamError
from ..geo import Place
from ..polyline import decode
from ..sampling import LatLon
from .http import request_json

VALHALLA_HOST = "valhalla1.openstreetmap.de"
OSRM_HOST = "router.project-osrm.org"

WANTED_ROUTES = 3
POUNDS_PER_METRIC_TON = 2204.62
METERS_PER_MILE = 1609.344
# Routes closer in length than this are treated as the same road.
DUPLICATE_DISTANCE_RATIO = 0.02
# The OSRM demo snaps unreachable places to whatever road is nearest, however far.
MAX_SNAP_DISTANCE_M = 5_000


@dataclass(frozen=True)
class Route:
    id: str
    points: list[LatLon]
    distance_mi: float
    duration_s: float
    # (index into points, elapsed seconds) pairs used to time checkpoints.
    knots: list[tuple[int, float]]


def fetch_routes(origin: Place, destination: Place, load_lb: float) -> list[Route]:
    """Up to three routes: Valhalla truck routing first, OSRM filling any gap."""
    found: list[Route] = []
    try:
        found = _valhalla_routes(origin, destination, load_lb)
    except UpstreamError:
        pass

    if len(found) < WANTED_ROUTES:
        try:
            for route in _osrm_routes(origin, destination):
                if len(found) < WANTED_ROUTES and not any(_same_road(route, other) for other in found):
                    found.append(route)
        except (UpstreamError, InvalidRequest):
            if not found:
                raise

    if not found:
        raise InvalidRequest("No drivable route between these places")
    return [replace(route, id=f"r{number}") for number, route in enumerate(found, 1)]


def _same_road(a: Route, b: Route) -> bool:
    return abs(a.distance_mi - b.distance_mi) <= DUPLICATE_DISTANCE_RATIO * b.distance_mi


def _valhalla_routes(origin: Place, destination: Place, load_lb: float) -> list[Route]:
    body = {
        "locations": [{"lat": origin.lat, "lon": origin.lon}, {"lat": destination.lat, "lon": destination.lon}],
        "costing": "truck",
        "costing_options": {"truck": {"weight": round(load_lb / POUNDS_PER_METRIC_TON, 2)}},
        "alternates": WANTED_ROUTES - 1,
        "directions_options": {"units": "miles"},
    }
    data = request_json("Valhalla", "POST", f"https://{VALHALLA_HOST}/route", json=body)
    trips = [data["trip"]] + [alternate["trip"] for alternate in data.get("alternates", [])]
    return [_valhalla_route(trip) for trip in trips]


def _valhalla_route(trip: dict) -> Route:
    leg = trip["legs"][0]
    points = decode(leg["shape"])
    last = len(points) - 1

    knots: list[tuple[int, float]] = []
    elapsed = 0.0
    for maneuver in leg["maneuvers"]:
        knots.append((maneuver["begin_shape_index"], elapsed))
        elapsed += maneuver["time"]
    if knots[-1][0] == last:
        knots[-1] = (last, elapsed)
    else:
        knots.append((last, elapsed))

    return Route("", points, trip["summary"]["length"], trip["summary"]["time"], knots)


def _osrm_routes(origin: Place, destination: Place) -> list[Route]:
    coordinates = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
    data = request_json(
        "OSRM",
        "GET",
        f"https://{OSRM_HOST}/route/v1/driving/{coordinates}",
        params={"alternatives": "3", "overview": "full", "geometries": "polyline6"},
    )
    snapped_far = any(waypoint["distance"] > MAX_SNAP_DISTANCE_M for waypoint in data.get("waypoints", []))
    if data.get("code") != "Ok" or snapped_far:
        raise InvalidRequest("No drivable route between these places")

    routes = []
    for raw in data["routes"]:
        points = decode(raw["geometry"])
        routes.append(
            Route("", points, raw["distance"] / METERS_PER_MILE, raw["duration"], [(0, 0.0), (len(points) - 1, raw["duration"])])
        )
    return routes
