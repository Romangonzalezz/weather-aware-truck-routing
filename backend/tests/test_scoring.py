import pytest

from routing.risk import Level
from routing.scoring import Candidate, rank, summarize_risk

L, M, H, S, N = Level.LOW, Level.MODERATE, Level.HIGH, Level.SEVERE, Level.NO_TRAVEL


def test_summary_sums_miles_per_level_and_weights_the_average():
    totals = summarize_risk([(10, L), (20, M), (10, H), (5, S), (5, N)])
    assert totals.no_travel_mi == 5
    assert totals.severe_mi == 5
    assert totals.high_mi == 10
    assert totals.avg_risk == pytest.approx((0 * 10 + 1 * 20 + 2 * 10 + 3 * 5 + 4 * 5) / 50)
    assert totals.max_level == N


def test_summary_of_clear_route():
    totals = summarize_risk([(25, L), (25, L)])
    assert (totals.no_travel_mi, totals.severe_mi, totals.high_mi, totals.avg_risk) == (0, 0, 0, 0)
    assert totals.max_level == L


def test_summary_of_empty_route_is_clear():
    assert summarize_risk([]).avg_risk == 0


def candidate(route_id, segments, duration_h):
    return Candidate(route_id, summarize_risk(segments), duration_h * 3600)


def test_fewest_no_travel_miles_beats_everything_else():
    fast = candidate("fast", [(100, N)], 5)
    slow = candidate("slow", [(100, S)], 9)
    ranked, reason = rank([fast, slow])
    assert [c.route_id for c in ranked] == ["slow", "fast"]
    assert reason == "Fewest no-travel miles (0 vs 100)"


def test_fewest_severe_miles_beats_high_miles_and_speed():
    a = candidate("a", [(50, S), (50, L)], 6)
    b = candidate("b", [(100, H)], 9)
    ranked, reason = rank([a, b])
    assert ranked[0].route_id == "b"
    assert reason == "Fewest severe-risk miles (0 vs 50)"


def test_fewest_high_miles_decides_next():
    a = candidate("a", [(30, H), (70, L)], 6)
    b = candidate("b", [(100, M)], 9)
    ranked, reason = rank([a, b])
    assert ranked[0].route_id == "b"
    assert reason == "Fewest high-risk miles (0 vs 30)"


def test_lowest_average_risk_decides_next():
    a = candidate("a", [(50, M), (50, L)], 9)
    b = candidate("b", [(100, M)], 6)
    ranked, reason = rank([a, b])
    assert ranked[0].route_id == "a"
    assert reason == "Lowest average risk (0.50 vs 1.00)"


def test_travel_time_breaks_a_full_tie():
    a = candidate("a", [(100, M)], 10)
    b = candidate("b", [(100, M)], 10 - 22 / 60)
    ranked, reason = rank([a, b])
    assert ranked[0].route_id == "b"
    assert reason == "All routes tie on risk; fastest by 22 min"


def test_reason_names_the_risk_gap_and_mentions_the_time_break_among_tied_routes():
    a = candidate("a", [(100, M)], 10)
    b = candidate("b", [(100, M)], 9)
    c = candidate("c", [(100, H)], 8)
    ranked, reason = rank([a, b, c])
    assert [x.route_id for x in ranked] == ["b", "a", "c"]
    assert reason == "Fewest high-risk miles (0 vs 100); fastest of the tied routes by 60 min"


def test_reason_compares_against_the_worst_route_on_the_deciding_criterion():
    a = candidate("a", [(100, L)], 10)
    b = candidate("b", [(50, S), (50, L)], 8)
    c = candidate("c", [(80, S), (20, L)], 7)
    ranked, reason = rank([c, b, a])
    assert [x.route_id for x in ranked] == ["a", "b", "c"]
    assert reason == "Fewest severe-risk miles (0 vs 80)"


def test_single_route_is_recommended_without_comparison():
    ranked, reason = rank([candidate("only", [(10, L)], 1)])
    assert ranked[0].route_id == "only"
    assert reason == "Only one route available"


def test_identical_routes_report_equivalence():
    a = candidate("a", [(100, M)], 10)
    b = candidate("b", [(100, M)], 10)
    ranked, reason = rank([a, b])
    assert [x.route_id for x in ranked] == ["a", "b"]
    assert reason == "Routes are equivalent on risk and time"


def test_average_risks_that_display_the_same_tie_and_fall_through_to_travel_time():
    slower = candidate("slower", [(972, L), (28, M)], 13.5)  # 0.028, shown as 0.03
    faster = candidate("faster", [(966, L), (34, M)], 13.1)  # 0.034, shown as 0.03
    ordered, _ = rank([slower, faster])
    assert [c.route_id for c in ordered] == ["faster", "slower"]
