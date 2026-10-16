from datetime import datetime, timedelta, timezone
from math import ceil

import pytest

from routing.clients.geocode import PHOTON_HOST
from routing.clients.routes import OSRM_HOST, VALHALLA_HOST, fetch_routes
from routing.clients.weather import OPEN_METEO_HOST
from routing.geo import Place
from routing.sampling import haversine_mi

from .conftest import hourly_weather, load_fixture

DALLAS = {"lat": 32.7767, "lon": -96.797}
DENVER = {"lat": 39.7392, "lon": -104.9903}


def tomorrow_morning() -> datetime:
    return (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)


def body(**overrides) -> dict:
    payload = {
        "origin": DALLAS,
        "destination": DENVER,
        "departure": tomorrow_morning().isoformat(),
        "load_lb": 38_000,
        "interval_miles": 25,
    }
    return {**payload, **overrides}


@pytest.fixture
def services(upstream):
    upstream.on(VALHALLA_HOST, load_fixture("valhalla_dallas_denver.json"))
    upstream.on(OSRM_HOST, load_fixture("osrm_dallas_denver.json"))
    upstream.on(OPEN_METEO_HOST, hourly_weather())
    return upstream


def post(client, payload):
    return client.post("/api/plan", payload, content_type="application/json")


def storm_on_the_shortest_route(services):
    """Wind over a stretch of the shortest route that the other two routes stay far away from."""
    routes = fetch_routes(Place("a", **DALLAS), Place("b", **DENVER), load_lb=0)
    shortest = min(routes, key=lambda r: r.distance_mi)
    others = [point for route in routes if route is not shortest for point in route.points[::40]]
    centre = max(shortest.points[::40], key=lambda p: min(haversine_mi(p, q) for q in others))

    def storm(lat, lon):
        return {"wind": 50} if haversine_mi((lat, lon), centre) < 60 else None

    services.on(OPEN_METEO_HOST, hourly_weather(storm))
    return shortest.id


def test_plans_three_routes_with_checkpoints_and_a_recommendation(client, services):
    response = post(client, body())

    assert response.status_code == 200
    data = response.json()
    assert [r["id"] for r in data["routes"]] == ["r2", "r1", "r3"]
    assert [r["rank"] for r in data["routes"]] == [1, 2, 3]
    assert [r["recommended"] for r in data["routes"]] == [True, False, False]
    assert data["recommended_route_id"] == "r2"
    assert data["recommendation_reason"] == "All routes tie on risk; fastest by 10 min"
    assert data["origin"] == {"name": "32.7767, -96.7970", "lat": DALLAS["lat"], "lon": DALLAS["lon"]}
    assert data["load_lb"] == 38_000 and data["interval_miles"] == 25

    best = data["routes"][0]
    assert best["summary"]["distance_mi"] == pytest.approx(808.3, abs=0.1)
    assert best["summary"]["duration_h"] == pytest.approx(13.07, abs=0.01)
    assert best["summary"]["max_level"] == "Low"
    assert best["summary"]["avg_risk"] == 0
    assert best["summary"]["no_travel_mi"] == best["summary"]["severe_mi"] == best["summary"]["high_mi"] == 0
    first_lon, first_lat = best["geometry"][0]
    assert (first_lat, first_lon) == pytest.approx((32.77, -96.8), abs=0.05)


def test_checkpoints_follow_the_requested_interval_with_increasing_etas(client, services):
    data = post(client, body(interval_miles=50)).json()

    for route in data["routes"]:
        checkpoints = route["checkpoints"]
        miles = [c["mile"] for c in checkpoints]
        assert miles[:-1] == [50.0 * n for n in range(1, len(miles))]
        assert len(miles) == ceil(route["summary"]["distance_mi"] / 50)
        etas = [c["eta"] for c in checkpoints]
        assert etas == sorted(etas) and etas[0] > data["departure"]
        assert etas[-1] == route["summary"]["arrival"]

    checkpoint = data["routes"][0]["checkpoints"][0]
    assert set(checkpoint) == {"mile", "lat", "lon", "eta", "wind_mph", "rain_in_hr", "snow_in_hr", "level", "reasons"}
    assert checkpoint["level"] == "Low" and checkpoint["reasons"] == []


def test_a_storm_on_the_shortest_route_moves_the_recommendation_elsewhere(client, services):
    stormy_id = storm_on_the_shortest_route(services)

    data = post(client, body(load_lb=20_000)).json()

    stormy = next(r for r in data["routes"] if r["id"] == stormy_id)
    assert stormy["summary"]["severe_mi"] > 0 and stormy["summary"]["max_level"] == "Severe"
    assert stormy["recommended"] is False
    assert data["recommended_route_id"] != stormy_id
    assert data["recommendation_reason"].startswith(f"Fewest severe-risk miles (0 vs {stormy['summary']['severe_mi']:g})")
    assert any(c["reasons"] == ["Wind 50 mph"] for c in stormy["checkpoints"])


def test_the_same_storm_is_no_travel_for_a_heavy_load(client, services):
    stormy_id = storm_on_the_shortest_route(services)

    data = post(client, body(load_lb=45_000)).json()

    stormy = next(r for r in data["routes"] if r["id"] == stormy_id)
    assert stormy["summary"]["no_travel_mi"] > 0 and stormy["summary"]["max_level"] == "No Travel"
    assert data["recommendation_reason"].startswith("Fewest no-travel miles (0 vs")
    assert any(c["reasons"] == ["Wind 50 mph with a 45,000 lb load"] for c in stormy["checkpoints"])


def test_text_places_are_geocoded(client, services):
    services.on(PHOTON_HOST, load_fixture("photon_dallas.json"))

    data = post(client, body(origin="Dallas, TX")).json()

    assert data["origin"]["name"] == "Dallas, Texas, United States"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"interval_miles": 15}, "interval_miles"),
        ({"load_lb": 80_001}, "load_lb"),
        ({"load_lb": -1}, "load_lb"),
        ({"departure": "tomorrow"}, "departure"),
        ({"origin": ""}, "origin"),
        ({"destination": {"lat": 95, "lon": 0}}, "Coordinates"),
        ({"departure": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()}, "past"),
        ({"departure": (datetime.now(timezone.utc) + timedelta(days=17)).isoformat()}, "16 days"),
    ],
)
def test_bad_input_is_a_400_with_a_message(client, services, overrides, message):
    response = post(client, body(**overrides))

    assert response.status_code == 400
    assert message in response.json()["error"]


def test_missing_fields_are_a_400(client, services):
    response = post(client, {"origin": "Dallas"})

    assert response.status_code == 400
    assert "required" in response.json()["error"]


def test_unknown_place_is_a_400(client, services):
    services.on(PHOTON_HOST, {"features": []})

    response = post(client, body(origin="Nowhereville"))

    assert response.status_code == 400
    assert "Nowhereville" in response.json()["error"]


def test_a_trip_whose_checkpoints_pass_the_forecast_window_is_a_400(client, services):
    late_departure = (datetime.now(timezone.utc) + timedelta(days=15, hours=20)).isoformat()

    response = post(client, body(departure=late_departure))

    assert response.status_code == 400
    assert "16 days" in response.json()["error"]


def test_router_outage_is_a_502(client, upstream):
    upstream.on(VALHALLA_HOST, (500, {}))
    upstream.on(OSRM_HOST, (500, {}))

    response = post(client, body())

    assert response.status_code == 502
    assert response.json() == {"error": "OSRM is unavailable"}


def test_weather_outage_is_a_502(client, services):
    services.on(OPEN_METEO_HOST, (500, {}))

    response = post(client, body())

    assert response.status_code == 502
    assert response.json() == {"error": "Open-Meteo is unavailable"}


def test_only_post_is_allowed(client):
    response = client.get("/api/plan")

    assert response.status_code == 405
    assert "error" in response.json()
