from ..errors import InvalidRequest
from ..geo import Place
from .http import request_json

PHOTON_HOST = "photon.komoot.io"


def search_places(query: str, limit: int) -> list[Place]:
    data = request_json(
        "Photon geocoder",
        "GET",
        f"https://{PHOTON_HOST}/api",
        params={"q": query, "limit": limit, "lang": "en"},
    )
    return [_place(feature) for feature in data["features"]]


def resolve_place(value: str | dict) -> Place:
    """A place from free text (geocoded) or from {"lat": ..., "lon": ..., "name": optional label}."""
    if isinstance(value, dict):
        return _coordinates(value)
    matches = search_places(value, limit=1)
    if not matches:
        raise InvalidRequest(f"Could not find a place named '{value}'")
    return matches[0]


def _coordinates(value: dict) -> Place:
    lat, lon = value.get("lat"), value.get("lon")
    numbers = all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in (lat, lon))
    if not numbers or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise InvalidRequest("Coordinates need a numeric lat in [-90, 90] and lon in [-180, 180]")
    name = value.get("name")
    return Place(name.strip() if isinstance(name, str) and name.strip() else f"{lat:.4f}, {lon:.4f}", lat, lon)


def _place(feature: dict) -> Place:
    properties = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"]
    street = " ".join(filter(None, (properties.get("housenumber"), properties.get("street"))))
    parts = [properties.get("name") or street, properties.get("city"), properties.get("state"), properties.get("country")]
    unique = list(dict.fromkeys(part for part in parts if part))
    return Place(", ".join(unique), lat, lon)
