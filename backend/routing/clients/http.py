import hashlib
import json
from typing import Any

import httpx
from django.core.cache import cache

from ..errors import UpstreamError

USER_AGENT = "truck-routing-demo/1.0"
TIMEOUT = httpx.Timeout(20.0, connect=5.0)
ATTEMPTS = 2

client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)


def _is_transient(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def request_json(service: str, method: str, url: str, **kwargs: Any) -> Any:
    """Call an upstream API and return its JSON, cached by request for the cache timeout.

    Timeouts and 5xx answers are retried once; any remaining failure becomes an UpstreamError
    naming the service.
    """
    key = "upstream:" + hashlib.sha256(json.dumps([method, url, kwargs], sort_keys=True, default=str).encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached
    for attempt in range(ATTEMPTS):
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            body = response.json()
            break
        except (httpx.HTTPError, ValueError) as exc:
            if attempt + 1 < ATTEMPTS and isinstance(exc, httpx.HTTPError) and _is_transient(exc):
                continue
            raise UpstreamError(f"{service} is unavailable") from exc
    cache.set(key, body)
    return body
