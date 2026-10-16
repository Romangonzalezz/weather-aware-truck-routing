import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, fetchCorridor, planTrip, searchPlaces } from "./client";

function respondWith(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

const request = {
  origin: "Dallas, TX",
  destination: "Denver, CO",
  departure: "2026-10-17T13:00:00.000Z",
  load_lb: 38000,
  interval_miles: 25 as const,
};

describe("api client", () => {
  it("posts the plan request as JSON and returns the body", async () => {
    const fetchMock = respondWith(200, { routes: [] });

    await expect(planTrip(request)).resolves.toEqual({ routes: [] });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/plan$/);
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual(request);
  });

  it("posts corridor requests to their own endpoint", async () => {
    const fetchMock = respondWith(200, { times: [], spacing_deg: 0.2, cells: [] });

    await fetchCorridor({ routes: [[[-97, 32]]], departure: request.departure, load_lb: 0 });

    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/corridor$/);
  });

  it("encodes the autocomplete query", async () => {
    const fetchMock = respondWith(200, []);

    await searchPlaces("St. Louis, MO");

    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/geocode\?q=St\.%20Louis%2C%20MO$/);
  });

  it("surfaces the API's own error message", async () => {
    respondWith(400, { error: "Could not find a place called Nowhere" });

    await expect(planTrip(request)).rejects.toThrow(new ApiError("Could not find a place called Nowhere"));
  });

  it("explains a 502 even when the body has no message", async () => {
    respondWith(502, {});

    await expect(planTrip(request)).rejects.toThrow(/weather or routing service/i);
  });

  it("explains an unreachable server", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(planTrip(request)).rejects.toThrow(/could not reach the server/i);
  });

  it("lets an aborted request pass through untouched", async () => {
    const abort = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));

    await expect(searchPlaces("Dal")).rejects.toBe(abort);
  });
});
