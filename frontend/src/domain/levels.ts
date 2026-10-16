export type Level = "Low" | "Moderate" | "High" | "Severe" | "No Travel";

// One scale for every place a risk level is drawn: map circles, badges, legend and heatmap.
export const LEVELS: readonly { label: Level; color: string }[] = [
  { label: "Low", color: "#2e9d5b" },
  { label: "Moderate", color: "#f2c230" },
  { label: "High", color: "#f08a24" },
  { label: "Severe", color: "#d93a2e" },
  { label: "No Travel", color: "#6a2c91" },
];

export function levelIndex(level: Level): number {
  return LEVELS.findIndex((entry) => entry.label === level);
}

export function levelColor(level: Level): string {
  return LEVELS[levelIndex(level)].color;
}

// Heatmap scores run 0-4 and a score of n starts level n (see the backend corridor score).
export function levelFromScore(score: number): Level {
  return LEVELS[Math.min(Math.floor(score), LEVELS.length - 1)].label;
}
