import pytest

from routing.risk import (
    Level,
    classify_checkpoint,
    rain_level,
    snow_level,
    wind_level,
    wind_level_for_load,
)

L, M, H, S, N = Level.LOW, Level.MODERATE, Level.HIGH, Level.SEVERE, Level.NO_TRAVEL


@pytest.mark.parametrize(
    "mph, expected",
    [(0, L), (24.9, L), (25, M), (34.6, M), (35, H), (44.9, H), (45, S), (54.9, S), (55, N), (90, N)],
)
def test_wind_level_boundaries(mph, expected):
    assert wind_level(mph) == expected


@pytest.mark.parametrize(
    "inches, expected",
    [(0, L), (0.09, L), (0.10, M), (0.249, M), (0.25, H), (0.499, H), (0.50, S), (1.00, S), (1.001, N), (3, N)],
)
def test_rain_level_boundaries(inches, expected):
    assert rain_level(inches) == expected


@pytest.mark.parametrize(
    "inches, expected",
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_level_boundaries(inches, expected):
    assert snow_level(inches) == expected


@pytest.mark.parametrize(
    "mph, load_lb, expected",
    [
        (55, 0, N),
        (70, 1_000, N),
        (45, 30_000, S),
        (45, 30_001, N),
        (54.9, 30_001, N),
        (54.9, 80_000, N),
        (44.9, 80_000, S),
        (35, 40_000, H),
        (35, 40_001, S),
        (44.9, 40_001, S),
        (35, 80_000, S),
        (34.9, 80_000, M),
        (25, 80_000, M),
        (10, 80_000, L),
    ],
)
def test_load_rules_only_raise_the_wind_level(mph, load_lb, expected):
    assert wind_level_for_load(mph, load_lb) == expected


def test_checkpoint_level_is_the_worst_of_the_three_conditions():
    risk = classify_checkpoint(wind_mph=10, rain_in_hr=0.3, snow_in_hr=0.6, load_lb=20_000)
    assert risk.level == H
    assert risk.reasons == ["Rain 0.30 in/hr", "Snow 0.6 in/hr"]


def test_checkpoint_in_clear_weather_has_no_reasons():
    risk = classify_checkpoint(wind_mph=8, rain_in_hr=0, snow_in_hr=0, load_lb=80_000)
    assert risk.level == L
    assert risk.reasons == []


def test_checkpoint_reason_names_the_load_when_it_raised_the_level():
    risk = classify_checkpoint(wind_mph=40, rain_in_hr=0, snow_in_hr=0, load_lb=45_000)
    assert risk.level == S
    assert risk.reasons == ["Wind 40 mph with a 45,000 lb load"]


def test_checkpoint_wind_reason_without_load_effect():
    risk = classify_checkpoint(wind_mph=31, rain_in_hr=0, snow_in_hr=0, load_lb=10_000)
    assert risk.level == M
    assert risk.reasons == ["Wind 31 mph"]


def test_level_labels():
    assert [level.label for level in Level] == ["Low", "Moderate", "High", "Severe", "No Travel"]
