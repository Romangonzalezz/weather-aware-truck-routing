import pytest

from routing.clients.routes import VALHALLA_HOST, OSRM_HOST, fetch_routes
from routing.errors import InvalidRequest, UpstreamError
from routing.geo import Place

from .conftest import load_fixture

DALLAS = Place("Dallas, Texas", 32.7767, -96.797)
DENVER = Place("Denver, Colorado", 39.7392, -104.9903)


@pytest.fixture
def both(upstream):
    upstream.on(VALHALLA_HOST, load_fixture("valhalla_dallas_denver.json"))
    upstream.on(OSRM_HOST, load_fixture("osrm_dallas_denver.json"))
    return upstream


def valhalla_with(alternates: int) -> dict:
    data = load_fixture("valhalla_dallas_denver.json")
    data["alternates"] = data["alternates"][:alternates]
    return data


def test_returns_three_valhalla_routes_with_distance_duration_and_knots(both):
    routes = fetch_routes(DALLAS, DENVER, load_lb=38_000)

    assert [r.id for r in routes] == ["r1", "r2", "r3"]
    assert [round(r.distance_mi) for r in routes] == [887, 808, 851]
    assert routes[0].duration_s == pytest.approx(47636.1, abs=1)
    assert both.calls_to(OSRM_HOST) == []

    route = routes[0]
    assert route.points[0] == pytest.approx((32.7695, -96.7956), abs=0.01)
    assert route.knots[0] == (0, 0)
    assert route.knots[-1] == (len(route.points) - 1, pytest.approx(route.duration_s, abs=1))
    indexes = [index for index, _ in route.knots]
    seconds = [s for _, s in route.knots]
    assert indexes == sorted(indexes) and seconds == sorted(seconds)


def test_asks_valhalla_for_truck_routes_with_the_load_in_metric_tons(both):
    fetch_routes(DALLAS, DENVER, load_lb=44_092.5)

    _, url, kwargs = both.calls_to(VALHALLA_HOST)[0]
    body = kwargs["json"]
    assert body["costing"] == "truck"
    assert body["alternates"] == 2
    assert body["costing_options"]["truck"]["weight"] == pytest.approx(20.0, abs=0.01)
    assert body["locations"][0] == {"lat": DALLAS.lat, "lon": DALLAS.lon}


def test_osrm_fills_missing_routes_but_skips_duplicates(upstream):
    upstream.on(VALHALLA_HOST, valhalla_with(alternates=0))
    upstream.on(OSRM_HOST, load_fixture("osrm_dallas_denver.json"))

    routes = fetch_routes(DALLAS, DENVER, load_lb=10_000)

    # OSRM's second route (880 mi) is the same road as Valhalla's 887 mi route; its first is a real alternative.
    assert [round(r.distance_mi) for r in routes] == [887, 795]
    assert routes[1].knots == [(0, 0), (len(routes[1].points) - 1, pytest.approx(51597.2, abs=1))]


def test_falls_back_to_osrm_when_valhalla_fails(upstream):
    upstream.on(VALHALLA_HOST, (500, {"error": "boom"}))
    upstream.on(OSRM_HOST, load_fixture("osrm_dallas_denver.json"))

    routes = fetch_routes(DALLAS, DENVER, load_lb=10_000)

    assert [r.id for r in routes] == ["r1", "r2"]


def test_reports_upstream_error_when_every_router_fails(upstream):
    upstream.on(VALHALLA_HOST, (500, {}))
    upstream.on(OSRM_HOST, (503, {}))

    with pytest.raises(UpstreamError):
        fetch_routes(DALLAS, DENVER, load_lb=10_000)


def test_reports_no_route_as_an_invalid_request(upstream):
    upstream.on(VALHALLA_HOST, (400, {"error": "no path"}))
    upstream.on(OSRM_HOST, {"code": "NoRoute", "routes": []})

    with pytest.raises(InvalidRequest, match="No drivable route"):
        fetch_routes(DALLAS, DENVER, load_lb=10_000)


def test_identical_requests_hit_the_network_once(both):
    fetch_routes(DALLAS, DENVER, load_lb=38_000)
    fetch_routes(DALLAS, DENVER, load_lb=38_000)

    assert len(both.calls_to(VALHALLA_HOST)) == 1


def test_rejects_osrm_routes_whose_endpoints_snapped_far_from_the_request(upstream):
    far = load_fixture("osrm_dallas_denver.json")
    far["waypoints"][1]["distance"] = 7_900_000
    upstream.on(VALHALLA_HOST, (400, {"error": "no path"}))
    upstream.on(OSRM_HOST, far)

    with pytest.raises(InvalidRequest, match="No drivable route"):
        fetch_routes(DALLAS, DENVER, load_lb=10_000)
