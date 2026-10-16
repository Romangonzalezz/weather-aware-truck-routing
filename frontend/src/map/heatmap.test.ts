import { describe, expect, it } from "vitest";
import { LEVELS } from "../domain/levels";
import { HEATMAP_COLOR, heatmapRadius, heatmapWeight } from "./heatmap";

describe("heatmapWeight", () => {
  it("reads the chosen hour's score and scales it to 0-1", () => {
    expect(heatmapWeight(5)).toEqual(["/", ["to-number", ["get", "s5"], 0], 4]);
  });
});

describe("heatmapRadius", () => {
  it("doubles with every zoom level so cells keep blending as the map zooms", () => {
    const [kind, , input, firstZoom, firstRadius, lastZoom, lastRadius] = heatmapRadius(0.2) as [
      string, unknown, unknown, number, number, number, number,
    ];

    expect(kind).toBe("interpolate");
    expect(input).toEqual(["zoom"]);
    expect(lastRadius / firstRadius).toBeCloseTo(2 ** (lastZoom - firstZoom));
  });

  it("grows with the grid spacing", () => {
    const radiusAt = (spacing: number) => (heatmapRadius(spacing) as unknown[])[4] as number;

    expect(radiusAt(0.4)).toBeCloseTo(radiusAt(0.2) * 2);
  });
});

describe("HEATMAP_COLOR", () => {
  const stops = HEATMAP_COLOR.slice(3) as (number | string)[];

  it("starts transparent so calm weather shows only the basemap", () => {
    expect(stops[0]).toBe(0);
    expect(stops[1]).toMatch(/^rgba\(.*, 0\)$/);
  });

  it("reaches each level's color where the score reaches that level", () => {
    LEVELS.slice(1).forEach((level, offset) => {
      const at = stops.indexOf((offset + 1) / 4);
      expect(stops[at + 1]).toBe(level.color);
    });
  });
});
