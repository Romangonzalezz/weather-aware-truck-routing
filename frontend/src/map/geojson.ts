import type { Corridor, Route } from "../api/types";

type Position = [number, number];

export interface FeatureCollection<Geometry, Properties> {
  type: "FeatureCollection";
  features: { type: "Feature"; geometry: Geometry; properties: Properties }[];
}
type Line = { type: "LineString"; coordinates: Position[] };
type Point = { type: "Point"; coordinates: Position };

// Recommended route first; blue stands apart from the risk scale, which owns green to purple.
const ROUTE_COLORS = ["#1d4ed8", "#0e7490", "#475569"];

export const routeColorForRank = (rank: number) => ROUTE_COLORS[(rank - 1) % ROUTE_COLORS.length];

export const scoreProperty = (hour: number) => `s${hour}`;

export function routeFeatures(routes: Route[]): FeatureCollection<Line, { id: string; rank: number; recommended: boolean; color: string }> {
  return {
    type: "FeatureCollection",
    features: routes.map((route) => ({
      type: "Feature",
      geometry: { type: "LineString", coordinates: route.geometry },
      properties: {
        id: route.id,
        rank: route.rank,
        recommended: route.recommended,
        color: routeColorForRank(route.rank),
      },
    })),
  };
}

export function checkpointFeatures(route: Route | undefined): FeatureCollection<Point, { index: number; level: string }> {
  return {
    type: "FeatureCollection",
    features: (route?.checkpoints ?? []).map((checkpoint, index) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [checkpoint.lon, checkpoint.lat] },
      properties: { index, level: checkpoint.level },
    })),
  };
}

export function corridorFeatures(corridor: Corridor): FeatureCollection<Point, Record<string, number>> {
  return {
    type: "FeatureCollection",
    features: corridor.cells.map((cell) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [cell.lon, cell.lat] },
      properties: Object.fromEntries(cell.score.map((score, hour) => [scoreProperty(hour), score])),
    })),
  };
}

export function routeBounds(routes: Route[]): [Position, Position] {
  const points = routes.flatMap((route) => route.geometry);
  const lons = points.map(([lon]) => lon);
  const lats = points.map(([, lat]) => lat);
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ];
}
