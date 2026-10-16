from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float
