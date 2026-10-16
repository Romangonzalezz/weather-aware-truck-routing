import { describe, expect, it } from "vitest";
import { LEVELS, levelColor, levelFromScore, levelIndex } from "./levels";

describe("levels", () => {
  it("orders the five levels from Low to No Travel", () => {
    expect(LEVELS.map((level) => level.label)).toEqual(["Low", "Moderate", "High", "Severe", "No Travel"]);
  });

  it("gives every level its own color", () => {
    expect(new Set(LEVELS.map((level) => level.color)).size).toBe(5);
    expect(levelColor("Severe")).toBe(LEVELS[3].color);
  });

  it("indexes levels by severity", () => {
    expect(levelIndex("Low")).toBe(0);
    expect(levelIndex("No Travel")).toBe(4);
  });

  it("names the level a heatmap score falls in", () => {
    expect(levelFromScore(0)).toBe("Low");
    expect(levelFromScore(0.99)).toBe("Low");
    expect(levelFromScore(1)).toBe("Moderate");
    expect(levelFromScore(2.5)).toBe("High");
    expect(levelFromScore(3)).toBe("Severe");
    expect(levelFromScore(4)).toBe("No Travel");
  });
});
