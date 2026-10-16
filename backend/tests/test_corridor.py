from datetime import datetime, timedelta, timezone
from math import ceil

import pytest

from routing.clients.weather import BATCH_SIZE, OPEN_METEO_HOST
from routing.corridor import CORRIDOR_RADIUS_KM, MAX_CELLS, corridor_points
from routing.sampling import haversine_mi

from .conftest import hourly_weather

DALLAS_TO_DENVER = [[-96.797, 32.7767], [-101.8, 35.2], [-104.9903, 39.7392]]  # [lon, lat] like the plan geometry
SHORT_HOP = [[-97.0, 32.7], [-96.8, 32.9]]


def tomorrow_morning() -> datetime:
    return (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)


def body(**overrides) -> dict:
    return {"routes": [DALLAS_TO_DENVER], "departure": tomorrow_morning().isoformat(), "load_lb": 38_000, **overrides}


def post(client, payload):
    return client.post("/api/corridor", payload, content_type="application/json")


def lat_lon(route: list[list[float]], steps_per_leg: int = 400) -> list[tuple[float, float]]:
    """Densely sampled (lat, lon) points along a [lon, lat] polyline."""
    points = []
    for (lon1, lat1), (lon2, lat2) in zip(route, route[1:]):
        for step in range(steps_per_leg):
            t = step / steps_per_leg
            points.append((lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1)))
    points.append((route[-1][1], route[-1][0]))
    return points


def km_from_route(point: tuple[float, float], route: list[list[float]]) -> float:
    return min(haversine_mi(point, other) for other in lat_lon(route)) * 1.609


def test_a_long_trip_gets_a_capped_band_of_cells_around_the_route():
    spacing, points = corridor_points([lat_lon(DALLAS_TO_DENVER)])

    assert 150 <= len(points) <= MAX_CELLS
    assert len(set(points)) == len(points)
    assert 0.1 <= spacing < 0.5
    assert max(km_from_route(point, DALLAS_TO_DENVER) for point in points) <= CORRIDOR_RADIUS_KM + 2


def test_cells_far_from_the_route_are_left_out_of_the_bounding_box():
    _, points = corridor_points([lat_lon(DALLAS_TO_DENVER)])

    assert not [point for point in points if point[0] > 38 and point[1] > -100]
    assert not [point for point in points if point[0] < 34 and point[1] < -102]


def test_every_route_contributes_to_the_band():
    north = [[-96.797, 32.7767], [-97.0, 39.0], [-104.9903, 39.7392]]

    _, points = corridor_points([lat_lon(DALLAS_TO_DENVER), lat_lon(north)])

    assert any(lat > 38 and lon > -98.5 for lat, lon in points)
    assert any(lat < 34 and lon < -99 and km_from_route((lat, lon), DALLAS_TO_DENVER) < 50 for lat, lon in points)


def test_a_short_trip_does_not_go_finer_than_the_forecast_resolution():
    spacing, points = corridor_points([lat_lon(SHORT_HOP)])

    assert spacing == pytest.approx(0.1)
    assert 10 < len(points) <= MAX_CELLS


def test_a_single_repeated_point_still_yields_a_disc_of_cells():
    _, points = corridor_points([[(32.0, -97.0), (32.0, -97.0)]])

    assert points and all(haversine_mi(point, (32.0, -97.0)) * 1.609 <= CORRIDOR_RADIUS_KM + 2 for point in points)


def test_returns_hourly_times_and_a_score_per_cell_and_hour(client, upstream):
    upstream.on(OPEN_METEO_HOST, hourly_weather())
    departure = tomorrow_morning().replace(minute=20)

    response = post(client, body(departure=departure.isoformat()))

    assert response.status_code == 200
    data = response.json()
    assert len(data["times"]) == 49
    assert data["times"][0] == tomorrow_morning().isoformat().replace("+00:00", "Z")
    assert data["times"][1] == (tomorrow_morning() + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    assert 150 <= len(data["cells"]) <= MAX_CELLS
    cell = data["cells"][0]
    assert set(cell) == {"lat", "lon", "score"}
    assert len(cell["score"]) == 49
    assert cell["score"][0] == pytest.approx(8 / 25, abs=0.01)
    assert len(upstream.calls) == ceil(len(data["cells"]) / BATCH_SIZE)


def test_scores_rise_where_the_forecast_is_bad_and_use_the_load(client, upstream):
    def storm(lat, lon):
        return {"wind": 40} if lat > 38 else None

    upstream.on(OPEN_METEO_HOST, hourly_weather(storm))

    light = post(client, body(load_lb=10_000)).json()
    heavy = post(client, body(load_lb=45_000)).json()

    def north_scores(data):
        return {cell["score"][5] for cell in data["cells"] if cell["lat"] > 39}

    assert north_scores(light) == {2.5}
    assert north_scores(heavy) == {3.0}
    assert {cell["score"][5] for cell in light["cells"] if cell["lat"] < 36} == {0.32}


def test_hours_limits_the_number_of_steps(client, upstream):
    upstream.on(OPEN_METEO_HOST, hourly_weather())

    data = post(client, body(hours=3)).json()

    assert len(data["times"]) == 3
    assert all(len(cell["score"]) == 3 for cell in data["cells"])


def test_repeated_requests_reuse_the_cached_forecast(client, upstream):
    upstream.on(OPEN_METEO_HOST, hourly_weather())

    post(client, body())
    calls = len(upstream.calls)
    post(client, body())

    assert len(upstream.calls) == calls


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"routes": []}, "routes"),
        ({"routes": [[[-97.0, 32.0]]]}, "routes"),
        ({"routes": [[[-97.0, 132.0], [-96.0, 33.0]]]}, "routes"),
        ({"routes": [[[-97.0, 32.0, 5.0], [-96.0, 33.0]]]}, "routes"),
        ({"routes": [SHORT_HOP] * 6}, "routes"),
        ({"hours": 50}, "hours"),
        ({"departure": (datetime.now(timezone.utc) + timedelta(days=16)).isoformat()}, "16 days"),
        ({"departure": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()}, "past"),
    ],
)
def test_bad_input_is_a_400(client, upstream, overrides, message):
    response = post(client, body(**overrides))

    assert response.status_code == 400
    assert message in response.json()["error"]


def test_weather_outage_is_a_502(client, upstream):
    upstream.on(OPEN_METEO_HOST, (500, {}))

    response = post(client, body())

    assert response.status_code == 502
