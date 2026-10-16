import { describe, expect, it } from "vitest";
import {
  departureToIso,
  formatConditions,
  formatDuration,
  formatMiles,
  formatTime,
  formatWindowHour,
  nextFullHour,
  toDateTimeLocalValue,
} from "./format";

describe("formatDuration", () => {
  it("shows hours and minutes", () => {
    expect(formatDuration(13.07)).toBe("13 h 4 min");
    expect(formatDuration(2)).toBe("2 h");
  });

  it("drops the hours under one hour and carries a rounded-up minute", () => {
    expect(formatDuration(0.5)).toBe("30 min");
    expect(formatDuration(1.999)).toBe("2 h");
  });
});

describe("formatMiles", () => {
  it("rounds to whole miles with a thousands separator", () => {
    expect(formatMiles(808.3)).toBe("808 mi");
    expect(formatMiles(1234.5)).toBe("1,235 mi");
    expect(formatMiles(0)).toBe("0 mi");
  });
});

describe("times", () => {
  it("formats an ISO instant in the requested zone", () => {
    expect(formatTime("2026-10-17T13:00:00Z", "UTC")).toBe("Sat, Oct 17, 1:00 PM");
    expect(formatTime("2026-10-17T13:00:00Z", "America/Denver")).toBe("Sat, Oct 17, 7:00 AM");
  });

  it("labels slider hours with the day and hour", () => {
    expect(formatWindowHour("2026-10-18T03:00:00Z", "UTC")).toBe("Sun 3:00 AM");
  });
});

describe("departure input", () => {
  it("defaults to the next full hour, never the current one", () => {
    expect(nextFullHour(new Date(2026, 9, 16, 14, 20)).getTime()).toBe(new Date(2026, 9, 16, 15, 0).getTime());
    expect(nextFullHour(new Date(2026, 9, 16, 14, 0)).getTime()).toBe(new Date(2026, 9, 16, 15, 0).getTime());
  });

  it("rolls over midnight", () => {
    expect(nextFullHour(new Date(2026, 9, 16, 23, 30)).getTime()).toBe(new Date(2026, 9, 17, 0, 0).getTime());
  });

  it("writes a datetime-local value in local time", () => {
    expect(toDateTimeLocalValue(new Date(2026, 9, 7, 8, 5))).toBe("2026-10-07T08:05");
  });

  it("sends the local wall-clock time as an absolute instant", () => {
    const local = new Date(2026, 9, 17, 8, 0);
    expect(departureToIso("2026-10-17T08:00")).toBe(local.toISOString());
  });
});

describe("formatConditions", () => {
  it("lists wind, rain and snow with their units", () => {
    expect(formatConditions({ wind_mph: 31.4, rain_in_hr: 0.12, snow_in_hr: 0 })).toBe(
      "Wind 31 mph, rain 0.12 in/hr, snow 0 in/hr",
    );
  });

  it("keeps two decimals only where they matter", () => {
    expect(formatConditions({ wind_mph: 8, rain_in_hr: 0, snow_in_hr: 1.5 })).toBe("Wind 8 mph, rain 0 in/hr, snow 1.5 in/hr");
  });
});
