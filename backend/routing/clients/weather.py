from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from ..errors import InvalidRequest, UpstreamError
from ..sampling import LatLon
from .http import request_json

OPEN_METEO_HOST = "api.open-meteo.com"

BATCH_SIZE = 100
PARALLEL_BATCHES = 4
# Open-Meteo serves today plus the next 15 days.
FORECAST_DAYS = 16
HOURLY_VARIABLES = "wind_speed_10m,rain,showers,snowfall"
# A browser's "now" is already a little in the past by the time the request arrives.
PAST_DEPARTURE_GRACE = timedelta(hours=1)


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class HourlySeries:
    start: datetime
    samples: list[Weather]

    def at(self, when: datetime) -> Weather:
        """The sample for the hour nearest to when."""
        index = round((when - self.start).total_seconds() / 3600)
        if not 0 <= index < len(self.samples):
            raise InvalidRequest("The trip reaches beyond the available weather forecast")
        return self.samples[index]


def check_departure(departure: datetime, now: datetime) -> None:
    if departure < now - PAST_DEPARTURE_GRACE:
        raise InvalidRequest("Departure is in the past")
    check_forecast_window(departure, now)


def check_forecast_window(last_time: datetime, now: datetime) -> None:
    last_day = now.astimezone(timezone.utc).date() + timedelta(days=FORECAST_DAYS - 1)
    if last_time.astimezone(timezone.utc).date() > last_day:
        raise InvalidRequest(
            f"Weather forecasts only cover the next {FORECAST_DAYS} days; "
            "the trip would reach a checkpoint after that. Choose an earlier departure."
        )


def fetch_hourly(points: list[LatLon], first: datetime, last: datetime) -> list[HourlySeries]:
    """Hourly weather for every point from first's UTC day through last's UTC day."""
    first_day = first.astimezone(timezone.utc).date()
    last_day = last.astimezone(timezone.utc).date()
    batches = [points[i : i + BATCH_SIZE] for i in range(0, len(points), BATCH_SIZE)]
    with ThreadPoolExecutor(max_workers=PARALLEL_BATCHES) as pool:
        results = pool.map(lambda batch: _fetch_batch(batch, first_day, last_day), batches)
        return [series for batch in results for series in batch]


def _fetch_batch(points: list[LatLon], first_day: date, last_day: date) -> list[HourlySeries]:
    # Open-Meteo's grid is coarser than 0.01 degrees, so rounding only shortens the URL.
    data = request_json(
        "Open-Meteo",
        "GET",
        f"https://{OPEN_METEO_HOST}/v1/forecast",
        params={
            "latitude": ",".join(str(round(lat, 2)) for lat, _ in points),
            "longitude": ",".join(str(round(lon, 2)) for _, lon in points),
            "hourly": HOURLY_VARIABLES,
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "timezone": "UTC",
        },
    )
    locations = data if isinstance(data, list) else [data]
    if len(locations) != len(points):
        raise UpstreamError("Open-Meteo returned an unexpected number of locations")
    return [_series(location["hourly"]) for location in locations]


def _series(hourly: dict) -> HourlySeries:
    def values(name: str) -> list[float]:
        return [value or 0.0 for value in hourly[name]]

    start = datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=timezone.utc)
    samples = [
        Weather(wind, rain + showers, snow)
        for wind, rain, showers, snow in zip(
            values("wind_speed_10m"), values("rain"), values("showers"), values("snowfall")
        )
    ]
    return HourlySeries(start, samples)
