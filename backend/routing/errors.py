from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class InvalidRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid request"


class UpstreamError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "An upstream service failed"


def _first_message(detail) -> str:
    if isinstance(detail, dict):
        field, value = next(iter(detail.items()))
        message = _first_message(value)
        return message if field in ("detail", "non_field_errors") else f"{field}: {message}"
    if isinstance(detail, list):
        return _first_message(detail[0])
    return str(detail)


def handle_exception(exc, context):
    """Render every API error as {"error": "<message>"}."""
    response = exception_handler(exc, context)
    if response is not None:
        detail = exc.detail if isinstance(exc, (APIException, ValidationError)) else response.data
        response.data = {"error": _first_message(detail)}
    return response
