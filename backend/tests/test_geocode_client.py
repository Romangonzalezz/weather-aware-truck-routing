import pytest

from routing.clients.geocode import PHOTON_HOST, resolve_place, search_places
from routing.errors import InvalidRequest, UpstreamError

from .conftest import load_fixture


@pytest.fixture
def photon(upstream):
    upstream.on(PHOTON_HOST, load_fixture("photon_dallas.json"))
    return upstream


def test_search_builds_a_readable_name_and_coordinates(photon):
    [place] = search_places("Dallas, TX", limit=1)

    assert place.name == "Dallas, Texas, United States"
    assert (place.lat, place.lon) == pytest.approx((32.77627, -96.79686), abs=1e-5)
    _, _, kwargs = photon.calls[0]
    assert kwargs["params"] == {"q": "Dallas, TX", "limit": 1, "lang": "en"}


def test_search_without_matches_is_empty(upstream):
    upstream.on(PHOTON_HOST, {"type": "FeatureCollection", "features": []})
    assert search_places("zzzz", limit=5) == []


def test_resolve_geocodes_text_and_takes_the_first_match(photon):
    place = resolve_place("Dallas, TX")
    assert place.name == "Dallas, Texas, United States"


def test_resolve_unknown_text_is_an_invalid_request(upstream):
    upstream.on(PHOTON_HOST, {"features": []})
    with pytest.raises(InvalidRequest, match="Could not find a place named 'nowhere'"):
        resolve_place("nowhere")


def test_resolve_coordinates_skips_the_network(upstream):
    place = resolve_place({"lat": 32.7767, "lon": -96.797})
    assert (place.lat, place.lon) == (32.7767, -96.797)
    assert place.name == "32.7767, -96.7970"
    assert upstream.calls == []


@pytest.mark.parametrize("value", [{"lat": 91, "lon": 0}, {"lat": 0, "lon": 181}, {"lat": "x", "lon": 0}, {"lat": 1}])
def test_resolve_rejects_bad_coordinates(value):
    with pytest.raises(InvalidRequest):
        resolve_place(value)


def test_geocoder_outage_is_an_upstream_error(upstream):
    upstream.on(PHOTON_HOST, (500, {}))
    with pytest.raises(UpstreamError):
        resolve_place("Dallas")
