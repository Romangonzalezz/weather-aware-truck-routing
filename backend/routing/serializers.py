from rest_framework import serializers

MAX_LOAD_LB = 80_000  # the US legal gross vehicle weight
INTERVAL_CHOICES = (10, 25, 50)
MAX_FORECAST_HOURS = 49


class PlaceField(serializers.Field):
    """Free text to geocode, or {"lat": ..., "lon": ...}; coordinates are range-checked when resolved."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.strip():
            return data.strip()
        if isinstance(data, dict):
            return data
        raise serializers.ValidationError('Enter a place name or {"lat": ..., "lon": ...}')

    def to_representation(self, value):
        return value


class PlanRequestSerializer(serializers.Serializer):
    origin = PlaceField()
    destination = PlaceField()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=0, max_value=MAX_LOAD_LB)
    interval_miles = serializers.ChoiceField(choices=INTERVAL_CHOICES, default=25)


class CorridorRequestSerializer(serializers.Serializer):
    bbox = serializers.ListField(child=serializers.FloatField(), min_length=4, max_length=4)
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=0, max_value=MAX_LOAD_LB, default=0)
    hours = serializers.IntegerField(min_value=1, max_value=MAX_FORECAST_HOURS, default=MAX_FORECAST_HOURS)

    def validate_bbox(self, bbox: list[float]) -> list[float]:
        min_lon, min_lat, max_lon, max_lat = bbox
        if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
            raise serializers.ValidationError("Expected [minLon, minLat, maxLon, maxLat] within world bounds")
        return bbox
