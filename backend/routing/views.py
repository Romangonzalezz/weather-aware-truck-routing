from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .clients.geocode import search_places
from .corridor import corridor_forecast
from .planner import plan_trip
from .serializers import CorridorRequestSerializer, PlanRequestSerializer

SUGGESTION_LIMIT = 5


@api_view(["POST"])
def plan(request: Request) -> Response:
    serializer = PlanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(plan_trip(**serializer.validated_data, now=timezone.now()))


@api_view(["GET"])
def geocode(request: Request) -> Response:
    query = request.query_params.get("q", "").strip()
    if len(query) < 2:
        return Response([])
    places = search_places(query, limit=SUGGESTION_LIMIT)
    return Response([{"name": p.name, "lat": p.lat, "lon": p.lon} for p in places])


@api_view(["POST"])
def corridor(request: Request) -> Response:
    serializer = CorridorRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(corridor_forecast(**serializer.validated_data, now=timezone.now()))
