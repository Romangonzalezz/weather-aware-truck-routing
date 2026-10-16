from datetime import datetime, timedelta, timezone
from math import ceil

import pytest

from routing.clients.weather import BATCH_SIZE, OPEN_METEO_HOST
from routing.corridor import MAX_CELLS, grid_points

from .conftest import hourly_weather

DALLAS_DENVER = [-105.0, 32.7, -96.7, 39.8]


def tomorrow_morning() -> datetime:
    return (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)


def body(**overrides) -> dict:
    return {"bbox": DALLAS_DENVER, "departure": tomorrow_morning().isoformat(), "load_lb": 38_000, **overrides}


def post(client, payload):
    return client.post("/api/corridor", payload, content_type="application/json")


def test_grid_for_a_long_trip_stays_under_the_cell_cap_and_covers_the_bbox():
    spacing, points = grid_points(DALLAS_DENVER)

    assert 200 <= len(points) <= MAX_CELLS
    assert len(set(points)) == len(points)
    lats = [lat for lat, _ in points]
    lons = [lon for _, lon in points]
    assert (min(lats), max(lats)) == pytest.approx((32.7, 39.8))
    assert (min(lons), max(lons)) == pytest.approx((-105.0, -96.7))
    assert 0.3 < spacing < 0.7


def test_grid_for_a_short_trip_does_not_go_finer_than_the_forecast_resolution():
    spacing, points = grid_points([-97.0, 32.7, -96.8, 32.9])

    assert spacing == pytest.approx(0.1)
    assert len(points) == 9


def test_grid_for_a_thin_bbox_is_a_single_column():
    _, points = grid_points([-97.0, 30.0, -96.95, 35.0])

    assert len({lon for _, lon in points}) == 1
    assert len(points) > 10


def test_returns_hourly_times_and_a_score_per_cell_and_hour(client, upstream):
    upstream.on(OPEN_METEO_HOST, hourly_weather())
    departure = tomorrow_morning().replace(minute=20)

    response = post(client, body(departure=departure.isoformat()))

    assert response.status_code == 200
    data = response.json()
    assert len(data["times"]) == 49
    assert data["times"][0] == tomorrow_morning().isoformat().replace("+00:00", "Z")
    assert data["times"][1] == (tomorrow_morning() + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    assert 200 <= len(data["cells"]) <= MAX_CELLS
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
        ({"bbox": [-96.0, 32.0, -97.0, 33.0]}, "bbox"),
        ({"bbox": [1, 2, 3]}, "bbox"),
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
