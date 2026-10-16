import type { ExpressionSpecification, Map as MapLibreMap } from "maplibre-gl";
import { LEVELS } from "../domain/levels";
import { HEATMAP_COLOR, heatmapRadius, heatmapWeight } from "./heatmap";

export const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

const EMPTY = { type: "FeatureCollection", features: [] } as const;
const DEFAULT_SPACING_DEG = 0.2;

export const SOURCES = { corridor: "corridor", routes: "routes", checkpoints: "checkpoints" } as const;
export const LAYERS = { heat: "heat", routeCasing: "route-casing", routeLine: "route-line", checkpoints: "checkpoint-circles" } as const;

/** Adds sources and layers once. Draw order: heatmap under the basemap labels, then routes, then checkpoints. */
export function addTripLayers(map: MapLibreMap): void {
  for (const source of Object.values(SOURCES)) map.addSource(source, { type: "geojson", data: EMPTY });

  const firstLabel = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
  map.addLayer(
    {
      id: LAYERS.heat,
      type: "heatmap",
      source: SOURCES.corridor,
      paint: {
        "heatmap-weight": heatmapWeight(0),
        "heatmap-radius": heatmapRadius(DEFAULT_SPACING_DEG),
        "heatmap-intensity": 0.9,
        "heatmap-color": HEATMAP_COLOR,
        "heatmap-opacity": 0.8,
      },
    },
    firstLabel,
  );

  map.addLayer({
    id: LAYERS.routeCasing,
    type: "line",
    source: SOURCES.routes,
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#ffffff", "line-width": 8, "line-opacity": 0.9 },
  });
  map.addLayer({
    id: LAYERS.routeLine,
    type: "line",
    source: SOURCES.routes,
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": ["get", "color"], "line-width": 5 },
  });

  map.addLayer({
    id: LAYERS.checkpoints,
    type: "circle",
    source: SOURCES.checkpoints,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 4, 10, 8],
      "circle-color": ["match", ["get", "level"], ...LEVELS.flatMap((level) => [level.label, level.color]), "#888888"] as unknown as ExpressionSpecification, // the spread defeats the tuple type
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
    },
  });
}

/** Highlights the selected route: wider, opaque and drawn last; the others are narrower and faded. */
export function styleSelectedRoute(map: MapLibreMap, selectedId: string | undefined): void {
  const isSelected: ExpressionSpecification = ["==", ["get", "id"], selectedId ?? ""];
  const width = (selected: number, recommended: number, other: number): ExpressionSpecification => [
    "case",
    isSelected,
    selected,
    ["get", "recommended"],
    recommended,
    other,
  ];
  map.setPaintProperty(LAYERS.routeLine, "line-width", width(8, 6, 4));
  map.setPaintProperty(LAYERS.routeLine, "line-opacity", ["case", isSelected, 1, 0.5]);
  map.setPaintProperty(LAYERS.routeCasing, "line-width", width(12, 10, 7));
  map.setPaintProperty(LAYERS.routeCasing, "line-opacity", ["case", isSelected, 0.95, 0.5]);
  for (const layer of [LAYERS.routeLine, LAYERS.routeCasing]) {
    map.setLayoutProperty(layer, "line-sort-key", ["case", isSelected, 1, 0]);
  }
}
