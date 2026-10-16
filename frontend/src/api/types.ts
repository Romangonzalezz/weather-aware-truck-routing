import type { Level } from "../domain/levels";

export interface Place {
  name: string;
  lat: number;
  lon: number;
}

export type IntervalMiles = 10 | 25 | 50;

export interface PlanRequest {
  origin: string | Place;
  destination: string | Place;
  departure: string;
  load_lb: number;
  interval_miles: IntervalMiles;
}

export interface RouteSummary {
  distance_mi: number;
  duration_h: number;
  arrival: string;
  no_travel_mi: number;
  severe_mi: number;
  high_mi: number;
  avg_risk: number;
  max_level: Level;
}

export interface Checkpoint {
  mile: number;
  lat: number;
  lon: number;
  eta: string;
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
  level: Level;
  reasons: string[];
}

export interface Route {
  id: string;
  rank: number;
  recommended: boolean;
  summary: RouteSummary;
  geometry: [number, number][];
  checkpoints: Checkpoint[];
}

export interface Plan {
  origin: Place;
  destination: Place;
  departure: string;
  load_lb: number;
  interval_miles: IntervalMiles;
  recommended_route_id: string;
  recommendation_reason: string;
  routes: Route[];
}

export interface CorridorRequest {
  routes: [number, number][][];
  departure: string;
  load_lb: number;
}

export interface CorridorCell {
  lat: number;
  lon: number;
  score: number[];
}

export interface Corridor {
  times: string[];
  spacing_deg: number;
  cells: CorridorCell[];
}
