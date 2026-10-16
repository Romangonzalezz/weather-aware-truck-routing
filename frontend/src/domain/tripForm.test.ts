import { describe, expect, it } from "vitest";
import type { Plan } from "../api/types";
import { corridorRequestFor, planRequestFrom, type TripForm } from "./tripForm";

const form: TripForm = {
  origin: { text: "Dallas, TX" },
  destination: { text: "Denver, CO, United States", place: { name: "Denver, CO, United States", lat: 39.74, lon: -104.99 } },
  departure: "2026-10-17T08:00",
  loadLb: "38000",
  intervalMiles: 25,
};

describe("planRequestFrom", () => {
  it("sends typed text for the backend to geocode and chosen suggestions as coordinates", () => {
    const result = planRequestFrom(form);

    expect(result).toEqual({
      ok: true,
      request: {
        origin: "Dallas, TX",
        destination: { lat: 39.74, lon: -104.99, name: "Denver, CO, United States" },
        departure: new Date(2026, 9, 17, 8, 0).toISOString(),
        load_lb: 38000,
        interval_miles: 25,
      },
    });
  });

  it("asks for both places", () => {
    expect(planRequestFrom({ ...form, origin: { text: "  " } })).toEqual({ ok: false, error: "Enter an origin." });
    expect(planRequestFrom({ ...form, destination: { text: "" } })).toEqual({ ok: false, error: "Enter a destination." });
  });

  it("asks for a departure time", () => {
    expect(planRequestFrom({ ...form, departure: "" })).toEqual({ ok: false, error: "Choose a departure date and time." });
  });

  it.each(["", "abc", "-5", "80001", "1200.5"])("rejects the load %j", (loadLb) => {
    expect(planRequestFrom({ ...form, loadLb })).toEqual({
      ok: false,
      error: "Load weight must be a whole number of pounds from 0 to 80,000.",
    });
  });

  it("accepts the limits of the load range", () => {
    expect(planRequestFrom({ ...form, loadLb: "0" }).ok).toBe(true);
    expect(planRequestFrom({ ...form, loadLb: "80000" }).ok).toBe(true);
  });
});

describe("corridorRequestFor", () => {
  it("reuses the plan's geometries, departure and load", () => {
    const plan = {
      departure: "2026-10-17T13:00:00Z",
      load_lb: 38000,
      routes: [{ geometry: [[-97, 32], [-105, 39]] }, { geometry: [[-97, 32], [-100, 36], [-105, 39]] }],
    } as Plan;

    expect(corridorRequestFor(plan)).toEqual({
      routes: [
        [[-97, 32], [-105, 39]],
        [[-97, 32], [-100, 36], [-105, 39]],
      ],
      departure: "2026-10-17T13:00:00Z",
      load_lb: 38000,
    });
  });
});
