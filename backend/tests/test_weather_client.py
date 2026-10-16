from datetime import datetime, timedelta, timezone

import pytest

from routing.clients.weather import (
    OPEN_METEO_HOST,
    check_forecast_window,
    fetch_hourly,
)
from routing.errors import InvalidRequest, UpstreamError

from .conftest import load_fixture

UTC = timezone.utc
DALLAS, DENVER = (32.7767, -96.797), (39.7392, -104.9903)
DAY = datetime(2026, 10, 17, tzinfo=UTC)


def location(lat: float, wind: float = 10, rain: float = 0, showers: float = 0, snow: float = 0, hours: int = 24) -> dict:
    def hourly(value):
        return [value] * hours

    return {
        "latitude": lat,
        "hourly": {
            "time": [f"2026-10-17T{h:02d}:00" for h in range(hours)],
            "wind_speed_10m": hourly(wind),
            "rain": hourly(rain),
            "showers": hourly(showers),
            "snowfall": hourly(snow),
        },
    }


def test_reads_recorded_open_meteo_response_and_requests_the_right_units(upstream):
    recorded = load_fixture("open_meteo_two_points.json")
    upstream.on(OPEN_METEO_HOST, recorded)

    dallas, denver = fetch_hourly([DALLAS, DENVER], DAY, DAY)

    params = upstream.calls[0][2]["params"]
    assert params["latitude"] == "32.78,39.74"
    assert params["longitude"] == "-96.8,-104.99"
    assert params["wind_speed_unit"] == "mph"
    assert params["precipitation_unit"] == "inch"
    assert params["timezone"] == "UTC"
    assert (params["start_date"], params["end_date"]) == ("2026-10-17", "2026-10-17")
    assert params["hourly"] == "wind_speed_10m,rain,showers,snowfall"

    hourly = recorded[0]["hourly"]
    weather = dallas.at(datetime(2026, 10, 17, 13, 20, tzinfo=UTC))
    assert weather.wind_mph == hourly["wind_speed_10m"][13]
    assert weather.rain_in_hr == pytest.approx(hourly["rain"][13] + hourly["showers"][13])
    assert weather.snow_in_hr == hourly["snowfall"][13]
    assert denver.at(DAY).wind_mph == recorded[1]["hourly"]["wind_speed_10m"][0]


def test_uses_the_hour_nearest_to_the_eta(upstream):
    data = location(33)
    data["hourly"]["wind_speed_10m"] = list(range(24))
    upstream.on(OPEN_METEO_HOST, [data])
    [series] = fetch_hourly([DALLAS], DAY, DAY)

    assert series.at(datetime(2026, 10, 17, 5, 29, tzinfo=UTC)).wind_mph == 5
    assert series.at(datetime(2026, 10, 17, 5, 30, tzinfo=UTC)).wind_mph == 6


def test_a_single_location_comes_back_as_an_object_not_a_list(upstream):
    upstream.on(OPEN_METEO_HOST, location(33, wind=12))
    [series] = fetch_hourly([DALLAS], DAY, DAY)
    assert series.at(DAY).wind_mph == 12


def test_rain_includes_showers_and_missing_values_count_as_zero(upstream):
    data = location(33, rain=0.1, showers=0.05)
    data["hourly"]["snowfall"][0] = None
    data["hourly"]["wind_speed_10m"][0] = None
    upstream.on(OPEN_METEO_HOST, [data])
    [series] = fetch_hourly([DALLAS], DAY, DAY)

    weather = series.at(DAY)
    assert weather.rain_in_hr == pytest.approx(0.15)
    assert (weather.wind_mph, weather.snow_in_hr) == (0, 0)


def test_asking_outside_the_fetched_hours_is_an_invalid_request(upstream):
    upstream.on(OPEN_METEO_HOST, [location(33)])
    [series] = fetch_hourly([DALLAS], DAY, DAY)
    with pytest.raises(InvalidRequest, match="forecast"):
        series.at(DAY + timedelta(days=1, hours=2))


def test_many_points_are_batched_and_keep_their_order(upstream):
    def respond(method, url, params, **kwargs):
        lats = [float(v) for v in params["latitude"].split(",")]
        return [location(lat, wind=lat) for lat in lats]

    upstream.on(OPEN_METEO_HOST, respond)
    points = [(30 + i * 0.01, -100.0) for i in range(230)]

    series = fetch_hourly(points, DAY, DAY)

    assert len(upstream.calls) == 3
    assert [round(s.at(DAY).wind_mph, 2) for s in series] == [round(lat, 2) for lat, _ in points]


def test_repeated_requests_are_served_from_the_cache(upstream):
    upstream.on(OPEN_METEO_HOST, [location(33)])
    fetch_hourly([DALLAS], DAY, DAY)
    fetch_hourly([DALLAS], DAY, DAY)
    assert len(upstream.calls) == 1


def test_a_response_with_the_wrong_number_of_locations_is_an_upstream_error(upstream):
    upstream.on(OPEN_METEO_HOST, [location(33)])
    with pytest.raises(UpstreamError):
        fetch_hourly([DALLAS, DENVER], DAY, DAY)


def test_weather_outage_is_an_upstream_error(upstream):
    upstream.on(OPEN_METEO_HOST, (429, {"reason": "too many requests"}))
    with pytest.raises(UpstreamError):
        fetch_hourly([DALLAS], DAY, DAY)


def test_forecast_window_ends_fifteen_days_after_today():
    now = datetime(2026, 10, 16, 18, 0, tzinfo=UTC)
    check_forecast_window(datetime(2026, 10, 31, 23, 0, tzinfo=UTC), now)
    with pytest.raises(InvalidRequest, match="16 days"):
        check_forecast_window(datetime(2026, 11, 1, 0, 0, tzinfo=UTC), now)
