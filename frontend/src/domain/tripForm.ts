import type { CorridorRequest, IntervalMiles, Place, Plan, PlanRequest } from "../api/types";
import { departureToIso } from "./format";

export const MAX_LOAD_LB = 80_000;

export interface PlaceField {
  text: string;
  // Set when the driver picked a suggestion; cleared as soon as the text is edited.
  place?: Place;
}

export interface TripForm {
  origin: PlaceField;
  destination: PlaceField;
  departure: string;
  loadLb: string;
  intervalMiles: IntervalMiles;
}

export type PlanRequestResult = { ok: true; request: PlanRequest } | { ok: false; error: string };

export function planRequestFrom(form: TripForm): PlanRequestResult {
  if (!form.origin.text.trim()) return { ok: false, error: "Enter an origin." };
  if (!form.destination.text.trim()) return { ok: false, error: "Enter a destination." };
  if (!form.departure) return { ok: false, error: "Choose a departure date and time." };
  const loadLb = Number(form.loadLb);
  if (form.loadLb.trim() === "" || !Number.isInteger(loadLb) || loadLb < 0 || loadLb > MAX_LOAD_LB) {
    return { ok: false, error: "Load weight must be a whole number of pounds from 0 to 80,000." };
  }
  return {
    ok: true,
    request: {
      origin: placeInput(form.origin),
      destination: placeInput(form.destination),
      departure: departureToIso(form.departure),
      load_lb: loadLb,
      interval_miles: form.intervalMiles,
    },
  };
}

export function corridorRequestFor(plan: Plan): CorridorRequest {
  return {
    routes: plan.routes.map((route) => route.geometry),
    departure: plan.departure,
    load_lb: plan.load_lb,
  };
}

function placeInput({ text, place }: PlaceField): PlanRequest["origin"] {
  return place ? { lat: place.lat, lon: place.lon } : text.trim();
}
