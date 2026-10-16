import pytest

from routing.risk import (
    Level,
    classify_checkpoint,
    rain_level,
    snow_level,
    wind_level,
    wind_level_for_load,
    wind_score,
    rain_score,
    snow_score,
    weather_score,
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


@pytest.mark.parametrize(
    "mph, load_lb, expected",
    [
        (0, 0, 0),
        (12.5, 0, 0.5),
        (25, 0, 1),
        (30, 0, 1.5),
        (40, 0, 2.5),
        (55, 0, 4),
        (80, 0, 4),
        (40, 40_000, 2.5),
        (40, 40_001, 3),
        (50, 30_000, 3.5),
        (50, 30_001, 4),
        (30, 80_000, 1.5),
    ],
)
def test_wind_score_is_continuous_and_follows_the_load_rules(mph, load_lb, expected):
    assert wind_score(mph, load_lb) == pytest.approx(expected)


@pytest.mark.parametrize(
    "scorer, value, expected",
    [
        (rain_score, 0.05, 0.5),
        (rain_score, 0.10, 1),
        (rain_score, 0.175, 1.5),
        (rain_score, 0.75, 3.5),
        (rain_score, 4, 4),
        (snow_score, 0.25, 0.5),
        (snow_score, 1.5, 2.5),
        (snow_score, 3.0, 4),
    ],
)
def test_rain_and_snow_scores_interpolate_between_the_level_bounds(scorer, value, expected):
    assert scorer(value) == pytest.approx(expected)


def test_wind_score_rounds_down_to_the_wind_level():
    for tenth in range(0, 700):
        mph = tenth / 10
        for load_lb in (0, 35_000, 45_000):
            assert int(wind_score(mph, load_lb)) == wind_level_for_load(mph, load_lb)


def test_weather_score_is_the_worst_condition():
    assert weather_score(wind_mph=10, rain_in_hr=0.175, snow_in_hr=0.25, load_lb=0) == pytest.approx(1.5)
