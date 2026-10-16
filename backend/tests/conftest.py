import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest
from django.core.cache import cache

from routing.clients import http

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


class FakeUpstream:
    """Stands in for the network: each host maps to a handler returning JSON or (status, JSON)."""

    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}
        self.calls: list[tuple[str, str, dict]] = []

    def on(self, host: str, handler) -> None:
        self.handlers[host] = handler if callable(handler) else (lambda method, url, **kw: handler)

    def calls_to(self, host: str) -> list[tuple[str, str, dict]]:
        return [call for call in self.calls if urlparse(call[1]).hostname == host]

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        self.calls.append((method, url, kwargs))
        host = urlparse(url).hostname
        if host not in self.handlers:
            raise AssertionError(f"unexpected network call to {url}")
        result = self.handlers[host](method, url, **kwargs)
        status, body = result if isinstance(result, tuple) else (200, result)
        return httpx.Response(status, json=body, request=httpx.Request(method, url))


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()


@pytest.fixture
def upstream(monkeypatch) -> FakeUpstream:
    fake = FakeUpstream()
    monkeypatch.setattr(http.client, "request", fake.request)
    return fake
