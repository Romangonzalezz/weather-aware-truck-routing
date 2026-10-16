from datetime import datetime, timedelta, timezone

import pytest

from routing.sampling import haversine_mi, sample_checkpoints

DEPARTURE = datetime(2026, 10, 17, 13, 0, tzinfo=timezone.utc)
# One degree of longitude on the equator.
DEGREE_MI = haversine_mi((0, 0), (0, 1))
LINE = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]


def test_haversine_known_distance():
    assert haversine_mi((32.7767, -96.7970), (39.7392, -104.9903)) == pytest.approx(663, abs=3)


def test_checkpoints_every_interval_and_one_at_the_destination():
    total = 2 * DEGREE_MI
    result = sample_checkpoints(LINE, total, [(0, 0), (2, 7200)], DEPARTURE, 50)
    assert [round(c.mile, 1) for c in result] == [50, 100, round(total, 1)]
    assert result[0].lat == pytest.approx(0)
    assert result[0].lon == pytest.approx(50 / DEGREE_MI)
    assert (result[-1].lat, result[-1].lon) == pytest.approx((0, 2))


def test_checkpoint_on_the_destination_is_not_duplicated():
    result = sample_checkpoints([(0.0, 0.0), (0.0, 1.0)], 100, [(0, 0), (1, 3600)], DEPARTURE, 50)
    assert [c.mile for c in result] == [50, 100]


def test_short_route_has_only_the_destination():
    result = sample_checkpoints([(0.0, 0.0), (0.0, 0.1)], DEGREE_MI / 10, [(0, 0), (1, 600)], DEPARTURE, 25)
    assert len(result) == 1
    assert result[0].eta == DEPARTURE + timedelta(seconds=600)


def test_eta_follows_the_router_times_not_a_flat_average_speed():
    total = 2 * DEGREE_MI
    knots = [(0, 0), (1, 3600), (2, 3600 + 7200)]  # second degree is twice as slow
    result = sample_checkpoints(LINE, total, knots, DEPARTURE, 50)
    first = next(c for c in result if round(c.mile) == 50)
    third = next(c for c in result if round(c.mile) == 100)
    assert first.eta == DEPARTURE + timedelta(seconds=3600 * 50 / DEGREE_MI)
    seconds_at_100 = 3600 + 7200 * (100 - DEGREE_MI) / DEGREE_MI
    assert third.eta == DEPARTURE + timedelta(seconds=seconds_at_100)
    assert result[-1].eta == DEPARTURE + timedelta(seconds=10800)


def test_router_distance_rescales_geometry_miles():
    # The router says the line is twice as long as the straight-line distance.
    result = sample_checkpoints(LINE, 4 * DEGREE_MI, [(0, 0), (2, 7200)], DEPARTURE, 100)
    assert result[0].mile == 100
    assert result[0].lon == pytest.approx(50 / DEGREE_MI)


def test_degenerate_route_yields_the_destination_checkpoint():
    result = sample_checkpoints([(1.0, 1.0)], 0, [(0, 0)], DEPARTURE, 25)
    assert [(c.lat, c.lon, c.eta) for c in result] == [(1.0, 1.0, DEPARTURE)]
