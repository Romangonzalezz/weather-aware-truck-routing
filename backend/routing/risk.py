from dataclasses import dataclass
from enum import IntEnum


class Level(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True)
class Scale:
    """Lower bounds of Moderate, High, Severe and No Travel for one weather condition."""

    bounds: tuple[float, float, float, float]
    # Wind reaches No Travel at its bound (55 mph); rain and snow only above theirs.
    no_travel_inclusive: bool

    def level(self, value: float) -> Level:
        moderate, high, severe, no_travel = self.bounds
        if value > no_travel or (self.no_travel_inclusive and value == no_travel):
            return Level.NO_TRAVEL
        return Level(sum(value >= bound for bound in (moderate, high, severe)))

    def score(self, value: float) -> float:
        """Position on the 0-4 level axis, linear between bounds: 0 at no weather, 1 at Moderate's bound."""
        lower = 0.0
        for index, bound in enumerate(self.bounds):
            if value < bound:
                return index + (value - lower) / (bound - lower)
            lower = bound
        return float(Level.NO_TRAVEL)


WIND = Scale((25, 35, 45, 55), no_travel_inclusive=True)
RAIN = Scale((0.10, 0.25, 0.50, 1.00), no_travel_inclusive=False)
SNOW = Scale((0.5, 1.0, 2.0, 3.0), no_travel_inclusive=False)

HEAVY_WIND_LOAD_LB = 30_000
VERY_HEAVY_WIND_LOAD_LB = 40_000


def wind_level(mph: float) -> Level:
    return WIND.level(mph)


def rain_level(inches_per_hour: float) -> Level:
    return RAIN.level(inches_per_hour)


def snow_level(inches_per_hour: float) -> Level:
    return SNOW.level(inches_per_hour)


def wind_level_for_load(mph: float, load_lb: float) -> Level:
    """Wind level after the load rules, which can only raise it."""
    level = wind_level(mph)
    if level == Level.SEVERE and load_lb > HEAVY_WIND_LOAD_LB:
        return Level.NO_TRAVEL
    if level == Level.HIGH and load_lb > VERY_HEAVY_WIND_LOAD_LB:
        return Level.SEVERE
    return level


@dataclass(frozen=True)
class CheckpointRisk:
    level: Level
    reasons: list[str]


def classify_checkpoint(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> CheckpointRisk:
    wind = wind_level_for_load(wind_mph, load_lb)
    rain = rain_level(rain_in_hr)
    snow = snow_level(snow_in_hr)

    reasons = []
    if wind > Level.LOW:
        reason = f"Wind {wind_mph:.0f} mph"
        if wind > wind_level(wind_mph):
            reason += f" with a {load_lb:,.0f} lb load"
        reasons.append(reason)
    if rain > Level.LOW:
        reasons.append(f"Rain {rain_in_hr:.2f} in/hr")
    if snow > Level.LOW:
        reasons.append(f"Snow {snow_in_hr:.1f} in/hr")
    return CheckpointRisk(max(wind, rain, snow), reasons)


def wind_score(mph: float, load_lb: float) -> float:
    return max(WIND.score(mph), float(wind_level_for_load(mph, load_lb)))


def rain_score(inches_per_hour: float) -> float:
    return RAIN.score(inches_per_hour)


def snow_score(inches_per_hour: float) -> float:
    return SNOW.score(inches_per_hour)


def weather_score(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> float:
    """Continuous 0-4 severity for heatmaps; its integer part is the classified level (rain 1.00 and snow 3.0 score 4 but classify Severe)."""
    return max(wind_score(wind_mph, load_lb), rain_score(rain_in_hr), snow_score(snow_in_hr))
