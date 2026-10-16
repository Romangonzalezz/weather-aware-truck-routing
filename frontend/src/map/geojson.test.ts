import { describe, expect, it } from "vitest";
import type { Corridor, Route } from "../api/types";
import { checkpointFeatures, corridorFeatures, routeBounds, routeFeatures, scoreProperty } from "./geojson";

function route(overrides: Partial<Route> = {}): Route {
  return {
    id: "r1",
    rank: 1,
    recommended: true,
    summary: {
      distance_mi: 100,
      duration_h: 2,
      arrival: "2026-10-17T15:00:00Z",
      no_travel_mi: 0,
      severe_mi: 0,
      high_mi: 0,
      avg_risk: 0,
      max_level: "Low",
    },
    geometry: [
      [-97, 32],
      [-100, 35],
      [-105, 39],
    ],
    checkpoints: [
      { mile: 25, lat: 33, lon: -98, eta: "2026-10-17T13:30:00Z", wind_mph: 10, rain_in_hr: 0, snow_in_hr: 0, level: "Low", reasons: [] },
      { mile: 50, lat: 34, lon: -99, eta: "2026-10-17T14:00:00Z", wind_mph: 40, rain_in_hr: 0, snow_in_hr: 0, level: "High", reasons: ["Wind 40 mph"] },
    ],
    ...overrides,
  };
}

describe("routeFeatures", () => {
  it("makes one line per route carrying its id, rank and color", () => {
    const collection = routeFeatures([route(), route({ id: "r2", rank: 2, recommended: false })]);

    expect(collection.features).toHaveLength(2);
    const [first, second] = collection.features;
    expect(first.geometry).toEqual({ type: "LineString", coordinates: route().geometry });
    expect(first.properties).toMatchObject({ id: "r1", rank: 1, recommended: true });
    expect(second.properties).toMatchObject({ id: "r2", recommended: false });
    expect(first.properties.color).not.toBe(second.properties.color);
  });
});

describe("checkpointFeatures", () => {
  it("makes lon/lat points with the level and the checkpoint's position in its route", () => {
    const { features } = checkpointFeatures(route());

    expect(features.map((feature) => feature.geometry.coordinates)).toEqual([
      [-98, 33],
      [-99, 34],
    ]);
    expect(features.map((feature) => feature.properties)).toEqual([
      { index: 0, level: "Low" },
      { index: 1, level: "High" },
    ]);
  });

  it("is empty when no route is selected", () => {
    expect(checkpointFeatures(undefined).features).toEqual([]);
  });
});

describe("corridorFeatures", () => {
  const corridor: Corridor = {
    times: ["2026-10-17T13:00:00Z", "2026-10-17T14:00:00Z", "2026-10-17T15:00:00Z"],
    spacing_deg: 0.2,
    cells: [
      { lat: 33, lon: -98, score: [0.5, 1.5, 2.5] },
      { lat: 34, lon: -99, score: [0, 0, 4] },
    ],
  };

  it("stores every hour's score on its cell so the data is loaded once", () => {
    const { features } = corridorFeatures(corridor);

    expect(features[0].geometry.coordinates).toEqual([-98, 33]);
    expect(features[0].properties).toEqual({ s0: 0.5, s1: 1.5, s2: 2.5 });
    expect(features[1].properties).toEqual({ s0: 0, s1: 0, s2: 4 });
  });

  it("names the property for an hour", () => {
    expect(scoreProperty(0)).toBe("s0");
    expect(scoreProperty(48)).toBe("s48");
  });
});

describe("routeBounds", () => {
  it("spans every route as [[west, south], [east, north]]", () => {
    const other = route({ geometry: [[-90, 30], [-110, 41]] });

    expect(routeBounds([route(), other])).toEqual([
      [-110, 30],
      [-90, 41],
    ]);
  });
});
