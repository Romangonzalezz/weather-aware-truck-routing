from dataclasses import dataclass

from .risk import Level


@dataclass(frozen=True)
class RiskTotals:
    no_travel_mi: float
    severe_mi: float
    high_mi: float
    avg_risk: float
    max_level: Level


@dataclass(frozen=True)
class Candidate:
    route_id: str
    risk: RiskTotals
    duration_s: float


def summarize_risk(segments: list[tuple[float, Level]]) -> RiskTotals:
    """Totals for (miles, level) segments; avg_risk is the mileage-weighted mean level index."""

    def miles_at(level: Level) -> float:
        return sum(miles for miles, seg_level in segments if seg_level == level)

    total = sum(miles for miles, _ in segments)
    weighted = sum(miles * level for miles, level in segments)
    return RiskTotals(
        no_travel_mi=miles_at(Level.NO_TRAVEL),
        severe_mi=miles_at(Level.SEVERE),
        high_mi=miles_at(Level.HIGH),
        avg_risk=weighted / total if total else 0.0,
        max_level=max((level for _, level in segments), default=Level.LOW),
    )


def _risk_key(candidate: Candidate) -> tuple[float, float, float, float]:
    risk = candidate.risk
    # Rounded so float noise in summed miles cannot decide a tie.
    return (
        round(risk.no_travel_mi, 1),
        round(risk.severe_mi, 1),
        round(risk.high_mi, 1),
        round(risk.avg_risk, 3),
    )


def _sort_key(candidate: Candidate) -> tuple[float, float, float, float, float]:
    return (*_risk_key(candidate), candidate.duration_s)


# (label, number format) for each element of the risk key, in priority order.
_CRITERIA = [
    ("Fewest no-travel miles", "g"),
    ("Fewest severe-risk miles", "g"),
    ("Fewest high-risk miles", "g"),
    ("Lowest average risk", ".2f"),
]


def rank(candidates: list[Candidate]) -> tuple[list[Candidate], str]:
    """Order candidates best first and explain what separated the best from the runner-up."""
    ordered = sorted(candidates, key=_sort_key)
    if len(ordered) < 2:
        return ordered, "Only one route available"

    best, runner_up = ordered[0], ordered[1]
    for (label, number_format), mine, theirs in zip(_CRITERIA, _risk_key(best), _risk_key(runner_up)):
        if mine != theirs:
            return ordered, f"{label} ({mine:{number_format}} vs {theirs:{number_format}})"

    minutes_faster = round((runner_up.duration_s - best.duration_s) / 60)
    if minutes_faster <= 0:
        return ordered, "Routes are equivalent on risk and time"
    if all(_risk_key(c) == _risk_key(best) for c in ordered):
        return ordered, f"All routes tie on risk; fastest by {minutes_faster} min"
    return ordered, f"Ties the next route on risk; faster by {minutes_faster} min"
