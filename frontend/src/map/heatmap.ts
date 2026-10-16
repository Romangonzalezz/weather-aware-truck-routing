import type { ExpressionSpecification } from "maplibre-gl";
import { LEVELS } from "../domain/levels";
import { scoreProperty } from "./geojson";

const MAX_SCORE = LEVELS.length - 1;
const WORLD_PIXELS_AT_ZOOM_0 = 512;
// A kernel's visible spread is a third of its radius, so two spacings keeps neighbouring cells blending.
const RADIUS_IN_SPACINGS = 2;
// Past this zoom the radius stops growing; cells blur but the layer stays cheap to draw.
const LAST_RADIUS_ZOOM = 9;

export function heatmapWeight(hour: number): ExpressionSpecification {
  return ["/", ["to-number", ["get", scoreProperty(hour)], 0], MAX_SCORE];
}

export function heatmapRadius(spacingDeg: number): ExpressionSpecification {
  const pixelsAtZoom0 = (RADIUS_IN_SPACINGS * spacingDeg * WORLD_PIXELS_AT_ZOOM_0) / 360;
  return ["interpolate", ["exponential", 2], ["zoom"], 0, pixelsAtZoom0, LAST_RADIUS_ZOOM, pixelsAtZoom0 * 2 ** LAST_RADIUS_ZOOM];
}

const CLEAR = "rgba(46, 157, 91, 0)";
const CALM_DENSITY = 0.12;

// Density 0-1 is score / 4, so each level's color lands where its score range begins.
export const HEATMAP_COLOR: ExpressionSpecification = [
  "interpolate",
  ["linear"],
  ["heatmap-density"],
  0,
  CLEAR,
  // Calm weather scores about 0.3 of 4; staying clear up to here keeps it from tinting the basemap.
  CALM_DENSITY,
  CLEAR,
  ...LEVELS.slice(1).flatMap((level, offset) => [(offset + 1) / MAX_SCORE, level.color]),
];
