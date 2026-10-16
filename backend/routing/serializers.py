from rest_framework import serializers

MAX_LOAD_LB = 80_000  # the US legal gross vehicle weight
INTERVAL_CHOICES = (10, 25, 50)
MAX_FORECAST_HOURS = 49
MAX_ROUTES = 5
MAX_ROUTE_POINTS = 5_000


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


class RouteGeometryField(serializers.ListField):
    """A route as [[lon, lat], ...], the shape of the plan response; becomes (lat, lon) tuples."""

    child = serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2)

    def __init__(self, **kwargs):
        super().__init__(min_length=2, max_length=MAX_ROUTE_POINTS, **kwargs)

    def to_internal_value(self, data):
        pairs = super().to_internal_value(data)
        if not all(-180 <= lon <= 180 and -90 <= lat <= 90 for lon, lat in pairs):
            raise serializers.ValidationError("Coordinates must be [lon, lat] within world bounds")
        return [(lat, lon) for lon, lat in pairs]


class CorridorRequestSerializer(serializers.Serializer):
    routes = serializers.ListField(child=RouteGeometryField(), min_length=1, max_length=MAX_ROUTES)
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=0, max_value=MAX_LOAD_LB, default=0)
    hours = serializers.IntegerField(min_value=1, max_value=MAX_FORECAST_HOURS, default=MAX_FORECAST_HOURS)
