from routing.clients.geocode import PHOTON_HOST

from .conftest import load_fixture


def test_suggests_places_for_a_query(client, upstream):
    upstream.on(PHOTON_HOST, load_fixture("photon_dallas.json"))

    response = client.get("/api/geocode", {"q": "Dall"})

    assert response.status_code == 200
    [place] = response.json()
    assert place["name"] == "Dallas, Texas, United States"
    assert upstream.calls[0][2]["params"]["limit"] == 5


def test_a_very_short_query_does_not_call_the_geocoder(client, upstream):
    response = client.get("/api/geocode", {"q": "D"})

    assert response.json() == []
    assert upstream.calls == []
