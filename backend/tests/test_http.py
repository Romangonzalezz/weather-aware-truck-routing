import httpx
import pytest

from routing.clients import http
from routing.errors import UpstreamError

URL = "https://example.test/data"


def flaky(monkeypatch, outcomes):
    """Make client.request return or raise each outcome in turn."""
    calls = []

    def request(method, url, **kwargs):
        calls.append(url)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome, json={"ok": True}, request=httpx.Request(method, url))

    monkeypatch.setattr(http.client, "request", request)
    return calls


def test_a_timeout_is_retried_once(monkeypatch):
    calls = flaky(monkeypatch, [httpx.ReadTimeout("slow"), 200])

    assert http.request_json("Example", "GET", URL) == {"ok": True}
    assert len(calls) == 2


def test_a_server_error_is_retried_once(monkeypatch):
    calls = flaky(monkeypatch, [503, 200])

    assert http.request_json("Example", "GET", URL) == {"ok": True}
    assert len(calls) == 2


def test_two_failures_become_an_upstream_error(monkeypatch):
    calls = flaky(monkeypatch, [httpx.ConnectTimeout("down"), httpx.ConnectTimeout("down")])

    with pytest.raises(UpstreamError, match="Example is unavailable"):
        http.request_json("Example", "GET", URL)
    assert len(calls) == 2


def test_a_client_error_is_not_retried(monkeypatch):
    calls = flaky(monkeypatch, [400, 200])

    with pytest.raises(UpstreamError):
        http.request_json("Example", "GET", URL)
    assert len(calls) == 1
